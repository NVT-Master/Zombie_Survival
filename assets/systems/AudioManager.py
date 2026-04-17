"""
Audio Manager for handling background music and sound effects
Uses pygame.mixer for cross-platform audio support
"""

import os
import warnings
from typing import Optional, Dict

warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioManager:
    """Manages all audio (music and SFX) for the game"""

    # Real assets live in assets/audio; this module is now in assets/systems.
    AUDIO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "audio"))
    MUSIC_DIR = os.path.join(AUDIO_ROOT, "music")
    SFX_DIR = os.path.join(AUDIO_ROOT, "sfx")

    # Default volumes (0.0 - 1.0)
    DEFAULT_MUSIC_VOLUME = 1.0
    DEFAULT_SFX_VOLUME = 1.0

    def __init__(self):
        self.music_enabled = PYGAME_AVAILABLE
        self.sfx_enabled = PYGAME_AVAILABLE
        self.initialized = False
        self.last_error = None
        self.current_music = None
        self.music_volume = self.DEFAULT_MUSIC_VOLUME
        self.sfx_volume = self.DEFAULT_SFX_VOLUME
        self.sfx_cache: Dict[str, pygame.mixer.Sound] = {}

        if PYGAME_AVAILABLE:
            if not self._init_mixer():
                self.music_enabled = False
                self.sfx_enabled = False
            else:
                self._preload_common_sfx()

    def _preload_common_sfx(self):
        """Preload frequently used SFX to avoid first-play stutter/delay."""
        common = (
            "shoot_handgun.wav",
            "shoot_shotgun.wav",
            "shoot_rifle.wav",
            "zombie_hit.wav",
            "zombie_death.wav",
            "player_hit.wav",
            "dash.wav",
        )
        for name in common:
            path = self._resolve_audio_path(self.SFX_DIR, name)
            if not path:
                continue
            try:
                if path not in self.sfx_cache:
                    self.sfx_cache[path] = pygame.mixer.Sound(path)
            except Exception:
                continue

    def _init_mixer(self) -> bool:
        """Initialize mixer, retrying with common Windows audio drivers."""
        try:
            if pygame.mixer.get_init() is not None:
                self.initialized = True
                self.last_error = None
                return True
        except Exception:
            pass

        drivers = [None, "directsound", "wasapi", "winmm"]
        original_driver = os.environ.get("SDL_AUDIODRIVER")

        for driver in drivers:
            try:
                if driver is None:
                    if original_driver is None and "SDL_AUDIODRIVER" in os.environ:
                        del os.environ["SDL_AUDIODRIVER"]
                    elif original_driver is not None:
                        os.environ["SDL_AUDIODRIVER"] = original_driver
                else:
                    os.environ["SDL_AUDIODRIVER"] = driver

                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                pygame.mixer.set_num_channels(32)
                self.initialized = True
                self.music_enabled = True
                self.sfx_enabled = True
                self.last_error = None
                return True
            except Exception as e:
                self.last_error = f"mixer init failed ({driver or 'default'}): {e}"
                continue

        self.initialized = False
        print("Failed to initialize pygame mixer with available audio drivers")
        return False

    def _resolve_audio_path(self, audio_dir: str, file_name: str) -> Optional[str]:
        """Resolve an audio file by name, allowing wav/mp3 fallback."""
        normalized_name = os.path.basename(str(file_name).replace("\\", "/"))
        direct_path = os.path.join(audio_dir, normalized_name)
        if os.path.exists(direct_path):
            return direct_path

        base_name, extension = os.path.splitext(normalized_name)
        if extension.lower() in (".wav", ".mp3"):
            alt_extension = ".mp3" if extension.lower() == ".wav" else ".wav"
            alt_path = os.path.join(audio_dir, base_name + alt_extension)
            if os.path.exists(alt_path):
                return alt_path
        return None

    def play_music(
        self,
        music_name: str,
        loops: int = -1,
        fade_in: int = 0,
        start_pos_seconds: float = 0.0,
    ) -> bool:
        """
        Play background music

        Args:
            music_name: filename without path (e.g., "boss_music.mp3")
            loops: -1 for infinite loop, 0+ for specific loops
            fade_in: fade in duration in milliseconds
            start_pos_seconds: start playback at this offset in seconds
        """
        if not self.music_enabled:
            self.last_error = "music disabled"
            return False

        if not self.initialized and not self._init_mixer():
            if self.last_error is None:
                self.last_error = "mixer init failed"
            return False

        try:
            music_path = self._resolve_audio_path(self.MUSIC_DIR, music_name)
            if music_path is None:
                print(f"Music file not found: {os.path.join(self.MUSIC_DIR, music_name)}")
                self.last_error = f"music file not found: {music_name}"
                return False

            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            fade_ms = max(0, int(fade_in))
            start_pos = max(0.0, float(start_pos_seconds or 0.0))
            if start_pos > 0.0:
                pygame.mixer.music.play(loops=loops, fade_ms=fade_ms, start=start_pos)
            else:
                pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self.current_music = music_name
            self.last_error = None
            return True
        except Exception as e:
            # One retry after resetting music stream handles transient SDL decoder hiccups.
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass

            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                fade_ms = max(0, int(fade_in))
                start_pos = max(0.0, float(start_pos_seconds or 0.0))
                if start_pos > 0.0:
                    pygame.mixer.music.play(loops=loops, fade_ms=fade_ms, start=start_pos)
                else:
                    pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
                self.current_music = music_name
                self.last_error = None
                return True
            except Exception as retry_e:
                self.last_error = f"play music failed: {retry_e}"
                print(f"Error playing music {music_name}: {retry_e}")
                return False

    def stop_music(self, fade_out: int = 0):
        """Stop current music with optional fade out"""
        if not self.music_enabled:
            return

        if not self.initialized:
            return

        try:
            if fade_out > 0:
                pygame.mixer.music.fadeout(fade_out)
            else:
                pygame.mixer.music.stop()
            self.current_music = None
        except Exception as e:
            print(f"Error stopping music: {e}")

    def play_sfx(self, sfx_name: str, volume: Optional[float] = None, max_duration_ms: Optional[int] = None) -> bool:
        """
        Play sound effect

        Args:
            sfx_name: filename without path (e.g., "shoot.wav")
            volume: optional volume override (0.0-1.0)
        """
        if not self.sfx_enabled:
            self.last_error = "sfx disabled"
            return False

        if not self.initialized and not self._init_mixer():
            if self.last_error is None:
                self.last_error = "mixer init failed"
            return False

        try:
            sfx_path = self._resolve_audio_path(self.SFX_DIR, sfx_name)
            if sfx_path is None:
                print(f"SFX file not found: {os.path.join(self.SFX_DIR, sfx_name)}")
                self.last_error = f"sfx file not found: {sfx_name}"
                return False

            # Use cached sound if available
            if sfx_path not in self.sfx_cache:
                sound = pygame.mixer.Sound(sfx_path)
                self.sfx_cache[sfx_path] = sound

            sound = self.sfx_cache[sfx_path]
            vol = volume if volume is not None else self.sfx_volume
            play_volume = min(1.0, max(0.0, vol))

            channel = pygame.mixer.find_channel(True)
            if channel is None:
                self.last_error = "no free mixer channel"
                return False

            channel.set_volume(play_volume)
            if max_duration_ms is not None and max_duration_ms > 0:
                channel.play(sound, maxtime=int(max_duration_ms))
            else:
                channel.play(sound)
            self.last_error = None
            return True
        except Exception as e:
            print(f"Error playing SFX {sfx_name}: {e}")
            self.last_error = f"play sfx failed: {e}"
            return False

    def set_music_volume(self, volume: float):
        """Set music volume (0.0-1.0)"""
        self.music_volume = min(1.0, max(0.0, volume))
        if self.music_enabled and PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except:
                pass

    def set_sfx_volume(self, volume: float):
        """Set SFX volume (0.0-1.0)"""
        self.sfx_volume = min(1.0, max(0.0, volume))

    def get_status(self) -> dict:
        """Return current audio runtime status for quick debugging."""
        music_busy = False
        try:
            if PYGAME_AVAILABLE and self.initialized:
                music_busy = pygame.mixer.music.get_busy()
        except Exception:
            music_busy = False

        return {
            "initialized": self.initialized,
            "music_enabled": self.music_enabled,
            "sfx_enabled": self.sfx_enabled,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "current_music": self.current_music,
            "music_busy": music_busy,
            "last_error": self.last_error,
        }

    def cleanup(self):
        """Clean up audio resources"""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.stop()
                pygame.mixer.quit()
                self.initialized = False
            except:
                pass
