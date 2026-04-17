from tkinter import NE

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.TextSprite import TextSprite
from assets.utils.Vectors import Vector2

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game import Game


class ScoreIndicator(TextSprite):
    POS_NORMAL = Vector2(GAME_WIDTH - 20, 20)
    POS_GAMEOVER = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.2)

    def __init__(self, game: "Game"):
        super(ScoreIndicator, self).__init__(game.canvas)
        self.game: "Game" = game
        self.text = self.game.score

        self.options["font"] = 'Helvetica 12 bold'  # Nhá» hÆ¡n
        self.options["fill"] = self.game.hudColor
        self.options["anchor"] = NE
        self.position = self.__class__.POS_NORMAL

    @TextSprite.position.getter
    def position(self) -> Vector2:
        return TextSprite.position.fget(self)

    @TextSprite.position.setter
    def position(self, position: Vector2):
        TextSprite.position.fset(self, position)
        font_size = 50 if position == self.__class__.POS_GAMEOVER else 12
        self.options["font"] = f'Helvetica {font_size} bold'

    def update(self, dt):
        if self.game.player.destroyed:
            return
        self.options["fill"] = self.game.hudColor

        # Build HUD text with wave info (compact)
        wave_text = ""
        if self.game.waveManager:
            wave_num = self.game.waveManager.get_current_wave_number()
            total_waves = self.game.waveManager.get_total_waves()
            wave_text = f"S{wave_num}/{total_waves} "

        self.text = f"{wave_text}K{self.game.killedCountTotal}/{self.game.killTargetTotal} Sc{self.game.score}"

