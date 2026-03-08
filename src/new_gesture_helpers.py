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
    "candidate_note": None,
    "candidate_quality": "major",
    "candidate_frames": 0,
    "current_note":    None,
    "current_quality": "major",
    "last_played":     None,
    "debug_text":      "",
    "locked_note":     None,
    "locked_quality":  "major",
    "is_locked":       False,
    # Debounce flags — track previous frame state so we only
    # trigger on the RISING EDGE of each gesture, not every frame.
    "_prev_thumbs_up":   False,
    "_prev_thumbs_down": False,
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
    index_on  = finger_extended(lm, 8,  6)
    middle_on = finger_extended(lm, 12, 10)
    pinky_on  = finger_extended(lm, 20, 18)
    combo = (index_on, middle_on, pinky_on)
    return CHORD_QUALITY_MAP.get(combo, "major")


def thumb_is_out(lm, margin=0.02):
    wrist     = lm[0]
    thumb_tip = lm[4]
    thumb_ip  = lm[3]
    thumb_mcp = lm[2]
    tip_dist  = dist3(thumb_tip, wrist)
    ip_dist   = dist3(thumb_ip,  wrist)
    mcp_dist  = dist3(thumb_mcp, wrist)
    return tip_dist > ip_dist + margin and tip_dist > mcp_dist + margin


def is_fist(lm):
    index_on  = finger_extended(lm, 8,  6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on   = finger_extended(lm, 16, 14)
    pinky_on  = finger_extended(lm, 20, 18)
    thumb_out = thumb_is_out(lm)
    return not index_on and not middle_on and not ring_on and not pinky_on and not thumb_out


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
    print("STOP")


def handle_gesture(landmarks, selector_center=(0.5, 0.5)):
    global gesture_state

    palm_xy = hand_center(landmarks)
    quality = classify_chord_quality(landmarks)
    note, radius, angle_deg = gesture_to_note_by_angle(
        palm_xy, center_xy=selector_center, deadzone=0.08)

    # ── Detect gesture edges (rising edge only, not held state) ──────────────
    thumbs_up_now   = is_thumbs_up(landmarks)
    thumbs_down_now = is_thumbs_down(landmarks)

    # Rising edge: gesture just became true this frame
    thumbs_up_triggered   = thumbs_up_now   and not gesture_state["_prev_thumbs_up"]
    thumbs_down_triggered = thumbs_down_now and not gesture_state["_prev_thumbs_down"]

    # Always update previous state before any early returns
    gesture_state["_prev_thumbs_up"]   = thumbs_up_now
    gesture_state["_prev_thumbs_down"] = thumbs_down_now

    # ── Stop: fist near centre ────────────────────────────────────────────────
    if note is None and is_fist(landmarks):
        stop_chord()
        gesture_state.update({
            "current_note":    None,
            "current_quality": "major",
            "last_played":     None,
            "locked_note":     None,
            "is_locked":       False,
            "debug_text":      "STOP",
        })
        return {
            "action": "stop", "note": None, "quality": None,
            "locked": False, "angle_deg": angle_deg, "radius": radius,
        }

    # ── Unlock: thumbs down RISING EDGE only ──────────────────────────────────
    if gesture_state["is_locked"] and thumbs_down_triggered:
        gesture_state["is_locked"]     = False
        gesture_state["locked_note"]   = None
        gesture_state["locked_quality"] = "major"
        gesture_state["debug_text"]    = "UNLOCKED"
        return {
            "action": "unlocked", "note": gesture_state["current_note"],
            "quality": quality, "locked": False,
            "angle_deg": angle_deg, "radius": radius,
        }

    # ── Hold locked chord (ignore new position while locked) ─────────────────
    if gesture_state["is_locked"]:
        ln, lq = gesture_state["locked_note"], gesture_state["locked_quality"]
        gesture_state["debug_text"] = f"LOCKED {ln} {lq}"
        return {
            "action": "holding_locked", "note": ln, "quality": lq,
            "locked": True, "angle_deg": angle_deg, "radius": radius,
        }

    # ── Lock: thumbs up RISING EDGE only ─────────────────────────────────────
    if thumbs_up_triggered and gesture_state["current_note"] is not None:
        gesture_state["is_locked"]     = True
        gesture_state["locked_note"]   = gesture_state["current_note"]
        gesture_state["locked_quality"] = gesture_state["current_quality"]
        gesture_state["debug_text"]    = f"LOCKED {gesture_state['locked_note']} {gesture_state['locked_quality']}"
        return {
            "action": "locked",
            "note":    gesture_state["locked_note"],
            "quality": gesture_state["locked_quality"],
            "locked":  True, "angle_deg": angle_deg, "radius": radius,
        }

    # ── Deadzone / centre ─────────────────────────────────────────────────────
    if note is None:
        gesture_state["debug_text"] = "CENTER / DEADZONE"
        return {
            "action": "idle_center", "note": gesture_state["current_note"],
            "quality": quality, "locked": False,
            "angle_deg": angle_deg, "radius": radius,
        }

    # ── Normal note selection ─────────────────────────────────────────────────
    candidate = (note, quality)
    current_candidate = (gesture_state["candidate_note"], gesture_state["candidate_quality"])

    if candidate == current_candidate:
        gesture_state["candidate_frames"] += 1
    else:
        gesture_state["candidate_note"] = note
        gesture_state["candidate_quality"] = quality
        gesture_state["candidate_frames"] = 1

    # require a few consecutive frames before committing
    if gesture_state["candidate_frames"] >= 3:
        gesture_state["current_note"] = note
        gesture_state["current_quality"] = quality
    gesture_state["debug_text"] = f"{note} {quality} angle={angle_deg:.1f}"
    return {
        "action": "selecting", "note": note, "quality": quality,
        "locked": False, "angle_deg": angle_deg, "radius": radius,
    }
