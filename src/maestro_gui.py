"""
Integrated MaestroSynth: Circle of Fifths GUI + camera gesture detection.
Runs the GUI and camera together; detected notes update the GUI in real time.
"""
import cv2
import mediapipe
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import tkinter as tk
import urllib.request
import os

from midi_helpers import init_midi, close_midi
from gesture_helpers import draw_landmarks, draw_hud
from new_gesture_helpers import handle_gesture
from gui import CircleOfFifthsRing

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def _ensure_model():
    """Download the hand landmarker model if missing. Exit with a clear message on failure."""
    if os.path.exists(MODEL_PATH):
        return
    print("Downloading hand landmarker model...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")
    except OSError as e:
        print(f"ERROR: Could not download model: {e}")
        print("Check your network connection and try again, or place hand_landmarker.task in this directory.")
        raise SystemExit(1) from e


_ensure_model()


def main():
    root = tk.Tk()
    root.title("MaestroSynth - Circle of Fifths")
    root.configure(bg='#1e1e1e')

    # Build GUI with camera as background (single window: ring overlaid on camera)
    app = CircleOfFifthsRing(root, camera_overlay=True)

    # MIDI
    midi_port_name = init_midi()

    # Hand detector
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
        root.destroy()
        return

    print("Camera open. Press Q or close the window to quit.\n")
    running = [True]  # use list so inner function can rebind

    def process_frame():
        if not running[0]:
            return
        ret, frame = cap.read()
        if not ret:
            root.after(10, process_frame)
            return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            draw_landmarks(frame, landmarks)
            gesture_result = handle_gesture(landmarks)
        else:
            gesture_result = {"action": "idle", "note": None, "quality": None}

        # Update GUI with detected note
        note = gesture_result.get("note")
        if gesture_result.get("action") == "stop":
            app.update_from_note(None)
        else:
            app.update_from_note(note)

        draw_hud(frame, gesture_result, midi_port_name)
        app.update_background(frame)

        root.after(1, process_frame)

    # Start camera loop (driven by tkinter)
    root.after(100, process_frame)

    def on_closing():
        running[0] = False
        cap.release()
        cv2.destroyAllWindows()
        close_midi()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.bind("<KeyPress-q>", lambda e: on_closing())
    root.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
