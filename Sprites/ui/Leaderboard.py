"""
Leaderboard stored as
{score}, {date}, {name}
"""

from tkinter import Canvas

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.core.ISprite import ISprite

from typing import Union, List, Tuple


class Leaderboard(ISprite):
    FILE_TEMPLATE = "leaderboard_{0}.txt"
    MAX_RECORDS = 5

    TITLE = "Leaderboard"
    HEADER_NUM = "#"
    HEADER_SCORE = "Score"
    HEADER_DATE = "Date"
    HEADER_NAME = "Name"

    def __init__(
        self,
        canvas: Canvas,
        newScore: int = None,
        newDate: str = None,
        newName: str = None,
        level_key: str = "all",
        top_ratio: float = 0.42,
    ):
        super().__init__(canvas)
        self.levelKey = self._normaliseLevelKey(level_key)
        self.filePath = self.__class__.FILE_TEMPLATE.format(self.levelKey)
        self.title = f"{self.__class__.TITLE} - {level_key}"
        self.top_ratio = max(0.2, min(0.7, float(top_ratio)))

        leaderboard = sorted(self.getLeaderboard(), key=lambda x: x[0], reverse=True)  # sort desc by score

        if newScore is not None:
            leaderboard = self.addToLeaderboard(leaderboard, newScore, newDate, newName)

        self.lines = [
            Leaderboard._formatRow(Leaderboard.HEADER_NUM, Leaderboard.HEADER_SCORE, Leaderboard.HEADER_DATE, Leaderboard.HEADER_NAME, highlight=False)
        ]
        for i in range(len(leaderboard)):
            self.lines.append(Leaderboard._formatRow(i+1, *leaderboard[i], highlight=leaderboard[i][-1] == newName))

        self.line_padding = 12
        self.font_size = 13 if GAME_WIDTH < 1500 else 14
        self.font = f'Courier {self.font_size} bold'

        self.canvas_texts = []

    def addToLeaderboard(self, leaderboard: List[tuple], newScore: int, newDate: str, newName: str):
        # if new score should be on the leaderboard
        if len(leaderboard) < Leaderboard.MAX_RECORDS or newScore > leaderboard[-1][0]:
            # we don't want duplicate records, so remove a pre-existing record for this user if it exists
            for line in leaderboard:
                if line[-1].lower() == newName.lower():
                    if newScore <= line[0]:
                        return leaderboard
                    else:
                        leaderboard.remove(line)
                        break

            newLine = (newScore, newDate, newName)
            for i in range(len(leaderboard)):
                if leaderboard[i][0] < newScore:
                    leaderboard.insert(i, newLine)  # insert at right place in sorted list
                    break
            else:
                leaderboard.append(newLine)
            leaderboard = leaderboard[:Leaderboard.MAX_RECORDS]  # only keep the best 5
            self.writeLeaderboard(leaderboard)  # save to txt file
        return leaderboard

    def first_draw(self):
        super(Leaderboard, self).first_draw()

        self.canvas_texts = []

        x = GAME_WIDTH * 0.5
        y = GAME_HEIGHT * self.top_ratio

        self.canvas_texts.append(self.canvas.create_text(x, y, text=self.title.ljust(len(self.lines[0])), fill="white", font=self.font))
        y += self.font_size + self.line_padding

        for i in range(len(self.lines)):
            self.canvas_texts.append(self.canvas.create_text(x, y, text=self.lines[i], fill="white", font=self.font))
            y += self.font_size + self.line_padding

    def redraw(self):
        super(Leaderboard, self).redraw()
        # assume we never need to update the leaderboard after it's been first_draw()ed
        pass

    def undraw(self):
        super(Leaderboard, self).undraw()
        for canvas_text in self.canvas_texts:
            self.canvas.delete(canvas_text)

    @staticmethod
    def _formatRow(n: Union[int, str], score: Union[int, str], date: str, name: str, highlight: bool):
        if n == "#":
            return f"| {n} | {score:<10} |{date:^14}| {name:>17} |"
        prefix = f"({n})" if highlight else f" {n} "
        return f"|{prefix}|  {score:<9} |{date:^14}| {name:>16}  |"

    @staticmethod
    def parseLeaderboardLine(line: str) -> (Union[int, str], str, str):
        parts = line.split(", ", maxsplit=2)  # using `maxsplit=2` means we don't need to remove commas from name
        score = int(parts[0])
        date = parts[1]
        name = parts[2]
        return score, date, name

    @classmethod
    def _normaliseLevelKey(cls, level_key: str) -> str:
        cleaned = "".join(ch.lower() for ch in str(level_key) if ch.isalnum())
        return cleaned or "all"

    def getLeaderboard(self):
        for encoding in ("utf-8", "cp1252"):
            try:
                with open(self.filePath, encoding=encoding) as f:
                    leaderboard = []
                    for line in f.readlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            leaderboard.append(self.__class__.parseLeaderboardLine(line))
                        except (ValueError, IndexError):
                            continue
                    return leaderboard
            except FileNotFoundError:
                return []
            except UnicodeDecodeError:
                continue
        return []

    def writeLeaderboard(self, leaderboard: List[Tuple[int, str, str]]):
        lines = [f"{score}, {date}, {name}\r\n" for (score, date, name) in leaderboard]
        with open(self.filePath, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)

