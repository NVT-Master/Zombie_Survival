"""
Wave Management System - Spawns enemies in organized waves
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from enum import Enum, auto as enum_next
from collections import deque

if TYPE_CHECKING:
    from game import Game


class ZombieType(Enum):
    """Different types of zombies"""
    Normal = enum_next()
    Tank = enum_next()
    Sprinter = enum_next()
    Bomber = enum_next()


@dataclass
class WaveConfig:
    """Configuration for a wave"""
    wave_number: int
    total_zombies: int
    zombie_composition: dict  # {ZombieType: count}
    duration_seconds: float  # Time to spawn all zombies
    boss_at_end: bool = False


class WaveManager:
    """Manages wave-based zombie spawning"""

    # Wave configurations by difficulty
    WAVE_CONFIGS = {
        "De": [
            WaveConfig(1, 7, {ZombieType.Normal: 7}, 18, boss_at_end=False),
            WaveConfig(2, 10, {ZombieType.Normal: 8, ZombieType.Tank: 2}, 24, boss_at_end=False),
            WaveConfig(3, 12, {ZombieType.Normal: 6, ZombieType.Sprinter: 3, ZombieType.Tank: 1, ZombieType.Bomber: 2}, 30, boss_at_end=True),
        ],
        "Trung Binh": [
            WaveConfig(1, 10, {ZombieType.Normal: 8, ZombieType.Tank: 2}, 15, boss_at_end=False),
            WaveConfig(2, 15, {ZombieType.Normal: 8, ZombieType.Sprinter: 4, ZombieType.Bomber: 3}, 20, boss_at_end=False),
            WaveConfig(3, 20, {ZombieType.Sprinter: 10, ZombieType.Tank: 5, ZombieType.Bomber: 5}, 25, boss_at_end=True),
        ],
        "Kho": [
            WaveConfig(1, 15, {ZombieType.Normal: 8, ZombieType.Sprinter: 4, ZombieType.Tank: 3}, 18, boss_at_end=False),
            WaveConfig(2, 20, {ZombieType.Sprinter: 8, ZombieType.Tank: 7, ZombieType.Bomber: 5}, 22, boss_at_end=False),
            WaveConfig(3, 25, {ZombieType.Sprinter: 10, ZombieType.Tank: 8, ZombieType.Bomber: 7}, 28, boss_at_end=True),
        ],
        "Dia Nguc": [
            WaveConfig(1, 18, {ZombieType.Sprinter: 10, ZombieType.Tank: 5, ZombieType.Bomber: 3}, 15, boss_at_end=False),
            WaveConfig(2, 25, {ZombieType.Sprinter: 12, ZombieType.Tank: 8, ZombieType.Bomber: 5}, 20, boss_at_end=False),
            WaveConfig(3, 30, {ZombieType.Sprinter: 15, ZombieType.Tank: 10, ZombieType.Bomber: 5}, 25, boss_at_end=True),
        ],
    }

    def __init__(self, game: "Game"):
        self.game = game
        self.current_wave = 0
        self.waves = self.WAVE_CONFIGS.get(game.difficulty, self.WAVE_CONFIGS["De"])
        self.zombies_spawned_this_wave = 0
        self.wave_start_time = 0.0
        self.is_wave_active = False
        self.spawn_queue = deque()  # queue of (time, zombie_type)
        self.pending_spawn_types = deque()
        self.pending_boss_spawn = False

    def start_wave(self, current_time: float):
        """Start a new wave"""
        if self.current_wave >= len(self.waves):
            return

        self.is_wave_active = True
        self.wave_start_time = current_time
        self.zombies_spawned_this_wave = 0

        config = self.waves[self.current_wave]
        self._build_spawn_queue(config)

    def _build_spawn_queue(self, config: WaveConfig):
        """Build spawn times for all zombies in wave"""
        self.spawn_queue.clear()
        self.pending_spawn_types.clear()
        total_time = config.duration_seconds
        zombie_types = []

        # Flatten zombie composition into a list
        for zombie_type, count in config.zombie_composition.items():
            zombie_types.extend([zombie_type] * count)

        # Distribute spawns evenly across wave duration with some randomness
        for i, zombie_type in enumerate(zombie_types):
            spawn_time = (i / max(1, len(zombie_types) - 1)) * total_time if len(zombie_types) > 1 else 0
            # Add some jitter
            import random
            spawn_time += random.uniform(-1, 1)
            spawn_time = max(0, spawn_time)
            self.spawn_queue.append((spawn_time, zombie_type))

        sorted_queue = sorted(self.spawn_queue, key=lambda x: x[0])
        self.spawn_queue = deque(sorted_queue)

    def update(self, current_time: float, spawn_capacity: Optional[int] = None) -> List[ZombieType]:
        """
        Update wave spawning
        Returns list of zombie types to spawn this frame
        """
        to_spawn = []

        if not self.is_wave_active:
            return to_spawn

        elapsed = current_time - self.wave_start_time

        # Move due entries into a pending pool so they are not lost when spawn slots are full.
        while self.spawn_queue and self.spawn_queue[0][0] <= elapsed:
            spawn_time, zombie_type = self.spawn_queue.popleft()
            self.pending_spawn_types.append(zombie_type)

        if spawn_capacity is None:
            spawn_capacity = len(self.pending_spawn_types)
        spawn_capacity = max(0, spawn_capacity)

        for _ in range(min(spawn_capacity, len(self.pending_spawn_types))):
            zombie_type = self.pending_spawn_types.popleft()
            to_spawn.append(zombie_type)
            self.zombies_spawned_this_wave += 1

        # Wave is complete when all zombies have been released for spawn.
        if not self.spawn_queue and not self.pending_spawn_types and self.zombies_spawned_this_wave > 0:
            self.end_wave()

        return to_spawn

    def end_wave(self):
        """End current wave and prepare next one"""
        if self.current_wave < len(self.waves):
            self.pending_boss_spawn = self.waves[self.current_wave].boss_at_end
        self.is_wave_active = False
        self.current_wave += 1

    def is_all_waves_complete(self) -> bool:
        """Check if all waves are done"""
        return self.current_wave >= len(self.waves)

    def get_current_wave_number(self) -> int:
        """Get wave number for UI display (1-indexed)."""
        total_waves = len(self.waves)
        if total_waves == 0:
            return 1

        # While a wave is actively spawning, current_wave points to that wave.
        # After end_wave(), current_wave points to the next wave, so show the
        # previous number until the next wave actually starts.
        if self.is_wave_active:
            display_wave = self.current_wave + 1
        else:
            display_wave = self.current_wave

        return max(1, min(display_wave, total_waves))

    def get_total_waves(self) -> int:
        """Get total number of waves"""
        return len(self.waves)

    def should_spawn_boss_at_wave_end(self) -> bool:
        """Check if a completed wave is waiting to spawn its boss."""
        return self.pending_boss_spawn

    def mark_boss_spawned(self):
        """Clear pending boss spawn state after boss has been created."""
        self.pending_boss_spawn = False
