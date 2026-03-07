import cv2
import mediapipe
import mido
import urllib.request
import os

# Download model if needed
MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading hand landmarker model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL_PATH
    )
    print("Done.")

# Hand connections (index pairs)
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),       # thumb
    (0,5),(5,6),(6,7),(7,8),       # index
    (0,9),(9,10),(10,11),(11,12),  # middle
    (0,13),(13,14),(14,15),(15,16),# ring
    (0,17),(17,18),(18,19),(19,20),# pinky
    (5,9),(9,13),(13,17)           # palm
]

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
    (False, False, False): "major",  # none
    (True,  False, False): "minor",  # index
    (True,  True,  False): "maj7",   # index + middle
    (True,  True,  True):  "min7",   # index + middle + pinky
    (True,  False, True):  "7",      # index + pinky
}

gesture_state = {
    "locked": False,               # whether current chord is locked
    "selection_anchor": None,      # hand center when thumb first extends
    "selection_thumb_dir": None,   # thumb direction when entering selection
    "current_note": None,
    "current_quality": "major",
    "last_played": None,           # tuple(note, quality)
}

def dist(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

def hand_center(lm):
    """
    Approximate palm center using wrist + MCP joints.
    Returns normalized (x, y) in [0,1].
    """
    palm_ids = [0, 5, 9, 13, 17]
    cx = sum(lm[i].x for i in palm_ids) / len(palm_ids)
    cy = sum(lm[i].y for i in palm_ids) / len(palm_ids)
    return (cx, cy)

def finger_extended(lm, tip_id, pip_id, wrist_id=0, margin=0.02):
    """
    Simple extension test:
    finger is extended if fingertip is farther from wrist than PIP joint.
    """
    tip_dist = dist(lm[tip_id], lm[wrist_id])
    pip_dist = dist(lm[pip_id], lm[wrist_id])
    return tip_dist > pip_dist + margin

def thumb_is_out(lm, margin=0.03):
    """
    Thumb considered 'out' if thumb tip is noticeably farther from wrist
    than thumb IP / MCP area.
    """
    tip_dist = dist(lm[4], lm[0])
    joint_dist = dist(lm[2], lm[0])
    return tip_dist > joint_dist + margin

def classify_chord_quality(lm):
    """
    Uses index, middle, pinky as chord selectors.
    Ring finger ignored.
    """
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    pinky_on = finger_extended(lm, 20, 18)

    combo = (index_on, middle_on, pinky_on)
    return CHORD_QUALITY_MAP.get(combo, "major")

def is_fist(lm):
    """
    All four fingers curled + thumb not out.
    """
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    thumb_out = thumb_is_out(lm)

    return (not index_on and not middle_on and not ring_on and not pinky_on and not thumb_out)

def in_center_zone(lm, center_margin=0.18):
    """
    Hand is near middle of screen.
    """
    cx, cy = hand_center(lm)
    return (abs(cx - 0.5) < center_margin) and (abs(cy - 0.5) < center_margin)

def movement_bucket(anchor, current, threshold=0.08):
    """
    Determine whether hand moved LEFT, UP, or RIGHT from the anchor.
    Only those 3 directions are used for note selection.
    
    Image coordinates:
      x increases to the right
      y increases downward
    So 'up' means dy < 0
    """
    ax, ay = anchor
    cx, cy = current

    dx = cx - ax
    dy = cy - ay

    # Need enough movement to count
    if abs(dx) < threshold and abs(dy) < threshold:
        return None

    # If moved upward enough and that movement dominates, treat as UP
    if dy < -threshold and abs(dy) >= abs(dx):
        return "UP"

    if dx < -threshold:
        return "LEFT"

    if dx > threshold:
        return "RIGHT"

    return None

def draw_landmarks(frame, landmarks):
    h, w = frame.shape[:2]
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], (0, 200, 0), 2)
    for pt in points:
        cv2.circle(frame, pt, 5, (0, 0, 255), -1)

def classify_thumb(lm):
    thumb_tip = lm[4]
    thumb_mcp = lm[2]
    dx = thumb_tip.x - thumb_mcp.x
    dy = thumb_tip.y - thumb_mcp.y
    if abs(dx) > abs(dy):
        return "THUMB RIGHT" if dx > 0 else "THUMB LEFT"
    else:
        return "THUMB UP" if dy < 0 else "THUMB DOWN"
    
# Setup detector
options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

#Global Chromatic Scale Array
chromatic_scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
BASE_MIDI_NOTE = 60
# Coordinate event in HandLandmarks triggers activation of chromatic_scale function that then converts to midi cc note data 
# Chromatic Scale function should have

def gui():


def handle_gesture(landmarks):
    """
    landmarks: one hand's 21 landmarks from MediaPipe
    Assumes this is the RIGHT hand for now.

    Behavior:
    - Thumb out => selection mode
    - Thumb direction + hand motion => choose note
    - Index/middle/pinky => choose chord quality
    - Thumb back in => lock current chord
    - Fist in center => stop sound
    """
    global gesture_state

    # 1) Stop gesture: fist in center
    if is_fist(landmarks) and in_center_zone(landmarks):
        gesture_to_note("stop", "stop")
        gesture_state["locked"] = False
        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["current_note"] = None
        gesture_state["last_played"] = None
        return {
            "action": "stop",
            "note": None,
            "quality": None,
            "locked": False
        }

    thumb_out = thumb_is_out(landmarks)
    quality = classify_chord_quality(landmarks)
    current_center = hand_center(landmarks)

    # 2) Thumb folded back in => lock chord
    if not thumb_out:
        if gesture_state["current_note"] is not None:
            gesture_state["locked"] = True

        gesture_state["selection_anchor"] = None
        gesture_state["selection_thumb_dir"] = None
        gesture_state["current_quality"] = quality

        return {
            "action": "locked" if gesture_state["current_note"] else "idle",
            "note": gesture_state["current_note"],
            "quality": gesture_state["current_quality"],
            "locked": gesture_state["locked"]
        }

    # 3) Thumb out => enter/update selection mode
    thumb_dir = classify_thumb(landmarks)

    # If chord was locked and thumb comes back out, unlock for reselection
    if gesture_state["locked"]:
        gesture_state["locked"] = False

    # Reset anchor if:
    # - first entering selection mode
    # - thumb direction changed
    if (gesture_state["selection_anchor"] is None or
        gesture_state["selection_thumb_dir"] != thumb_dir):
        gesture_state["selection_anchor"] = current_center
        gesture_state["selection_thumb_dir"] = thumb_dir

    move_dir = movement_bucket(gesture_state["selection_anchor"], current_center)

    # Only update note once a valid left/up/right movement has been made
    if move_dir is not None:
        note = NOTE_GRID[thumb_dir][move_dir]
        gesture_state["current_note"] = note
        gesture_state["current_quality"] = quality

        chord_tuple = (note, quality)

        # Only trigger playback when chord actually changes
        if gesture_state["last_played"] != chord_tuple:
            gesture_to_note(note, quality)
            gesture_state["last_played"] = chord_tuple

        return {
            "action": "selecting",
            "note": note,
            "quality": quality,
            "locked": False,
            "thumb_dir": thumb_dir,
            "move_dir": move_dir
        }

    # Thumb is out, but movement not large enough yet
    return {
        "action": "arming_selection",
        "note": gesture_state["current_note"],
        "quality": quality,
        "locked": False,
        "thumb_dir": thumb_dir,
        "move_dir": None
    }


def gesture_to_note(note, quality):


def note_to_midi(note: str) -> int:
    # Convert note from chromatic_scale global array to midi note number
    if note not in chromatic_scale:
        raise ValueError(f"Note {note} is not in the chromatic scale.")
    midi_note_number = chromatic_scale.index(note) + BASE_MIDI_NOTE
    return midi_note_number

def parameter_to_midi(note: str, param: float) -> tuple[int, int]:
    # Convert note and parameter to midi cc data
    midi_note_number = note_to_midi(note)
    param_clamped = max(0.0, min(1.0, param)) 
    midi_cc_value = int(param_clamped * 127)
    return midi_note_number, midi_cc_value


def main():
