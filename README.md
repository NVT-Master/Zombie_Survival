# Zombie Survival

Top-down zombie shooter written in Python (Tkinter + sprite system) with wave progression, boss phases, multiple zombie variants, weapon switching, optional hand control, and optional audio via pygame.

## Current Project Scope

- Wave-based gameplay with dynamic spawn pacing.
- Enemy variants: Normal, Tank, Sprinter, Bomber, Boss.
- Weapon system: Handgun, Shotgun, AK.
- Difficulty presets: De, Trung Binh, Kho, Dia Nguc.
- Story/cutscene hooks between gameplay moments.
- Leaderboard text files for score persistence.

## Requirements

- Python 3.10+ recommended.
- Tkinter (usually bundled with Python on Windows).
- Python packages from requirements.txt:

```bash
pip install -r requirements.txt
```

Note:
- Audio needs pygame.
- Some hand-control paths in game startup may expect an environment that includes mediapipe/opencv.

## Run

```bash
python game.py
```

## Controls

- WASD or Arrow keys: move
- Mouse move: aim
- Left click: shoot
- Q: cycle weapon
- 1/2/3: select Handgun/Shotgun/AK
- Space: dash
- Esc: pause

## Project Structure

```text
game.py
Sprites/
   player/
   enemies/
   ui/
   world/
assets/
   core/
   systems/
   utils/
   audio/
scripts/
tests/
images/
saves/
```

Compatibility wrappers from old paths are still present in some top-level files under Sprites/ and assets/.

## Audio Files

- Music docs: ./assets/audio/music/README.md
- SFX docs: ./assets/audio/sfx/README.md

If audio files are missing, run placeholder generator:

```bash
python scripts/create_audio.py
```

## Test

Run smoke test:

```bash
python test_modules.py
```

Or:

```bash
python tests/test_modules.py
```

## Notes

- This repository contains game code and assets for the Zombie Survival project.
- README content was updated to match the current folder layout and active systems.
