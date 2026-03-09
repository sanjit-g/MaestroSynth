# MaestroSynth
Project for BU Hackathon 2026. Uses hand gestures to control an Omnichord-style MIDI Controller. (Winner of Best Overall Hack Award)

MaestroSynth allows users to play and modulate different chords by moving their hand and fingers in front of the camera. The script tracks hand placement relative to the camera, highlighting the current selected chord as well as the residing quarant in the circle of fifths, sending MIDI signals to a DAW.

FEATURES

Circle of Fifths GUI - A diagram of the circle of fifths is overlayed on the right side of the camera feed, showing all 12 notes divided into four quadrants. Moving either hand relative to the camera will cycle through the different chords, allowing for easy chord progressions.

Hand Tracking - Powered through MediaPipe, allows for detection of hand landmakrs with a high level of certainty.

Chord Quality Selection - Using different combinations of the pointer, middle, ring, and pinky fingers while highlighting a chord on the circle of fifths, users can change between major, minor, maj7, min7, and dominant 7th chords

Lock Mode - Users can lock a selected chord in so it will continue playing without changing using two simple gestures: thumbs up to lock the chord in and thumbs down to unlock.

MIDI Output - Functions like a standard MIDI controller, sends MIDI on/off signals to any compatible hardware/software (DAWs, other MIDI controllers, etc)

Live Visual Feedback - GUI updates with accurate tracking of where the hand is on the circle of fifths, providing real time updates for selected chords

REQUIREMENTS

-Python 3.8 - 3.12 (3.12 is recommended)
-Webcam
-MIDI destination (virtual or physical MIDI port, DAW, hardware synth)
-Dependencies:
 Install: pip install -r requirements.txt
 Optional (for MIDI on Windows): pip install python-rtmidi  (needs C++ build tools)

opencv-python>=4.8.0
mediapipe>=0.10.0
mido>=1.3.0
Pillow>=9.0.0

USAGE

| Gesture                          | Action                                   |
|----------------------------------|------------------------------------------|
| **Move hand**                    | Select a note (hand position maps to the wheel) |
| **Pointer Finger Up**       | Minor   |
| **Thumb Up**                    | Lock current chord (stays on even if hand leaves) |
| **Thumbs‑down**                  | Unlock chord                             |
| **Fist (anywhere)**              | Stop all sound, clear lock, reset        |
| **Pointer Finger + Pinky**               | Dominant 7th      |
| **Pointer + Middle + Pinky**               | Minor 7th      |
| **Middle + Pinky**               | Major     |
| **Pointer  + Middle**               | Major 7th      |

CONFIGURATION

MIDI Port - First available output is used. To change, modify init_midi() in midi_helpers.py.

Deadzone Size - Adjust deadzone=0.08 in gesture_to_note_by_angle to make the centre area larger/smaller.

Cooldown/Stability - candidate_frames sets the number of frames needed to confirm a note change (currently = 3)


