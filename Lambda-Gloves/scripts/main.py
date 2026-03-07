import cv2
import mediapipe as mp
import time
import mido
from mido import Message

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=4,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Open the camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Failed to open camera")
    exit()

# Optional: Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("✅ Camera opened successfully")

# Open a virtual MIDI port  
try:
    midi_out = mido.open_output('HandControl 2')  # Replace with your virtual MIDI port name
    print("✅ MIDI port opened successfully")
except Exception as e:
    print(f"❌ Failed to open MIDI port: {e}")
    exit()

# Normalize function to map x, y to MIDI range (0-127) with clamping
def normalize(value, min_val, max_val):
    normalized = int((value - min_val) / (max_val - min_val) * 127)
    return max(0, min(127, normalized))  # Clamp the value to the range 0–127

# Map finger landmarks to MIDI CC numbers
finger_midi_mapping = {
    mp_hands.HandLandmark.THUMB_TIP: (1, 2),  # CC1 (X), CC2 (Y)
    mp_hands.HandLandmark.INDEX_FINGER_TIP: (3, 4),  # CC3 (X), CC4 (Y)
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP: (5, 6),  # CC5 (X), CC6 (Y)
    mp_hands.HandLandmark.RING_FINGER_TIP: (7, 8),  # CC7 (X), CC8 (Y)
    mp_hands.HandLandmark.PINKY_TIP: (9, 10),  # CC9 (X), CC10 (Y)
}

# Map finger landmarks to their names
finger_names = {
    mp_hands.HandLandmark.THUMB_TIP: "Thumb",
    mp_hands.HandLandmark.INDEX_FINGER_TIP: "Index Finger",
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP: "Middle Finger",
    mp_hands.HandLandmark.RING_FINGER_TIP: "Ring Finger",
    mp_hands.HandLandmark.PINKY_TIP: "Pinky",
}

# Force Normal Mode
current_mode = 0  # Always operate in Normal Mode

# FPS tracking
prev_time = 0

while True:
    success, frame = cap.read()
    if not success:
        print("❌ Failed to read frame.")
        break

    # Flip for mirror effect (optional)
    frame = cv2.flip(frame, 1)
    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Display the current mode on the frame
            mode_text = "Mode: Normal"  # Always display Normal Mode
            cv2.putText(frame, mode_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Normal Mode: All fingers control parameters
            for finger, (cc_x, cc_y) in finger_midi_mapping.items():
                finger_tip = hand_landmarks.landmark[finger]
                corrected_x = 1 - finger_tip.x  # Invert x after flipping the frame
                corrected_y = 1 - finger_tip.y  # Invert y to fix mirroring
                midi_x = normalize(corrected_x, 0, 1)
                midi_y = normalize(corrected_y, 0, 1)
                try:
                    midi_out.send(Message('control_change', channel=0, control=cc_x, value=midi_x))
                    midi_out.send(Message('control_change', channel=0, control=cc_y, value=midi_y))
                except Exception as e:
                    print(f"❌ Failed to send MIDI message: {e}")

    # FPS display (optional)
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time else 0
    prev_time = curr_time
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Show the result
    cv2.imshow("Camster - Hand Tracking", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

