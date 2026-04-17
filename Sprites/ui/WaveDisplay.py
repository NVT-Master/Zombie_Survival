from tkinter import NW

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.TextSprite import TextSprite
from assets.utils.Vectors import Vector2

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game import Game


class WaveDisplay(TextSprite):
    """Display current wave and kill progress at top-left"""

    def __init__(self, game: "Game"):
        super(WaveDisplay, self).__init__(game.canvas)
        self.game: "Game" = game

        self.options["font"] = 'Helvetica 14 bold'  # Nho hon
        self.options["fill"] = "#7cff9b"
        self.options["anchor"] = NW
        self.position = Vector2(20, 50)  # Dich xuong de khong de len score

    def update(self, dt):
        if self.game.player.destroyed or not self.game.started:
            self.hidden = True
            return

        self.hidden = False

        # Get wave info
        if self.game.waveManager:
            wave_num = self.game.waveManager.get_current_wave_number()
            total_waves = self.game.waveManager.get_total_waves()
            remaining = max(0, self.game.killTargetTotal - self.game.killedCountTotal)

            # Color change based on wave
            if wave_num == 1:
                self.options["fill"] = "#7cff9b"  # Green
            elif wave_num == 2:
                self.options["fill"] = "#ffd66a"  # Yellow
            else:
                self.options["fill"] = "#ff6b6b"  # Red (boss wave)

            self.text = f"Sóng {wave_num}/{total_waves}\nCòn: {remaining} zombie"
        else:
            self.text = ""


