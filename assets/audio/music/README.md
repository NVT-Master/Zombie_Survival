# Music Directory

Put background music files in this folder.

The game currently looks for these names:
- menu_music.mp3 (main menu)
- wave_music.mp3 (normal gameplay waves)
- boss_music.mp3 (boss approach/spawn)

Supported formats by resolver:
- .mp3
- .wav

Tips:
- Keep music length reasonable for loop transitions.
- Use consistent loudness between tracks to avoid volume jumps.

Audio playback requires pygame:

```bash
pip install pygame
```
