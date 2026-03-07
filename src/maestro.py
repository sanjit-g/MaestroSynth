import cv2
import mediapipe
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os

from midi_helpers import init_midi, close_midi
from gesture_helpers import draw_landmarks, draw_hud, handle_gesture


MODEL_PATH = "hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading hand landmarker model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL_PATH
    )
    print("Done.")



def main():
    midi_port_name = init_midi()

    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    print("Camera open. Press Q to quit.\n")
    gesture_result = {"action": "idle", "note": None, "quality": None, "locked": False}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=rgb)
        result   = detector.detect(mp_image)

        if result.hand_landmarks:
            landmarks      = result.hand_landmarks[0]
            draw_landmarks(frame, landmarks)
            gesture_result = handle_gesture(landmarks)
        else:
            gesture_result = {"action": "idle", "note": None, "quality": None, "locked": False}

        draw_hud(frame, gesture_result, midi_port_name)
        cv2.imshow("MaestroSynth", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    close_midi()


if __name__ == "__main__":
    main()
