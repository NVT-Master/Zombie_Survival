from os import name as os_name


BASE_WIDTH: int = 1280
BASE_HEIGHT: int = 720
WINDOW_MARGIN_X: int = 48
WINDOW_MARGIN_Y: int = 96
MIN_WIDTH: int = 800
MIN_HEIGHT: int = 450


def _get_screen_size():
    if os_name != "nt":
        return None

    try:
        import ctypes
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return None


def _fit_landscape_resolution():
    screen_size = _get_screen_size()
    if screen_size is None:
        return BASE_WIDTH, BASE_HEIGHT

    screen_width, screen_height = screen_size
    max_width = max(MIN_WIDTH, screen_width - WINDOW_MARGIN_X)
    max_height = max(MIN_HEIGHT, screen_height - WINDOW_MARGIN_Y)

    scale = min(max_width / BASE_WIDTH, max_height / BASE_HEIGHT)
    width = max(MIN_WIDTH, int(BASE_WIDTH * scale))
    height = max(MIN_HEIGHT, int(BASE_HEIGHT * scale))
    return width, height


GAME_WIDTH, GAME_HEIGHT = _fit_landscape_resolution()
WINDOW_GEOMETRY: str = f"{GAME_WIDTH}x{GAME_HEIGHT}"
