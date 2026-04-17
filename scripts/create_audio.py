"""
Audio Generator - Creates simple placeholder audio files for the game.
Run this once to generate all necessary audio files.
"""

from pathlib import Path


def create_placeholder_audio():
    """Create simple WAV/MP3 placeholder files."""
    project_root = Path(__file__).resolve().parent.parent

    music_dir = project_root / "assets" / "audio" / "music"
    sfx_dir = project_root / "assets" / "audio" / "sfx"

    music_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    print("Creating audio placeholder files...")

    music_files = ["menu_music.mp3", "wave_music.mp3", "boss_music.mp3"]
    for filename in music_files:
        filepath = music_dir / filename
        if not filepath.exists():
            with open(filepath, "wb") as f:
                f.write(b"\xff\xfb\x10\x00" + b"\x00" * 100)
            print(f"Created: {filepath}")
        else:
            print(f"Already exists: {filepath}")

    sfx_files = [
        "shoot_handgun.wav",
        "shoot_shotgun.wav",
        "shoot_rifle.wav",
        "zombie_hit.wav",
        "zombie_death.wav",
        "player_hit.wav",
        "dash.wav",
        "bomb_explode.wav",
    ]

    for filename in sfx_files:
        filepath = sfx_dir / filename
        if not filepath.exists():
            with open(filepath, "wb") as f:
                f.write(b"RIFF" + b"\x24\xf0\x00\x00" + b"WAVE")
                f.write(b"fmt " + b"\x10\x00\x00\x00" + b"\x01\x00\x01\x00")
                f.write(b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00")
                f.write(b"data" + b"\x00\xf0\x00\x00" + b"\x00" * 61632)
            print(f"Created: {filepath}")
        else:
            print(f"Already exists: {filepath}")

    print("Done. Placeholder audio files are ready.")


if __name__ == "__main__":
    create_placeholder_audio()
