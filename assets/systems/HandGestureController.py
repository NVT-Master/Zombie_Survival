"""
Hand Gesture Controller - control game with hand gestures via webcam.
Supports both legacy MediaPipe Solutions API and modern Tasks API.
"""

import os
import urllib.request
from math import acos, degrees, sqrt
from time import perf_counter

import cv2


def _signed_power(value: float, exponent: float) -> float:
    if value >= 0:
        return abs(value) ** exponent
    return -(abs(value) ** exponent)


def _apply_soft_deadzone(value: float, deadzone: float) -> float:
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    scaled = (magnitude - deadzone) / max(1e-6, 1.0 - deadzone)
    return scaled if value >= 0 else -scaled

# Reduce noisy native logs from MediaPipe/TFLite in terminal.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("ABSL_LOG_SEVERITY_LEVEL", "3")

try:
    from absl import logging as absl_logging

    absl_logging.set_verbosity(absl_logging.ERROR)
    absl_logging.set_stderrthreshold("error")
except Exception:
    pass

FINGER_INDEXES = {
    "thumb": (1, 2, 4),
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

ACTION_PROFILES = {
    "OpenPalm": {"thumb", "index", "middle", "ring", "pinky"},
    "Fist": set(),
    "Peace": {"index", "middle"},
    "Point": {"index"},
    "ThumbsUp": {"thumb"},
}

MEDIAPIPE_AVAILABLE = False
MEDIAPIPE_ERROR = None
MEDIAPIPE_BACKEND = None
HAND_TASK_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
HAND_TASK_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task")

try:
    import mediapipe as mp

    if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
        MEDIAPIPE_AVAILABLE = True
        MEDIAPIPE_BACKEND = "solutions"
    else:
        from mediapipe.tasks import python as mp_tasks_python
        from mediapipe.tasks.python import vision as mp_tasks_vision

        if hasattr(mp_tasks_vision, "HandLandmarker"):
            MEDIAPIPE_AVAILABLE = True
            MEDIAPIPE_BACKEND = "tasks"
        else:
            MEDIAPIPE_ERROR = "MediaPipe installed but does not expose hand tracking APIs."
except Exception as e:
    MEDIAPIPE_ERROR = f"MediaPipe is not available: {e}"


def _ensure_hand_task_model():
    """Ensure hand_landmarker.task exists locally for Tasks API backend."""
    if os.path.exists(HAND_TASK_MODEL_PATH):
        return HAND_TASK_MODEL_PATH

    os.makedirs(os.path.dirname(HAND_TASK_MODEL_PATH), exist_ok=True)
    try:
        urllib.request.urlretrieve(HAND_TASK_MODEL_URL, HAND_TASK_MODEL_PATH)
        return HAND_TASK_MODEL_PATH
    except Exception as e:
        raise RuntimeError(
            "Could not download Hand Landmarker model automatically. "
            f"Download it manually to {HAND_TASK_MODEL_PATH}. Error: {e}"
        )


class HandGestureController:
    """Detects hand gestures and converts them to game controls"""

    LEFT_MOVE_DEADZONE = 0.05
    LEFT_MOVE_CURVE = 1.08
    LEFT_MOVE_SMOOTHING = 0.26
    RIGHT_AIM_SENSITIVITY = 1.45
    RIGHT_AIM_CURVE = 0.80
    
    def __init__(self, camera_index=0, debug=False):
        self.debug = debug
        self.camera_index = camera_index
        self.cap = None
        self.backend = MEDIAPIPE_BACKEND
        self.mp_hands = None
        self.hands = None
        self.mp_drawing = None
        self.mp_tasks_python = None
        self.mp_tasks_vision = None
        self.hand_landmarker = None
        self.frame = None
        self.is_dummy = False  # Flag if running in fallback mode
        
        # Hand tracking
        self.left_hand_pos = None  # (x, y) normalized 0-1
        self.right_hand_pos = None  # (x, y) normalized 0-1
        self.left_hand_closed = False  # fingers are pinched
        self.right_hand_shooting = False  # is pointing/aiming
        self.left_hand_action = "Unknown"
        self.right_hand_action = "Unknown"
        
        self.frame_width = 640
        self.frame_height = 480
        self.last_video_timestamp_ms = 0
        self.is_mirrored_input = True
        self.capture_backend = "unknown"
        self._left_move_filtered_x = 0.0
        self._left_move_filtered_y = 0.0
        
        # If MediaPipe not available, run in dummy mode
        if not MEDIAPIPE_AVAILABLE:
            self.is_dummy = True
            raise RuntimeError(MEDIAPIPE_ERROR)

        # MediaPipe setup (legacy solutions or new tasks backend)
        try:
            if self.backend == "solutions":
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=2,
                    min_detection_confidence=0.55,
                    min_tracking_confidence=0.45
                )
                self.mp_drawing = mp.solutions.drawing_utils
            elif self.backend == "tasks":
                from mediapipe.tasks import python as mp_tasks_python
                from mediapipe.tasks.python import vision as mp_tasks_vision

                model_path = _ensure_hand_task_model()
                options = mp_tasks_vision.HandLandmarkerOptions(
                    base_options=mp_tasks_python.BaseOptions(model_asset_path=model_path),
                    running_mode=mp_tasks_vision.RunningMode.VIDEO,
                    num_hands=2,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.45,
                    min_tracking_confidence=0.45,
                )
                self.mp_tasks_python = mp_tasks_python
                self.mp_tasks_vision = mp_tasks_vision
                self.hand_landmarker = mp_tasks_vision.HandLandmarker.create_from_options(options)
            else:
                raise RuntimeError("No compatible MediaPipe backend found.")
        except Exception as e:
            self.is_dummy = True
            raise RuntimeError(f"Failed to initialize MediaPipe hand tracker: {e}")
        
        # Camera setup
        try:
            backend_candidates = [
                (cv2.CAP_DSHOW, "DSHOW"),
                (cv2.CAP_MSMF, "MSMF"),
                (cv2.CAP_ANY, "ANY"),
            ]
            open_errors = []
            self.cap = None
            for backend, backend_name in backend_candidates:
                try:
                    if backend == cv2.CAP_ANY:
                        cap = cv2.VideoCapture(camera_index)
                    else:
                        cap = cv2.VideoCapture(camera_index, backend)
                except Exception as backend_error:
                    open_errors.append(f"{backend_name}: {backend_error}")
                    continue

                if cap is not None and cap.isOpened():
                    self.cap = cap
                    self.capture_backend = backend_name
                    break

                if cap is not None:
                    cap.release()
                open_errors.append(f"{backend_name}: open failed")

            if self.cap is None:
                details = "; ".join(open_errors) if open_errors else "no backend details"
                raise RuntimeError(f"Cannot open camera {camera_index} ({details})")

            # Use a lighter capture profile to reduce CPU load during gameplay.
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Get frame dimensions
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        except Exception as e:
            self.cap = None
            raise RuntimeError(f"Camera initialization failed: {e}")
        
        
    def _get_hand_distance(self, landmarks, idx1, idx2):
        """Calculate distance between two landmarks"""
        p1 = landmarks[idx1]
        p2 = landmarks[idx2]
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    def _is_pointing(self, landmarks):
        """Check if hand maps to pointing action."""
        states = self._compute_fingers(landmarks)
        return self._infer_action(states) == "Point"
    
    def _is_hand_closed(self, landmarks):
        """Check if hand maps to fist action."""
        states = self._compute_fingers(landmarks)
        return self._infer_action(states) == "Fist"

    def _angle_open(self, mcp, pip, tip, min_angle_deg=155.0):
        vec1 = (tip.x - pip.x, tip.y - pip.y, tip.z - pip.z)
        vec2 = (mcp.x - pip.x, mcp.y - pip.y, mcp.z - pip.z)

        dot = (vec1[0] * vec2[0]) + (vec1[1] * vec2[1]) + (vec1[2] * vec2[2])
        n1 = sqrt((vec1[0] ** 2) + (vec1[1] ** 2) + (vec1[2] ** 2)) + 1e-6
        n2 = sqrt((vec2[0] ** 2) + (vec2[1] ** 2) + (vec2[2] ** 2)) + 1e-6
        cosine = max(-1.0, min(1.0, dot / (n1 * n2)))
        angle = degrees(acos(cosine))
        return angle >= min_angle_deg

    def _thumb_extended(self, landmarks):
        thumb_mcp = landmarks[2]
        thumb_ip = landmarks[3]
        thumb_tip = landmarks[4]
        index_mcp = landmarks[5]

        joint_open = self._angle_open(thumb_mcp, thumb_ip, thumb_tip, min_angle_deg=145.0)

        tip_to_index = sqrt(
            (thumb_tip.x - index_mcp.x) ** 2 +
            (thumb_tip.y - index_mcp.y) ** 2 +
            (thumb_tip.z - index_mcp.z) ** 2
        )
        ip_to_index = sqrt(
            (thumb_ip.x - index_mcp.x) ** 2 +
            (thumb_ip.y - index_mcp.y) ** 2 +
            (thumb_ip.z - index_mcp.z) ** 2
        ) + 1e-6

        return joint_open and (tip_to_index > (1.08 * ip_to_index))

    def _is_pointing_loose(self, landmarks):
        """More tolerant pointing detector for real camera noise."""
        index_up = landmarks[8].y < (landmarks[6].y - 0.01)
        middle_folded = landmarks[12].y > (landmarks[10].y - 0.005)
        return index_up and middle_folded

    def _is_fist_loose(self, landmarks):
        """More tolerant fist detector; handles partial occlusion better."""
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        folded = 0
        for tip_idx, pip_idx in zip(finger_tips, finger_pips):
            if landmarks[tip_idx].y > (landmarks[pip_idx].y - 0.005):
                folded += 1

        thumb_to_index = sqrt(
            (landmarks[4].x - landmarks[8].x) ** 2 +
            (landmarks[4].y - landmarks[8].y) ** 2
        )
        return folded >= 3 or thumb_to_index < 0.08

    def _compute_fingers(self, landmarks):
        states = {}
        for name, (mcp, pip, tip) in FINGER_INDEXES.items():
            if name == "thumb":
                states[name] = self._thumb_extended(landmarks)
            else:
                states[name] = self._angle_open(landmarks[mcp], landmarks[pip], landmarks[tip], min_angle_deg=155.0)
        return states

    def _infer_action(self, finger_states):
        opened = {name for name, is_open in finger_states.items() if is_open}
        for action, profile in ACTION_PROFILES.items():
            if opened == profile:
                return action
        if len(opened) >= 4:
            return "OpenPalm"
        if len(opened) == 0:
            return "Fist"
        return "Custom"

    def update(self):
        """Update hand tracking from webcam frame"""
        if self.cap is None:
            return False

        ret, frame = self.cap.read()
        if not ret:
            return False
        
        # Flip and convert to RGB
        frame = cv2.flip(frame, 1)
        self.frame_height, self.frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Reset hand tracking
        self.left_hand_pos = None
        self.right_hand_pos = None
        self.left_hand_closed = False
        self.right_hand_shooting = False
        self.left_hand_action = "Unknown"
        self.right_hand_action = "Unknown"

        try:
            if self.backend == "solutions":
                results = self.hands.process(rgb_frame)
                if results.multi_hand_landmarks and results.multi_handedness:
                    for landmarks_wrapper, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        landmarks = landmarks_wrapper.landmark
                        label = handedness.classification[0].label
                        if self.is_mirrored_input:
                            is_right = label == "Left"
                        else:
                            is_right = label == "Right"

                        palm = landmarks[0]
                        x = palm.x
                        y = palm.y

                        if is_right:
                            self.right_hand_pos = (landmarks[8].x, landmarks[8].y)
                            right_states = self._compute_fingers(landmarks)
                            self.right_hand_action = self._infer_action(right_states)
                            self.right_hand_shooting = (self.right_hand_action == "Point") or self._is_pointing_loose(landmarks)
                            if self.debug:
                                status = "POINTING" if self.right_hand_shooting else "NORMAL"
                                cv2.putText(frame, f"Right: {status}", (10, 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        else:
                            # Left movement uses index fingertip only.
                            self.left_hand_pos = (landmarks[8].x, landmarks[8].y)
                            left_states = self._compute_fingers(landmarks)
                            self.left_hand_action = self._infer_action(left_states)
                            self.left_hand_closed = (self.left_hand_action == "Fist") or self._is_fist_loose(landmarks)
                            if self.debug:
                                status = "CLOSED" if self.left_hand_closed else "OPEN"
                                cv2.putText(frame, f"Left: {status}", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

                        if self.debug:
                            self.mp_drawing.draw_landmarks(frame, landmarks_wrapper, self.mp_hands.HAND_CONNECTIONS)
            elif self.backend == "tasks":
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                timestamp_ms = int(perf_counter() * 1000)
                if timestamp_ms <= self.last_video_timestamp_ms:
                    timestamp_ms = self.last_video_timestamp_ms + 1
                self.last_video_timestamp_ms = timestamp_ms
                result = self.hand_landmarker.detect_for_video(mp_image, timestamp_ms)

                if result.hand_landmarks and result.handedness:
                    for idx, landmarks in enumerate(result.hand_landmarks):
                        handedness_group = result.handedness[idx] if idx < len(result.handedness) else []
                        label = ""
                        if handedness_group:
                            top = handedness_group[0]
                            label = (getattr(top, "category_name", "") or getattr(top, "display_name", "") or "")

                        if label:
                            if self.is_mirrored_input:
                                is_right = label.lower() == "left"
                            else:
                                is_right = label.lower() == "right"
                        else:
                            is_right = landmarks[0].x > 0.5

                        palm = landmarks[0]
                        x = palm.x
                        y = palm.y

                        if is_right:
                            self.right_hand_pos = (landmarks[8].x, landmarks[8].y)
                            right_states = self._compute_fingers(landmarks)
                            self.right_hand_action = self._infer_action(right_states)
                            self.right_hand_shooting = (self.right_hand_action == "Point") or self._is_pointing_loose(landmarks)
                            if self.debug:
                                status = "POINTING" if self.right_hand_shooting else "NORMAL"
                                cv2.putText(frame, f"Right: {status}", (10, 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        else:
                            # Left movement uses index fingertip only.
                            self.left_hand_pos = (landmarks[8].x, landmarks[8].y)
                            left_states = self._compute_fingers(landmarks)
                            self.left_hand_action = self._infer_action(left_states)
                            self.left_hand_closed = (self.left_hand_action == "Fist") or self._is_fist_loose(landmarks)
                            if self.debug:
                                status = "CLOSED" if self.left_hand_closed else "OPEN"
                                cv2.putText(frame, f"Left: {status}", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

                        if self.debug:
                            for lm in landmarks:
                                px = int(lm.x * self.frame_width)
                                py = int(lm.y * self.frame_height)
                                cv2.circle(frame, (px, py), 2, (255, 255, 255), -1)
            else:
                return False
        except Exception:
            return False
        
        # Store frame for debug display
        self.frame = frame
        
        if self.debug:
            cv2.imshow("Hand Gesture Controller", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return False
        
        return True

    def get_preview_frame(self, width=220, height=165):
        """Return a resized BGR preview frame with simple hand status overlays."""
        if self.frame is None:
            return None

        preview = self.frame.copy()

        if self.left_hand_pos is not None:
            lx = int(self.left_hand_pos[0] * self.frame_width)
            ly = int(self.left_hand_pos[1] * self.frame_height)
            left_color = (0, 180, 255) if self.left_hand_closed else (255, 150, 0)
            left_text = f"LEFT {self.left_hand_action.upper()}"
            cv2.circle(preview, (lx, ly), 18, left_color, 3)
            cv2.putText(preview, left_text, (10, self.frame_height - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, left_color, 2)

        if self.right_hand_pos is not None:
            rx = int(self.right_hand_pos[0] * self.frame_width)
            ry = int(self.right_hand_pos[1] * self.frame_height)
            right_color = (70, 220, 70) if self.right_hand_shooting else (70, 170, 255)
            right_text = f"RIGHT {self.right_hand_action.upper()}"
            cv2.circle(preview, (rx, ry), 14, right_color, 2)
            cv2.putText(preview, right_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, right_color, 2)

        return cv2.resize(preview, (width, height), interpolation=cv2.INTER_AREA)
    
    def get_left_hand_direction(self, game_width, game_height):
        """
        Convert left index-fingertip position to normalized game direction (-1 to 1)
        Returns: (dx, dy) where dx is left-right, dy is up-down
        """
        if self.left_hand_pos is None:
            # Decay to neutral to avoid sudden snaps when detection flickers.
            self._left_move_filtered_x *= 0.55
            self._left_move_filtered_y *= 0.55
            return (self._left_move_filtered_x, self._left_move_filtered_y)

        x, y = self.left_hand_pos
        raw_dx = max(-1.0, min(1.0, (x - 0.5) * 2.0))
        raw_dy = max(-1.0, min(1.0, (y - 0.5) * 2.0))

        dx = _apply_soft_deadzone(raw_dx, self.LEFT_MOVE_DEADZONE)
        dy = _apply_soft_deadzone(raw_dy, self.LEFT_MOVE_DEADZONE)

        dx = _signed_power(dx, self.LEFT_MOVE_CURVE)
        dy = _signed_power(dy, self.LEFT_MOVE_CURVE)

        alpha = self.LEFT_MOVE_SMOOTHING
        self._left_move_filtered_x += (dx - self._left_move_filtered_x) * alpha
        self._left_move_filtered_y += (dy - self._left_move_filtered_y) * alpha

        return (self._left_move_filtered_x, self._left_move_filtered_y)
    
    def get_right_hand_direction(self, game_width, game_height):
        """
        Convert right hand position to normalized aim direction
        Returns: (dx, dy) where dx is left-right, dy is up-down
        """
        if self.right_hand_pos is None:
            return (0, 0)
        
        x, y = self.right_hand_pos
        
        # Convert from camera space (0-1) to game direction
        dx = (x - 0.5) * 2
        dy = (y - 0.5) * 2

        # Amplify small motions around center for snappier control.
        dx = _signed_power(dx, self.RIGHT_AIM_CURVE) * self.RIGHT_AIM_SENSITIVITY
        dy = _signed_power(dy, self.RIGHT_AIM_CURVE) * self.RIGHT_AIM_SENSITIVITY
        
        # Clamp
        dx = max(-1, min(1, dx))
        dy = max(-1, min(1, dy))
        
        return (dx, dy)
    
    def is_shooting(self):
        """Returns True if right hand is in shooting pose (pointing)"""
        return self.right_hand_shooting
    
    def is_dashing(self):
        """Returns True if left hand is closed (fist)"""
        return self.left_hand_closed
    
    def cleanup(self):
        """Release resources"""
        try:
            if self.hands is not None:
                self.hands.close()
        except:
            pass
        try:
            if self.hand_landmarker is not None:
                self.hand_landmarker.close()
        except:
            pass
        try:
            if self.cap:
                self.cap.release()
        except:
            pass
        try:
            cv2.destroyAllWindows()
        except:
            pass
    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass


if __name__ == "__main__":
    # Test the controller
    print("Testing Hand Gesture Controller...")
    print("Make sure your webcam is working")
    print("Press 'q' to quit")
    
    try:
        controller = HandGestureController(debug=True)
        
        while controller.update():
            left = controller.get_left_hand_direction(800, 600)
            right = controller.get_right_hand_direction(800, 600)
            
            print(f"Left: {left}, Right: {right}, Shooting: {controller.is_shooting()}, Dashing: {controller.is_dashing()}")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        controller.cleanup()
