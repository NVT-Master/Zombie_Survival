"""
Game window is portrait for mobile-style play

- Submitted 26/11/2021
"""
from time import time
from random import random
from hashlib import sha1
from os.path import exists
import os
import sys
import subprocess
import importlib.util
from tkinter import *
from datetime import date


def _ensure_supported_runtime():
    """Relaunch with the conda runtime if critical deps are missing in current interpreter."""
    required_modules = ("pygame", "mediapipe")
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
    if not missing:
        return

    # Prevent endless relaunch loops.
    if os.environ.get("GAME_CONDA_RELAY") == "1":
        print("Missing dependencies in runtime:", ", ".join(missing))
        print("Please run with conda environment mtao: conda run -n mtao python game.py")
        return

    print("Current Python is missing required packages:", ", ".join(missing))
    print("Attempting to relaunch with conda environment: mtao")

    conda_candidates = [
        os.environ.get("CONDA_EXE"),
        os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "miniconda3", "Scripts", "conda.exe"),
        os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "miniconda3", "condabin", "conda.bat"),
        "conda",
    ]
    conda_cmd = None
    for candidate in conda_candidates:
        if not candidate:
            continue
        if candidate == "conda" or os.path.exists(candidate):
            conda_cmd = candidate
            break

    if conda_cmd is None:
        print("Conda runtime not found.")
        print("Please run with mtao python directly: C:/ProgramData/miniconda3/envs/mtao/python.exe game.py")
        raise SystemExit(1)

    cmd = [conda_cmd, "run", "-n", "mtao", "python", os.path.abspath(__file__)]
    relay_env = os.environ.copy()
    relay_env["GAME_CONDA_RELAY"] = "1"

    try:
        result = subprocess.run(cmd, env=relay_env)
        raise SystemExit(result.returncode)
    except FileNotFoundError:
        print("Conda command not found. Install required packages in this Python runtime.")
        print("Required: pygame, mediapipe, opencv-python")
        raise SystemExit(1)


_ensure_supported_runtime()

tk = Tk()

from assets.core.Config import GAME_WIDTH, GAME_HEIGHT, WINDOW_GEOMETRY
from assets.core.ISprite import ISprite
from assets.core.Sprite import Sprite
from assets.core.SpriteGroup import SpriteGroup
from assets.core.TextSprite import TextSprite
from assets.utils.Vectors import Vector2

from Sprites.world.BossKeyBg import BossKeyBg
from Sprites.enemies.Bullet import Bullets
from Sprites.ui.HealthIndicator import HealthIndicator
from Sprites.ui.Leaderboard import Leaderboard
from Sprites.player.Player import Player
from Sprites.ui.ScoreIndicator import ScoreIndicator
from Sprites.ui.WaveDisplay import WaveDisplay
from Sprites.enemies.Zombie import Zombie, BossZombie
from Sprites.enemies.ZombieVariants import TankZombie, SprinterZombie, BomberZombie

from assets.systems.AudioManager import AudioManager
from assets.systems.WaveManager import WaveManager, ZombieType
from assets.systems.StoryManager import StoryManager, StorySequence
from assets.systems.HandInputAdapter import HandInputAdapter

from typing import List


UPDATE_INTERVAL_SECS = 1/60  # 60 fps
REDRAW_INTERVAL_SECS = 1/60  # 60 fps
MIN_DELAY = 0.001  # wait at least MIN_DELAY seconds for the next update/draw call

COLOR_GREEN = "#151f13"

IGNORED_KEYSYMS = ["Tab", "Alt_L", "Alt_R", "Shift_L", "Shift_R", "BackSpace"]  # ignore these keys when choosing controls
ARROW_KEYSYMS = ["Up", "Left", "Down", "Right"]  # the direction keys
ARROW_KEYSYMS_REPR = ["^", "<", "v", ">"]  # the direction keys


def keysymToSymbol(keysym: str):
    if keysym in ARROW_KEYSYMS:
        return ARROW_KEYSYMS_REPR[ARROW_KEYSYMS.index(keysym)]
    if len(keysym) == 1 and keysym.islower():
        return keysym.upper()
    return keysym


class Game:
    # time in milliseconds between each zombie spawn
    ZOMBIE_SPAWN_COOLDOWN: int = 500
    DEFAULT_DIFFICULTY = "De"
    DIFFICULTY_CONFIGS = {
        "De": {
            "max_alive": 3,
            "normal_target": 7,
            "boss_target": 1,
            "spawn_cooldown_ms": 1000,
            "boss_hearts": 28,
            "boss_reinforcements": 2,
            "boss_regen": False,
            "hud_color": "#77e596",
            "boss_hell_skill": False
        },
        "Trung Binh": {
            "max_alive": 5,
            "normal_target": 15,
            "boss_target": 1,
            "spawn_cooldown_ms": 650,
            "boss_hearts": 42,
            "boss_reinforcements": 3,
            "boss_regen": False,
            "hud_color": "#8dd8ff",
            "boss_hell_skill": False
        },
        "Kho": {
            "max_alive": 7,
            "normal_target": 20,
            "boss_target": 2,
            "spawn_cooldown_ms": 480,
            "boss_hearts": 56,
            "boss_reinforcements": 4,
            "boss_regen": True,
            "hud_color": "#ffd36a",
            "boss_hell_skill": False,
            "barricade_hp": 40
        },
        "Dia Nguc": {
            "max_alive": 9,
            "normal_target": 25,
            "boss_target": 3,
            "spawn_cooldown_ms": 350,
            "boss_hearts": 74,
            "boss_reinforcements": 5,
            "boss_regen": True,
            "hud_color": "#ff6b6b",
            "boss_hell_skill": True,
            "barricade_hp": 55
        }
    }
    DEFAULT_MAP_THEME = "Tan The"
    MAP_THEMES = ("Tan The", "Do Thi Dem", "Sa Mac Bui")
    DIFFICULTY_ORDER = ["De", "Trung Binh", "Kho", "Dia Nguc"]  # Order progression
    BOSS_MUSIC_START_SECONDS = 2.0

    def __init__(self, master):
        self.tk = master
        self.tk.geometry(WINDOW_GEOMETRY)
        self.tk.resizable(False, False)

        self.canvas = Canvas(
            self.tk,
            width=GAME_WIDTH,
            height=GAME_HEIGHT,
            bg=COLOR_GREEN,
            cursor="hand2",
            highlightthickness=0
        )
        self.canvas.pack(expand=YES, fill=BOTH)

        self.started = False
        self.isGameOver: bool = False
        self.isStageComplete = False
        self.username = "User"
        self.controls: List[str] = ["w", "a", "s", "d"]
        self.difficulty = self.__class__.DEFAULT_DIFFICULTY
        self.currentDifficultyIndex = 0  # Track progression
        self.mapTheme = self.__class__.DEFAULT_MAP_THEME
        self.hudColor = "#8dd8ff"

        self.sprites: List[ISprite] = []
        self.bullets = None
        self.player = None
        self.zombies = None
        self.score: int = 0
        self.scoreIndicator = None
        self.pausedIndicator = None
        self.pauseRestartBtn = None
        self.pauseHomeBtn = None
        self.pauseRestartWindow = None
        self.pauseHomeWindow = None
        self.stageCompleteBackBtn = None
        self.stageCompleteNextBtn = None
        self.stageCompleteBackWindow = None
        self.stageCompleteNextWindow = None
        self.stageCompleteTimer = None
        self.gameOverRestartBtn = None
        self.gameOverHomeBtn = None
        self.gameOverRestartWindow = None
        self.gameOverHomeWindow = None
        self.bossKeyBg = None
        self.customBackgroundImage = None
        self.hellWarningOverlay = None
        self.barricadeEnabled: bool = False
        self.barricadeMaxHp: int = 0
        self.barricadeHp: int = 0
        self.barricadeY: float = GAME_HEIGHT * 0.58
        self.barricadeLine = None
        self.barricadeHpBg = None
        self.barricadeHpFg = None
        self.barricadeHpText = None
        self.barricadeCracks = []
        self.lastBarricadeHitSfxTime: float = 0.0
        self.barricadeHitSfxCooldown: float = 0.14
        self.targetNumZombies: float = 0
        self.maxAliveZombies: int = 5
        self.zombieSpawnCooldownMs: int = self.__class__.ZOMBIE_SPAWN_COOLDOWN
        self.normalSpawnTarget: int = 15
        self.bossSpawnTarget: int = 1
        self.normalSpawnedCount: int = 0
        self.bossesSpawnedCount: int = 0
        self.bossesKilledCount: int = 0
        self.killTargetTotal: int = 0
        self.killedCountTotal: int = 0
        self.bossCanRegenerate: bool = False
        self.bossHasHellSkill: bool = False
        self.bossHearts: int = 42
        self.bossReinforcements: int = 3
        self.isStageComplete: bool = False
        self.currentBoss = None
        self.dontSpawnZombie: bool = True
        self.updateScheduled: bool = False
        self.redrawScheduled: bool = False
        self.paused: bool = True
        self.lastAudioRetryTime: float = 0.0
        self.bossApproachCuePlayed: bool = False
        self.assetsPrewarmed: bool = False

        # Initialize managers
        self.audioManager = AudioManager()
        self.waveManager = None  # Will be initialized on game start
        self.storyManager = StoryManager()
        self.handInput = HandInputAdapter(enable_at_start=False)  # Hand gesture control
        self.handPreviewPanel = None
        self.handPreviewImage = None
        self.handPreviewPlaceholder = None
        self.handPreviewTitle = None
        self.handPreviewStatus = None
        self.handPreviewPhoto = None
        self.handPreviewLastData = None
        self.handPreviewVersion = 0
        self.isStoryBlockingGameplay = False
        self.storyResumeAction = None
        self.storyDialoguePanel = None
        self.storyDialoguePortraitBg = None
        self.storyDialoguePortraitFace = None
        self.storyDialoguePortraitTag = None
        self.storyDialogueSpeaker = None
        self.storyDialogueText = None
        self.storyDialogueHint = None
        self.storyTypewriterLineKey = None
        self.storyTypewriterElapsed = 0.0
        self.storyTypewriterChars = 0
        self.storyTypewriterSpeed = 36.0

        # Adaptive performance state (auto quality scaling).
        self.frameTimeEma = UPDATE_INTERVAL_SECS
        self.performanceLevel = 0
        self.frameCounter = 0
        self.handAutoStartPending = False
        self.handAimPos = None
        self.handAimVisible = False
        self.handAimCursorRing = None
        self.handAimCursorCrossH = None
        self.handAimCursorCrossV = None
        self.handShootHoldUntil = 0.0
        self.handMoveXFiltered = 0.0
        self.handMoveYFiltered = 0.0
        self.handMoveLeftActive = False
        self.handMoveRightActive = False
        self.handMoveUpActive = False
        self.handMoveDownActive = False

        self.createForm()

        tk.bind('<Escape>', lambda e: self.togglePaused())
        tk.bind('<Control-Escape>', lambda e: self.toggleBossKey())
        tk.bind('<Return>', self._handleReturnKey)
        tk.bind('<space>', self._handleSpaceKey)
        tk.bind('<b>', lambda e: self.stageCompleteBack())
        tk.bind('<n>', lambda e: self.stageCompleteNext())
        tk.bind('<r>', lambda e: self.gameOverRestart())
        tk.bind('<h>', lambda e: self._handleHomeShortcut())
        tk.bind('<g>', lambda e: self._enableHandControl())  # 'g' to enable/retry hand gesture control
        tk.bind('<G>', lambda e: self._disableHandControl())  # 'Shift+g' to disable hand gesture control
        tk.bind('<F8>', lambda e: self._testAudioOutput())  # quick audio test
        tk.bind('<F9>', lambda e: self._adjustAudioVolume(-0.1))
        tk.bind('<F10>', lambda e: self._adjustAudioVolume(0.1))
        tk.protocol("WM_DELETE_WINDOW", self.onClose)

        self.lastUpdateTime = time()

    # noinspection PyAttributeOutsideInit
    def createForm(self):
        """Create main menu with cleaner layout"""
        font_title = "Helvetica 32 bold"
        font_header = "Helvetica 14 bold"
        font_normal = "Helvetica 12"

        center_x = GAME_WIDTH * 0.5
        center_y = GAME_HEIGHT * 0.5

        self._drawPostApocalypseBackground(menu_mode=True)
        self._playMusicTrack("menu_music.mp3", loops=-1, fade_in=300)

        # Main title panel - Compact
        panel_w = min(500, GAME_WIDTH - 50)
        panel_h = min(700, GAME_HEIGHT - 80)
        panel_left = center_x - panel_w * 0.5
        panel_top = 30
        panel_right = center_x + panel_w * 0.5
        panel_bottom = panel_top + panel_h

        # Panel border
        self.canvas.create_rectangle(
            panel_left - 8, panel_top - 8, panel_right + 8, panel_bottom + 8,
            fill="#0a1f16", outline="#1ec773", width=3
        )
        self.canvas.create_rectangle(
            panel_left, panel_top, panel_right, panel_bottom,
            fill="#0f2817", outline="#2f8e5c", width=2
        )

        # Title
        self.canvas.create_text(
            center_x, panel_top + 25,
            text="ZOMBIE", fill="#1ec773", font=font_title
        )
        self.canvas.create_text(
            center_x, panel_top + 65,
            text="SURVIVOR", fill="#f2fff5", font=font_title
        )
        self.canvas.create_text(
            center_x, panel_top + 100,
            text="v2.0", fill="#9bd7b1", font="Helvetica 14"
        )

        current_y = panel_top + 130

        # ===== PLAYER NAME =====
        self.canvas.create_text(
            panel_left + 20, current_y,
            text="Tên nhân vật:", fill="#d5f5df", font=font_header, anchor="w"
        )
        current_y += 35

        self.usernameInput = Entry(
            self.tk, width=25, font="Helvetica 14 bold",
            justify=CENTER, bg="#e8fff1", relief=SOLID, bd=2
        )
        self.usernameInput.bind("<Return>", lambda e: self.submitForm())
        self.canvas.create_window(center_x, current_y, window=self.usernameInput, width=350, height=38)
        current_y += 50

        # ===== DIFFICULTY =====
        self.canvas.create_text(
            panel_left + 20, current_y,
            text="Che do kho:", fill="#d5f5df", font=font_header, anchor="w"
        )
        current_y += 32

        self.difficultyVar = StringVar(self.tk, value=self.__class__.DEFAULT_DIFFICULTY)
        self.difficultyMenu = OptionMenu(self.tk, self.difficultyVar, *self.__class__.DIFFICULTY_CONFIGS.keys())
        self.difficultyMenu.configure(
            font="Helvetica 12 bold", bg="#e8fff1", fg="#0d2f20",
            activebackground="#d6ffe7", activeforeground="#0d2f20",
            highlightthickness=0, relief=SOLID, bd=1
        )
        self.canvas.create_window(center_x, current_y, window=self.difficultyMenu, width=320, height=32)
        current_y += 50

        # ===== MAP THEME =====
        self.canvas.create_text(
            panel_left + 20, current_y,
            text="Ban do:", fill="#d5f5df", font=font_header, anchor="w"
        )
        current_y += 32

        self.mapVar = StringVar(self.tk, value=self.__class__.DEFAULT_MAP_THEME)
        self.mapMenu = OptionMenu(self.tk, self.mapVar, *self.__class__.MAP_THEMES)
        self.mapMenu.configure(
            font="Helvetica 12 bold", bg="#e8fff1", fg="#0d2f20",
            activebackground="#d6ffe7", activeforeground="#0d2f20",
            highlightthickness=0, relief=SOLID, bd=1
        )
        self.canvas.create_window(center_x, current_y, window=self.mapMenu, width=320, height=32)
        current_y += 55

        # ===== CONTROLS (Compact) =====
        self.canvas.create_text(
            panel_left + 20, current_y,
            text="Điều khiển:", fill="#d5f5df", font=font_header, anchor="w"
        )
        current_y += 30

        # Arrows showing keys (compact grid)
        self.controlsInputs = []
        control_labels = ["^ Len", "< Trai", "v Xuong", "> Phai"]
        controlsInputsPositions = (
            (center_x, current_y),
            (center_x - 80, current_y + 50),
            (center_x, current_y + 50),
            (center_x + 80, current_y + 50),
        )

        for i in range(len(self.controls)):
            entry = Entry(
                self.tk, width=2, font="Helvetica 18 bold",
                justify=CENTER, bg="#e8fff1", relief=SOLID, bd=1
            )
            entry.insert(0, keysymToSymbol(self.controls[i]))
            entry.configure(state="readonly")
            entry.bind("<KeyPress>", lambda e, entry=entry: self.controlsInputKeypress(entry, e))
            entry.keysym = self.controls[i]
            self.controlsInputs.append(entry)
            self.canvas.create_window(*controlsInputsPositions[i], window=entry, width=50, height=45)

        current_y += 120

        # ===== START BUTTON =====
        self.usernameBtn = Button(
            self.tk, text="Bắt đầu trận chiến", bg="#1ec773", fg="white",
            activebackground="#18a861", activeforeground="white",
            relief=FLAT, font="Helvetica 16 bold", command=self.submitForm, cursor="hand2"
        )
        self.canvas.create_window(center_x, panel_bottom - 35, window=self.usernameBtn, width=280, height=50)

        self.usernameInput.focus_set()

    def start(self):
        self.started = True

        if self.stageCompleteTimer:
            self.tk.after_cancel(self.stageCompleteTimer)
            self.stageCompleteTimer = None

        self._destroyStageCompleteButtons()
        self._destroyGameOverButtons()
        self._destroyPauseMenuButtons()
        self._clearBarricadeUI()
        self._resetHandPreviewOverlay()
        self._clearStoryDialogueOverlay()
        self.storyManager.skip()
        self.isStoryBlockingGameplay = False
        self.storyResumeAction = None
        self.canvas.delete('all')
        del self.sprites

        self.isGameOver: bool = False
        self.isStageComplete = False

        self.sprites: List[ISprite] = []

        self._drawPostApocalypseBackground(menu_mode=False)
        self._ensureHellWarningOverlay()

        self.bullets = Bullets(self)
        self.sprites.append(self.bullets)

        self.player = Player(self, self.bullets)
        self.player.setupKeyBindings()
        self.sprites.append(self.player)

        self.zombies = SpriteGroup(self.canvas)
        self.sprites.append(self.zombies)

        self.sprites.append(HealthIndicator(self.canvas, self.player))

        self.score: int = 0
        self.scoreIndicator = ScoreIndicator(self)
        self.sprites.append(self.scoreIndicator)

        self.waveDisplay = WaveDisplay(self)
        self.sprites.append(self.waveDisplay)

        self.pausedIndicator = Sprite(self.canvas, "images/Emojis/23f8.png")
        self.pausedIndicator.position = Vector2(GAME_WIDTH, GAME_HEIGHT) / 2
        self.sprites.append(self.pausedIndicator)
        self._createPauseMenuButtons()

        self.bossKeyBg = BossKeyBg(self.canvas)
        self.sprites.append(self.bossKeyBg)

        config = self.__class__.DIFFICULTY_CONFIGS.get(self.difficulty, self.__class__.DIFFICULTY_CONFIGS[self.__class__.DEFAULT_DIFFICULTY])
        self.maxAliveZombies = config["max_alive"]
        self.normalSpawnTarget = config["normal_target"]
        self.bossSpawnTarget = config["boss_target"]
        self.zombieSpawnCooldownMs = config["spawn_cooldown_ms"]
        self.bossCanRegenerate = config["boss_regen"]
        self.bossHearts = config["boss_hearts"]
        self.bossReinforcements = config["boss_reinforcements"]
        self.bossHasHellSkill = config.get("boss_hell_skill", False)
        self.hudColor = config.get("hud_color", "#8dd8ff")
        self.targetNumZombies = float(self.maxAliveZombies)
        self.normalSpawnedCount = 0
        self.bossesSpawnedCount = 0
        self.bossesKilledCount = 0
        self.killTargetTotal = 0
        self.killedCountTotal = 0
        self.currentBoss = None
        self.dontSpawnZombie: bool = False

        self._setupBarricade(config)

        # Preload expensive enemy directional assets once to avoid spawn stutter.
        self._prewarmGameplayAssets()

        # Initialize wave system
        self.waveManager = WaveManager(self)
        self.waveManager.start_wave(time())
        self._playMusicTrack("wave_music.mp3", loops=-1, fade_in=300)
        self.bossApproachCuePlayed = False

        # Calculate kill target for current wave (will be per-wave, not global)
        self._updateKillTargetForWave()
        self.handAutoStartPending = False

        self.storyManager.set_player_name(self.username)
        if self.currentDifficultyIndex == 0 and self.waveManager and self.waveManager.current_wave == 0:
            if self.storyManager.start_intro_cutscene(self.username):
                self.isStoryBlockingGameplay = True
                self.storyResumeAction = "resume_game"

        self.paused = False

    def _ensureHellWarningOverlay(self):
        if self.hellWarningOverlay is None:
            self.hellWarningOverlay = self.canvas.create_rectangle(
                0,
                0,
                GAME_WIDTH,
                GAME_HEIGHT,
                fill="#d82727",
                outline="",
                stipple="gray50",
                state="hidden"
            )

    def triggerHellWarning(self):
        if not self.started or self.isGameOver or self.isStageComplete:
            return
        self._ensureHellWarningOverlay()

        self.canvas.itemconfigure(self.hellWarningOverlay, state="normal")
        self.canvas.tag_raise(self.hellWarningOverlay)

        def _hide_overlay():
            if self.hellWarningOverlay is not None:
                self.canvas.itemconfigure(self.hellWarningOverlay, state="hidden")

        # Two quick flashes so players can react before boss skill lands.
        self.tk.after(120, _hide_overlay)
        self.tk.after(240, lambda: self.canvas.itemconfigure(self.hellWarningOverlay, state="normal") if self.hellWarningOverlay is not None else None)
        self.tk.after(360, _hide_overlay)

    def _setupBarricade(self, config: dict):
        self.barricadeEnabled = self.difficulty in ("Kho", "Dia Nguc")
        self.barricadeMaxHp = int(config.get("barricade_hp", 0)) if self.barricadeEnabled else 0
        self.barricadeHp = self.barricadeMaxHp
        self._clearBarricadeUI()
        if self.barricadeEnabled and self.barricadeMaxHp > 0:
            self._createBarricadeUI()

    def _hasActiveBarricade(self) -> bool:
        return self.barricadeEnabled and self.barricadeHp > 0

    def getBarricadeY(self) -> float:
        return self.barricadeY

    def damageBarricade(self, amount: int = 1):
        if not self._hasActiveBarricade():
            return

        current_time = time()
        if current_time - self.lastBarricadeHitSfxTime >= self.barricadeHitSfxCooldown:
            self._playBarricadeHitSfx()
            self.lastBarricadeHitSfxTime = current_time

        self.barricadeHp = max(0, self.barricadeHp - max(1, int(amount)))
        self._updateBarricadeUI()
        if self.barricadeHp <= 0:
            self._breakBarricade()

    def isPlayerProtectedByBarricade(self) -> bool:
        return self._hasActiveBarricade()

    def _createBarricadeUI(self):
        y = self.barricadeY
        self.barricadeLine = self.canvas.create_rectangle(
            30,
            y - 5,
            GAME_WIDTH - 30,
            y + 5,
            fill="#5a3b1a",
            outline="#d3a15e",
            width=2
        )
        self.barricadeHpBg = self.canvas.create_rectangle(
            GAME_WIDTH * 0.35,
            y - 24,
            GAME_WIDTH * 0.65,
            y - 14,
            fill="#2f2f2f",
            outline="#000000",
            width=1
        )
        self.barricadeHpFg = self.canvas.create_rectangle(
            GAME_WIDTH * 0.35 + 1,
            y - 23,
            GAME_WIDTH * 0.65 - 1,
            y - 15,
            fill="#6be27a",
            outline=""
        )
        self.barricadeHpText = self.canvas.create_text(
            GAME_WIDTH * 0.5,
            y - 34,
            text="Hang rao: 100%",
            fill="#ffe0a3",
            font="Helvetica 11 bold"
        )

        crack_xs = (
            GAME_WIDTH * 0.20,
            GAME_WIDTH * 0.32,
            GAME_WIDTH * 0.44,
            GAME_WIDTH * 0.56,
            GAME_WIDTH * 0.68,
            GAME_WIDTH * 0.80,
        )
        for i, x in enumerate(crack_xs):
            y_shift = ((i % 3) - 1) * 2
            crack = self.canvas.create_line(
                x - 10,
                y - 2 + y_shift,
                x,
                y + 5 + y_shift,
                x + 10,
                y - 1 + y_shift,
                fill="#f4cc88",
                width=2,
                smooth=True,
                state="hidden"
            )
            self.barricadeCracks.append(crack)

        self._updateBarricadeUI()

    def _updateBarricadeUI(self):
        if self.barricadeHpBg is None or self.barricadeHpFg is None or self.barricadeHpText is None:
            return

        left = GAME_WIDTH * 0.35
        right = GAME_WIDTH * 0.65
        inner_left = left + 1
        inner_right = right - 1
        width = max(0.0, inner_right - inner_left)

        ratio = 0.0 if self.barricadeMaxHp <= 0 else max(0.0, min(1.0, self.barricadeHp / self.barricadeMaxHp))
        fg_right = inner_left + width * ratio
        self.canvas.coords(self.barricadeHpFg, inner_left, self.barricadeY - 23, fg_right, self.barricadeY - 15)

        if ratio > 0.6:
            color = "#6be27a"
            crack_color = "#d8b078"
        elif ratio > 0.3:
            color = "#ffce63"
            crack_color = "#d9895b"
        else:
            color = "#ff7a7a"
            crack_color = "#c35749"
        self.canvas.itemconfig(self.barricadeHpFg, fill=color)
        self.canvas.itemconfig(self.barricadeHpText, text=f"Hang rao: {int(ratio * 100)}%")

        visible_cracks = int((1.0 - ratio) * len(self.barricadeCracks))
        for idx, crack in enumerate(self.barricadeCracks):
            state = "normal" if idx < visible_cracks else "hidden"
            self.canvas.itemconfig(crack, state=state, fill=crack_color)

    def _breakBarricade(self):
        if self.barricadeLine is not None:
            self.canvas.itemconfig(self.barricadeLine, fill="#3f3f3f", outline="#888888")
        if self.barricadeHpText is not None:
            self.canvas.itemconfig(self.barricadeHpText, text="Hang rao da hong!", fill="#ff6b6b")
        for crack in self.barricadeCracks:
            self.canvas.itemconfig(crack, state="normal", fill="#8a8a8a")

        self._playBarricadeBreakSfx()

    def _playBarricadeHitSfx(self):
        hit_name = "barricade_hit.wav"
        fallback_name = "zombie_hit.wav"
        if not self.audioManager.play_sfx(hit_name, volume=0.65):
            self.audioManager.play_sfx(fallback_name, volume=0.45)

    def _playBarricadeBreakSfx(self):
        break_name = "barricade_break.wav"
        fallback_name = "bomb_explode.wav"
        if not self.audioManager.play_sfx(break_name, volume=0.8):
            self.audioManager.play_sfx(fallback_name, volume=0.7)

    def _playBomberExplosionSfx(self):
        if self.audioManager.play_sfx("bomb_explode.wav", volume=0.95):
            return
        if self.audioManager.play_sfx("void_zombie.mp3", volume=0.9):
            return
        self.audioManager.play_sfx("zombie_death.wav", volume=0.8)

    def _clearBarricadeUI(self):
        for item_name in ("barricadeLine", "barricadeHpBg", "barricadeHpFg", "barricadeHpText"):
            item = getattr(self, item_name)
            if item is not None:
                self.canvas.delete(item)
                setattr(self, item_name, None)

        for crack in self.barricadeCracks:
            self.canvas.delete(crack)
        self.barricadeCracks = []

    def restart(self):
        if not self.isGameOver:
            return
        else:
            self.start()

    def restartFromPause(self):
        if not self.started:
            return
        self.start()

    def goHome(self):
        if self.stageCompleteTimer:
            self.tk.after_cancel(self.stageCompleteTimer)
            self.stageCompleteTimer = None

        self.storyManager.skip()
        self._clearStoryDialogueOverlay()
        self.isStoryBlockingGameplay = False
        self.storyResumeAction = None

        self.paused = True
        self.started = False
        self.isGameOver = False
        self.isStageComplete = False
        self.player = None
        self.zombies = None
        self.bullets = None
        self.score = 0
        self.currentBoss = None
        self.barricadeEnabled = False
        self.barricadeMaxHp = 0
        self.barricadeHp = 0
        self._clearBarricadeUI()
        self._destroyStageCompleteButtons()
        self._destroyGameOverButtons()
        self._destroyPauseMenuButtons()
        self._resetHandPreviewOverlay()
        self.canvas.delete("all")
        self.createForm()

    def submitForm(self):
        if self.started:
            return

        username = self.usernameInput.get()
        if len(username) == 0:
            self.usernameInput.configure(bg="red")
            self.tk.after(300, lambda: self.usernameInput.configure(bg="white"))
            return
        self.username = username
        self.storyManager.set_player_name(self.username)

        self.controls = [entry.keysym for entry in self.controlsInputs]
        self.difficulty = self.difficultyVar.get()
        self.mapTheme = self.mapVar.get()

        self.paused = False

    def controlsInputKeypress(self, entry: Entry, e):
        keysym = e.keysym
        if keysym in IGNORED_KEYSYMS:
            return

        if len(keysym) == 1:
            # if it's uppercase, the player would need to hold shift for every control
            # so make it lowercase
            keysym = keysym.lower()
        entry.keysym = keysym
        entry.configure(state=NORMAL)
        entry.delete(0, END)
        entry.insert(0, keysymToSymbol(keysym))
        entry.configure(state="readonly")

    def update(self):
        startTime = time()
        dt = startTime - self.lastUpdateTime
        dt = min(dt, 0.05)
        self._updatePerformanceState(dt)

        # Finalize any in-progress async hand-camera startup without blocking UI.
        self.handInput.poll_startup()

        can_run_gameplay = (not self.paused) and (not self.isStoryBlockingGameplay)

        # Apply hand gesture input if enabled
        if self.handInput.enabled and self.started and can_run_gameplay:
            self._applyHandGestureInput()

        self._maintainAudioPlayback(startTime)

        # Update spatial grid for fast collision detection before sprite updates
        if can_run_gameplay and hasattr(self.bullets, 'update_spatial_grid'):
            self.bullets.update_spatial_grid()

        if can_run_gameplay:
            for sprite in self.sprites:
                sprite.update(dt)

        # Update story/cutscenes
        was_story_playing = self.storyManager.is_playing
        self.storyManager.update(dt)
        self._updateStoryTypewriter(dt)
        if was_story_playing and not self.storyManager.is_playing:
            self._onStoryFinished()

        # Update wave system and spawn waves
        if can_run_gameplay and self.waveManager and not self.isGameOver and not self.isStageComplete:
            available_slots = max(0, self.maxAliveZombies - len(self.zombies.children))
            spawn_capacity = available_slots
            if self.difficulty == "De":
                # Keep easy mode smooth by avoiding multi-zombie burst spawns.
                spawn_capacity = min(spawn_capacity, 1)
            # If a frame is already heavy, limit how many zombies are introduced at once.
            if dt > 0.030:
                spawn_capacity = min(spawn_capacity, 1)
            elif dt > 0.022:
                spawn_capacity = min(spawn_capacity, 2)

            # Global burst cap helps avoid frame spikes on late waves.
            spawn_capacity = min(spawn_capacity, 2)
            if self.waveManager.should_spawn_boss_at_wave_end():
                spawn_capacity = min(spawn_capacity, 1)

            self._updateBossApproachAudio()

            zombies_to_spawn = self.waveManager.update(startTime, spawn_capacity)
            for zombie_type in zombies_to_spawn:
                if zombie_type == ZombieType.Normal:
                    self.spawnZombie()
                else:
                    self.spawnZombieType(zombie_type)

            # Check if boss should spawn at end of wave
            if self.waveManager.should_spawn_boss_at_wave_end() and self.shouldSpawnBoss():
                self.spawnBoss()
                self.waveManager.mark_boss_spawned()

        # Old spawn system (disable wave-based)
        if can_run_gameplay and not self.isGameOver and not self.isStageComplete and not self.dontSpawnZombie and not self.waveManager:
            spawned = False
            if self.shouldSpawnBoss():
                self.spawnBoss()
                spawned = True
            elif self.shouldSpawnNormalZombie():
                self.spawnZombie()
                spawned = True

            if spawned:
                self.dontSpawnZombie = True
                self.tk.after(self.zombieSpawnCooldownMs, self._unlockZombieSpawn)

        if can_run_gameplay:
            self.checkStageCompletion()

        self.updateScheduled = False
        if not self.paused or self.storyManager.is_playing:
            self.lastUpdateTime = startTime
            target_update_interval = UPDATE_INTERVAL_SECS
            if self.performanceLevel >= 2:
                target_update_interval = 1 / 50
            elif self.performanceLevel == 1:
                target_update_interval = 1 / 55

            remainingTime = target_update_interval - (time() - startTime)
            if remainingTime < MIN_DELAY:
                remainingTime = MIN_DELAY

            self.updateScheduled = True
            self.tk.after(int(remainingTime * 1000), self.update)

    def _unlockZombieSpawn(self):
        self.dontSpawnZombie = False

    def _prewarmGameplayAssets(self):
        if self.assetsPrewarmed:
            return
        try:
            for zombie_cls in (Zombie, TankZombie, SprinterZombie, BomberZombie, BossZombie):
                if hasattr(zombie_cls, "_get_directional_frames"):
                    zombie_cls._get_directional_frames()
            self.assetsPrewarmed = True
        except Exception as exc:
            print(f"Asset prewarm warning: {exc}")

    def _updateBossApproachAudio(self):
        if not self.started or self.isGameOver:
            return
        if self.currentBoss is not None and not self.currentBoss.destroyed:
            return

        pending_boss = False
        if self.waveManager:
            pending_boss = self.waveManager.should_spawn_boss_at_wave_end()
        else:
            pending_boss = self.normalSpawnedCount >= self.normalSpawnTarget and self.bossesSpawnedCount < self.bossSpawnTarget

        if pending_boss and not self.bossApproachCuePlayed:
            if self._playMusicTrack(
                "boss_music.mp3",
                loops=-1,
                fade_in=220,
                start_at_seconds=self.BOSS_MUSIC_START_SECONDS,
            ):
                self.bossApproachCuePlayed = True
        elif not pending_boss:
            self.bossApproachCuePlayed = False

    def shouldSpawnNormalZombie(self) -> bool:
        return self.normalSpawnedCount < self.normalSpawnTarget and len(self.zombies.children) < self.maxAliveZombies

    def shouldSpawnBoss(self) -> bool:
        if self.bossesSpawnedCount >= self.bossSpawnTarget:
            return False
        if self.normalSpawnedCount < self.normalSpawnTarget:
            return False
        if self.currentBoss is not None and not self.currentBoss.destroyed:
            return False
        return len(self.zombies.children) < self.maxAliveZombies

    def redraw(self):
        startTime = time()

        for sprite in self.sprites:
            sprite.redraw()

        if self.started:
            self._drawHandAimReticle()

        if self.started:
            self._drawHandCameraOverlay()

        self._drawStoryDialogueOverlay()

        self.redrawScheduled = False
        if not self.paused or self.storyManager.is_playing:
            target_redraw_interval = REDRAW_INTERVAL_SECS
            if self.performanceLevel >= 2:
                target_redraw_interval = 1 / 48
            elif self.performanceLevel == 1:
                target_redraw_interval = 1 / 55

            remainingTime = target_redraw_interval - (time() - startTime)
            if remainingTime < MIN_DELAY:
                remainingTime = MIN_DELAY

            self.redrawScheduled = True
            self.tk.after(int(remainingTime * 1000), self.redraw)

    def _drawStoryDialogueOverlay(self):
        line = self.storyManager.get_current_line()
        if line is None:
            self._clearStoryDialogueOverlay()
            return

        panel_left = GAME_WIDTH * 0.08
        panel_right = GAME_WIDTH * 0.92
        panel_top = GAME_HEIGHT * 0.72
        panel_bottom = GAME_HEIGHT * 0.94
        portrait_left = panel_left + 16
        portrait_top = panel_top + 16
        portrait_size = 84
        text_left = portrait_left + portrait_size + 16

        if self.storyDialoguePanel is None:
            self.storyDialoguePanel = self.canvas.create_rectangle(
                panel_left,
                panel_top,
                panel_right,
                panel_bottom,
                fill="#0f1116",
                outline="#5ec8a8",
                width=2
            )

        portrait_color = self._getSpeakerColor(line.speaker)
        initials = self._getSpeakerInitials(line.speaker)

        if self.storyDialoguePortraitBg is None:
            self.storyDialoguePortraitBg = self.canvas.create_rectangle(
                portrait_left,
                portrait_top,
                portrait_left + portrait_size,
                portrait_top + portrait_size,
                fill="#18202a",
                outline=portrait_color,
                width=2
            )
        else:
            self.canvas.itemconfig(self.storyDialoguePortraitBg, outline=portrait_color)

        if self.storyDialoguePortraitFace is None:
            self.storyDialoguePortraitFace = self.canvas.create_text(
                portrait_left + portrait_size * 0.5,
                portrait_top + portrait_size * 0.50,
                text=initials,
                fill=portrait_color,
                font="Helvetica 24 bold"
            )
        else:
            self.canvas.itemconfig(self.storyDialoguePortraitFace, text=initials, fill=portrait_color)

        if self.storyDialoguePortraitTag is None:
            self.storyDialoguePortraitTag = self.canvas.create_text(
                portrait_left + portrait_size * 0.5,
                portrait_top + portrait_size + 10,
                text="NPC",
                fill="#9fb0c5",
                font="Helvetica 9 bold"
            )

        if self.storyDialogueSpeaker is None:
            self.storyDialogueSpeaker = self.canvas.create_text(
                text_left,
                panel_top + 16,
                anchor="nw",
                text=line.speaker,
                fill="#9df5d9",
                font=("Segoe UI", 14, "bold")
            )
        else:
            self.canvas.itemconfig(self.storyDialogueSpeaker, text=line.speaker)

        visible_text = self._getVisibleStoryText(line)
        if self.storyDialogueText is None:
            self.storyDialogueText = self.canvas.create_text(
                text_left,
                panel_top + 48,
                anchor="nw",
                text=visible_text,
                fill="white",
                width=panel_right - text_left - 14,
                justify="left",
                font=("Segoe UI", 13)
            )
        else:
            self.canvas.itemconfig(self.storyDialogueText, text=visible_text)

        hint_text = "Space/Enter: bo qua"
        if self.storyTypewriterChars < len(line.text):
            hint_text = "Space/Enter: hien nhanh"

        if self.storyDialogueHint is None:
            self.storyDialogueHint = self.canvas.create_text(
                panel_right - 14,
                panel_bottom - 12,
                anchor="se",
                text=hint_text,
                fill="#95a4be",
                font=("Segoe UI", 10, "italic")
            )
        else:
            self.canvas.itemconfig(self.storyDialogueHint, text=hint_text)

        for item in (
            self.storyDialoguePanel,
            self.storyDialoguePortraitBg,
            self.storyDialoguePortraitFace,
            self.storyDialoguePortraitTag,
            self.storyDialogueSpeaker,
            self.storyDialogueText,
            self.storyDialogueHint,
        ):
            if item is not None:
                self.canvas.tag_raise(item)

    def _clearStoryDialogueOverlay(self):
        for item_name in (
            "storyDialoguePanel",
            "storyDialoguePortraitBg",
            "storyDialoguePortraitFace",
            "storyDialoguePortraitTag",
            "storyDialogueSpeaker",
            "storyDialogueText",
            "storyDialogueHint",
        ):
            item = getattr(self, item_name)
            if item is not None:
                self.canvas.delete(item)
                setattr(self, item_name, None)

        self.storyTypewriterLineKey = None
        self.storyTypewriterElapsed = 0.0
        self.storyTypewriterChars = 0

    def _onStoryFinished(self):
        self._clearStoryDialogueOverlay()
        self.isStoryBlockingGameplay = False

        action = self.storyResumeAction
        self.storyResumeAction = None
        if action == "next_wave":
            self.startNextWave()

    def _updateStoryTypewriter(self, dt: float):
        line = self.storyManager.get_current_line()
        if line is None:
            self.storyTypewriterLineKey = None
            self.storyTypewriterElapsed = 0.0
            self.storyTypewriterChars = 0
            return

        line_key = (id(self.storyManager.current_cutscene), self.storyManager.current_line_index)
        if line_key != self.storyTypewriterLineKey:
            self.storyTypewriterLineKey = line_key
            self.storyTypewriterElapsed = 0.0
            self.storyTypewriterChars = 0

        self.storyTypewriterElapsed += max(0.0, dt)
        max_chars = int(self.storyTypewriterElapsed * self.storyTypewriterSpeed)
        self.storyTypewriterChars = min(len(line.text), max_chars)

    def _getVisibleStoryText(self, line):
        if self.storyTypewriterChars >= len(line.text):
            return line.text
        clipped = line.text[:self.storyTypewriterChars]
        return f"{clipped}_"

    def _skipOrAdvanceStory(self) -> bool:
        if not self.storyManager.is_playing:
            return False

        line = self.storyManager.get_current_line()
        if line is None:
            return False

        if self.storyTypewriterChars < len(line.text):
            self.storyTypewriterChars = len(line.text)
            self.storyTypewriterElapsed = len(line.text) / max(1.0, self.storyTypewriterSpeed)
            return True

        still_playing = self.storyManager.advance_line()
        if not still_playing:
            self._onStoryFinished()
        else:
            self.storyTypewriterLineKey = None
        return True

    def _handleReturnKey(self, _event):
        if self._skipOrAdvanceStory():
            return "break"
        self.restart()

    def _handleSpaceKey(self, _event):
        if self._skipOrAdvanceStory():
            return "break"
        return None

    def _getSpeakerInitials(self, speaker: str) -> str:
        cleaned = (speaker or "NPC").replace("NPC", "").strip()
        if not cleaned:
            return "NPC"
        parts = cleaned.split()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _getSpeakerColor(self, speaker: str) -> str:
        palette = ("#6de8c6", "#8dc3ff", "#ffd26d", "#ff8da1", "#caa5ff", "#8bf17e")
        token = speaker or "NPC"
        color_index = sum(ord(ch) for ch in token) % len(palette)
        return palette[color_index]

    def _updatePerformanceState(self, dt: float):
        alpha = 0.08
        self.frameTimeEma = (1 - alpha) * self.frameTimeEma + alpha * dt
        self.frameCounter += 1

        if self.frameTimeEma > 0.030:
            self.performanceLevel = 2
        elif self.frameTimeEma > 0.023:
            self.performanceLevel = 1
        else:
            self.performanceLevel = 0

    def shouldRenderZombieHealthBars(self, zombie: Zombie = None) -> bool:
        if isinstance(zombie, BossZombie):
            return True

        alive = len(self.zombies.children) if self.zombies is not None else 0
        if self.performanceLevel >= 2:
            return alive <= 4
        if self.performanceLevel == 1:
            return alive <= 6
        return alive <= 10

    def shouldUpdateZombieHealthBarThisFrame(self) -> bool:
        if self.performanceLevel >= 2:
            return (self.frameCounter % 3) == 0
        if self.performanceLevel == 1:
            return (self.frameCounter % 2) == 0
        return True

    def _resetHandPreviewOverlay(self):
        for item_name in ("handPreviewPanel", "handPreviewImage", "handPreviewPlaceholder", "handPreviewTitle", "handPreviewStatus"):
            item_id = getattr(self, item_name)
            if item_id is not None:
                self.canvas.delete(item_id)
                setattr(self, item_name, None)
        self.handPreviewPhoto = None
        self.handPreviewLastData = None
        self.handPreviewVersion = 0

    def _clearHandAimReticle(self):
        for item_name in ("handAimCursorRing", "handAimCursorCrossH", "handAimCursorCrossV"):
            item_id = getattr(self, item_name)
            if item_id is not None:
                self.canvas.delete(item_id)
                setattr(self, item_name, None)
        self.handAimPos = None
        self.handAimVisible = False

    def _drawHandAimReticle(self):
        if not self.handAimVisible or self.handAimPos is None:
            self._clearHandAimReticle()
            return

        x = self.handAimPos.x
        y = self.handAimPos.y
        radius = 11

        if self.handAimCursorRing is None:
            self.handAimCursorRing = self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline="#76f0ff", width=2
            )
            self.handAimCursorCrossH = self.canvas.create_line(
                x - (radius + 6), y, x + (radius + 6), y,
                fill="#76f0ff", width=2
            )
            self.handAimCursorCrossV = self.canvas.create_line(
                x, y - (radius + 6), x, y + (radius + 6),
                fill="#76f0ff", width=2
            )
        else:
            self.canvas.coords(self.handAimCursorRing, x - radius, y - radius, x + radius, y + radius)
            self.canvas.coords(self.handAimCursorCrossH, x - (radius + 6), y, x + (radius + 6), y)
            self.canvas.coords(self.handAimCursorCrossV, x, y - (radius + 6), x, y + (radius + 6))

        for item in (self.handAimCursorRing, self.handAimCursorCrossH, self.handAimCursorCrossV):
            self.canvas.tag_raise(item)

    def _drawHandCameraOverlay(self):
        preview_width = 240
        preview_height = 180
        pad = 12

        panel_left = GAME_WIDTH - preview_width - (pad * 2)
        panel_top = GAME_HEIGHT - preview_height - 62
        panel_right = GAME_WIDTH - pad
        panel_bottom = GAME_HEIGHT - pad

        image_x = panel_left + pad
        image_y = panel_top + 34

        if self.handPreviewPanel is None:
            self.handPreviewPanel = self.canvas.create_rectangle(
                panel_left,
                panel_top,
                panel_right,
                panel_bottom,
                fill="#0e1417",
                outline="#38a36f",
                width=2
            )

        if self.handPreviewTitle is None:
            self.handPreviewTitle = self.canvas.create_text(
                panel_left + 10,
                panel_top + 10,
                text="HAND CAM",
                fill="#b7f2cf",
                anchor="nw",
                font="Helvetica 10 bold"
            )

        camera_data, camera_version = self.handInput.get_preview_payload(width=preview_width, height=preview_height)
        if camera_data:
            if camera_version != self.handPreviewVersion:
                self.handPreviewPhoto = PhotoImage(data=camera_data)
                self.handPreviewLastData = camera_data
                self.handPreviewVersion = camera_version
                if self.handPreviewImage is None:
                    self.handPreviewImage = self.canvas.create_image(
                        image_x,
                        image_y,
                        anchor="nw",
                        image=self.handPreviewPhoto
                    )
                else:
                    self.canvas.itemconfig(self.handPreviewImage, image=self.handPreviewPhoto, state="normal")
            elif self.handPreviewImage is not None:
                self.canvas.itemconfig(self.handPreviewImage, state="normal")

            if self.handPreviewPlaceholder is not None:
                self.canvas.itemconfig(self.handPreviewPlaceholder, state="hidden")

            if self.handPreviewStatus is None:
                self.handPreviewStatus = self.canvas.create_text(
                    panel_right - 10,
                    panel_top + 10,
                    anchor="ne",
                    text="ON",
                    fill="#6df599",
                    font="Helvetica 10 bold"
                )
            else:
                self.canvas.itemconfig(self.handPreviewStatus, text="ON", fill="#6df599")
        else:
            if self.handPreviewImage is not None:
                self.canvas.itemconfig(self.handPreviewImage, state="hidden")

            if self.handInput.start_in_progress:
                status_text = "STARTING"
                status_color = "#8fdcff"
            elif self.handInput.enabled:
                status_text = "NO FRAME"
                status_color = "#ffd57a"
            elif self.handAutoStartPending:
                status_text = "STARTING"
                status_color = "#8fdcff"
            else:
                status_text = "OFF (G)"
                status_color = "#ff8f8f"

            if self.handPreviewStatus is None:
                self.handPreviewStatus = self.canvas.create_text(
                    panel_right - 10,
                    panel_top + 10,
                    anchor="ne",
                    text=status_text,
                    fill=status_color,
                    font="Helvetica 10 bold"
                )
            else:
                self.canvas.itemconfig(self.handPreviewStatus, text=status_text, fill=status_color)

            # Placeholder box when no camera frame is available.
            if self.handPreviewPlaceholder is None:
                self.handPreviewPlaceholder = self.canvas.create_rectangle(
                    image_x,
                    image_y,
                    image_x + preview_width,
                    image_y + preview_height,
                    fill="#1b2328",
                    outline="#24313a"
                )
            else:
                self.canvas.itemconfig(self.handPreviewPlaceholder, state="normal")

        for item in (self.handPreviewPanel, self.handPreviewPlaceholder, self.handPreviewImage, self.handPreviewTitle, self.handPreviewStatus):
            if item is not None:
                self.canvas.tag_raise(item)

    def _findNonOverlappingSpawnPosition(self, collider_width: float) -> Vector2:
        top_spawn_min = GAME_HEIGHT * 0.06
        top_spawn_max = GAME_HEIGHT * 0.30
        margin_x = collider_width * 0.8
        min_x = margin_x
        max_x = GAME_WIDTH - margin_x
        if max_x <= min_x:
            min_x, max_x = 0, GAME_WIDTH

        base_min_sqr = (collider_width * 1.35) ** 2
        attempts = 40
        for _ in range(attempts):
            candidate = Vector2(
                min_x + random() * (max_x - min_x),
                top_spawn_min + random() * (top_spawn_max - top_spawn_min)
            )
            valid = True
            for zombie in self.zombies.children:
                min_sqr = max(
                    base_min_sqr,
                    (collider_width + getattr(zombie.__class__, "COLLIDER_WIDTH", collider_width)) ** 2 * 0.55
                )
                if (zombie.position - candidate).sqrMagnitude < min_sqr:
                    valid = False
                    break
            if valid:
                return candidate

        return Vector2(
            min_x + random() * (max_x - min_x),
            top_spawn_min + random() * (top_spawn_max - top_spawn_min)
        )

    def _drawPostApocalypseBackground(self, menu_mode: bool = False):
        self.canvas.delete("bg")

        if self._drawCustomBackgroundImage():
            return

        if self.mapTheme == "Do Thi Dem":
            self._drawNightCityBackground(menu_mode)
            return
        if self.mapTheme == "Sa Mac Bui":
            self._drawDesertDustBackground(menu_mode)
            return

        horizon = GAME_HEIGHT * (0.47 if menu_mode else 0.40)

        # sky gradient slices
        sky_colors = ("#2a1c16", "#3a251d", "#533022", "#6e3b24", "#84472a")
        band_h = horizon / len(sky_colors)
        for i, color in enumerate(sky_colors):
            self.canvas.create_rectangle(
                0,
                i * band_h,
                GAME_WIDTH,
                (i + 1) * band_h,
                fill=color,
                outline="",
                tags="bg"
            )

        # burnt sun / haze
        sun_x = GAME_WIDTH * 0.78
        sun_y = horizon * 0.48
        self.canvas.create_oval(
            sun_x - 64,
            sun_y - 64,
            sun_x + 64,
            sun_y + 64,
            fill="#f29d52",
            outline="",
            tags="bg"
        )
        self.canvas.create_oval(
            sun_x - 100,
            sun_y - 100,
            sun_x + 100,
            sun_y + 100,
            fill="#bf6d34",
            outline="",
            stipple="gray25",
            tags="bg"
        )

        # city silhouette
        building_colors = ("#161617", "#1d1e21", "#24252a")
        x = 0
        idx = 0
        while x < GAME_WIDTH:
            w = 34 + int((idx % 5) * 10)
            h = 56 + int((idx % 7) * 16)
            self.canvas.create_rectangle(
                x,
                horizon - h,
                min(GAME_WIDTH, x + w),
                horizon,
                fill=building_colors[idx % len(building_colors)],
                outline="",
                tags="bg"
            )
            x += w - 2
            idx += 1

        # cracked ground
        self.canvas.create_rectangle(
            0,
            horizon,
            GAME_WIDTH,
            GAME_HEIGHT,
            fill="#2a2624",
            outline="",
            tags="bg"
        )

        crack_count = 18 if menu_mode else 14
        for i in range(crack_count):
            x0 = (i + 1) * GAME_WIDTH / (crack_count + 1)
            y0 = horizon + 10 + (i % 4) * 18
            x1 = x0 + ((i % 3) - 1) * 26
            y1 = y0 + 38 + (i % 5) * 8
            x2 = x1 + ((i % 2) * 2 - 1) * 22
            y2 = y1 + 36
            self.canvas.create_line(
                x0,
                y0,
                x1,
                y1,
                x2,
                y2,
                fill="#3c302d",
                width=2,
                smooth=True,
                tags="bg"
            )

        # dust tint overlay
        self.canvas.create_rectangle(
            0,
            0,
            GAME_WIDTH,
            GAME_HEIGHT,
            fill="#6d3b25",
            outline="",
            stipple="gray50",
            tags="bg"
        )

    def _drawNightCityBackground(self, menu_mode: bool = False):
        horizon = GAME_HEIGHT * (0.50 if menu_mode else 0.43)

        sky_colors = ("#070912", "#0d1324", "#131d34", "#1a2844", "#213459")
        band_h = horizon / len(sky_colors)
        for i, color in enumerate(sky_colors):
            self.canvas.create_rectangle(0, i * band_h, GAME_WIDTH, (i + 1) * band_h, fill=color, outline="", tags="bg")

        moon_x = GAME_WIDTH * 0.20
        moon_y = horizon * 0.28
        self.canvas.create_oval(moon_x - 45, moon_y - 45, moon_x + 45, moon_y + 45, fill="#c9d8ff", outline="", tags="bg")
        self.canvas.create_oval(moon_x - 32, moon_y - 48, moon_x + 52, moon_y + 36, fill="#131d34", outline="", tags="bg")

        x = 0
        idx = 0
        while x < GAME_WIDTH:
            w = 40 + int((idx % 4) * 12)
            h = 70 + int((idx % 6) * 24)
            self.canvas.create_rectangle(x, horizon - h, min(GAME_WIDTH, x + w), horizon, fill="#10141e", outline="", tags="bg")
            if idx % 2 == 0:
                self.canvas.create_rectangle(x + 8, horizon - h + 15, min(GAME_WIDTH, x + w - 8), horizon - h + 25, fill="#ffcf66", outline="", tags="bg")
            x += w - 3
            idx += 1

        self.canvas.create_rectangle(0, horizon, GAME_WIDTH, GAME_HEIGHT, fill="#232833", outline="", tags="bg")
        for i in range(12):
            x0 = (i + 1) * GAME_WIDTH / 13
            y0 = horizon + 18 + (i % 3) * 28
            self.canvas.create_line(x0 - 28, y0, x0 + 28, y0 + 20, fill="#2f3746", width=3, tags="bg")

        self.canvas.create_rectangle(0, 0, GAME_WIDTH, GAME_HEIGHT, fill="#0f1830", outline="", stipple="gray50", tags="bg")

    def _drawDesertDustBackground(self, menu_mode: bool = False):
        horizon = GAME_HEIGHT * (0.48 if menu_mode else 0.42)

        sky_colors = ("#4f2d1d", "#6a3b22", "#864b26", "#a35e2f", "#be7238")
        band_h = horizon / len(sky_colors)
        for i, color in enumerate(sky_colors):
            self.canvas.create_rectangle(0, i * band_h, GAME_WIDTH, (i + 1) * band_h, fill=color, outline="", tags="bg")

        sun_x = GAME_WIDTH * 0.82
        sun_y = horizon * 0.36
        self.canvas.create_oval(sun_x - 52, sun_y - 52, sun_x + 52, sun_y + 52, fill="#ffd082", outline="", tags="bg")

        dune1 = (0, horizon + 50, GAME_WIDTH * 0.22, horizon + 4, GAME_WIDTH * 0.48, horizon + 58, GAME_WIDTH * 0.76, horizon + 16, GAME_WIDTH, horizon + 54, GAME_WIDTH, GAME_HEIGHT, 0, GAME_HEIGHT)
        self.canvas.create_polygon(*dune1, fill="#7d5731", outline="", smooth=True, tags="bg")
        dune2 = (0, horizon + 120, GAME_WIDTH * 0.30, horizon + 70, GAME_WIDTH * 0.55, horizon + 130, GAME_WIDTH * 0.84, horizon + 88, GAME_WIDTH, horizon + 126, GAME_WIDTH, GAME_HEIGHT, 0, GAME_HEIGHT)
        self.canvas.create_polygon(*dune2, fill="#92653a", outline="", smooth=True, tags="bg")

        for i in range(18):
            x0 = (i + 1) * GAME_WIDTH / 19
            y0 = horizon + 40 + (i % 4) * 36
            self.canvas.create_line(x0 - 20, y0, x0 + 22, y0 + 14, fill="#b1824b", width=2, tags="bg")

        self.canvas.create_rectangle(0, 0, GAME_WIDTH, GAME_HEIGHT, fill="#ad6a35", outline="", stipple="gray50", tags="bg")

    def _drawCustomBackgroundImage(self) -> bool:
        theme_file = self.mapTheme.lower().replace(" ", "_")
        image_path = f"images/background_{theme_file}.png"
        fallback_path = "images/background_apocalypse.png"
        if not exists(image_path):
            image_path = fallback_path
        if not exists(image_path):
            return False
        try:
            self.customBackgroundImage = PhotoImage(file=image_path)
            self.canvas.create_image(
                GAME_WIDTH * 0.5,
                GAME_HEIGHT * 0.5,
                image=self.customBackgroundImage,
                tags="bg"
            )
            self.canvas.create_rectangle(
                0,
                0,
                GAME_WIDTH,
                GAME_HEIGHT,
                fill="#20140f",
                outline="",
                stipple="gray50",
                tags="bg"
            )
            return True
        except Exception:
            self.customBackgroundImage = None
            return False

    def spawnZombie(self):
        spawn_position = self._findNonOverlappingSpawnPosition(Zombie.COLLIDER_WIDTH)
        self.zombies.children.insertRight(
            Zombie(self.canvas, self.player, game=self, spawn_position=spawn_position)
        )
        self.normalSpawnedCount += 1
        if not self.waveManager:
            self.killTargetTotal += 1

    def spawnZombieType(self, zombie_type: ZombieType):
        """Spawn a specific type of zombie"""
        if zombie_type == ZombieType.Tank:
            collider = TankZombie.COLLIDER_WIDTH
            spawn_position = self._findNonOverlappingSpawnPosition(collider)
            zombie = TankZombie(self.canvas, self.player, game=self, spawn_position=spawn_position)
        elif zombie_type == ZombieType.Sprinter:
            collider = SprinterZombie.COLLIDER_WIDTH
            spawn_position = self._findNonOverlappingSpawnPosition(collider)
            zombie = SprinterZombie(self.canvas, self.player, game=self, spawn_position=spawn_position)
        elif zombie_type == ZombieType.Bomber:
            collider = BomberZombie.COLLIDER_WIDTH
            spawn_position = self._findNonOverlappingSpawnPosition(collider)
            zombie = BomberZombie(self.canvas, self.player, game=self, spawn_position=spawn_position)
        else:  # Normal
            self.spawnZombie()
            return

        self.zombies.children.insertRight(zombie)
        self.normalSpawnedCount += 1
        if not self.waveManager:
            self.killTargetTotal += 1

    def spawnBoss(self):
        if self.bossesSpawnedCount >= self.bossSpawnTarget:
            return
        spawn_position = self._findNonOverlappingSpawnPosition(BossZombie.COLLIDER_WIDTH)
        boss = BossZombie(
            self.canvas,
            self.player,
            game=self,
            hearts=self.bossHearts,
            reinforcement_count=self.bossReinforcements,
            can_regenerate=self.bossCanRegenerate,
            has_hell_skill=self.bossHasHellSkill,
            spawn_position=spawn_position
        )
        self.zombies.children.insertRight(boss)
        self.currentBoss = boss
        self.bossesSpawnedCount += 1
        self.bossApproachCuePlayed = True
        self._playMusicTrack(
            "boss_music.mp3",
            loops=-1,
            fade_in=250,
            start_at_seconds=self.BOSS_MUSIC_START_SECONDS,
        )
        if not self.waveManager:
            self.killTargetTotal += 1

    def spawnReinforcements(self, amount: int):
        for _ in range(amount):
            if len(self.zombies.children) >= self.maxAliveZombies + 3:
                break
            self.spawnZombie()

    def OnZombieKilled(self, zombie: Zombie = None):
        self.killedCountTotal += 1
        if isinstance(zombie, BossZombie):
            self.score += 12
            self.bossesKilledCount += 1
            self.currentBoss = None
            self._playMusicTrack("wave_music.mp3", loops=-1, fade_in=250)
        else:
            self.score += 1

        if zombie is not None and not isinstance(zombie, BomberZombie):
            self.audioManager.play_sfx("zombie_death.wav", volume=0.55)

    def checkStageCompletion(self):
        if self.isStageComplete or self.isGameOver:
            return

        # Wave-based completion check
        if self.waveManager:
            # Advance only after all required kills are done and no zombies remain alive.
            if self.killedCountTotal >= self.killTargetTotal and len(self.zombies.children) == 0:
                self.onStageComplete()
        else:
            # Old spawn system check
            if self.normalSpawnedCount < self.normalSpawnTarget:
                return
            if self.bossesKilledCount < self.bossSpawnTarget:
                return
            if self.killedCountTotal < self.killTargetTotal:
                return
            if len(self.zombies.children) > 0:
                return
            self.onStageComplete()

    def onStageComplete(self):
        if self.isStageComplete:
            return
        self.isStageComplete = True

        # Check if there are more waves
        if self.waveManager and not self.waveManager.is_all_waves_complete():
            completed_wave = self.waveManager.current_wave
            if self.storyManager.start_wave_complete_cutscene(completed_wave, self.difficulty, self.username):
                self.isStoryBlockingGameplay = True
                self.storyResumeAction = "next_wave"
            else:
                self.startNextWave()
        else:
            # All waves complete for this difficulty: show WIN screen.
            self.paused = True
            self.pausedIndicator.hidden = True

            has_next_difficulty = (self.currentDifficultyIndex + 1) < len(self.__class__.DIFFICULTY_ORDER)
            next_diff = self.__class__.DIFFICULTY_ORDER[self.currentDifficultyIndex + 1] if has_next_difficulty else None

            title = TextSprite(self.canvas, text="WIN!")
            title.options["font"] = "Helvetica 46 bold"
            title.options["fill"] = "#7cff9b"
            title.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.20)
            self.sprites.append(title)

            detail = TextSprite(
                self.canvas,
                text=f"Che do {self.difficulty} | Kill {self.killedCountTotal}/{self.killTargetTotal} | Score: {self.score}"
            )
            detail.options["font"] = "Helvetica 18 bold"
            detail.options["fill"] = "white"
            detail.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.30)
            self.sprites.append(detail)

            if has_next_difficulty:
                next_text = TextSprite(self.canvas, text=f"Tu dong sang {next_diff} sau 3s")
                next_text.options["font"] = "Helvetica 16 bold"
                next_text.options["fill"] = "#ffd66a"
                next_text.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.40)
                self.sprites.append(next_text)

                self._createStageCompleteButtons()
                self.stageCompleteTimer = self.tk.after(3000, self.progressNextDifficulty)
            else:
                # Last difficulty complete
                self.sprites.append(
                    Leaderboard(
                        self.canvas,
                        self.score,
                        date.today().strftime("%d-%m-%Y"),
                        self.username,
                        level_key=self.difficulty
                    )
                )

                hint = TextSprite(self.canvas, text="Ban da hoan thanh moi che do")
                hint.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.82)
                self.sprites.append(hint)

                self._createStageCompleteButtons(has_next=False)

    def nextDifficulty(self):
        """Progress to next difficulty level"""
        self.currentDifficultyIndex += 1

        if self.currentDifficultyIndex >= len(self.__class__.DIFFICULTY_ORDER):
            # No more difficulties - game over
            self.isGameOver = True
            return False

        # Set new difficulty
        self.difficulty = self.__class__.DIFFICULTY_ORDER[self.currentDifficultyIndex]

        # Reset game state for new difficulty
        self.isStageComplete = False
        self.paused = False
        self.killedCountTotal = 0
        self.normalSpawnedCount = 0
        self.bossesSpawnedCount = 0
        self.bossesKilledCount = 0

        # Clear sprites
        self.sprites = [s for s in self.sprites if s == self.player or isinstance(s, (type(self.scoreIndicator), type(self.pausedIndicator)))]

        # Reinitialize with new difficulty config
        self._apply_difficulty_config()

        # Reset game
        self.isGameOver = False
        self.started = True

        return True

    def _apply_difficulty_config(self):
        """Apply difficulty config to game"""
        if self.difficulty not in self.__class__.DIFFICULTY_CONFIGS:
            return

        config = self.__class__.DIFFICULTY_CONFIGS[self.difficulty]
        self.maxAliveZombies = config.get("max_alive", 5)
        self.normalSpawnTarget = config.get("normal_target", 15)
        self.bossSpawnTarget = config.get("boss_target", 1)
        self.zombieSpawnCooldownMs = config.get("spawn_cooldown_ms", 900)
        self.hudColor = config.get("hud_color", "#8dd8ff")
        self.zombieSpawnCooldown = self.zombieSpawnCooldownMs
        self.dontSpawnZombie = False
        self._setupBarricade(config)
        # Note: killTargetTotal is set per-wave via _updateKillTargetForWave()

    def _updateKillTargetForWave(self):
        """Update fixed kill target for current wave."""
        if not self.waveManager or self.waveManager.current_wave >= len(self.waveManager.waves):
            return

        current_wave = self.waveManager.waves[self.waveManager.current_wave]
        self.killTargetTotal = current_wave.total_zombies
        if current_wave.boss_at_end:
            self.killTargetTotal += self.bossSpawnTarget

    def progressNextDifficulty(self):
        """Progress to next difficulty after stage complete"""
        # Cancel timer since we're progressing
        if self.stageCompleteTimer:
            self.tk.after_cancel(self.stageCompleteTimer)
            self.stageCompleteTimer = None

        if self.nextDifficulty():
            # Start new difficulty - apply config and restart game
            self._apply_difficulty_config()
            self.start()
        else:
            # All difficulties complete
            self.isGameOver = True
            self.paused = True

    def stageCompleteBack(self):
        """Home button on WIN screen"""
        if not self.stageCompleteBackBtn or not self.paused or not self.isStageComplete:
            return

        # Cancel auto-transition
        if self.stageCompleteTimer:
            self.tk.after_cancel(self.stageCompleteTimer)
            self.stageCompleteTimer = None

        self.currentDifficultyIndex = 0
        self.difficulty = self.__class__.DEFAULT_DIFFICULTY
        self.goHome()

    def _handleHomeShortcut(self):
        """Shared Home shortcut for WIN/GAME OVER screens."""
        if self.isStageComplete:
            self.stageCompleteBack()
            return
        if self.isGameOver:
            self.gameOverHome()

    def stageCompleteNext(self):
        """Continue button on WIN screen - go to next difficulty"""
        if not self.stageCompleteNextBtn or not self.paused or not self.isStageComplete:
            return

        # Cancel auto-transition and progress immediately
        if self.stageCompleteTimer:
            self.tk.after_cancel(self.stageCompleteTimer)
            self.stageCompleteTimer = None

        self.progressNextDifficulty()

    def gameOverRestart(self):
        """Restart button on game over screen"""
        if not self.gameOverRestartBtn or not self.isGameOver:
            return
        # Same as pressing Return
        self.restart()

    def gameOverHome(self):
        """Home button on game over screen - go back to main menu"""
        if not self.gameOverHomeBtn or not self.isGameOver:
            return
        # Reset to main menu
        self.currentDifficultyIndex = 0
        self.difficulty = self.__class__.DEFAULT_DIFFICULTY
        self.goHome()

    def startNextWave(self):
        """Start the next wave"""
        if not self.started or self.isGameOver:
            return

        # Clear stage complete flag
        self.isStageComplete = False

        # Start next wave
        self.waveManager.start_wave(time())
        self._playMusicTrack("wave_music.mp3", loops=-1, fade_in=250)
        self.bossApproachCuePlayed = False

        # Reset kill counter for new wave
        self.killedCountTotal = 0

        # Update kill target for new wave
        self._updateKillTargetForWave()

        # Reset spawn counter
        self.dontSpawnZombie = False

        # Do not show wave transition cutscene to avoid obstructing gameplay.

        # Resume game
        self.paused = False

    def togglePaused(self):
        if not self.started or self.isGameOver or self.isStageComplete or self.isStoryBlockingGameplay:
            return
        self.paused = not self.paused

    def toggleBossKey(self):
        if not self.started:
            return
        if self.paused:
            self.paused = False
        else:
            self.paused = True
            self.pausedIndicator.hidden = True
            self.bossKeyBg.hidden = False
            self._setPauseMenuVisible(False)

    @property
    def paused(self) -> bool:
        return self.__paused

    @paused.setter
    def paused(self, paused: bool):
        self.__paused = paused
        if not self.started:
            if not paused:
                self.start()
            return
        self.pausedIndicator.hidden = not self.paused
        self._setPauseMenuVisible(self.paused and not self.isGameOver and not self.isStageComplete)
        self.bossKeyBg.hidden = True
        if not paused:
            self.lastUpdateTime = time()
            if not self.updateScheduled:
                self.updateScheduled = True
                self.update()
            if not self.redrawScheduled:
                self.redrawScheduled = True
                self.redraw()

    def _createPauseMenuButtons(self):
        self._destroyPauseMenuButtons()
        self.pauseRestartBtn = Button(
            self.tk,
            text="Choi Lai",
            bg="#2b7de9",
            fg="white",
            activebackground="#2368c2",
            activeforeground="white",
            relief=FLAT,
            font="Helvetica 14 bold",
            cursor="hand2",
            command=self.restartFromPause
        )
        self.pauseHomeBtn = Button(
            self.tk,
            text="Home",
            bg="#37474f",
            fg="white",
            activebackground="#2b383f",
            activeforeground="white",
            relief=FLAT,
            font="Helvetica 14 bold",
            cursor="hand2",
            command=self.goHome
        )
        self.pauseRestartWindow = self.canvas.create_window(
            GAME_WIDTH * 0.5,
            GAME_HEIGHT * 0.60,
            window=self.pauseRestartBtn,
            width=180,
            height=44
        )
        self.pauseHomeWindow = self.canvas.create_window(
            GAME_WIDTH * 0.5,
            GAME_HEIGHT * 0.66,
            window=self.pauseHomeBtn,
            width=180,
            height=44
        )
        self._setPauseMenuVisible(False)

    def _setPauseMenuVisible(self, visible: bool):
        state = "normal" if visible else "hidden"
        if self.pauseRestartWindow is not None:
            self.canvas.itemconfigure(self.pauseRestartWindow, state=state)
        if self.pauseHomeWindow is not None:
            self.canvas.itemconfigure(self.pauseHomeWindow, state=state)

    def _destroyPauseMenuButtons(self):
        if self.pauseRestartWindow is not None:
            self.canvas.delete(self.pauseRestartWindow)
            self.pauseRestartWindow = None
        if self.pauseHomeWindow is not None:
            self.canvas.delete(self.pauseHomeWindow)
            self.pauseHomeWindow = None
        if self.pauseRestartBtn is not None:
            self.pauseRestartBtn.destroy()
            self.pauseRestartBtn = None
        if self.pauseHomeBtn is not None:
            self.pauseHomeBtn.destroy()
            self.pauseHomeBtn = None

    def _createStageCompleteButtons(self, has_next: bool = True):
        self._destroyStageCompleteButtons()

        self.stageCompleteBackBtn = Button(
            self.tk,
            text="Home",
            bg="#37474f",
            fg="white",
            activebackground="#2b383f",
            activeforeground="white",
            relief=FLAT,
            font="Helvetica 14 bold",
            cursor="hand2",
            command=self.stageCompleteBack
        )
        self.stageCompleteBackWindow = self.canvas.create_window(
            GAME_WIDTH * 0.35,
            GAME_HEIGHT * 0.80,
            window=self.stageCompleteBackBtn,
            width=170,
            height=44
        )

        if has_next:
            self.stageCompleteNextBtn = Button(
                self.tk,
                text="Choi tiep",
                bg="#2b7de9",
                fg="white",
                activebackground="#2368c2",
                activeforeground="white",
                relief=FLAT,
                font="Helvetica 14 bold",
                cursor="hand2",
                command=self.stageCompleteNext
            )
            self.stageCompleteNextWindow = self.canvas.create_window(
                GAME_WIDTH * 0.65,
                GAME_HEIGHT * 0.80,
                window=self.stageCompleteNextBtn,
                width=170,
                height=44
            )

    def _destroyStageCompleteButtons(self):
        if self.stageCompleteBackWindow is not None:
            self.canvas.delete(self.stageCompleteBackWindow)
            self.stageCompleteBackWindow = None
        if self.stageCompleteNextWindow is not None:
            self.canvas.delete(self.stageCompleteNextWindow)
            self.stageCompleteNextWindow = None

        if self.stageCompleteBackBtn is not None:
            self.stageCompleteBackBtn.destroy()
            self.stageCompleteBackBtn = None
        if self.stageCompleteNextBtn is not None:
            self.stageCompleteNextBtn.destroy()
            self.stageCompleteNextBtn = None

    def _createGameOverButtons(self):
        self._destroyGameOverButtons()

        self.gameOverRestartBtn = Button(
            self.tk,
            text="Choi lai",
            bg="#2b7de9",
            fg="white",
            activebackground="#2368c2",
            activeforeground="white",
            relief=FLAT,
            font="Helvetica 14 bold",
            cursor="hand2",
            command=self.gameOverRestart
        )
        self.gameOverRestartWindow = self.canvas.create_window(
            GAME_WIDTH * 0.35,
            GAME_HEIGHT * 0.80,
            window=self.gameOverRestartBtn,
            width=170,
            height=44
        )

        self.gameOverHomeBtn = Button(
            self.tk,
            text="Home",
            bg="#37474f",
            fg="white",
            activebackground="#2b383f",
            activeforeground="white",
            relief=FLAT,
            font="Helvetica 14 bold",
            cursor="hand2",
            command=self.gameOverHome
        )
        self.gameOverHomeWindow = self.canvas.create_window(
            GAME_WIDTH * 0.65,
            GAME_HEIGHT * 0.80,
            window=self.gameOverHomeBtn,
            width=170,
            height=44
        )

    def _destroyGameOverButtons(self):
        if self.gameOverRestartWindow is not None:
            self.canvas.delete(self.gameOverRestartWindow)
            self.gameOverRestartWindow = None
        if self.gameOverHomeWindow is not None:
            self.canvas.delete(self.gameOverHomeWindow)
            self.gameOverHomeWindow = None

        if self.gameOverRestartBtn is not None:
            self.gameOverRestartBtn.destroy()
            self.gameOverRestartBtn = None
        if self.gameOverHomeBtn is not None:
            self.gameOverHomeBtn.destroy()
            self.gameOverHomeBtn = None

    @property
    def usernameHash(self):
        return self._usernameHash

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, new: str):
        self._username = new
        self._usernameHash = sha1(self._username.encode("utf-8")).hexdigest()

    def onGameOver(self):
        if self.isGameOver:
            return

        self.isGameOver = True
        self.audioManager.stop_music(fade_out=200)
        self.paused = True
        self.pausedIndicator.hidden = True

        if self.scoreIndicator is not None:
            self.scoreIndicator.hidden = True

        self.sprites.append(
            Leaderboard(
                self.canvas,
                self.score,
                date.today().strftime("%d-%m-%Y"),
                self.username,
                level_key=self.difficulty,
                top_ratio=0.46
            )
        )

        # Game over title
        title = TextSprite(self.canvas, text="GAME OVER!")
        title.options["font"] = "Helvetica 52 bold"
        title.options["fill"] = "#ff6b6b"
        title.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.16)
        self.sprites.append(title)

        # Stats
        detail = TextSprite(
            self.canvas,
            text=f"Che do {self.difficulty} | Kill {self.killedCountTotal} | Score: {self.score}"
        )
        detail.options["font"] = "Helvetica 20 bold"
        detail.options["fill"] = "white"
        detail.position = Vector2(GAME_WIDTH * 0.5, GAME_HEIGHT * 0.25)
        self.sprites.append(detail)

        self._createGameOverButtons()

    def _enableHandControl(self):
        """Enable/retry hand gesture control."""
        if not self.started:
            return

        if self.handInput.enabled:
            return

        if self.handInput.start_in_progress:
            return

        status = self.handInput.start_async()
        if status == "starting":
            self.handAutoStartPending = False
            print("Hand gesture control: starting camera...")
        else:
            reason = self.handInput.last_error or "Unknown reason"
            print(f"Hand gesture control not available - {reason}")

    def _disableHandControl(self):
        """Disable hand gesture control."""
        if not self.started:
            return
        if not self.handInput.enabled:
            print("Hand gesture control already disabled")
            return
        self.handInput.stop()
        self.handAutoStartPending = False
        self._clearHandAimReticle()

    def _autoEnableHandControl(self):
        """Non-blocking hand-camera bootstrap after entering gameplay."""
        # Intentionally disabled to keep entering gameplay responsive.
        if not self.handAutoStartPending:
            return
        if not self.started or self.isGameOver:
            self.handAutoStartPending = False
            return
        if self.handInput.enabled:
            self.handAutoStartPending = False
            return

        self.handInput.start()
        self.handAutoStartPending = False

    def _testAudioOutput(self):
        """Play a clear SFX sample and print runtime audio status."""
        status = self.audioManager.get_status()
        print(
            "Audio status:",
            f"init={status['initialized']}",
            f"music_enabled={status['music_enabled']}",
            f"sfx_enabled={status['sfx_enabled']}",
            f"music_busy={status['music_busy']}",
            f"music_vol={status['music_volume']:.2f}",
            f"sfx_vol={status['sfx_volume']:.2f}",
        )
        played = self.audioManager.play_sfx("zombie_death.mp3", volume=1.0)
        if not played:
            played = self.audioManager.play_sfx("zombie_hit.mp3", volume=1.0)
        print("Audio test SFX", "played OK" if played else "failed", "(F8)")

    def _playMusicTrack(
        self,
        music_name: str,
        loops: int = -1,
        fade_in: int = 0,
        start_at_seconds: float = 0.0,
    ):
        """Play a music track and fallback to a short SFX when playback fails."""
        if self.audioManager.play_music(
            music_name,
            loops=loops,
            fade_in=fade_in,
            start_pos_seconds=start_at_seconds,
        ):
            return True
        reason = self.audioManager.get_status().get("last_error")
        if reason:
            print(f"Audio warning: could not start {music_name} ({reason})")
        else:
            print(f"Audio warning: could not start {music_name}")
        self.audioManager.play_sfx("zombie_hit.mp3", volume=1.0, max_duration_ms=300)
        return False

    def _maintainAudioPlayback(self, current_time: float):
        """Recover background music if SDL/driver briefly drops playback."""
        if not self.started or self.paused or self.isGameOver:
            return
        if current_time - self.lastAudioRetryTime < 2.0:
            return

        self.lastAudioRetryTime = current_time
        status = self.audioManager.get_status()
        current_track = status.get("current_music")
        if not status.get("initialized"):
            return
        if not status.get("music_enabled"):
            return
        if not current_track:
            return
        if status.get("music_busy"):
            return

        self._playMusicTrack(current_track, loops=-1, fade_in=120)

    def _adjustAudioVolume(self, delta: float):
        """Adjust music and sfx volume together for quick troubleshooting."""
        new_music = min(1.0, max(0.0, self.audioManager.music_volume + delta))
        new_sfx = min(1.0, max(0.0, self.audioManager.sfx_volume + delta))
        self.audioManager.set_music_volume(new_music)
        self.audioManager.set_sfx_volume(new_sfx)
        print(f"Audio volume set: music={new_music:.2f}, sfx={new_sfx:.2f} (F9/F10)")

    def _applyHandGestureInput(self):
        """Apply hand gesture input to player"""
        if self.player is None:
            return
        
        try:
            hand_data = self.handInput.update(GAME_WIDTH, GAME_HEIGHT)
            if hand_data is None:
                self.handInput.enabled = False
                self._clearHandAimReticle()
                return
            
            # Apply movement from left hand (normalize to game units)
            move_x = hand_data['move_x']  # -1 to 1
            move_y = hand_data['move_y']  # -1 to 1
            left_detected = hand_data.get('left_detected', False)
            
            # Smooth movement then apply hysteresis to avoid rapid on/off jitter near center.
            move_alpha = 0.55
            self.handMoveXFiltered += (move_x - self.handMoveXFiltered) * move_alpha
            self.handMoveYFiltered += (move_y - self.handMoveYFiltered) * move_alpha

            if not left_detected:
                self.handMoveXFiltered *= 0.55
                self.handMoveYFiltered *= 0.55

            enter_deadzone = 0.16
            exit_deadzone = 0.08

            x_axis = self.handMoveXFiltered
            y_axis = self.handMoveYFiltered

            if self.handMoveLeftActive:
                self.handMoveLeftActive = x_axis < -exit_deadzone
            else:
                self.handMoveLeftActive = x_axis < -enter_deadzone

            if self.handMoveRightActive:
                self.handMoveRightActive = x_axis > exit_deadzone
            else:
                self.handMoveRightActive = x_axis > enter_deadzone

            if self.handMoveUpActive:
                self.handMoveUpActive = y_axis < -exit_deadzone
            else:
                self.handMoveUpActive = y_axis < -enter_deadzone

            if self.handMoveDownActive:
                self.handMoveDownActive = y_axis > exit_deadzone
            else:
                self.handMoveDownActive = y_axis > enter_deadzone

            if self.handMoveLeftActive and self.handMoveRightActive:
                if abs(x_axis) < exit_deadzone:
                    self.handMoveLeftActive = False
                    self.handMoveRightActive = False
                elif x_axis > 0:
                    self.handMoveLeftActive = False
                else:
                    self.handMoveRightActive = False

            if self.handMoveUpActive and self.handMoveDownActive:
                if abs(y_axis) < exit_deadzone:
                    self.handMoveUpActive = False
                    self.handMoveDownActive = False
                elif y_axis > 0:
                    self.handMoveUpActive = False
                else:
                    self.handMoveDownActive = False

            self.player.setInput(up=1 if self.handMoveUpActive else 0, down=1 if self.handMoveDownActive else 0)
            self.player.setInput(left=1 if self.handMoveLeftActive else 0, right=1 if self.handMoveRightActive else 0)
            
            # Apply aim direction from right hand
            aim_x = hand_data['aim_x']  # -1 to 1
            aim_y = hand_data['aim_y']  # -1 to 1
            right_detected = hand_data.get('right_detected', False)
            
            # Convert to screen position
            target_aim = Vector2(
                (0.5 + aim_x * 0.5) * GAME_WIDTH,
                (0.5 + aim_y * 0.5) * GAME_HEIGHT
            )

            if right_detected:
                if self.handAimPos is None:
                    self.handAimPos = target_aim
                else:
                    distance = (target_aim - self.handAimPos).magnitude
                    smooth_factor = 0.48 if distance < 90 else 0.72
                    self.handAimPos = self.handAimPos + (target_aim - self.handAimPos) * smooth_factor
                self.handAimVisible = True
                self.player.setInput(mouse=self.handAimPos)
            else:
                self.handAimVisible = False
            
            # Apply actions
            now_time = time()
            if hand_data['shoot'] and right_detected:
                # Right hand pointing gesture - shoot
                self.handShootHoldUntil = now_time + 0.12
                if not self.player.isFiring:
                    self.player.setInput(firing=True)
            else:
                if self.player.isFiring and now_time >= self.handShootHoldUntil:
                    self.player.setInput(firing=False)
            
            if hand_data['dash']:
                # Left hand closed fist - dash
                # Only dash if enough time has passed since last dash
                current_time = time()
                if current_time - self.player.dashCooldown > 0.5:
                    self.player.dash()
        
        except Exception as e:
            print(f"Hand control error: {e}")
            self.handInput.enabled = False
            self._clearHandAimReticle()

    def onClose(self):
        self._clearBarricadeUI()
        self._destroyStageCompleteButtons()
        self._destroyGameOverButtons()
        self._destroyPauseMenuButtons()
        self._resetHandPreviewOverlay()
        self._clearHandAimReticle()
        
        # Cleanup hand gesture control
        if self.handInput:
            self.handInput.cleanup()
        
        self.tk.destroy()


if __name__ == "__main__":
    game = Game(tk)
    tk.mainloop()

