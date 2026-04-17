from random import random
from math import pi, atan2, degrees
from tkinter import PhotoImage, Canvas
from enum import Enum, auto as enum_next

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.AnimatedSprite import AnimatedSprite
from assets.utils.Vectors import Vector2

from typing import List, TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Sprites.player.Player import Player
    from game import Game

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False


class ZombiePriority(Enum):
    Moving = enum_next()
    Attacking = enum_next()
    Idle = enum_next()


def _get_scaled_frames(file_pattern: str, scale_divisor: int = 2) -> List[PhotoImage]:
    frames = AnimatedSprite.getFramesWithFilePattern(file_pattern)
    if scale_divisor <= 1:
        return frames
    return [frame.subsample(scale_divisor, scale_divisor) for frame in frames]


def _get_scaled_pil_frames(file_pattern: str, scale_divisor: int = 2):
    if not PIL_AVAILABLE:
        return []

    frames = []
    i = 0
    while True:
        file = file_pattern.format(i)
        try:
            img = Image.open(file).convert("RGBA")
        except Exception:
            break

        if scale_divisor > 1:
            w = max(1, img.width // scale_divisor)
            h = max(1, img.height // scale_divisor)
            img = img.resize((w, h), Image.Resampling.BILINEAR)
        frames.append(img)
        i += 1

    return frames


class Zombie(AnimatedSprite):
    SCALE_DIVISOR: int = 2
    ATTACK_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-attack_{0}.png"
    IDLE_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-idle_{0}.png"
    MOVE_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-move_{0}.png"

    FRAMES_ATTACK: List[PhotoImage] = _get_scaled_frames(
        ATTACK_PATTERN,
        SCALE_DIVISOR
    )
    FRAMES_ATTACK_CRITICAL_POINT = 0.55  # the point in the animation when damage is dealt

    FRAMES_IDLE: List[PhotoImage] = _get_scaled_frames(
        IDLE_PATTERN,
        SCALE_DIVISOR
    )
    FRAMES_MOVE: List[PhotoImage] = _get_scaled_frames(
        MOVE_PATTERN,
        SCALE_DIVISOR
    )

    _DIRECTIONAL_ANGLES = (-180, -135, -90, -45, 0, 45, 90, 135)
    _BASE_SPRITE_OFFSET_DEG = 0
    _DIRECTIONAL_CACHE = {}

    MAX_SPEED: float = 50
    COLLIDER_WIDTH: float = 40

    def __init__(
        self,
        canvas: Canvas,
        target_player: "Player",
        game: Optional["Game"] = None,
        spawn_position: Optional[Vector2] = None
    ):
        super().__init__(canvas, self.__class__.FRAMES_MOVE)
        self.target_player = target_player
        self.game = game

        x_jitter = GAME_WIDTH * 0.06
        min_x = self.halfImageSize.x
        max_x = GAME_WIDTH - self.halfImageSize.x
        spawn_x = self.target_player.position.x + (random() * 2 - 1) * x_jitter
        spawn_x = min(max_x, max(min_x, spawn_x))
        self.position = Vector2(spawn_x, self.halfImageSize.y * 0.7)
        if spawn_position is not None:
            self.position = spawn_position
        self.rotation = -pi / 2
        self.sqrDistToPlayer = GAME_WIDTH
        self.sqrDistToPlayerLimit = (self.__class__.COLLIDER_WIDTH + self.target_player.__class__.COLLIDER_WIDTH) ** 2
        self.speed = self.__class__.MAX_SPEED  # pixels per second
        self.cycleLength = 2

        self._directional_frames = self.__class__._get_directional_frames()
        self._last_facing_angle = None

        self.__priority = ZombiePriority.Moving
        self.priority: ZombiePriority = ZombiePriority.Moving

        # has the zombie attacked the player in the current animation cycle (only for ZombiePriority.Attacking)
        self.hasAttacked = False
        # the zombie's HP
        self.hearts = 10
        self.maxHearts = self.hearts
        self._last_drawn_hearts = self.hearts  # Cache for optimization
        self._last_drawn_max_hearts = self.maxHearts

        self.healthBarWidth = max(28, self.halfImageSize.x * 1.8)
        self.healthBarHeight = 6
        self.healthBarOffset = 12
        self.canvas_health_bg = None
        self.canvas_health_fg = None

    @property
    def priority(self) -> ZombiePriority:
        return self.__priority

    @priority.setter
    def priority(self, new: ZombiePriority):
        if self.__priority != new:
            self.cycleTime = 0  # restart animation time if we change it
        self.__priority = new
        self._apply_current_frames(force=True)

    @classmethod
    def _get_directional_frames(cls):
        if not PIL_AVAILABLE:
            return None

        cached = cls._DIRECTIONAL_CACHE.get(cls)
        if cached is not None:
            return cached

        move_base = _get_scaled_pil_frames(cls.MOVE_PATTERN, cls.SCALE_DIVISOR)
        idle_base = _get_scaled_pil_frames(cls.IDLE_PATTERN, cls.SCALE_DIVISOR)
        attack_base = _get_scaled_pil_frames(cls.ATTACK_PATTERN, cls.SCALE_DIVISOR)
        if not move_base or not idle_base or not attack_base:
            cls._DIRECTIONAL_CACHE[cls] = None
            return None

        def _build_rotated(base_frames):
            out = {}
            for angle in cls._DIRECTIONAL_ANGLES:
                out[angle] = [
                    ImageTk.PhotoImage(frame.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False))
                    for frame in base_frames
                ]
            return out

        directional = {
            ZombiePriority.Moving: _build_rotated(move_base),
            ZombiePriority.Idle: _build_rotated(idle_base),
            ZombiePriority.Attacking: _build_rotated(attack_base),
        }
        cls._DIRECTIONAL_CACHE[cls] = directional
        return directional

    def _get_facing_angle(self) -> int:
        if self.forwards.sqrMagnitude == 0:
            return 0

        raw = degrees(atan2(self.forwards.x, self.forwards.y)) + self.__class__._BASE_SPRITE_OFFSET_DEG
        angle = int(round(raw / 45.0) * 45)
        if angle > 180:
            angle -= 360
        if angle <= -180:
            angle += 360
        if angle == 180:
            angle = -180
        if angle not in self.__class__._DIRECTIONAL_ANGLES:
            angle = 0
        return angle

    def _apply_current_frames(self, force: bool = False):
        if not hasattr(self, "_directional_frames"):
            return

        if self._directional_frames is None:
            if self.priority == ZombiePriority.Moving:
                self.frames = self.__class__.FRAMES_MOVE
            elif self.priority == ZombiePriority.Attacking:
                self.frames = self.__class__.FRAMES_ATTACK
            else:
                self.frames = self.__class__.FRAMES_IDLE
            return

        angle = self._get_facing_angle()
        if not force and self._last_facing_angle == angle:
            return

        frames_map = self._directional_frames.get(self.priority)
        if frames_map is None:
            return
        selected = frames_map.get(angle)
        if selected is None:
            return

        self.frames = selected
        self._last_facing_angle = angle

    def update(self, dt):
        super(Zombie, self).update(dt)

        if self.game is not None and self.game._hasActiveBarricade():
            stop_y = self.game.getBarricadeY() - self.halfImageSize.y * 0.45
            if self.position.y >= stop_y:
                self.position = Vector2(self.position.x, stop_y)
                self.priority = ZombiePriority.Attacking
                if not self.hasAttacked and self.cycleTime >= self.cycleLength * self.__class__.FRAMES_ATTACK_CRITICAL_POINT:
                    self.game.damageBarricade(self.get_barricade_damage())
                    self.hasAttacked = True
                return

        displacement = self.target_player.position - self.position

        # point towards player
        self.forwards = displacement
        self._apply_current_frames()

        # if player is close enough, switch to attacking
        self.sqrDistToPlayer: float = displacement.sqrMagnitude
        if self.sqrDistToPlayer < self.sqrDistToPlayerLimit:
            self.priority = ZombiePriority.Attacking

        if self.priority == ZombiePriority.Moving:
            self.position += self.forwards * (self.speed * dt)
        elif self.priority == ZombiePriority.Attacking:
            if not self.hasAttacked and self.sqrDistToPlayer < self.sqrDistToPlayerLimit \
                    and self.cycleTime >= self.cycleLength * self.__class__.FRAMES_ATTACK_CRITICAL_POINT:
                self.target_player.attacked()
                self.hasAttacked = True

    def get_barricade_damage(self) -> int:
        return 1

    def cycleEnded(self):
        if self.priority != ZombiePriority.Attacking:
            return

        self.hasAttacked = False

        # check if player has moved away since attack ended,
        # stop attacking if so
        if self.sqrDistToPlayer > self.sqrDistToPlayerLimit:
            self.priority = ZombiePriority.Moving

    def shot(self) -> bool:
        """
        :returns: If the zombie has died.
        """
        self.hearts -= 1
        if self.hearts <= 0:
            self.destroyed = True
            return True
        return False

    def _getHealthBarRect(self):
        top = self.position.y - self.halfImageSize.y - self.healthBarOffset
        left = self.position.x - self.healthBarWidth / 2
        right = left + self.healthBarWidth
        bottom = top + self.healthBarHeight
        return left, top, right, bottom

    def _updateHealthBar(self):
        if self.canvas_health_bg is None or self.canvas_health_fg is None:
            return

        # Always update bar position so it follows the zombie smoothly.
        left, top, right, bottom = self._getHealthBarRect()
        self.canvas.coords(self.canvas_health_bg, left, top, right, bottom)

        ratio = max(0.0, min(1.0, self.hearts / self.maxHearts))
        inner_left = left + 1
        inner_top = top + 1
        inner_right = inner_left + max(0.0, (self.healthBarWidth - 2) * ratio)
        inner_bottom = bottom - 1
        self.canvas.coords(self.canvas_health_fg, inner_left, inner_top, inner_right, inner_bottom)

        # Color only needs update when health values change.
        if self.hearts != self._last_drawn_hearts or self.maxHearts != self._last_drawn_max_hearts:
            self._last_drawn_hearts = self.hearts
            self._last_drawn_max_hearts = self.maxHearts

            if ratio > 0.6:
                color = "#4caf50"
            elif ratio > 0.3:
                color = "#ffb300"
            else:
                color = "#e53935"
            self.canvas.itemconfig(self.canvas_health_fg, fill=color)

        self.canvas.tag_raise(self.canvas_health_bg)
        self.canvas.tag_raise(self.canvas_health_fg)

    def first_draw(self):
        if self.hidden:
            return
        super(Zombie, self).first_draw()
        left, top, right, bottom = self._getHealthBarRect()
        self.canvas_health_bg = self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#2f2f2f",
            outline="#000000",
            width=1
        )
        self.canvas_health_fg = self.canvas.create_rectangle(
            left + 1,
            top + 1,
            right - 1,
            bottom - 1,
            fill="#4caf50",
            outline=""
        )
        self._updateHealthBar()

    def redraw(self):
        super(Zombie, self).redraw()
        self._updateHealthBar()

    def undraw(self):
        if self.canvas_health_bg is not None:
            self.canvas.delete(self.canvas_health_bg)
            self.canvas_health_bg = None
        if self.canvas_health_fg is not None:
            self.canvas.delete(self.canvas_health_fg)
            self.canvas_health_fg = None
        super(Zombie, self).undraw()


class BossZombie(Zombie):
    SCALE_DIVISOR: int = 1
    ATTACK_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-attack_{0}.png"
    IDLE_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-idle_{0}.png"
    MOVE_PATTERN: str = "images/Top_Down_Zombie/portrait/skeleton-move_{0}.png"
    FRAMES_ATTACK: List[PhotoImage] = _get_scaled_frames(
        ATTACK_PATTERN,
        SCALE_DIVISOR
    )
    FRAMES_IDLE: List[PhotoImage] = _get_scaled_frames(
        IDLE_PATTERN,
        SCALE_DIVISOR
    )
    FRAMES_MOVE: List[PhotoImage] = _get_scaled_frames(
        MOVE_PATTERN,
        SCALE_DIVISOR
    )
    MAX_SPEED: float = 40
    COLLIDER_WIDTH: float = 65
    DASH_DURATION: float = 1.0
    DASH_SPEED_MULTIPLIER: float = 3.2
    REGEN_PER_SECOND: float = 2.0
    HELL_SKILL_COOLDOWN: float = 6.2
    HELL_SKILL_CAST_DELAY: float = 0.55

    def __init__(
        self,
        canvas: Canvas,
        target_player: "Player",
        game: Optional["Game"] = None,
        hearts: int = 42,
        reinforcement_count: int = 4,
        can_regenerate: bool = False,
        has_hell_skill: bool = False,
        spawn_position: Optional[Vector2] = None
    ):
        super(BossZombie, self).__init__(canvas, target_player, game=game, spawn_position=spawn_position)
        self.hearts = hearts
        self.maxHearts = hearts
        self.reinforcementCount = reinforcement_count
        self.canRegenerate = can_regenerate
        self.hasHellSkill = has_hell_skill

        self.summonedReinforcements = False
        self.usedDash = False
        self.dashTimer = 0.0
        self.dashHitRegistered = False
        self.hellSkillTimer = self.__class__.HELL_SKILL_COOLDOWN
        self.hellSkillPending = False
        self.hellSkillCastTimer = 0.0
        self.hellWarningShown = False

        self.healthBarWidth = max(80, self.halfImageSize.x * 1.6)
        self.healthBarHeight = 10
        self.healthBarOffset = 20

    def _applyRegeneration(self, dt: float):
        if not self.canRegenerate:
            return
        if self.hearts <= self.maxHearts * 0.5 and self.hearts > 0:
            self.hearts = min(self.maxHearts, self.hearts + self.__class__.REGEN_PER_SECOND * dt)

    def _triggerDash(self):
        self.usedDash = True
        self.dashTimer = self.__class__.DASH_DURATION
        self.dashHitRegistered = False
        self.priority = ZombiePriority.Moving

    def _maybeUseSkills(self):
        if self.game is None:
            return
        if not self.summonedReinforcements and self.hearts <= self.maxHearts * 0.5:
            self.summonedReinforcements = True
            self.game.spawnReinforcements(self.reinforcementCount)
        if not self.usedDash and self.hearts <= self.maxHearts * 0.7:
            self._triggerDash()

    def _maybeCastHellSkill(self, dt: float):
        if not self.hasHellSkill or self.game is None:
            return
        if self.hearts > self.maxHearts * 0.65:
            return

        if self.hellSkillPending:
            if not self.hellWarningShown:
                self.game.triggerHellWarning()
                self.hellWarningShown = True

            self.hellSkillCastTimer -= dt
            if self.hellSkillCastTimer > 0:
                return

            self.hellSkillPending = False
            self.hellWarningShown = False
            self.hellSkillTimer = self.__class__.HELL_SKILL_COOLDOWN

            self.game.spawnReinforcements(2)

            player_distance_sqr = (self.target_player.position - self.position).sqrMagnitude
            if player_distance_sqr < (GAME_WIDTH * 0.35) ** 2:
                self.target_player.attacked()

            if self.dashTimer <= 0 and not self.usedDash:
                self._triggerDash()
            return

        self.hellSkillTimer -= dt
        if self.hellSkillTimer > 0:
            return
        self.hellSkillPending = True
        self.hellSkillCastTimer = self.__class__.HELL_SKILL_CAST_DELAY
        self.hellWarningShown = False

    def update(self, dt):
        self._applyRegeneration(dt)
        self._maybeUseSkills()
        self._maybeCastHellSkill(dt)
        if self.dashTimer > 0:
            self.dashTimer -= dt
            displacement = self.target_player.position - self.position
            self.forwards = displacement
            self.position += self.forwards * (self.speed * self.__class__.DASH_SPEED_MULTIPLIER * dt)
            self.frames = self.__class__.FRAMES_MOVE
            super(Zombie, self).update(dt)

            sqr_limit = self.sqrDistToPlayerLimit * 0.8
            if not self.dashHitRegistered and (self.target_player.position - self.position).sqrMagnitude < sqr_limit:
                self.target_player.attacked()
                self.dashHitRegistered = True
            return
        super(BossZombie, self).update(dt)

