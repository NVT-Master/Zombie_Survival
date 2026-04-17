# Sound Effects Directory

Add sound effect files here (WAV recommended for low latency).

Recommended sound effects:
- `shoot_handgun.wav` - Handgun shot sound
- `shoot_shotgun.wav` - Shotgun shot sound
- `shoot_rifle.wav` - AK/rifle shot sound
- `zombie_hit.wav` - Zombie takes damage
- `zombie_death.wav` - Zombie dies
- `player_hit.wav` - Player takes damage
- `dash.wav` - Player dash sound
- `bomb_explode.wav` - Bomber zombie explosion
- `barricade_hit.wav` - Barricade takes damage (optional)
- `barricade_break.wav` - Barricade breaks (optional)

If barricade sound files are missing, the game will fallback to:
- `zombie_hit.wav` for barricade hit
- `bomb_explode.wav` for barricade break

Note: Requires pygame to be installed for audio playback:
```bash
pip install pygame
```
