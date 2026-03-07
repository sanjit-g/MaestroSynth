import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
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

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    results = detector.detect(mp_image)

    gesture = ""
    if results.hand_landmarks:
        for hand_lms in results.hand_landmarks:
            gesture = classify_thumb(hand_lms)
            draw_landmarks(frame, hand_lms)

    cv2.putText(frame, gesture, (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
    cv2.imshow("Thumb Direction Detector", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
