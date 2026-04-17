"""
Story and Cutscene System
"""

from dataclasses import dataclass
from enum import Enum, auto as enum_next
from typing import List, Optional


class StorySequence(Enum):
    """Different story sequences"""
    INTRO = enum_next()
    WAVE_1_COMPLETE = enum_next()
    WAVE_2_COMPLETE = enum_next()
    BOSS_INTRO = enum_next()
    VICTORY = enum_next()


@dataclass
class DialogueLine:
    """A single line of dialogue"""
    speaker: str
    text: str
    duration_seconds: float = 2.0


@dataclass
class Cutscene:
    """A cutscene with dialogue"""
    sequence: StorySequence
    lines: List[DialogueLine]
    background_color: str = "#000000"


class StoryManager:
    """Manages game story, dialogue, and cutscenes"""

    CUTSCENES = {
        StorySequence.INTRO: Cutscene(
            StorySequence.INTRO,
            [
                DialogueLine("NPC Kiet", "{player_name}, cuối cùng bạn đã đến trạm an toàn.", 2.8),
                DialogueLine("NPC Kiet", "Thành phố này đã sụp đổ từ khi virus zombie lan ra.", 3.2),
                DialogueLine("NPC Kiet", "Muốn cứu mọi người, chúng ta phải giữ từng khu vực một.", 3.0),
                DialogueLine("NPC Kiet", "Sống sót qua mỗi đợt tấn công, tôi sẽ mở đường cho bạn.", 3.0),
            ],
            background_color="#1f120d"
        ),
        StorySequence.WAVE_1_COMPLETE: Cutscene(
            StorySequence.WAVE_1_COMPLETE,
            [
                DialogueLine("NPC Kiet", "Bạn đã trụ vững được đợt đầu tiên.", 2.4),
                DialogueLine("NPC Kiet", "Nhưng đây chỉ là tiền trạm, chúng đang học cách săn chúng ta.", 3.0),
            ],
            background_color="#131f2a"
        ),
        StorySequence.BOSS_INTRO: Cutscene(
            StorySequence.BOSS_INTRO,
            [
                DialogueLine("NPC Kiet", "Có thứ gì đó rất lớn đang tiến tới...", 2.8),
                DialogueLine("NPC Kiet", "Trùm zombie xuất hiện rồi!", 2.2),
                DialogueLine("NPC Kiet", "Giữ vị trí, đây là cửa ải để cuối cùng.", 2.8),
            ],
            background_color="#2b0000"
        ),
        StorySequence.VICTORY: Cutscene(
            StorySequence.VICTORY,
            [
                DialogueLine("NPC Kiet", "Bạn đã sống sót qua đợt bão zombie.", 2.5),
                DialogueLine("NPC Kiet", "Nhưng cuộc chiến lớn hơn vẫn đang chờ ở phía trước.", 3.0),
                DialogueLine("NPC Kiet", "Nghỉ ngơi một chút rồi chúng ta đi tiếp.", 2.5),
            ],
            background_color="#001a00"
        ),
    }

    def __init__(self):
        self.current_cutscene: Cutscene = None
        self.current_line_index = 0
        self.line_timer = 0.0
        self.is_playing = False
        self.player_name = "User"

    WAVE_COMPLETE_DIALOGUES = {
        "De": {
            1: [
                DialogueLine("NPC Kiet", "Tuyệt vời, {player_name}! Bạn đã giữ được cổng chính.", 2.7),
                DialogueLine("NPC Lan", "Người bị thương đã được đưa vào hầm trú ẩn.", 2.6),
                DialogueLine("NPC Kiet", "Đợt tiếp theo sẽ đông hơn. Đừng đứng quá lâu.", 2.6),
            ],
            2: [
                DialogueLine("NPC Lan", "Tin xấu: đường tiếp tế vừa bị cắt đứt.", 2.8),
                DialogueLine("NPC Kiet", "{player_name}, bạn là người duy nhất còn đủ sức chiến đấu.", 2.8),
                DialogueLine("NPC Lan", "Có dấu hiệu trùm ở ngoài hàng rào.", 2.6),
            ],
            3: [
                DialogueLine("NPC Kiet", "Khu Dễ đã an toàn tạm thời.", 2.4),
                DialogueLine("NPC Lan", "Nhưng khu Trung Bình đang mất phòng tuyến.", 2.5),
                DialogueLine("NPC Kiet", "Theo tôi, chúng ta đi ngay khi bạn sẵn sàng.", 2.6),
            ],
        },
        "Trung Binh": {
            1: [
                DialogueLine("NPC Bao", "Máy phát điện dự phòng đã khởi động lại.", 2.5),
                DialogueLine("NPC Kiet", "Tốt lắm, {player_name}. Mọi thứ đang nóng dần.", 2.7),
                DialogueLine("NPC Bao", "Sprinter đang xuất hiện nhiều hơn ở hướng đông.", 2.7),
            ],
            2: [
                DialogueLine("NPC Bao", "Camera đêm thấy nhiều bóng lớn đang di chuyển.", 2.8),
                DialogueLine("NPC Lan", "Bomber cũng đã bắt đầu lao vào cổng.", 2.6),
                DialogueLine("NPC Kiet", "Sống qua đợt này, ta mới đủ sức sang khu Khó.", 2.8),
            ],
            3: [
                DialogueLine("NPC Lan", "Khu Trung Bình giữ được, nhưng mặt đất đã vỡ trận.", 2.8),
                DialogueLine("NPC Kiet", "{player_name}, tôi cần bạn ở tiền tuyến khu Khó.", 2.7),
                DialogueLine("NPC Bao", "Tất cả dân được đã đẩy lên xe, lên đường thôi.", 2.6),
            ],
        },
        "Kho": {
            1: [
                DialogueLine("NPC Rook", "Các toán do thám đã mất 2 điểm liên lạc.", 2.8),
                DialogueLine("NPC Kiet", "Phòng tuyến này chỉ còn trông vào bạn, {player_name}.", 2.7),
                DialogueLine("NPC Rook", "Tank đang triển khai theo cặp. Cần đổi vị trí liên tục.", 2.8),
            ],
            2: [
                DialogueLine("NPC Lan", "Hàng rào sắt đã bị băm nát ở cánh tay phải.", 2.7),
                DialogueLine("NPC Rook", "Trùm đã gần đến, nhiệt độ có thể tăng đột biến.", 2.8),
                DialogueLine("NPC Kiet", "Đợt cuối khu Khó sẽ rất thô bạo. Chuẩn bị tinh thần.", 2.9),
            ],
            3: [
                DialogueLine("NPC Rook", "Khu Khó vừa được giảm áp lực.", 2.4),
                DialogueLine("NPC Kiet", "Trạm chỉ huy vừa gọi: Địa Ngục đang mở cổng.", 2.8),
                DialogueLine("NPC Lan", "Nếu vượt qua đêm này, chúng ta còn có hi vọng.", 2.6),
            ],
        },
        "Dia Nguc": {
            1: [
                DialogueLine("NPC Echo", "Tín hiệu vô tuyến đang bị nhiễu rất nặng.", 2.8),
                DialogueLine("NPC Kiet", "{player_name}, đây là va chạm cuối cùng của đêm nay.", 2.7),
                DialogueLine("NPC Echo", "Phát hiện nhiều cụm sinh học cấp độ đỏ.", 2.7),
            ],
            2: [
                DialogueLine("NPC Lan", "Hệ thống của hầm trú ẩn đã quá tải.", 2.6),
                DialogueLine("NPC Echo", "Có 3 mục tiêu trùm đang áp sát trong tầm 200m.", 2.8),
                DialogueLine("NPC Kiet", "Nếu chúng ta gục xuống, thành phố sẽ kết thúc.", 2.7),
            ],
            3: [
                DialogueLine("NPC Kiet", "Bạn đã làm được điều không ai tin là có thật.", 2.6),
                DialogueLine("NPC Lan", "Người sống sót đang theo đến vị trí của bạn.", 2.6),
                DialogueLine("NPC Echo", "Đêm nay kết thúc... nhưng cuộc chiến ngày mai mới bắt đầu.", 2.9),
            ],
        },
    }

    def set_player_name(self, name: str):
        clean_name = (name or "").strip()
        self.player_name = clean_name if clean_name else "User"

    def _format_line(self, line: DialogueLine) -> DialogueLine:
        return DialogueLine(
            speaker=line.speaker,
            text=line.text.format(player_name=self.player_name),
            duration_seconds=line.duration_seconds,
        )

    def _set_cutscene(self, cutscene: Cutscene):
        self.current_cutscene = Cutscene(
            sequence=cutscene.sequence,
            lines=[self._format_line(line) for line in cutscene.lines],
            background_color=cutscene.background_color,
        )
        self.current_line_index = 0
        self.line_timer = 0.0
        self.is_playing = True

    def start_cutscene(self, sequence: StorySequence) -> bool:
        """Start playing a cutscene"""
        if sequence not in self.CUTSCENES:
            return False

        self._set_cutscene(self.CUTSCENES[sequence])
        return True

    def start_intro_cutscene(self, player_name: Optional[str] = None) -> bool:
        if player_name is not None:
            self.set_player_name(player_name)
        return self.start_cutscene(StorySequence.INTRO)

    def start_wave_complete_cutscene(self, wave_number: int, difficulty: str, player_name: Optional[str] = None) -> bool:
        if player_name is not None:
            self.set_player_name(player_name)

        lines = self._get_wave_complete_lines(wave_number, difficulty)
        if not lines:
            return False

        self._set_cutscene(
            Cutscene(
                sequence=StorySequence.WAVE_2_COMPLETE,
                lines=lines,
                background_color="#0f1a1f",
            )
        )
        return True

    def _get_wave_complete_lines(self, wave_number: int, difficulty: str) -> List[DialogueLine]:
        diff_key = difficulty if difficulty in self.WAVE_COMPLETE_DIALOGUES else "De"
        clamped_wave = 1 if wave_number < 1 else (3 if wave_number > 3 else wave_number)
        lines = self.WAVE_COMPLETE_DIALOGUES.get(diff_key, {}).get(clamped_wave)
        if lines:
            return lines

        return [
            DialogueLine("NPC Kiet", "Giằng co được giữ vững trong thời gian ngắn.", 2.6),
            DialogueLine("NPC Kiet", "{player_name}, hãy chuẩn bị cho đợt tấn công tiếp theo.", 2.8),
        ]

    def update(self, dt: float) -> bool:
        """
        Update cutscene playback
        Returns True if cutscene is still playing
        """
        if not self.is_playing or self.current_cutscene is None:
            return False

        self.line_timer += dt

        if self.current_line_index >= len(self.current_cutscene.lines):
            self.is_playing = False
            return False

        current_line = self.current_cutscene.lines[self.current_line_index]
        if self.line_timer >= current_line.duration_seconds:
            self.line_timer = 0.0
            self.current_line_index += 1

        return self.is_playing

    def get_current_dialogue_text(self) -> str:
        """Get text to display for current line"""
        if not self.is_playing or self.current_line_index >= len(self.current_cutscene.lines):
            return ""

        line = self.current_cutscene.lines[self.current_line_index]
        return f"{line.speaker}: {line.text}"

    def get_current_line(self) -> Optional[DialogueLine]:
        if not self.is_playing or self.current_cutscene is None:
            return None
        if self.current_line_index >= len(self.current_cutscene.lines):
            return None
        return self.current_cutscene.lines[self.current_line_index]

    def get_background_color(self) -> str:
        """Get background color for current cutscene"""
        if not self.current_cutscene:
            return "#000000"
        return self.current_cutscene.background_color

    def advance_line(self) -> bool:
        """Advance to next line immediately. Returns True if still playing."""
        if not self.is_playing or self.current_cutscene is None:
            return False

        self.line_timer = 0.0
        self.current_line_index += 1
        if self.current_line_index >= len(self.current_cutscene.lines):
            self.is_playing = False
            return False
        return True

    def skip(self):
        """Skip current cutscene"""
        self.is_playing = False
        self.current_cutscene = None
