import math
import cv2
from midi_helpers import gesture_to_note

# ─── Note Grid & Chord Maps ───────────────────────────────────────────────────

NOTE_GRID = {
    "THUMB UP": {
        "LEFT":  "C",
        "UP":    "G",
        "RIGHT": "D",
    },
    "THUMB RIGHT": {
        "LEFT":  "A",
        "UP":    "E",
        "RIGHT": "B",
    },
    "THUMB LEFT": {
        "LEFT":  "Eb",
        "UP":    "Bb",
        "RIGHT": "F",
    },
    "THUMB DOWN": {
        "LEFT":  "Gb",
        "UP":    "Db",
        "RIGHT": "Ab",
    }
}

CHORD_QUALITY_MAP = {
    (False, False, False): "major",
    (True,  False, False): "minor",
    (True,  True,  False): "maj7",
    (True,  True,  True):  "min7",
    (True,  False, True):  "7",
}

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),        # thumb
    (0,5),(5,6),(6,7),(7,8),        # index
    (0,9),(9,10),(10,11),(11,12),   # middle
    (0,13),(13,14),(14,15),(15,16), # ring
    (0,17),(17,18),(18,19),(19,20), # pinky
    (5,9),(9,13),(13,17)            # palm
]

# ─── Gesture State ────────────────────────────────────────────────────────────

gesture_state = {
    "locked": False,
    "selection_anchor": None,
    "selection_thumb_dir": None,
    "current_note": None,
    "current_quality": "major",
    "last_played": None,
    "prev_thumb_out": False,
    "stop_cooldown": 0,
}


# ─── Landmark Math ────────────────────────────────────────────────────────────

def dist(a, b) -> float:
    """Euclidean distance between two MediaPipe landmarks."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

def hand_center(lm) -> tuple:
    """
    Approximate palm center using wrist + MCP joints.

    Returns:
        tuple[float, float]: Normalized (x, y) in [0, 1].
    """
    palm_ids = [0, 5, 9, 13, 17]
    cx = sum(lm[i].x for i in palm_ids) / len(palm_ids)
    cy = sum(lm[i].y for i in palm_ids) / len(palm_ids)
    return (cx, cy)


# ─── Finger State Checks ──────────────────────────────────────────────────────

def finger_extended(lm, tip_id: int, pip_id: int, wrist_id: int = 0, margin: float = 0.02) -> bool:
    """
    Check if a finger is extended.

    Finger is extended if its tip is farther from the wrist than its PIP joint.

    Args:
        lm       : MediaPipe landmark list
        tip_id   : Landmark index of fingertip
        pip_id   : Landmark index of PIP joint
        wrist_id : Landmark index of wrist (default 0)
        margin   : Extra distance threshold to avoid noise
    """
    return dist(lm[tip_id], lm[wrist_id]) > dist(lm[pip_id], lm[wrist_id]) + margin

def thumb_is_out(lm, margin: float = 0.03) -> bool:
    """
    Check if the thumb is extended.

    Thumb tip must be noticeably farther from wrist than the thumb IP/MCP area.
    """
    return dist(lm[4], lm[0]) > dist(lm[2], lm[0]) + margin

def is_fist(lm) -> bool:
    """All four fingers curled and thumb not extended."""
    return not any([
        finger_extended(lm, 8,  6),   # index
        finger_extended(lm, 12, 10),  # middle
        finger_extended(lm, 16, 14),  # ring
        finger_extended(lm, 20, 18),  # pinky
        thumb_is_out(lm),
    ])

def in_center_zone(lm, center_margin: float = 0.18) -> bool:
    """Check if the hand center is within the middle region of the frame."""
    cx, cy = hand_center(lm)
    return abs(cx - 0.5) < center_margin and abs(cy - 0.5) < center_margin


# ─── Classification ───────────────────────────────────────────────────────────

def classify_chord_quality(lm) -> str:
    """
    Classify chord quality from finger extension state.

    Uses index, middle, and pinky fingers as selectors. Ring finger ignored.

    Returns:
        str: One of 'major', 'minor', 'maj7', 'min7', '7'
    """
    combo = (
        finger_extended(lm, 8,  6),   # index
        finger_extended(lm, 12, 10),  # middle
        finger_extended(lm, 20, 18),  # pinky
    )
    return CHORD_QUALITY_MAP.get(combo, "major")

def classify_thumb(lm) -> str:
    """
    Classify thumb direction relative to its MCP joint.

    Returns:
        str: One of 'THUMB UP', 'THUMB DOWN', 'THUMB LEFT', 'THUMB RIGHT'
    """
    dx = lm[4].x - lm[2].x
    dy = lm[4].y - lm[2].y
    if abs(dx) > abs(dy):
        return "THUMB RIGHT" if dx > 0 else "THUMB LEFT"
    return "THUMB UP" if dy < 0 else "THUMB DOWN"

def movement_bucket(anchor: tuple, current: tuple, threshold: float = 0.08):
    """
    Determine hand movement direction from an anchor point.

    Only LEFT, UP, and RIGHT are returned — no DOWN.
    Image coordinates: x increases right, y increases downward.

    Args:
        anchor    : (x, y) reference position
        current   : (x, y) current hand center
        threshold : Minimum displacement to register a direction

    Returns:
        str | None: 'LEFT', 'UP', 'RIGHT', or None if not enough movement
    """
    dx = current[0] - anchor[0]
    dy = current[1] - anchor[1]

    if abs(dx) < threshold and abs(dy) < threshold:
        return None
    if dy < -threshold and abs(dy) >= abs(dx):
        return "UP"
    if dx < -threshold:
        return "LEFT"
    if dx > threshold:
        return "RIGHT"
    return None


# ─── Drawing ──────────────────────────────────────────────────────────────────

ACTION_COLORS = {
    "stop":             (0,   0,   255),
    "idle":             (180, 180, 180),
    "locked":           (0,   255, 255),
    "selecting":        (0,   255, 0),
    "arming_selection": (255, 165, 0),
}

def draw_landmarks(frame, landmarks):
    """Draw hand skeleton onto the frame."""
    h, w = frame.shape[:2]
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], (0, 200, 0), 2)
    for pt in points:
        cv2.circle(frame, pt, 5, (0, 0, 255), -1)

def draw_hud(frame, gesture_result: dict, midi_port_name: str):
    """
    Draw a status HUD overlay onto the frame.

    Shows: action state, current chord, MIDI port, thumb/move direction.
    """
    h, w   = frame.shape[:2]
    action  = gesture_result.get("action", "idle")
    note    = gesture_result.get("note")
    quality = gesture_result.get("quality")
    locked  = gesture_result.get("locked", False)
    color   = ACTION_COLORS.get(action, (255, 255, 255))

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, f"State: {action.upper().replace('_', ' ')}",
                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    chord_str = f"{note} {quality}" if note else "---"
    lock_str  = " [LOCKED]" if locked else ""
    cv2.putText(frame, f"Chord: {chord_str}{lock_str}",
                (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    cv2.putText(frame, f"MIDI: {midi_port_name}",
                (12, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 255), 1)

    if action in ("selecting", "arming_selection"):
        thumb_dir = gesture_result.get("thumb_dir", "")
        move_dir  = gesture_result.get("move_dir", "waiting...")
        cv2.putText(frame, f"{thumb_dir}  ->  {move_dir}",
                    (w - 280, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 220, 100), 2)

    cv2.putText(frame, "Fist in center = STOP  |  Q to quit",
                (12, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1)


# ─── State Machine ────────────────────────────────────────────────────────────

def handle_gesture(landmarks):
    global gesture_state

    thumb_out = thumb_is_out(landmarks)
    fist_now = is_fist(landmarks) and in_center_zone(landmarks)

    # cooldown after stop
    if gesture_state["stop_cooldown"] > 0:
        gesture_state["stop_cooldown"] -= 1
        gesture_state["prev_thumb_out"] = thumb_out
        return {
            "action": "cooldown",
            "note": None,
            "quality": None,
            "locked": False
        }

    # STOP gesture
    if fist_now:
        stop_chord()
        gesture_state["locked"] = False
        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["current_note"] = None
        gesture_state["last_played"] = None
        gesture_state["stop_cooldown"] = 8   # ignore input for a few frames
        gesture_state["prev_thumb_out"] = thumb_out
        return {
            "action": "stop",
            "note": None,
            "quality": None,
            "locked": False
        }

    # LOCK only on transition: thumb out -> thumb in
    if gesture_state["prev_thumb_out"] and not thumb_out:
        if gesture_state["current_note"] is not None:
            gesture_state["locked"] = True
        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["prev_thumb_out"] = thumb_out
        return {
            "action": "locked",
            "note": gesture_state["current_note"],
            "quality": gesture_state["current_quality"],
            "locked": gesture_state["locked"]
        }

    # if locked, do nothing until thumb comes back out
    if gesture_state["locked"] and not thumb_out:
        gesture_state["prev_thumb_out"] = thumb_out
        return {
            "action": "holding_locked",
            "note": gesture_state["current_note"],
            "quality": gesture_state["current_quality"],
            "locked": True
        }

    # thumb out means unlock and allow reselection
    if thumb_out:
        gesture_state["locked"] = False
        # selection logic here ...

    gesture_state["prev_thumb_out"] = thumb_out
