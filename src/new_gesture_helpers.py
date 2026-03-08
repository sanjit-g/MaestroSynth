import math

CIRCLE_OF_FIFTHS = [
    "C", "G", "D", "A", "E", "B",
    "Gb", "Db", "Ab", "Eb", "Bb", "F"
]

CHORD_QUALITY_MAP = {
    (False, False, False): "major",
    (True,  False, False): "minor",
    (True,  True,  False): "maj7",
    (True,  True,  True):  "min7",
    (True,  False, True):  "7",
}

gesture_state = {
    "current_note": None,
    "current_quality": "major",
    "last_played": None,
    "debug_text": "",
    "locked_note": None,
    "locked_quality": "major",
    "is_locked": False,
}

def dist3(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

def hand_center(lm):
    palm_ids = [0, 5, 9, 13, 17]
    cx = sum(lm[i].x for i in palm_ids) / len(palm_ids)
    cy = sum(lm[i].y for i in palm_ids) / len(palm_ids)
    return (cx, cy)

def finger_extended(lm, tip_id, pip_id, wrist_id=0, margin=0.015):
    tip_dist = dist3(lm[tip_id], lm[wrist_id])
    pip_dist = dist3(lm[pip_id], lm[wrist_id])
    return tip_dist > pip_dist + margin

def classify_chord_quality(lm):
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    pinky_on = finger_extended(lm, 20, 18)

    combo = (index_on, middle_on, pinky_on)
    return CHORD_QUALITY_MAP.get(combo, "major")

def thumb_is_out(lm, margin=0.02):
    wrist = lm[0]
    thumb_tip = lm[4]
    thumb_ip = lm[3]
    thumb_mcp = lm[2]

    tip_dist = dist3(thumb_tip, wrist)
    ip_dist = dist3(thumb_ip, wrist)
    mcp_dist = dist3(thumb_mcp, wrist)

    return tip_dist > ip_dist + margin and tip_dist > mcp_dist + margin

def is_fist(lm):
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    thumb_out = thumb_is_out(lm)

    return (not index_on and not middle_on and not ring_on and not pinky_on and not thumb_out)


def gesture_to_note_by_angle(hand_xy, center_xy=(0.5, 0.5), deadzone=0.08):
    """
    Convert hand position around a center point into a circle-of-fifths note.

    hand_xy: palm center in normalized coords
    center_xy: center of radial selector
    deadzone: ignore/select nothing if too close to center
    """
    hx, hy = hand_xy
    cx, cy = center_xy

    dx = -(hx - cx)
    dy = hy - cy

    radius = math.sqrt(dx*dx + dy*dy)
    if radius < deadzone:
        return None, radius, None

    # atan2 with flipped y so screen-up becomes positive angle
    angle = math.atan2(-(dy), dx)   # right=0, up=pi/2, left=pi, down=-pi/2
    angle_deg = (math.degrees(angle) + 360) % 360

    # We want 12 equal sectors = 30 degrees each
    # Shift by 15 degrees so boundaries are centered nicely
    sector = int(((angle_deg + 15) % 360) // 30)

    # sector 0 = right, sector 3 = up, etc.
    # To make TOP = C, rotate sector index so 90 degrees maps to C.
    # angle_deg=90 -> sector=3, so subtract 3
    note_index = (sector - 3) % 12

    note = CIRCLE_OF_FIFTHS[note_index]
    return note, radius, angle_deg

def play_chord(root_note, chord_quality):
    print(f"PLAY -> {root_note} {chord_quality}")

def stop_chord():
    print("STOP")

def handle_gesture(landmarks, selector_center=(0.5, 0.5)):
    global gesture_state

    palm_xy = hand_center(landmarks)
    quality = classify_chord_quality(landmarks)

    note, radius, angle_deg = gesture_to_note_by_angle(
        palm_xy,
        center_xy=selector_center,
        deadzone=0.08
    )

    # stop gesture: fist near center — also clears lock
    if note is None and is_fist(landmarks):
        stop_chord()
        gesture_state["current_note"] = None
        gesture_state["current_quality"] = "major"
        gesture_state["last_played"] = None
        gesture_state["locked_note"] = None
        gesture_state["is_locked"] = False
        gesture_state["debug_text"] = "STOP"
        return {
            "action": "stop",
            "note": None,
            "quality": None,
            "locked": False,
            "angle_deg": angle_deg,
            "radius": radius,
        }

    # Thumbs down = UNLOCK (release the held chord)
    if gesture_state["is_locked"] and is_thumbs_down(landmarks):
        gesture_state["is_locked"] = False
        gesture_state["locked_note"] = None
        gesture_state["locked_quality"] = "major"
        gesture_state["debug_text"] = "UNLOCKED"
        return {
            "action": "unlocked",
            "note": gesture_state["current_note"],
            "quality": quality,
            "locked": False,
            "angle_deg": angle_deg,
            "radius": radius,
        }

    # While locked, keep holding the locked chord (ignore new hand position)
    if gesture_state["is_locked"]:
        ln = gesture_state["locked_note"]
        lq = gesture_state["locked_quality"]
        gesture_state["debug_text"] = f"LOCKED {ln} {lq}"
        return {
            "action": "holding_locked",
            "note": ln,
            "quality": lq,
            "locked": True,
            "angle_deg": angle_deg,
            "radius": radius,
        }

    # Thumbs up = LOCK (hold current note/chord)
    if is_thumbs_up(landmarks) and gesture_state["current_note"] is not None:
        gesture_state["is_locked"] = True
        gesture_state["locked_note"] = gesture_state["current_note"]
        gesture_state["locked_quality"] = gesture_state["current_quality"]
        gesture_state["debug_text"] = f"LOCKED {gesture_state['locked_note']} {gesture_state['locked_quality']}"
        return {
            "action": "locked",
            "note": gesture_state["locked_note"],
            "quality": gesture_state["locked_quality"],
            "locked": True,
            "angle_deg": angle_deg,
            "radius": radius,
        }

    # inside center, but not stopping
    if note is None:
        gesture_state["debug_text"] = "CENTER / DEADZONE"
        return {
            "action": "idle_center",
            "note": gesture_state["current_note"],
            "quality": quality,
            "locked": False,
            "angle_deg": angle_deg,
            "radius": radius,
        }

    gesture_state["current_note"] = note
    gesture_state["current_quality"] = quality

    chord_tuple = (note, quality)
    if gesture_state["last_played"] != chord_tuple:
        play_chord(note, quality)
        gesture_state["last_played"] = chord_tuple

    gesture_state["debug_text"] = f"{note} {quality} angle={angle_deg:.1f}"

    return {
        "action": "selecting",
        "note": note,
        "quality": quality,
        "locked": False,
        "angle_deg": angle_deg,
        "radius": radius,
    }
def is_thumbs_up(lm):
    """Detect thumbs up gesture: thumb extended, all other fingers curled"""
    thumb_out = thumb_is_out(lm)
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    
    return thumb_out and not index_on and not middle_on and not ring_on and not pinky_on

def is_thumbs_down(lm, y_margin=0.015):
    """
    Detect thumbs down: thumb pointing downward, all other fingers curled.
    Does NOT require thumb_is_out so a curled thumbs-down still unlocks.
    Uses both tip-below-MCP and tip-below-wrist so it fires in more orientations.
    """
    thumb_tip = lm[4]
    thumb_mcp = lm[2]
    wrist = lm[0]
    # Image Y increases downward. Thumb down = tip below base and/or below wrist.
    tip_below_mcp = thumb_tip.y > thumb_mcp.y + y_margin
    tip_below_wrist = thumb_tip.y > wrist.y + y_margin
    thumb_pointing_down = tip_below_mcp or tip_below_wrist

    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    fingers_curled = not index_on and not middle_on and not ring_on and not pinky_on

    return thumb_pointing_down and fingers_curled