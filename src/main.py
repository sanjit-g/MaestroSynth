import cv2
import mediapipe
import mido

#Global Chromatic Scale Array
chromatic_scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
BASE_MIDI_NOTE = 60
# Coordinate event in HandLandmarks triggers activation of chromatic_scale function that then converts to midi cc note data 
# Chromatic Scale function should have

def gui():


def handle_gesture():


def gesture_to_note():


def note_to_midi(note: str) -> int:
    # Convert note from chromatic_scale global array to midi note number
    if note not in chromatic_scale:
        raise ValueError(f"Note {note} is not in the chromatic scale.")
    midi_note_number = chromatic_scale.index(note) + BASE_MIDI_NOTE
    return midi_note_number

def parameter_to_midi(note: str, param: float) -> tuple[int, int]:
    # Convert note and parameter to midi cc data
    midi_note_number = note_to_midi(note)
    param_clamped = max(0.0, min(1.0, param)) 
    midi_cc_value = int(param_clamped * 127)
    return midi_note_number, midi_cc_value


def main():
