from random import random
from tkinter import Canvas

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.SpriteGroup import SpriteGroup
from assets.core.ISprite import ISprite
from assets.utils.Vectors import Vector2
from assets.systems.SpatialPartitioning import SpatialGrid

from Sprites.enemies.Zombie import Zombie

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game import Game


class Bullets(SpriteGroup):
    def __init__(self, game: "Game"):
        super().__init__(game.canvas)
        self.game: Game = game
        self.spatial_grid = SpatialGrid()  # For fast collision detection

    def newBullet(self, startPos: Vector2, forwards: Vector2) -> "_Bullet":
        bullet = _Bullet(self.canvas, startPos, forwards, self.game, self.spatial_grid)
        self.children.insertRight(bullet)
        return bullet

    def spawnBlood(self, position: Vector2, hitDirection: Vector2, amount: int = 8):
        for _ in range(amount):
            self.children.insertRight(_BloodParticle(self.canvas, position, hitDirection))
    
    def update_spatial_grid(self):
        """Update spatial grid with current zombie positions"""
        self.spatial_grid.clear()
        for zombie in self.game.zombies.children:
            if not zombie.hidden:
                self.spatial_grid.insert(zombie, zombie.position)


class _Bullet(ISprite):
    # bullet speed in pixels per second
    SPEED: float = (GAME_WIDTH ** 2 + GAME_HEIGHT ** 2) ** 0.5

    COLLIDER_WIDTH: float = 14
    TRAIL_LENGTH: float = 18
    TRAIL_WIDTH: int = 4
    CORE_WIDTH: int = 2
    NOSE_LENGTH: float = 7.5
    NOSE_HALF_WIDTH: float = 3.0

    WORLD_MARGIN: int = 20

    def __init__(self, canvas: Canvas, startPos: Vector2, forwards: Vector2, game: "Game", spatial_grid=None):
        self.trailStart = Vector2(0, 0)
        self.trailEnd = Vector2(0, 0)
        self.bodyEnd = Vector2(0, 0)
        self.nosePoints = ()

        self.canvas_trail = None
        self.canvas_core = None
        self.canvas_nose = None

        super(_Bullet, self).__init__(canvas)
        self.game: Game = game
        self.forwards = forwards
        self.position = startPos
        self.spatial_grid = spatial_grid  # Reference to spatial grid for fast collision

    def update(self, dt):
        super(_Bullet, self).update(dt)

        if self.hidden:
            return

        self.position += self.forwards * (self.__class__.SPEED * dt)

        sqr_collision_threshold = (Zombie.COLLIDER_WIDTH + self.__class__.COLLIDER_WIDTH) ** 2
        
        # Use spatial grid for faster collision detection if available
        if self.spatial_grid is not None:
            nearby_zombies = self.spatial_grid.query_radius(self.position, Zombie.COLLIDER_WIDTH + self.__class__.COLLIDER_WIDTH)
        else:
            nearby_zombies = self.game.zombies.children
        
        zombie: Zombie
        for zombie in nearby_zombies:
            if (zombie.position - self.position).sqrMagnitude < sqr_collision_threshold:
                # collision
                killed = zombie.shot()
                self.game.audioManager.play_sfx("zombie_hit.wav", volume=0.45)
                alive_count = len(self.game.zombies.children)
                if alive_count >= 8:
                    blood_amount = 7 if killed else 4
                elif alive_count >= 5:
                    blood_amount = 10 if killed else 6
                else:
                    blood_amount = 14 if killed else 8
                self.game.bullets.spawnBlood(self.position, self.forwards, amount=blood_amount)
                if killed:
                    self.game.OnZombieKilled(zombie)
                self.destroy()
                break

    def destroy(self):
        self.destroyed = True

    def validatePosition(self):
        if self.position.x < -self.__class__.WORLD_MARGIN or self.position.x > GAME_WIDTH + self.__class__.WORLD_MARGIN \
                or self.position.y < -self.__class__.WORLD_MARGIN or self.position.y > GAME_HEIGHT + self.__class__.WORLD_MARGIN:
            self.destroy()

    @ISprite.position.setter
    def position(self, new: Vector2):
        ISprite.position.fset(self, new)
        if not hasattr(self, "_forwards"):
            return
        self._updateDrawPoints()

    @ISprite.rotation.setter
    def rotation(self, new: float):
        ISprite.rotation.fset(self, new)
        self._updateDrawPoints()

    def _updateDrawPoints(self):
        self.trailEnd = self.position
        self.bodyEnd = self.position - (self.forwards * self.__class__.NOSE_LENGTH)
        self.trailStart = self.bodyEnd - (self.forwards * self.__class__.TRAIL_LENGTH)

        right = Vector2(-self.forwards.y, self.forwards.x)
        left_base = self.bodyEnd - (right * self.__class__.NOSE_HALF_WIDTH)
        right_base = self.bodyEnd + (right * self.__class__.NOSE_HALF_WIDTH)
        self.nosePoints = (
            self.position.x, self.position.y,
            left_base.x, left_base.y,
            right_base.x, right_base.y
        )

    def first_draw(self):
        if self.hidden:
            return
        super(_Bullet, self).first_draw()
        self.canvas_trail = self.canvas.create_line(
            *self.trailStart,
            *self.bodyEnd,
            fill="#ffb74d",
            width=self.__class__.TRAIL_WIDTH,
            capstyle="round"
        )
        self.canvas_core = self.canvas.create_line(
            *self.trailStart,
            *self.bodyEnd,
            fill="#fffde7",
            width=self.__class__.CORE_WIDTH,
            capstyle="round"
        )
        self.canvas_nose = self.canvas.create_polygon(
            *self.nosePoints,
            fill="#fff176",
            outline=""
        )

    def redraw(self):
        super(_Bullet, self).redraw()
        self.canvas.coords(self.canvas_trail, *self.trailStart, *self.bodyEnd)
        self.canvas.coords(self.canvas_core, *self.trailStart, *self.bodyEnd)
        self.canvas.coords(self.canvas_nose, *self.nosePoints)
        self.canvas.tag_raise(self.canvas_trail)
        self.canvas.tag_raise(self.canvas_core)
        self.canvas.tag_raise(self.canvas_nose)

    def undraw(self):
        super(_Bullet, self).undraw()
        self.canvas.delete(self.canvas_trail)
        self.canvas.delete(self.canvas_core)
        self.canvas.delete(self.canvas_nose)


class _BloodParticle(ISprite):
    LIFE: float = 0.24
    SIZE: float = 4.0
    SPEED_MIN: float = 75.0
    SPEED_MAX: float = 210.0
    DRAG_PER_SEC: float = 4.5

    def __init__(self, canvas: Canvas, origin: Vector2, hitDirection: Vector2):
        super(_BloodParticle, self).__init__(canvas)

        self.life = self.__class__.LIFE * (0.7 + random() * 0.7)
        self.maxLife = self.life
        self.size = self.__class__.SIZE * (0.65 + random() * 0.8)
        self.canvas_oval = None

        if hitDirection.sqrMagnitude == 0:
            hitDirection = Vector2(0, -1)

        forward = hitDirection.normalise()
        right = Vector2(-forward.y, forward.x)
        spread = (random() * 2 - 1) * 0.9
        speed = self.__class__.SPEED_MIN + random() * (self.__class__.SPEED_MAX - self.__class__.SPEED_MIN)
        self.velocity = (forward + right * spread).normalise() * speed
        self.position = origin + forward * (2 + random() * 3)

        self.topLeft = Vector2(0, 0)
        self.bottomRight = Vector2(0, 0)
        self._updateBounds()

    def _updateBounds(self):
        half = self.size * 0.5
        self.topLeft = self.position + Vector2(-half, -half)
        self.bottomRight = self.position + Vector2(half, half)

    def update(self, dt):
        super(_BloodParticle, self).update(dt)
        if self.hidden:
            return

        self.life -= dt
        if self.life <= 0:
            self.destroyed = True
            return

        drag = max(0.0, 1.0 - self.__class__.DRAG_PER_SEC * dt)
        self.velocity = self.velocity * drag
        self.position += self.velocity * dt
        self._updateBounds()

    @ISprite.position.setter
    def position(self, new: Vector2):
        self._pos = new

    def first_draw(self):
        if self.hidden:
            return
        super(_BloodParticle, self).first_draw()
        self.canvas_oval = self.canvas.create_oval(
            *self.topLeft,
            *self.bottomRight,
            fill="#c62828",
            outline=""
        )

    def redraw(self):
        super(_BloodParticle, self).redraw()
        if self.canvas_oval is not None:
            self.canvas.coords(self.canvas_oval, *self.topLeft, *self.bottomRight)
            if self.maxLife > 0 and self.life < self.maxLife * 0.45:
                self.canvas.itemconfig(self.canvas_oval, fill="#8e0000")

    def undraw(self):
        super(_BloodParticle, self).undraw()
        self.canvas.delete(self.canvas_oval)


