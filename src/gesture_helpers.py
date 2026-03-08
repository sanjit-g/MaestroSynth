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
def vec3(a, b):
    return (b.x - a.x, b.y - a.y, b.z - a.z)

def norm3(v, eps=1e-8):
    mag = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if mag < eps:
        return (0.0, 0.0, 0.0)
    return (v[0] / mag, v[1] / mag, v[2] / mag)

def dot3(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def cross3(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    )

def dist3(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

def normalize2(vx, vy, eps=1e-8):
    mag = math.sqrt(vx * vx + vy * vy)
    if mag < eps:
        return 0.0, 0.0
    return vx / mag, vy / mag

def dot(ax, ay, bx, by):
    return ax * bx + ay * by

def dist(a, b) -> float:
    """Euclidean distance between two MediaPipe landmarks."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

def hand_center(lm):
    """
    Palm center in normalized image coordinates.
    """
    palm_ids = [0, 5, 9, 13, 17]
    cx = sum(lm[i].x for i in palm_ids) / len(palm_ids)
    cy = sum(lm[i].y for i in palm_ids) / len(palm_ids)
    return (cx, cy)

def finger_extended(lm, tip_id, pip_id, wrist_id=0, margin=0.015):
    """
    Finger considered extended if the tip is farther from the wrist
    than the PIP joint by some margin.
    """
    tip_dist = dist3(lm[tip_id], lm[wrist_id])
    pip_dist = dist3(lm[pip_id], lm[wrist_id])
    return tip_dist > pip_dist + margin

def thumb_is_out(lm, margin=0.02):
    """
    Thumb is 'out' if the thumb tip is meaningfully farther from the wrist
    than the inner thumb joints.

    This is separate from thumb direction.
    """
    wrist = lm[0]
    thumb_tip = lm[4]
    thumb_ip = lm[3]
    thumb_mcp = lm[2]

    tip_dist = dist3(thumb_tip, wrist)
    ip_dist = dist3(thumb_ip, wrist)
    mcp_dist = dist3(thumb_mcp, wrist)

    return tip_dist > ip_dist + margin and tip_dist > mcp_dist + margin

def classify_chord_quality(lm):
    """
    index / middle / pinky choose chord quality.
    ring is ignored.
    """
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    pinky_on = finger_extended(lm, 20, 18)

    combo = (index_on, middle_on, pinky_on)
    return CHORD_QUALITY_MAP.get(combo, "major")

def is_fist(lm):
    """
    Rough fist detection:
    all non-thumb fingers curled and thumb not out.
    """
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    thumb_out = thumb_is_out(lm)

    return (not index_on and not middle_on and not ring_on and not pinky_on and not thumb_out)

def in_center_zone(lm, margin=0.18):
    """
    Stop gesture only works near center of frame.
    """
    cx, cy = hand_center(lm)
    return abs(cx - 0.5) < margin and abs(cy - 0.5) < margin

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


def classify_thumb(lm, min_strength=0.20):
    """
    Classify thumb direction relative to the hand, not the screen.

    Hand-local axes:
      hand_up    = wrist -> middle MCP
      palm_normal = cross(wrist->index MCP, wrist->pinky MCP)
      hand_right = cross(hand_up, palm_normal)

    Returns:
      "THUMB UP", "THUMB DOWN", "THUMB LEFT", "THUMB RIGHT", or None
    """

    wrist = lm[0]
    index_mcp = lm[5]
    middle_mcp = lm[9]
    pinky_mcp = lm[17]
    thumb_base = lm[1]
    thumb_tip = lm[4]

    hand_up = norm3(vec3(wrist, middle_mcp))

    wrist_to_index = norm3(vec3(wrist, index_mcp))
    wrist_to_pinky = norm3(vec3(wrist, pinky_mcp))

    palm_normal = norm3(cross3(wrist_to_index, wrist_to_pinky))

    # If left/right seems reversed in practice, swap cross order here
    hand_right = norm3(cross3(hand_up, palm_normal))

    thumb_vec = norm3(vec3(thumb_base, thumb_tip))

    up_score = dot3(thumb_vec, hand_up)
    right_score = dot3(thumb_vec, hand_right)

    # pick whichever axis dominates
    if abs(up_score) >= abs(right_score) and abs(up_score) > min_strength:
        return "THUMB UP" if up_score > 0 else "THUMB DOWN"
    elif abs(right_score) > min_strength:
        return "THUMB RIGHT" if right_score > 0 else "THUMB LEFT"
    else:
        return None


def movement_bucket(anchor, current, threshold=0.06):
    """
    Compare current palm center to selection anchor.
    User can move hand LEFT / UP / RIGHT to choose the note.
    """
    ax, ay = anchor
    cx, cy = current

    dx = cx - ax
    dy = cy - ay

    # Not enough movement yet
    if abs(dx) < threshold and abs(dy) < threshold:
        return None

    # Up if upward movement dominates
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
    """
    Right-hand gesture state machine.

    Behavior:
    - Thumb out => selection mode
    - Thumb direction chooses note group
    - Hand movement LEFT / UP / RIGHT chooses specific root note
    - Index / middle / pinky choose chord quality
    - Thumb out -> thumb in transition locks chord
    - Fist in center stops sound
    """

    global gesture_state

    # -----------------------------------------------------
    # 1. Cooldown after STOP
    # -----------------------------------------------------
    if gesture_state["stop_cooldown"] > 0:
        gesture_state["stop_cooldown"] -= 1
        gesture_state["debug_text"] = f"COOLDOWN {gesture_state['stop_cooldown']}"
        gesture_state["prev_thumb_out"] = thumb_is_out(landmarks)
        return {
            "action": "cooldown",
            "locked": False,
            "note": None,
            "quality": None
        }

    # -----------------------------------------------------
    # 2. Read current hand state
    # -----------------------------------------------------
    current_center = hand_center(landmarks)
    thumb_out = thumb_is_out(landmarks)
    chord_quality = classify_chord_quality(landmarks)
    fist_now = is_fist(landmarks) and in_center_zone(landmarks)

    thumb_dir = None
    if thumb_out:
        thumb_dir = classify_thumb(landmarks)

    # -----------------------------------------------------
    # 3. STOP gesture
    # -----------------------------------------------------
    if fist_now:
        stop_chord()

        gesture_state["mode"] = "IDLE"
        gesture_state["locked"] = False
        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["current_note"] = None
        gesture_state["current_quality"] = "major"
        gesture_state["last_played"] = None
        gesture_state["stop_cooldown"] = 6
        gesture_state["debug_text"] = "STOP"
        gesture_state["prev_thumb_out"] = thumb_out

        return {
            "action": "stop",
            "locked": False,
            "note": None,
            "quality": None
        }

    # -----------------------------------------------------
    # 4. Lock event: thumb was out, now is in
    # -----------------------------------------------------
    if gesture_state["prev_thumb_out"] and not thumb_out:
        if gesture_state["current_note"] is not None:
            gesture_state["mode"] = "LOCKED"
            gesture_state["locked"] = True
            gesture_state["current_quality"] = chord_quality
            gesture_state["debug_text"] = f"LOCKED {gesture_state['current_note']} {gesture_state['current_quality']}"
        else:
            gesture_state["mode"] = "IDLE"
            gesture_state["locked"] = False
            gesture_state["debug_text"] = "IDLE"

        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["prev_thumb_out"] = thumb_out

        return {
            "action": "locked" if gesture_state["locked"] else "idle",
            "locked": gesture_state["locked"],
            "note": gesture_state["current_note"],
            "quality": gesture_state["current_quality"]
        }

    # -----------------------------------------------------
    # 5. If locked and thumb is still in, hold chord
    # -----------------------------------------------------
    if gesture_state["mode"] == "LOCKED" and not thumb_out:
        gesture_state["debug_text"] = f"HOLD {gesture_state['current_note']} {gesture_state['current_quality']}"
        gesture_state["prev_thumb_out"] = thumb_out
        return {
            "action": "holding_locked",
            "locked": True,
            "note": gesture_state["current_note"],
            "quality": gesture_state["current_quality"]
        }

    # -----------------------------------------------------
    # 6. Thumb out => selection mode
    # -----------------------------------------------------
    if thumb_out:
        gesture_state["mode"] = "SELECTING"
        gesture_state["locked"] = False
        gesture_state["current_quality"] = chord_quality

        # If thumb direction can't be confidently classified yet, wait
        if thumb_dir is None:
            gesture_state["debug_text"] = "SELECTING: thumb unclear"
            gesture_state["prev_thumb_out"] = thumb_out
            return {
                "action": "selecting_unclear_thumb",
                "locked": False,
                "note": gesture_state["current_note"],
                "quality": chord_quality
            }

        # Reset anchor whenever selection starts or thumb direction changes
        if (gesture_state["selection_anchor"] is None or
            gesture_state["selection_thumb_dir"] != thumb_dir):
            gesture_state["selection_anchor"] = current_center
            gesture_state["selection_thumb_dir"] = thumb_dir

        move_dir = movement_bucket(gesture_state["selection_anchor"], current_center)

        if move_dir is None:
            gesture_state["debug_text"] = f"SELECTING {thumb_dir} (waiting for motion)"
            gesture_state["prev_thumb_out"] = thumb_out
            return {
                "action": "arming_selection",
                "locked": False,
                "thumb_dir": thumb_dir,
                "note": gesture_state["current_note"],
                "quality": chord_quality
            }

        # Determine note from thumb group + motion
        note = NOTE_GRID[thumb_dir][move_dir]
        gesture_state["current_note"] = note
        gesture_state["current_quality"] = chord_quality

        chord_tuple = (note, chord_quality)

        # only retrigger when note or quality changes
        if gesture_state["last_played"] != chord_tuple:
            play_chord(note, chord_quality)
            gesture_state["last_played"] = chord_tuple

        gesture_state["debug_text"] = f"SELECT {thumb_dir} + {move_dir} -> {note} {chord_quality}"
        gesture_state["prev_thumb_out"] = thumb_out

        return {
            "action": "selecting",
            "locked": False,
            "thumb_dir": thumb_dir,
            "move_dir": move_dir,
            "note": note,
            "quality": chord_quality
        }

    # -----------------------------------------------------
    # 7. Fallback idle
    # -----------------------------------------------------
    gesture_state["mode"] = "IDLE"
    gesture_state["locked"] = False
    gesture_state["selection_anchor"] = None
    gesture_state["selection_thumb_dir"] = None
    gesture_state["debug_text"] = "IDLE"
    gesture_state["prev_thumb_out"] = thumb_out

    return {
        "action": "idle",
        "locked": False,
        "note": gesture_state["current_note"],
        "quality": gesture_state["current_quality"]
    }
