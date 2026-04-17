"""
Hand Gesture Input Adapter - Integrates hand controls with game
"""

import base64
import threading
from time import time

import cv2

from assets.systems.HandGestureController import HandGestureController


class HandInputAdapter:
    """Bridges hand gestures to game input"""
    
    def __init__(self, enable_at_start=False):
        self.enabled = enable_at_start
        self.controller = None
        self.camera_initialized = False
        self.start_in_progress = False
        self._startup_ready = False
        self._startup_success = False
        self._startup_error = None
        self._startup_controller = None
        self._startup_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._worker_thread = None
        self._worker_stop_event = threading.Event()
        self.frame_fail_count = 0
        self.frame_fail_limit = 20
        self.last_error = None
        self.last_hand_data = {
            'move_x': 0,
            'move_y': 0,
            'aim_x': 0,
            'aim_y': 0,
            'left_detected': False,
            'right_detected': False,
            'shoot': False,
            'dash': False,
        }
        self.last_update_time = 0.0
        self.update_interval_secs = 1 / 60  # Main loop reads cached data; keep this effectively unlocked.
        self.tracking_interval_secs = 1 / 18  # Camera+gesture processing in worker thread.
        self.last_preview_time = 0.0
        self.preview_interval_secs = 1 / 8  # Preview refresh at 8 FPS max to reduce UI stutter.
        self.cached_preview_data = None
        self.cached_preview_version = 0
        self.preview_width = 220
        self.preview_height = 165
        self._game_width = 1280
        self._game_height = 720
        
        if enable_at_start:
            self.start()

    def _start_controller_sync(self):
        controller = HandGestureController(camera_index=0, debug=False)
        return controller
    
    def start(self):
        """Initialize hand controller"""
        if self.controller is not None:
            self.enabled = True
            self.frame_fail_count = 0
            self._start_tracking_worker()
            return True

        if self.start_in_progress:
            return False
        
        try:
            self.controller = self._start_controller_sync()
            self.camera_initialized = True
            self.enabled = True
            self.frame_fail_count = 0
            self.last_error = None
            self._start_tracking_worker()
            print("âœ“ Hand gesture control: ENABLED (Webcam active)")
            return True
        except RuntimeError as e:
            error_msg = str(e)
            print("=" * 70)
            print("âš  HAND GESTURE CONTROL: NOT AVAILABLE")
            print("=" * 70)
            print(f"Reason: {error_msg}")
            print("\nYour game will work normally with keyboard & mouse controls!")
            print("=" * 70)
            self.enabled = False
            self.last_error = error_msg
            return False
        except Exception as e:
            print(f"âœ— Unexpected error: {e}")
            self.enabled = False
            self.last_error = str(e)
            return False

    def start_async(self):
        """Start hand controller in a background thread to avoid UI freezes."""
        if self.controller is not None:
            self.enabled = True
            return "enabled"

        if self.start_in_progress:
            return "starting"

        with self._startup_lock:
            self.start_in_progress = True
            self._startup_ready = False
            self._startup_success = False
            self._startup_error = None
            self._startup_controller = None

        def _worker():
            controller = None
            err = None
            ok = False
            try:
                controller = self._start_controller_sync()
                ok = True
            except Exception as e:
                err = str(e)

            with self._startup_lock:
                self._startup_success = ok
                self._startup_error = err
                self._startup_controller = controller
                self._startup_ready = True
                self.start_in_progress = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return "starting"

    def poll_startup(self):
        """Finalize async startup result on main thread. Returns True when state changed."""
        with self._startup_lock:
            if not self._startup_ready:
                return False

            ok = self._startup_success
            err = self._startup_error
            controller = self._startup_controller

            self._startup_ready = False
            self._startup_success = False
            self._startup_error = None
            self._startup_controller = None

        if ok and controller is not None:
            self.controller = controller
            self.camera_initialized = True
            self.enabled = True
            self.frame_fail_count = 0
            self.last_error = None
            self._start_tracking_worker()
            print("âœ“ Hand gesture control: ENABLED (Webcam active)")
            return True

        error_msg = err or "Unknown startup error"
        print("=" * 70)
        print("âš  HAND GESTURE CONTROL: NOT AVAILABLE")
        print("=" * 70)
        print(f"Reason: {error_msg}")
        print("\nYour game will work normally with keyboard & mouse controls!")
        print("=" * 70)
        self.enabled = False
        self.last_error = error_msg
        return True
    
    def stop(self):
        """Disable hand controller"""
        self._stop_tracking_worker()
        if self.controller:
            self.controller.cleanup()
            self.controller = None
        self.enabled = False
        self.frame_fail_count = 0
        self.cached_preview_data = None
        self.last_preview_time = 0.0
        self.start_in_progress = False
        print("âœ“ Hand gesture control disabled")

    def _start_tracking_worker(self):
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._worker_stop_event.clear()

        def _worker_loop():
            local_fail_count = 0
            while not self._worker_stop_event.is_set():
                frame_start = time()
                controller = self.controller

                if not self.enabled or controller is None:
                    break

                try:
                    ok = controller.update()
                    if not ok:
                        local_fail_count += 1
                        with self._state_lock:
                            self.frame_fail_count = local_fail_count
                            self.last_hand_data = {
                                'move_x': 0,
                                'move_y': 0,
                                'aim_x': 0,
                                'aim_y': 0,
                                'left_detected': False,
                                'right_detected': False,
                                'shoot': False,
                                'dash': False,
                            }
                        if local_fail_count >= self.frame_fail_limit:
                            with self._state_lock:
                                self.enabled = False
                                self.last_error = "Camera feed lost"
                            break
                    else:
                        local_fail_count = 0
                        left_dx, left_dy = controller.get_left_hand_direction(self._game_width, self._game_height)
                        right_dx, right_dy = controller.get_right_hand_direction(self._game_width, self._game_height)

                        with self._state_lock:
                            self.frame_fail_count = 0
                            self.last_error = None
                            self.last_update_time = time()
                            self.last_hand_data = {
                                'move_x': left_dx,
                                'move_y': left_dy,
                                'aim_x': right_dx,
                                'aim_y': right_dy,
                                'left_detected': controller.left_hand_pos is not None,
                                'right_detected': controller.right_hand_pos is not None,
                                'shoot': controller.is_shooting(),
                                'dash': controller.is_dashing(),
                            }

                        now = time()
                        if (now - self.last_preview_time) >= self.preview_interval_secs:
                            preview = controller.get_preview_frame(width=self.preview_width, height=self.preview_height)
                            if preview is not None:
                                try:
                                    # Encode BGR frame directly; converting here swaps channels in Tk preview.
                                    ok_encode, encoded = cv2.imencode(
                                        '.png',
                                        preview,
                                        [cv2.IMWRITE_PNG_COMPRESSION, 1],
                                    )
                                    if ok_encode:
                                        preview_data = base64.b64encode(encoded.tobytes()).decode('ascii')
                                        with self._state_lock:
                                            self.cached_preview_data = preview_data
                                            self.cached_preview_version += 1
                                            self.last_preview_time = now
                                except Exception:
                                    pass
                except Exception as e:
                    local_fail_count += 1
                    with self._state_lock:
                        self.frame_fail_count = local_fail_count
                        self.last_error = str(e)
                    if local_fail_count >= self.frame_fail_limit:
                        with self._state_lock:
                            self.enabled = False
                        break

                elapsed = time() - frame_start
                sleep_for = self.tracking_interval_secs - elapsed
                if sleep_for > 0:
                    self._worker_stop_event.wait(sleep_for)

        self._worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        self._worker_thread.start()

    def _stop_tracking_worker(self):
        self._worker_stop_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.8)
        self._worker_thread = None
    
    def toggle(self):
        """Toggle hand control on/off"""
        if self.enabled:
            self.stop()
        else:
            self.start()
    
    def update(self, game_width, game_height):
        """Update hand tracking"""
        if not self.enabled or self.controller is None:
            return None

        self._game_width = game_width
        self._game_height = game_height

        now = time()
        if now - self.last_update_time < self.update_interval_secs:
            with self._state_lock:
                return dict(self.last_hand_data)

        with self._state_lock:
            return dict(self.last_hand_data)
    
    def cleanup(self):
        """Clean up resources"""
        self._stop_tracking_worker()
        if self.controller:
            self.controller.cleanup()
            self.controller = None
        self.enabled = False

    def get_preview_image_data(self, width=220, height=165):
        """Return base64 PNG data for Tk PhotoImage preview, or None if unavailable."""
        if not self.enabled or self.controller is None:
            self.cached_preview_data = None
            return None

        width = max(1, int(width))
        height = max(1, int(height))
        with self._state_lock:
            if width != self.preview_width or height != self.preview_height:
                self.preview_width = width
                self.preview_height = height
                self.cached_preview_data = None
                self.cached_preview_version = 0

        with self._state_lock:
            return self.cached_preview_data

    def get_preview_payload(self, width=220, height=165):
        """Return (base64_png_data, version) for cheap UI change detection."""
        data = self.get_preview_image_data(width=width, height=height)
        if data is None:
            return None, 0
        with self._state_lock:
            version = self.cached_preview_version
        return data, version

