from tkinter import Canvas

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.Sprite import Sprite
from assets.utils.Vectors import Vector2


class BossKeyBg(Sprite):
    def __init__(self, canvas: Canvas):
        super(BossKeyBg, self).__init__(canvas, "images/BossKeyBg.png")

        self.position = Vector2(GAME_WIDTH, GAME_HEIGHT) / 2
        self.hidden = True

    def redraw(self):
        self.canvas.tag_raise(self.canvas_image)

