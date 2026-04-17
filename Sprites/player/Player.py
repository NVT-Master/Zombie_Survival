from math import pi, sin, cos, atan2, degrees
from time import time
from random import random
from tkinter import PhotoImage
from enum import Enum, auto as enum_next

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.AnimatedSprite import AnimatedSprite
from assets.utils.Vectors import Vector2
from Sprites.enemies.Bullet import Bullets

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from game import Game
    from Sprites.enemies.Bullet import _Bullet


class _Gun(Enum):
    Handgun = enum_next()
    Shotgun = enum_next()
    AK = enum_next()


class _Facing(Enum):
    Up = "up"
    UpRight = "up_right"
    Right = "right"
    DownRight = "down_right"
    Down = "down"
    DownLeft = "down_left"
    Left = "left"
    UpLeft = "up_left"


def _get_scaled_frames(file_pattern: str, scale_divisor: int = 2) -> List[PhotoImage]:
    frames = AnimatedSprite.getFramesWithFilePattern(file_pattern)
    if scale_divisor <= 1:
        return frames
    return [frame.subsample(scale_divisor, scale_divisor) for frame in frames]


def _build_uniform_facing_frames(file_pattern: str, scale_divisor: int = 2):
    frames = _get_scaled_frames(file_pattern, scale_divisor)
    return {facing: frames for facing in _Facing}


class Player(AnimatedSprite):
    SCALE_DIVISOR: int = 2
    FRAMES_IDLE_HANDGUN = {
        _Facing.Up: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/up/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpRight: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/up_right/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Right: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/right/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownRight: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/down_right/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Down: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/down/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/down_left/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Left: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/left/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/idle_aim8/up_left/survivor-idle_handgun_{0}.png", SCALE_DIVISOR
        ),
    }
    FRAMES_MOVE_HANDGUN = {
        _Facing.Up: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/up/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpRight: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/up_right/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Right: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/right/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownRight: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/down_right/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Down: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/down/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/down_left/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Left: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/left/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/handgun/move_aim8/up_left/survivor-move_handgun_{0}.png", SCALE_DIVISOR
        ),
    }
    FRAMES_IDLE_SHOTGUN = {
        _Facing.Up: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/up/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpRight: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/up_right/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Right: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/right/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownRight: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/down_right/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Down: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/down/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/down_left/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Left: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/left/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/idle_aim8/up_left/survivor-idle_shotgun_{0}.png", SCALE_DIVISOR
        ),
    }
    FRAMES_MOVE_SHOTGUN = {
        _Facing.Up: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/up/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpRight: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/up_right/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Right: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/right/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownRight: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/down_right/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Down: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/down/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.DownLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/down_left/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.Left: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/left/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
        _Facing.UpLeft: _get_scaled_frames(
            "images/Top_Down_Survivor/shotgun/move_aim8/up_left/survivor-move_shotgun_{0}.png", SCALE_DIVISOR
        ),
    }
    FRAMES_IDLE_AK = _build_uniform_facing_frames(
        "images/Top_Down_Survivor/rifle/idle/survivor-idle_rifle_{0}.png", SCALE_DIVISOR
    )
    FRAMES_MOVE_AK = _build_uniform_facing_frames(
        "images/Top_Down_Survivor/rifle/move/survivor-move_rifle_{0}.png", SCALE_DIVISOR
    )

    MAX_SPEED: float = 100  # pixels per second
    COLLIDER_WIDTH: float = 30
    HANDGUN_FIRE_INTERVAL: float = 0.13
    SHOTGUN_FIRE_INTERVAL: float = 0.35
    AK_FIRE_INTERVAL: float = 0.085
    DASH_SPEED: float = 250  # pixels per second
    DASH_DURATION: float = 0.4  # seconds
    DASH_COOLDOWN: float = 2.0  # seconds

    def __init__(self, game: "Game", bullets: Bullets):
        super().__init__(game.canvas, self.__class__.FRAMES_IDLE_HANDGUN[_Facing.Up])
        self.game: Game = game
        self.bullets: Bullets = bullets

        self.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT - self.halfImageSize.y * 0.8)
        self.rotation = pi / 2
        self.max_speed = self.__class__.MAX_SPEED  # pixels per second
        self.speed = 0  # pixels per second

        self.hearts = 5

        self.walkingRotation: float = pi / 2
        self.walkingDirection: Vector2 = Vector2(1, 0)

        self.inputUp = 0
        self.inputDown = 0
        self.inputLeft = 0
        self.inputRight = 0
        self.mousePos = Vector2(0.5, 0.5) * Vector2(GAME_WIDTH, GAME_HEIGHT)

        self.facing: _Facing = _Facing.Up
        self.gun: _Gun = _Gun.Handgun

        self.setupKeyBindings()
        self.activeCheatCodes: List[str] = []
        self.isFiring = False
        self.shootCooldown = 0.0

        # Dash ability
        self.isDashing = False
        self.dashDuration = 0.0
        self.dashCooldown = 0.0
        self.dashDirection = Vector2(1, 0)
        self.lastHitSfxTime = 0.0
        self.hitSfxCooldown = 0.12

    def setupKeyBindings(self):
        controls = self.game.controls
        inputs = ("up", "left", "down", "right")
        # e.g. self.game.tk.bind("<KeyPress-w>", lambda e: self.setInput(up=1))
        for i in range(len(inputs)):
            self.game.tk.bind(f"<KeyPress-{controls[i]}>",
                              lambda e, kwarg=inputs[i]: self.setInput(**{kwarg: 1}))
            self.game.tk.bind(f"<KeyRelease-{controls[i]}>",
                              lambda e, kwarg=inputs[i]: self.setInput(**{kwarg: 0}))

        self.game.tk.bind('<Motion>', lambda e: self.setInput(mouse=Vector2(e.x, e.y)))
        self.game.tk.bind("<ButtonPress-1>", lambda e: self.setInput(firing=True))
        self.game.tk.bind("<ButtonRelease-1>", lambda e: self.setInput(firing=False))

        self.game.tk.bind('<space>', lambda e: self.dash())
        self.game.tk.bind('q', lambda e: self.cycleGun())
        self.game.tk.bind('1', lambda e: self.setGun(_Gun.Handgun))
        self.game.tk.bind('2', lambda e: self.setGun(_Gun.Shotgun))
        self.game.tk.bind('3', lambda e: self.setGun(_Gun.AK))
        self.game.tk.bind('quick', lambda e: self.cheatCode("quick"))
        self.game.tk.bind('ohno', lambda e: self.cheatCode("ohno"))

    def setGun(self, gun: _Gun):
        self.gun = gun

    def cycleGun(self):
        order = (_Gun.Handgun, _Gun.Shotgun, _Gun.AK)
        current_index = order.index(self.gun)
        self.gun = order[(current_index + 1) % len(order)]

    def setInput(
        self,
        up: int = None,
        down: int = None,
        left: int = None,
        right: int = None,
        mouse: Vector2 = None,
        firing: bool = None
    ):
        if up is not None:
            self.inputUp = up
        if down is not None:
            self.inputDown = down
        if left is not None:
            self.inputLeft = left
        if right is not None:
            self.inputRight = right
        if mouse is not None:
            self.mousePos = mouse
        if firing is not None:
            if firing and not self.isFiring:
                self.shoot()
            self.isFiring = firing

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, new):
        self._speed = new
        self.cycleLength = max(1, new / 100)

    @property
    def gun(self) -> _Gun:
        return self._gun

    @gun.setter
    def gun(self, gun: _Gun):
        self._gun = gun
        self._applyFacingFrames(is_moving=self.speed > 0)

    def shoot(self):
        if self.game.paused:
            return

        bulletDirection = self.mousePos - self.position
        if bulletDirection.sqrMagnitude == 0:
            return

        muzzlePos = self._getMuzzlePosition(bulletDirection)
        if self.gun == _Gun.Shotgun:
            for i in range(3):
                bullet: "_Bullet" = self.bullets.newBullet(muzzlePos, bulletDirection)
                bullet.rotation += (i-1) * 0.1  # bullets are 0.1 radians apart
                self._playGunshotSfx(_Gun.Shotgun)
        elif self.gun == _Gun.AK:
            bullet: "_Bullet" = self.bullets.newBullet(muzzlePos, bulletDirection)
            bullet.rotation += (random() - 0.5) * 0.05
            self._playGunshotSfx(_Gun.AK)
        else:
            self.bullets.newBullet(muzzlePos, bulletDirection)
            self._playGunshotSfx(_Gun.Handgun)
        self.shootCooldown = self._getFireInterval()

    def _playGunshotSfx(self, gun: _Gun) -> bool:
        if gun == _Gun.Shotgun:
            candidates = [
                "shoot_shotgun.wav", "shoot_shotgun.mp3",
                "shoot_handgun.wav", "shoot_handgun.mp3",
            ]
            volume = 0.72
            max_duration_ms = 320
        elif gun == _Gun.AK:
            candidates = [
                "shoot_rifle.wav", "shoot_rifle.mp3",
                "shoot_handgun.wav", "shoot_handgun.mp3",
            ]
            volume = 0.68
            max_duration_ms = 170
        else:
            candidates = [
                "shoot_handgun.wav", "shoot_handgun.mp3",
            ]
            volume = 0.65
            max_duration_ms = 180

        for name in candidates:
            if self.game.audioManager.play_sfx(name, volume=volume, max_duration_ms=max_duration_ms):
                return True
        return False

    def _getMuzzlePosition(self, bulletDirection: Vector2) -> Vector2:
        direction = bulletDirection.normalise()
        right = Vector2(-direction.y, direction.x)
        forward_offset = self.halfImageSize.y * 1.20
        side_offset = self.halfImageSize.x * 0.22
        if self.gun == _Gun.Shotgun:
            side_offset = self.halfImageSize.x * 0.20
        elif self.gun == _Gun.AK:
            side_offset = self.halfImageSize.x * 0.21
        return self.position + (direction * forward_offset) + (right * side_offset)

    def _facingFromDirection(self, direction: Vector2) -> _Facing:
        angle = (degrees(atan2(direction.y, direction.x)) + 360.0) % 360.0
        octant = int((angle + 22.5) // 45) % 8
        order = (
            _Facing.Right,
            _Facing.DownRight,
            _Facing.Down,
            _Facing.DownLeft,
            _Facing.Left,
            _Facing.UpLeft,
            _Facing.Up,
            _Facing.UpRight,
        )
        return order[octant]

    def _applyFacingFrames(self, is_moving: bool):
        if self.gun == _Gun.Handgun:
            idle_map = self.__class__.FRAMES_IDLE_HANDGUN
            move_map = self.__class__.FRAMES_MOVE_HANDGUN
        elif self.gun == _Gun.AK:
            idle_map = self.__class__.FRAMES_IDLE_AK
            move_map = self.__class__.FRAMES_MOVE_AK
        else:
            idle_map = self.__class__.FRAMES_IDLE_SHOTGUN
            move_map = self.__class__.FRAMES_MOVE_SHOTGUN

        self.framesIdle = idle_map[self.facing]
        self.framesMove = move_map[self.facing]
        self.frames = self.framesMove if is_moving else self.framesIdle

    def _getFireInterval(self) -> float:
        if self.gun == _Gun.Shotgun:
            return self.__class__.SHOTGUN_FIRE_INTERVAL
        if self.gun == _Gun.AK:
            return self.__class__.AK_FIRE_INTERVAL
        return self.__class__.HANDGUN_FIRE_INTERVAL

    def update(self, dt):
        super(self.__class__, self).update(dt)

        # Update dash cooldown
        self.dashCooldown = max(0.0, self.dashCooldown - dt)

        # Handle dash
        if self.isDashing:
            self.dashDuration -= dt
            self.position += self.dashDirection * (self.__class__.DASH_SPEED * dt)
            if self.dashDuration <= 0:
                self.isDashing = False
                self.dashCooldown = self.__class__.DASH_COOLDOWN
            return  # Skip normal movement while dashing

        # translate input into walking direction
        dx = self.inputRight - self.inputLeft
        dy = self.inputDown - self.inputUp
        self.walkingRotation = atan2(dx, dy)
        self.walkingDirection = Vector2(sin(self.walkingRotation), cos(self.walkingRotation))

        moving = (dx != 0 or dy != 0)

        # Aim is still based on mouse position.
        aim_vector = self.mousePos - self.position
        self.forwards = aim_vector

        # While moving, face movement direction to avoid backward-walk visuals.
        # When idle, face aim direction for shooting.
        if moving:
            new_facing = self._facingFromDirection(self.walkingDirection)
        elif aim_vector.sqrMagnitude > 0:
            new_facing = self._facingFromDirection(aim_vector)
        else:
            new_facing = self.facing

        if new_facing != self.facing:
            self.facing = new_facing
            self._applyFacingFrames(is_moving=moving)

        self.shootCooldown = max(0.0, self.shootCooldown - dt)
        if self.isFiring and self.shootCooldown <= 0:
            self.shoot()

        if not moving:
            self.frames = self.framesIdle
            self.speed = 0
        else:
            self.frames = self.framesMove
            self.speed = self.max_speed

        # move after speed state is updated to avoid one-frame lag/stick
        self.position += self.walkingDirection * (self.speed * dt)

    def dash(self):
        """Activate dash ability (space key)"""
        if self.isDashing or self.dashCooldown > 0 or self.game.paused:
            return

        self.isDashing = True
        self.dashDuration = self.__class__.DASH_DURATION

        # Use walking direction if moving, else use facing direction
        dx = self.inputRight - self.inputLeft
        dy = self.inputDown - self.inputUp
        if dx != 0 or dy != 0:
            walk_rotation = atan2(dx, dy)
            self.dashDirection = Vector2(sin(walk_rotation), cos(walk_rotation))
        else:
            # Use direction player is facing (towards mouse)
            aim_vector = self.mousePos - self.position
            if aim_vector.sqrMagnitude > 0:
                self.dashDirection = aim_vector.normalise()
            else:
                self.dashDirection = Vector2(1, 0)

        self.game.audioManager.play_sfx("dash.wav", volume=0.55)

    def cheatCode(self, code: str, reverse: bool = False):
        if (code in self.activeCheatCodes) != reverse:
            return
        if reverse:
            self.activeCheatCodes.remove(code)
        else:
            self.activeCheatCodes.append(code)

        duration: int = 3000
        if code == "quick":
            self.max_speed = self.__class__.MAX_SPEED * (1 if reverse else 2)
            duration = 3000
        elif code == "ohno":
            self.gun = _Gun.Handgun if reverse else _Gun.Shotgun
            duration = 3000
        else:
            return

        if not reverse:
            self.game.tk.after(duration, lambda: self.cheatCode(code, reverse=True))

    def attacked(self):
        if self.game.isPlayerProtectedByBarricade():
            return

        now = time()
        if now - self.lastHitSfxTime >= self.hitSfxCooldown:
            if not self.game.audioManager.play_sfx("player_hit.wav", volume=0.60):
                self.game.audioManager.play_sfx("zombie_hit.wav", volume=0.45)
            self.lastHitSfxTime = now

        self.hearts -= 1
        if self.hearts <= 0:
            self.game.onGameOver()
            self.destroyed = True

