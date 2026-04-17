# ZOMBIE SURVIVOR - Top-Down Shooter Game

> A post-apocalyptic survival shooter with progressive wave-based gameplay, multiple enemy types, and player abilities.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.7%2B-green)
![Status](https://img.shields.io/badge/status-playable-brightgreen)

## 🎮 Gameplay Overview

Survive waves of increasingly difficult zombies in a top-down shooter with strategic dash mechanics and team-based enemy behaviors.

### Features
- ✅ **Wave-Based Progression** - 3 challenging waves per difficulty
- ✅ **Multiple Zombie Types** - Tank, Sprinter, Bomber + standard zombies
- ✅ **Player Dash Ability** - Dodge with 2-second cooldown (SPACE key)
- ✅ **Story System** - Dialogue & cutscenes between waves
- ✅ **4 Difficulty Modes** - Dễ, Trung Bình, Khó, Địa Ngục
- ✅ **Audio Support** - Optional background music & sound effects
- ✅ **Leaderboard** - Track your best scores

## 🚀 Quick Start

### 1. Install & Run

```bash
# Clone or extract the game
cd top-down-zombie-shooter

# Install optional audio support
pip install -r requirements.txt

# Run the game
python game.py
```

### 2. Launch Game
- Select username
- Choose difficulty (Dễ, Trung Bình, Khó, or Địa Ngục)
- Pick a map theme
- Customize controls
- Click "Start Game"

## 🎮 Controls

| Input | Action |
|-------|--------|
| **W/A/S/D** | Move |
| **Arrow Keys** | Move (alternative) |
| **Mouse** | Aim |
| **Left Click** | Shoot |
| **Q** | Cycle weapon (Handgun -> Shotgun -> AK) |
| **1 / 2 / 3** | Equip Handgun / Shotgun / AK |
| **SPACE** | Dash/Dodge (2s cooldown) |
| **ESC** | Pause |
| **Enter** | Restart (game over) |

## 🧟 Enemy Types

### Zombie (Normal)
- HP: 10
- Speed: 50 px/s
- Basic threat

### Tank Zombie (NEW)
- HP: 20 (2x)
- Speed: 25 px/s (slower)
- Damage: 2x per hit
- **Strategy**: Keep distance, focus fire

### Sprinter Zombie (NEW)
- HP: 3 (fragile)
- Speed: 90 px/s (fast)
- Low threat individually
- **Strategy**: Group threat, use dash to escape

### Bomber Zombie (NEW)
- HP: 8
- Speed: 45 px/s
- Explodes on death
- Damages in 150px radius
- **Strategy**: Kite away from player

### Boss Zombie
- HP: 28-74 (difficulty dependent)
- Special abilities: Dash, Reinforcements, Hell Skill
- Appears at end of wave 3
- **Strategy**: Solo + dash to dodge attacks

## 📈 Difficulty Progression

### Dễ (Easy)
- Wave 1: 8 normal zombies
- Wave 2: Mix of normal + 2 tanks
- Wave 3: Variety + 1 boss

### Trung Bình (Normal)
- Progressive increase in tank & sprinter ratio
- More challenging wave compositions

### Khó (Hard)
- Heavy sprinter & tank presence
- Boss has regeneration ability

### Địa Ngục (Hell)
- Maximum difficulty
- Boss has special "Hell Skill"
- Frequent reinforcements
- Mostly sprinters & tanks

## 📖 Story Elements

The game includes dialogue sequences:

1. **Intro Cutscene** - Sets up the apocalyptic scenario
2. **Wave Completion** - Story progression between waves
3. **Boss Intro** - Dramatic pre-boss dialogue
4. **Victory** - Ending sequence

*Future: Full visual cutscenes planned*

## 🔊 Audio (Optional)

To enable audio:

1. Install pygame: `pip install pygame`
2. Add music files to `assets/audio/music/`
   - Supported: MP3, WAV, OGG, FLAC
3. Add sound effects to `assets/audio/sfx/`
   - Recommended: WAV format
4. Restart game

See documentation in audio folders for file recommendations.

## 📚 Documentation

- **[README.md](./README.md)** - Setup and gameplay overview
- **[assets/audio/music/README.md](./assets/audio/music/README.md)** - Music file notes
- **[assets/audio/sfx/README.md](./assets/audio/sfx/README.md)** - SFX file notes

## 🎯 Scoring System

| Kill | Points |
|------|--------|
| Normal Zombie | 1 |
| Tank Zombie | 1 |
| Sprinter Zombie | 1 |
| Bomber Zombie | 1 |
| Boss Zombie | 12 |

Score is saved to leaderboard automatically.

## ⌨️ Cheat Codes

Type these while playing:
- `quick` - Double speed for 3 seconds
- `ohno` - Toggle shotgun/handgun (legacy cheat)

## 🖼️ Game Maps

Three distinct themes with unique backgrounds:
1. **Tan The** (Post-Apocalypse) - Burnt landscape
2. **Do Thi Dem** (Night City) - Urban ruins
3. **Sa Mac Bui** (Desert Dust) - Sandy wasteland

## 🐛 Known Issues

- ⚠️ Dash doesn't grant invulnerability frames (planned)
- ⚠️ Bomber explosion has simple visual (enhanced graphics coming)
- ⚠️ Story cutscenes are text-only (full visuals planned)

## 📋 Troubleshooting

**No audio?**
- Install pygame: `pip install pygame`
- Add audio files to `assets/audio/` folders

**Game crashes on startup?**
- Ensure images folder exists
- Python 3.7+ required
- Try: `python -m pip install --upgrade pip`

**Slow performance?**
- Close other applications
- May be normal with 100+ sprites on screen

**Controls not working?**
- Rebind in game menu
- Default: WASD for movement

## 🔮 Planned Features

- [ ] Dash invulnerability frames
- [ ] Full visual cutscenes
- [ ] Additional zombie types (Healer, Splitter)
- [ ] Weapon upgrades
- [ ] Health/ammo pickups
- [ ] Environmental hazards
- [ ] Mobile touch controls
- [ ] Improved leaderboard

## 💻 Technical Details

- **Language**: Python 3.7+
- **GUI**: Tkinter (built-in)
- **Audio**: Pygame (optional)
- **Graphics**: Sprite-based 2D
- **FPS**: 60 target
- **Resolution**: Responsive (720x1280 base)

## 📊 Project Stats

- ~800 lines of new code
- 4 new systems (Audio, Waves, Story, Zombies)
- 4 new zombie types
- Backward compatible with v1.0 saves

## 🏆 High Score Tips

1. **Manage dash cooldown** - Don't waste dash on weak zombies
2. **Prioritize threats** - Kill tanks & bombers first
3. **Group positioning** - Stay near center of map
4. **Weapon switching** - Use both guns strategically
5. **Learn patterns** - Each zombie type has predictable behavior

## 📝 Files Overview

```
Core:
- game.py              Main game loop
- Sprites/Player.py    Player with dash
- Sprites/Zombie.py    Enemy base class

New Systems:
- assets/AudioManager.py     Audio handling
- assets/WaveManager.py      Wave progression
- assets/StoryManager.py     Story system
- Sprites/ZombieVariants.py  Tank, Sprinter, Bomber

Docs:
- README.md
- assets/audio/music/README.md
- assets/audio/sfx/README.md

Utilities:
- scripts/create_audio.py

Tests:
- tests/test_modules.py
```

## 🤝 Contributing

To add features:
1. New zombie type? Add to `ZombieVariants.py`
2. New waves? Modify `WaveManager.WAVE_CONFIGS`
3. New story? Extend `StoryManager.CUTSCENES`

## 📄 License

This game includes adapted sprite assets and is created for educational purposes.

## 🎉 Credits

- **Original Game**: Top-Down Survivor
- **Improvements v2.0**: Full system overhaul with waves, story, and new mechanics
- **Assets**: Various open-source zombie & survivor sprites

---

**Version**: 2.0  
**Last Updated**: April 13, 2026  

**Ready to survive? Run `python game.py` now!**

---

## Quick Links

- 🚀 [Run Game](./game.py)
- 🔊 [Generate Placeholder Audio](./scripts/create_audio.py)
- ✅ [Smoke Test](./tests/test_modules.py)
- ✅ [Legacy Smoke Test Entry](./test_modules.py)
