import math
import cv2
from gesture_math import dist3, hand_center, finger_extended, thumb_is_out, is_fist
from midi_helpers import stop_current_chord

CIRCLE_OF_FIFTHS = [
    "C", "G", "D", "A", "E", "B",
    "Gb", "Db", "Ab", "Eb", "Bb", "F"
]

CHORD_QUALITY_MAP = {
    (True,  True,  True): "major",
    (True,  False, False): "minor",
    (True,  True,  False): "maj7",
    (False,  True,  True):  "min7",
    (True,  False, True):  "7",
}

gesture_state = {
    "current_note":     None,
    "current_quality":  "major",
    "last_played":      None,
    "debug_text":       "",
    "locked_note":      None,
    "locked_quality":   "major",
    "is_locked":        False,
    "candidate_note":    None,
    "candidate_quality": "major",
    "candidate_frames":  0,
    "_prev_thumbs_up":   False,
    "_prev_thumbs_down": False,
}

def classify_chord_quality(lm):
    index_on  = finger_extended(lm, 8,  6)
    middle_on = finger_extended(lm, 12, 10)
    pinky_on  = finger_extended(lm, 20, 18)
    combo = (index_on, middle_on, pinky_on)
    return CHORD_QUALITY_MAP.get(combo, "major")

def is_thumbs_up(lm, y_margin=0.015):
    thumb_out  = thumb_is_out(lm)
    thumb_tip  = lm[4]
    thumb_mcp  = lm[2]
    index_on   = finger_extended(lm, 8,  6)
    middle_on  = finger_extended(lm, 12, 10)
    ring_on    = finger_extended(lm, 16, 14)
    pinky_on   = finger_extended(lm, 20, 18)
    tip_above  = thumb_tip.y < thumb_mcp.y - 2 * y_margin
    return thumb_out and tip_above and not index_on and not middle_on and not ring_on and not pinky_on

def is_thumbs_down(lm, y_margin=0.015):
    thumb_tip  = lm[4]
    thumb_mcp  = lm[2]
    wrist      = lm[0]
    tip_below_mcp   = thumb_tip.y > thumb_mcp.y + y_margin
    tip_below_wrist = thumb_tip.y > wrist.y + y_margin
    thumb_pointing_down = tip_below_mcp or tip_below_wrist
    index_on  = finger_extended(lm, 8,  6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on   = finger_extended(lm, 16, 14)
    pinky_on  = finger_extended(lm, 20, 18)
    fingers_curled = not index_on and not middle_on and not ring_on and not pinky_on
    return thumb_pointing_down and fingers_curled

def gesture_to_note_by_angle(hand_xy, center_xy=(0.5, 0.5), deadzone=0.08):
    hx, hy = hand_xy
    cx, cy = center_xy
    dx = -(hx - cx)
    dy = hy - cy
    radius = math.sqrt(dx*dx + dy*dy)
    if radius < deadzone:
        return None, radius, None
    angle     = math.atan2(-(dy), dx)
    angle_deg = (math.degrees(angle) + 360) % 360
    sector    = int(((angle_deg + 15) % 360) // 30)
    note_index = (sector - 3) % 12
    note = CIRCLE_OF_FIFTHS[note_index]
    return note, radius, angle_deg

def play_chord(root_note, chord_quality):
    print(f"PLAY -> {root_note} {chord_quality}")

def stop_chord():
    #stop_current_chord()
    print("STOP")

def handle_gesture(landmarks, selector_center=(0.5, 0.5)):
    global gesture_state

    palm_xy = hand_center(landmarks)
    quality = classify_chord_quality(landmarks)
    note, radius, angle_deg = gesture_to_note_by_angle(
        palm_xy, center_xy=selector_center, deadzone=0.08)

    # Detect gesture edges
    thumbs_up_now   = is_thumbs_up(landmarks)
    thumbs_down_now = is_thumbs_down(landmarks)
    thumbs_up_triggered   = thumbs_up_now   and not gesture_state["_prev_thumbs_up"]
    thumbs_down_triggered = thumbs_down_now and not gesture_state["_prev_thumbs_down"]

    # Update previous state
    gesture_state["_prev_thumbs_up"]   = thumbs_up_now
    gesture_state["_prev_thumbs_down"] = thumbs_down_now

    # STOP: fist anywhere
    if is_fist(landmarks):
        stop_chord()
        gesture_state.update({
            "current_note":     None,
            "current_quality":  "major",
            "last_played":      None,
            "locked_note":      None,
            "is_locked":        False,
            "candidate_note":   None,
            "candidate_quality": "major",
            "candidate_frames": 0,
            "debug_text":       "STOP",
        })
        return {
            "action": "stop", "note": None, "quality": None,
            "locked": False, "angle_deg": angle_deg, "radius": radius,
        }

    # Unlock: thumbs down
    if gesture_state["is_locked"] and thumbs_down_triggered:
        gesture_state["is_locked"]     = False
        gesture_state["locked_note"]   = None
        gesture_state["locked_quality"] = "major"
        gesture_state["debug_text"]    = "UNLOCKED"
        return {
            "action": "unlocked",
            "note":   gesture_state["current_note"],
            "quality": quality, "locked": False,
            "angle_deg": angle_deg, "radius": radius,
        }

    # Hold locked chord
    if gesture_state["is_locked"]:
        ln, lq = gesture_state["locked_note"], gesture_state["locked_quality"]
        gesture_state["debug_text"] = f"LOCKED {ln} {lq}"
        return {
            "action": "holding_locked", "note": ln, "quality": lq,
            "locked": True, "angle_deg": angle_deg, "radius": radius,
        }

    # Lock: thumbs up
    if thumbs_up_triggered and gesture_state["current_note"] is not None:
        gesture_state["is_locked"]     = True
        gesture_state["locked_note"]   = gesture_state["current_note"]
        gesture_state["locked_quality"] = gesture_state["current_quality"]
        gesture_state["debug_text"]    = f"LOCKED {gesture_state['locked_note']} {gesture_state['locked_quality']}"
        return {
            "action": "locked",
            "note":   gesture_state["locked_note"],
            "quality": gesture_state["locked_quality"],
            "locked": True, "angle_deg": angle_deg, "radius": radius,
        }

    # Deadzone / center
    if note is None:
        gesture_state["debug_text"] = "CENTER / DEADZONE"
        return {
            "action": "idle_center",
            "note":   gesture_state["current_note"],
            "quality": quality, "locked": False,
            "angle_deg": angle_deg, "radius": radius,
        }

    # Candidate stability
    candidate = (note, quality)
    current_candidate = (gesture_state["candidate_note"], gesture_state["candidate_quality"])

    if candidate == current_candidate:
        gesture_state["candidate_frames"] += 1
    else:
        gesture_state["candidate_note"]   = note
        gesture_state["candidate_quality"] = quality
        gesture_state["candidate_frames"]  = 1

    if gesture_state["candidate_frames"] >= 3:
        gesture_state["current_note"]    = note
        gesture_state["current_quality"] = quality

    chord_tuple = (gesture_state["current_note"], gesture_state["current_quality"])
    if (gesture_state["current_note"] is not None and
        gesture_state["last_played"] != chord_tuple):
        play_chord(gesture_state["current_note"], gesture_state["current_quality"])
        gesture_state["last_played"] = chord_tuple

    gesture_state["debug_text"] = f"{note} {quality} angle={angle_deg:.1f}"
    return {
        "action": "selecting",
        "note":   note,
        "quality": quality,
        "locked": False,
        "angle_deg": angle_deg,
        "radius": radius,
    }

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),        # thumb
    (0,5),(5,6),(6,7),(7,8),        # index
    (0,9),(9,10),(10,11),(11,12),   # middle
    (0,13),(13,14),(14,15),(15,16), # ring
    (0,17),(17,18),(18,19),(19,20), # pinky
    (5,9),(9,13),(13,17)            # palm
]

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
