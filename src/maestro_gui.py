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
from midi_helpers import init_midi, close_midi, play_chord_state
<<<<<<< HEAD
from new_gesture_helpers import handle_gesture, draw_landmarks, draw_hud
=======
from gesture_helpers import draw_landmarks, draw_hud
from new_gesture_helpers import handle_gesture, gesture_state
>>>>>>> 9300a4da3ffded98a87ff9b2bd5ec4e4696344ab
from gui import CircleOfFifthsRing


MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

def _ensure_model():
    """Download the hand landmarker model if missing."""
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
    root.geometry("960x540")
    root.minsize(400, 300)
    root.resizable(True, True)

    app = CircleOfFifthsRing(root, camera_overlay=True)

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
        root.destroy()
        return

    print("Camera open. Press Q or close the window to quit.\n")
    running = [True]

    def process_frame():
        if not running[0]:
            return

        ret, frame = cap.read()
        if not ret:
            root.after(10, process_frame)
            return

        # Flip once — all downstream coords are in correct physical space
        frame = cv2.flip(frame, 1)
        frame_h, frame_w = frame.shape[:2]

        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=rgb)
        result   = detector.detect(mp_image)

        if result.hand_landmarks:
            landmarks      = result.hand_landmarks[0]
            draw_landmarks(frame, landmarks)
            gesture_result = handle_gesture(landmarks)

            # Drive zone overlay with wrist position
            wrist  = landmarks[0]
            hand_x = wrist.x * frame_w
            hand_y = wrist.y * frame_h
            app.update_hand_position(hand_x, hand_y, frame_w, frame_h)

        else:
            # No hand detected – if locked, keep showing the locked chord on the GUI
            if gesture_state["is_locked"] and gesture_state["locked_note"]:
                app.update_from_note(gesture_state["locked_note"])
                app.update_lock_state(True)
                gesture_result = {
                    "action": "holding_locked",
                    "note":   gesture_state["locked_note"],
                    "quality": gesture_state["locked_quality"],
                    "locked": True,
                    "angle_deg": None,
                    "radius": None,
                }
            else:
                app.clear_selection()
                gesture_result = {"action": "idle", "note": None, "quality": None, "locked": False}
        # ── Handle all action states ──────────────────────────────────────────
        action  = gesture_result.get("action")
        note    = gesture_result.get("note")
        quality = gesture_result.get("quality") or "major"
        locked  = gesture_result.get("locked", False)

        if action == "stop":
            play_chord_state("stop", "stop")
            app.update_from_note(None)
            app.update_lock_state(False)

        elif action in ("locked", "holding_locked"):
            play_chord_state(note, quality)
            app.update_from_note(note)
            app.update_lock_state(True)

        elif action == "unlocked":
            play_chord_state("stop", "stop")
            app.update_from_note(note)
            app.update_lock_state(False)

        elif action == "selecting":
            play_chord_state(note, quality)
            app.update_from_note(note)
            app.update_lock_state(False)

        elif action == "idle_center":
            # Hand near centre deadzone — don't change anything
            pass

        draw_hud(frame, gesture_result, midi_port_name)
        app.update_background(frame)
        root.after(1, process_frame)

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
