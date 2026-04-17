# Sound Effects Directory

Put SFX files in this folder.

Main SFX names used by the game:
- shoot_handgun.wav
- shoot_shotgun.wav
- shoot_rifle.wav
- zombie_hit.wav
- zombie_death.wav
- player_hit.wav
- dash.wav
- bomb_explode.wav

Optional SFX:
- barricade_hit.wav
- barricade_break.wav

Fallback behavior:
- If barricade_hit.wav is missing, zombie_hit.wav can be used.
- If barricade_break.wav is missing, bomb_explode.wav can be used.

Format notes:
- WAV is recommended for low-latency shots.
- Keep files short and trimmed to reduce perceived delay.

Audio playback requires pygame:

```bash
pip install pygame
```
