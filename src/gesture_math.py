import math

def dist3(a, b):
    """3D distance between two landmarks"""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

def hand_center(lm):
    """Palm center from 5 key points"""
    palm_ids = [0, 5, 9, 13, 17]
    cx = sum(lm[i].x for i in palm_ids) / len(palm_ids)
    cy = sum(lm[i].y for i in palm_ids) / len(palm_ids)
    return (cx, cy)

def finger_extended(lm, tip_id, pip_id, wrist_id=0, margin=0.015):
    """Check if finger is extended"""
    tip_dist = dist3(lm[tip_id], lm[wrist_id])
    pip_dist = dist3(lm[pip_id], lm[wrist_id])
    return tip_dist > pip_dist + margin

def thumb_is_out(lm, margin=0.02):
    """Check if thumb is extended"""
    wrist = lm[0]
    thumb_tip = lm[4]
    thumb_ip = lm[3]
    thumb_mcp = lm[2]
    tip_dist = dist3(thumb_tip, wrist)
    ip_dist = dist3(thumb_ip, wrist)
    mcp_dist = dist3(thumb_mcp, wrist)
    return tip_dist > ip_dist + margin and tip_dist > mcp_dist + margin

def is_fist(lm):
    """All fingers curled"""
    index_on = finger_extended(lm, 8, 6)
    middle_on = finger_extended(lm, 12, 10)
    ring_on = finger_extended(lm, 16, 14)
    pinky_on = finger_extended(lm, 20, 18)
    thumb_out = thumb_is_out(lm)
    return not index_on and not middle_on and not ring_on and not pinky_on and not thumb_out
    