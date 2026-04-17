# -*- coding: utf-8 -*-
"""Smoke test to verify core game modules can be imported."""


def run_smoke_test() -> int:
    print("=" * 60)
    print("ZOMBIE SHOOTER - MODULE SMOKE TEST")
    print("=" * 60)

    test_results = []

    checks = [
        ("AudioManager", "from assets.systems.AudioManager import AudioManager"),
        ("WaveManager", "from assets.systems.WaveManager import WaveManager, ZombieType"),
        ("StoryManager", "from assets.systems.StoryManager import StoryManager, StorySequence"),
        ("SpatialPartitioning", "from assets.systems.SpatialPartitioning import SpatialGrid, FastCollisionDetector"),
        ("PerformanceConfig", "from assets.systems.PerformanceConfig import ENABLE_SPATIAL_PARTITIONING, SPATIAL_CELL_SIZE"),
    ]

    for label, statement in checks:
        try:
            exec(statement, {})
            print(f"[OK] {label}")
            test_results.append(True)
        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            test_results.append(False)

    # Some sprite modules build PhotoImage frames at import time.
    # Initialize a temporary Tk root so imports are valid in smoke tests.
    try:
        import tkinter as tk

        temp_root = tk.Tk()
        temp_root.withdraw()
        try:
            exec("from Sprites.enemies.ZombieVariants import TankZombie, SprinterZombie, BomberZombie", {})
            print("[OK] Zombie variants")
            test_results.append(True)
        finally:
            temp_root.destroy()
    except Exception as exc:
        print(f"[ERROR] Zombie variants: {exc}")
        test_results.append(False)

    passed = sum(test_results)
    total = len(test_results)
    print("-" * 60)
    print(f"Passed: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(run_smoke_test())

