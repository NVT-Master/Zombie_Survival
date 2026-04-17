from dataclasses import dataclass

from typing import List, TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from assets.utils.Vectors import Vector2


@dataclass
class SavedState:
    score: int
    hearts: int
    targetNumZombies: float
    playerPosition: "Vector2"
    zombiePositions: List["Vector2"]
    zombieHearts: List[float]
    controls: List[str]
    zombieIsBoss: Optional[List[bool]] = None
    difficulty: str = "Trung Binh"
    maxAliveZombies: int = 5
    normalSpawnTarget: int = 0
    bossSpawnTarget: int = 0
    normalSpawnedCount: int = 0
    bossesSpawnedCount: int = 0
    bossesKilledCount: int = 0

