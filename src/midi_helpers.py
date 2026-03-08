import mido

chromatic_scale = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

BASE_MIDI_NOTE = 60
MAX_PARAM_INDEX = 7

midi_out = None

active_note = None
active_quality = None
active_chord_notes = []

QUALITY_INDEX = {
    "major": 0,
    "minor": 1,
    "maj7":  2,
    "min7":  3,
    "7":     4,
}

CHORD_INTERVALS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "maj7":  [0, 4, 7, 11],
    "min7":  [0, 3, 7, 10],
    "7":     [0, 4, 7, 10],
}


def init_midi(target_name: str = "Maestro 1") -> str:
    global midi_out

    try:
        ports = mido.get_output_names()
    except Exception as e:
        print(f"\nMIDI backend unavailable — running without MIDI: {e}\n")
        return "No MIDI device"

    print("\nAvailable MIDI output ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p}")

    for port in ports:
        if target_name.lower() in port.lower():
            midi_out = mido.open_output(port)
            print(f"\nConnected to: {port}\n")
            return port

    print(f"\nCould not find MIDI port containing '{target_name}'\n")
    return "No MIDI device"


def close_midi():
    global midi_out
    stop_current_chord()
    if midi_out:
        midi_out.close()
        midi_out = None


def note_to_midi(note: str) -> int:
    if note not in chromatic_scale:
        raise ValueError(f"Note '{note}' not found in chromatic_scale: {chromatic_scale}")
    return chromatic_scale.index(note) + BASE_MIDI_NOTE


def parameter_to_midi(note: str, param_index: int) -> tuple[int, int]:
    cc_number = note_to_midi(note)
    param_clamped = max(0, min(MAX_PARAM_INDEX, param_index))
    cc_value = int((param_clamped / MAX_PARAM_INDEX) * 127)
    return cc_number, cc_value


def send_cc(cc_number: int, cc_value: int, channel: int = 0):
    if midi_out is None:
        return
    midi_out.send(mido.Message('control_change', channel=channel, control=cc_number, value=cc_value))


def send_note_on(midi_note: int, velocity: int = 100, channel: int = 0):
    if midi_out is None:
        return
    midi_out.send(mido.Message('note_on', channel=channel, note=midi_note, velocity=velocity))


def send_note_off(midi_note: int, channel: int = 0):
    if midi_out is None:
        return
    midi_out.send(mido.Message('note_off', channel=channel, note=midi_note, velocity=0))


def send_all_notes_off(channel: int = 0):
    if midi_out is None:
        return
    midi_out.send(mido.Message('control_change', channel=channel, control=123, value=0))


def stop_current_note():
    global active_note, active_quality

    if active_note is not None:
        try:
            midi_note = note_to_midi(active_note)
            send_note_off(midi_note)
        except ValueError:
            pass

    send_all_notes_off()
    active_note = None
    active_quality = None


def play_note_state(note: str, quality: str):
    """
    Only send MIDI when the musical state actually changes.
    """
    global active_note, active_quality

    if note == "stop":
        stop_current_note()
        return

    if active_note == note and active_quality == quality:
        return

    stop_current_note()

    midi_note = note_to_midi(note)
    q_index = QUALITY_INDEX.get(quality, 0)
    cc_num, cc_val = parameter_to_midi(note, q_index)

    send_note_on(midi_note)
    send_cc(cc_num, cc_val)

    active_note = note
    active_quality = quality

    print(f"[MIDI] Note: {note} ({midi_note}) | CC {cc_num} = {cc_val} | Quality: {quality}")

def build_chord_notes(note: str, quality: str) -> list[int]:
    root = note_to_midi(note)
    intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS["major"])
    return [root + interval for interval in intervals]


def stop_current_chord(channel: int = 0):
    global active_note, active_quality, active_chord_notes

    for midi_note in active_chord_notes:
        send_note_off(midi_note, channel=channel)

    send_all_notes_off(channel=channel)

    active_note = None
    active_quality = None
    active_chord_notes = []


def play_chord_state(note: str, quality: str, velocity: int = 100, channel: int = 0):
    """
    Only send MIDI when the chord state changes.
    Sends full chord notes, not just the root.
    """
    global active_note, active_quality, active_chord_notes

    if note == "stop":
        stop_current_chord(channel=channel)
        return

    if active_note == note and active_quality == quality:
        return

    stop_current_chord(channel=channel)

    chord_notes = build_chord_notes(note, quality)
    q_index = QUALITY_INDEX.get(quality, 0)
    cc_num, cc_val = parameter_to_midi(note, q_index)

    for midi_note in chord_notes:
        send_note_on(midi_note, velocity=velocity, channel=channel)

    send_cc(cc_num, cc_val, channel=channel)

    active_note = note
    active_quality = quality
    active_chord_notes = chord_notes

    print(f"[MIDI] Chord: {note} {quality} -> {chord_notes} | CC {cc_num} = {cc_val}")