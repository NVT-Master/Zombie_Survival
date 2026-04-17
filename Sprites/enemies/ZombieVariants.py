"""
Zombie variants with different behaviors and stats
"""

from random import random, randint
from math import pi, sqrt
from tkinter import PhotoImage, Canvas
from enum import Enum, auto as enum_next

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.AnimatedSprite import AnimatedSprite
from assets.utils.Vectors import Vector2
from Sprites.enemies.Zombie import Zombie, ZombiePriority

from typing import List, TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Sprites.player.Player import Player
    from game import Game


def _get_scaled_frames(file_pattern: str, scale_divisor: int = 2) -> List[PhotoImage]:
    frames = AnimatedSprite.getFramesWithFilePattern(file_pattern)
    if scale_divisor <= 1:
        return frames
    return [frame.subsample(scale_divisor, scale_divisor) for frame in frames]


class TankZombie(Zombie):
    """Slow, tanky zombie with high damage"""
    SCALE_DIVISOR: int = 2  # Smaller than boss (boss is 1)
    FRAMES_ATTACK: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-attack_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_IDLE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-idle_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_MOVE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-move_{0}.png",
        SCALE_DIVISOR
    )

    MAX_SPEED: float = 25  # Very slow
    COLLIDER_WIDTH: float = 40  # Medium size
    HEARTS: int = 18  # Moderate health
    DAMAGE_PER_ATTACK: int = 2  # Does 2x damage per hit

    def __init__(
        self,
        canvas: Canvas,
        target_player: "Player",
        game: Optional["Game"] = None,
        spawn_position: Optional[Vector2] = None
    ):
        super().__init__(canvas, target_player, game=game, spawn_position=spawn_position)
        self.hearts = self.HEARTS
        self.maxHearts = self.HEARTS
        self.speed = self.MAX_SPEED
        self.damage_multiplier = self.DAMAGE_PER_ATTACK
        self.shield_outer = None
        self.shield_inner = None
        self._last_drawn_shield_pos = None  # Optimization: only redraw when position changes

    def _update_shield_visual(self):
        if self.shield_outer is None or self.shield_inner is None:
            return

        # Optimization: skip if position hasn't changed much
        if self._last_drawn_shield_pos is not None:
            dist = (self.position - self._last_drawn_shield_pos).magnitude
            if dist < 2.0:  # Only update if moved more than 2 pixels
                return
        
        self._last_drawn_shield_pos = self.position

        forward = self.forwards
        mag = sqrt((forward.x * forward.x) + (forward.y * forward.y))
        if mag < 1e-6:
            dir_x, dir_y = 0.0, 1.0
        else:
            dir_x, dir_y = (forward.x / mag), (forward.y / mag)

        cx = self.position.x + dir_x * (self.halfImageSize.x * 0.56)
        cy = self.position.y + dir_y * (self.halfImageSize.y * 0.40)
        rx = max(10.0, self.halfImageSize.x * 0.62)
        ry = max(8.0, self.halfImageSize.y * 0.52)

        self.canvas.coords(self.shield_outer, cx - rx, cy - ry, cx + rx, cy + ry)
        self.canvas.coords(self.shield_inner, cx - rx * 0.72, cy - ry * 0.72, cx + rx * 0.72, cy + ry * 0.72)
        self.canvas.tag_raise(self.shield_outer)
        self.canvas.tag_raise(self.shield_inner)

    def first_draw(self):
        super().first_draw()
        if self.hidden:
            return
        self.shield_outer = self.canvas.create_oval(0, 0, 0, 0, outline="#66d9ff", width=3)
        self.shield_inner = self.canvas.create_oval(0, 0, 0, 0, outline="#b7f1ff", width=2)
        self._update_shield_visual()

    def redraw(self):
        super().redraw()
        self._update_shield_visual()

    def undraw(self):
        if self.shield_outer is not None:
            self.canvas.delete(self.shield_outer)
            self.shield_outer = None
        if self.shield_inner is not None:
            self.canvas.delete(self.shield_inner)
            self.shield_inner = None
        super().undraw()

    def shot(self) -> bool:
        """Takes extra hits to kill, drops extra score"""
        self.hearts -= 1
        if self.hearts <= 0:
            self.destroyed = True
            return True
        return False

    def get_barricade_damage(self) -> int:
        return randint(2, 3)

    def update(self, dt):
        super().update(dt)
        if self.game is not None and self.game._hasActiveBarricade() and self.position.y >= self.game.getBarricadeY() - self.halfImageSize.y * 0.45:
            return
        # Tank attacks trigger extra hits
        if self.priority == ZombiePriority.Attacking and not self.hasAttacked:
            if self.cycleTime >= self.cycleLength * self.__class__.FRAMES_ATTACK_CRITICAL_POINT:
                for _ in range(self.damage_multiplier):
                    self.target_player.attacked()
                self.hasAttacked = True


class SprinterZombie(Zombie):
    """Fast zombie with low health - glass cannon"""
    SCALE_DIVISOR: int = 2  # Smaller
    FRAMES_ATTACK: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-attack_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_IDLE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-idle_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_MOVE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-move_{0}.png",
        SCALE_DIVISOR
    )

    MAX_SPEED: float = 90  # 1.8x faster than normal
    COLLIDER_WIDTH: float = 30  # Small size
    HEARTS: int = 3  # Very fragile

    def __init__(
        self,
        canvas: Canvas,
        target_player: "Player",
        game: Optional["Game"] = None,
        spawn_position: Optional[Vector2] = None
    ):
        super().__init__(canvas, target_player, game=game, spawn_position=spawn_position)
        self.hearts = self.HEARTS
        self.maxHearts = self.HEARTS
        self.speed = self.MAX_SPEED
        self.cycleLength = 1.2  # Faster animations


class BomberZombie(Zombie):
    """Explodes on death, damages player in radius"""
    SCALE_DIVISOR: int = 2  # Smaller than boss
    FRAMES_ATTACK: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-attack_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_IDLE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-idle_{0}.png",
        SCALE_DIVISOR
    )
    FRAMES_MOVE: List[PhotoImage] = _get_scaled_frames(
        "images/Top_Down_Zombie/portrait/skeleton-move_{0}.png",
        SCALE_DIVISOR
    )

    MAX_SPEED: float = 45
    COLLIDER_WIDTH: float = 35  # Medium-small
    HEARTS: int = 8
    EXPLOSION_RADIUS: float = 120  # pixels
    EXPLOSION_DAMAGE_DISTANCE: float = 150  # pixels for damage check
    EXPLOSION_VISUAL_MS: int = 120

    def __init__(
        self,
        canvas: Canvas,
        target_player: "Player",
        game: Optional["Game"] = None,
        spawn_position: Optional[Vector2] = None
    ):
        super().__init__(canvas, target_player, game=game, spawn_position=spawn_position)
        self.hearts = self.HEARTS
        self.maxHearts = self.HEARTS
        self.speed = self.MAX_SPEED
        self.has_exploded = False
        self.explosion_canvas_id = None
        self.bomb_body = None
        self.bomb_cap = None
        self.bomb_fuse = None
        self._last_drawn_bomb_pos = None  # Optimization: only redraw when position changes

    def _update_bomb_visual(self):
        if self.bomb_body is None or self.bomb_cap is None or self.bomb_fuse is None:
            return

        # Optimization: skip if position hasn't changed much
        if self._last_drawn_bomb_pos is not None:
            dist = (self.position - self._last_drawn_bomb_pos).magnitude
            if dist < 2.0:  # Only update if moved more than 2 pixels
                return
        
        self._last_drawn_bomb_pos = self.position

        forward = self.forwards
        mag = sqrt((forward.x * forward.x) + (forward.y * forward.y))
        if mag < 1e-6:
            dir_x, dir_y = 0.0, 1.0
        else:
            dir_x, dir_y = (forward.x / mag), (forward.y / mag)

        side_x = -dir_y
        side_y = dir_x
        cx = self.position.x + dir_x * (self.halfImageSize.x * 0.48) + side_x * (self.halfImageSize.x * 0.26)
        cy = self.position.y + dir_y * (self.halfImageSize.y * 0.42) + side_y * (self.halfImageSize.y * 0.24)
        r = max(6.0, min(self.halfImageSize.x, self.halfImageSize.y) * 0.20)

        self.canvas.coords(self.bomb_body, cx - r, cy - r, cx + r, cy + r)
        self.canvas.coords(self.bomb_cap, cx - r * 0.45, cy - r * 1.25, cx + r * 0.45, cy - r * 0.65)

        fuse_x = cx + side_x * r * 0.90
        fuse_y = cy - r * 1.10 + side_y * r * 0.45
        spark_x = fuse_x + side_x * r * 0.45 + dir_x * r * 0.25
        spark_y = fuse_y - r * 0.55 + side_y * r * 0.28
        self.canvas.coords(self.bomb_fuse, fuse_x, fuse_y, spark_x, spark_y)

        self.canvas.tag_raise(self.bomb_body)
        self.canvas.tag_raise(self.bomb_cap)
        self.canvas.tag_raise(self.bomb_fuse)

    def first_draw(self):
        super().first_draw()
        if self.hidden:
            return
        self.bomb_body = self.canvas.create_oval(0, 0, 0, 0, fill="#1f1f1f", outline="#606060", width=2)
        self.bomb_cap = self.canvas.create_rectangle(0, 0, 0, 0, fill="#ffb347", outline="#ff8a00", width=1)
        self.bomb_fuse = self.canvas.create_line(0, 0, 0, 0, fill="#ffd766", width=2)
        self._update_bomb_visual()

    def redraw(self):
        super().redraw()
        self._update_bomb_visual()

    def undraw(self):
        for item_name in ("bomb_body", "bomb_cap", "bomb_fuse"):
            item = getattr(self, item_name)
            if item is not None:
                self.canvas.delete(item)
                setattr(self, item_name, None)
        super().undraw()

    def shot(self) -> bool:
        """Explode on death"""
        self.hearts -= 1
        if self.hearts <= 0:
            self._explode()
            self.destroyed = True
            return True
        return False

    def _explode(self):
        """Trigger explosion effect and damage nearby zombies"""
        if self.game is None or self.has_exploded:
            return

        self.has_exploded = True
        self.game._playBomberExplosionSfx()

        # Draw explosion effect on canvas
        try:
            explosion_color = "#ff4500"
            self.explosion_canvas_id = self.canvas.create_oval(
                self.position.x - self.EXPLOSION_RADIUS,
                self.position.y - self.EXPLOSION_RADIUS,
                self.position.x + self.EXPLOSION_RADIUS,
                self.position.y + self.EXPLOSION_RADIUS,
                fill=explosion_color,
                outline="#ff8c00",
                width=2
            )
            # Prevent canvas item buildup in long fights.
            self.canvas.after(self.__class__.EXPLOSION_VISUAL_MS, self._cleanup_explosion_visual)
        except:
            pass

        # Damage player if in range
        distance_to_player = (self.target_player.position - self.position).magnitude
        if distance_to_player < self.EXPLOSION_DAMAGE_DISTANCE:
            self.target_player.attacked()

        # Damage nearby zombies within explosion radius
        if self.game is not None:
            self._damage_nearby_zombies()

    def _damage_nearby_zombies(self):
        """Damage all zombies within explosion radius"""
        if self.game is None or not hasattr(self.game, 'zombies'):
            return

        sqr_explosion_radius = self.EXPLOSION_RADIUS ** 2
        zombie = None
        try:
            for zombie in self.game.zombies.children:
                # Don't damage self
                if zombie is self:
                    continue
                
                # Calculate distance to zombie
                distance_vector = zombie.position - self.position
                sqr_distance = distance_vector.sqrMagnitude
                
                # Damage if within radius
                if sqr_distance < sqr_explosion_radius:
                    # More damage at closer distance, less damage at edge
                    damage_distance_ratio = (sqr_distance ** 0.5) / self.EXPLOSION_RADIUS
                    damage = max(1, int(5 * (1 - damage_distance_ratio * 0.5)))
                    
                    # Apply damage multiple times to simulate impact
                    for _ in range(damage):
                        killed = zombie.shot()
                        if killed:
                            self.game.OnZombieKilled(zombie)
                            break
        except Exception:
            # Safely handle any iteration errors
            pass

    def _cleanup_explosion_visual(self):
        if self.explosion_canvas_id is None:
            return
        try:
            self.canvas.delete(self.explosion_canvas_id)
        except Exception:
            pass
        self.explosion_canvas_id = None

    def update(self, dt):
        super().update(dt)

