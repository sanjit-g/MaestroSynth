import mido

# ─── Global State ─────────────────────────────────────────────────────────────

chromatic_scale = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


BASE_MIDI_NOTE  = 60
MAX_PARAM_INDEX = 7

midi_out = None  # Set by init_midi()


def init_midi(target_name: str = "Maestro 1") -> str:
    """
    Connect to the MIDI output port whose name contains target_name.
    """
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

    print(f"\nCould not find MIDI port containing '{target_name}'")
    return "No MIDI device"

def close_midi():
    """Close the MIDI output port cleanly."""
    global midi_out
    if midi_out:
        midi_out.close()
        midi_out = None


# ─── Converters ───────────────────────────────────────────────────────────────

def note_to_midi(note: str) -> int:
    """
    Convert a note name from chromatic_scale to a MIDI note number.

    Index 0 ('C') maps to MIDI 60 (Middle C). Each semitone increments by 1.

    Args:
        note (str): A note name from chromatic_scale e.g. 'C', 'F#', 'B'

    Returns:
        int: MIDI note number [60–71]

    Raises:
        ValueError: If note is not in chromatic_scale.

    Examples:
        >>> note_to_midi('C')   # -> 60
        >>> note_to_midi('A')   # -> 69
        >>> note_to_midi('B')   # -> 71
    """
    if note not in chromatic_scale:
        raise ValueError(f"Note '{note}' not found in chromatic_scale: {chromatic_scale}")
    return chromatic_scale.index(note) + BASE_MIDI_NOTE

def parameter_to_midi(note: str, param_index: int) -> tuple:
    """
    Map a note + gesture parameter index to a (cc_number, cc_value) pair.

    The note determines the CC number (via its MIDI note number).
    The param_index is scaled evenly across [0–127].

    Args:
        note        (str): A note name from chromatic_scale e.g. 'C', 'F#'
        param_index (int): Zero-based gesture parameter index [0, MAX_PARAM_INDEX].
                           Clamped silently for real-time safety.

    Returns:
        tuple[int, int]: (cc_number, cc_value)

    Examples:
        >>> parameter_to_midi('C', 0)  # -> (60, 0)
        >>> parameter_to_midi('A', 3)  # -> (69, 54)
    """
    cc_number     = note_to_midi(note)
    param_clamped = max(0, min(MAX_PARAM_INDEX, param_index))
    cc_value      = int((param_clamped / MAX_PARAM_INDEX) * 127)
    return cc_number, cc_value


# ─── Senders ──────────────────────────────────────────────────────────────────

def send_cc(cc_number: int, cc_value: int, channel: int = 0):
    """Send a MIDI CC message."""
    if midi_out is None:
        return
    midi_out.send(mido.Message('control_change', channel=channel, control=cc_number, value=cc_value))

def send_note_on(midi_note: int, velocity: int = 100, channel: int = 0):
    """Send a MIDI Note On message."""
    if midi_out is None:
        return
    midi_out.send(mido.Message('note_on', channel=channel, note=midi_note, velocity=velocity))

def send_note_off(midi_note: int, channel: int = 0):
    """Send a MIDI Note Off message."""
    if midi_out is None:
        return
    midi_out.send(mido.Message('note_off', channel=channel, note=midi_note, velocity=0)) 

def send_all_notes_off(channel: int = 0):
    """Send MIDI CC 123 — All Notes Off."""
    if midi_out is None:
        return
    midi_out.send(mido.Message('control_change', channel=channel, control=123, value=0))

# ─── Gesture → MIDI ───────────────────────────────────────────────────────────

QUALITY_INDEX = {
    "major": 0,
    "minor": 1,
    "maj7":  2,
    "min7":  3,
    "7":     4,
}

def gesture_to_note(note: str, quality: str):
    """
    Convert a detected gesture (note + quality) to MIDI output.

    Sends:
      - Note On  for the MIDI note number
      - CC       using note as cc_number, quality index as param

    For 'stop': sends All Notes Off (CC 123).

    Args:
        note    (str): Note name from chromatic_scale, or 'stop'
        quality (str): Chord quality key from QUALITY_INDEX, or 'stop'
    """
    if note == "stop":
        send_all_notes_off()
        return

    try:
        midi_note        = note_to_midi(note)
        q_index          = QUALITY_INDEX.get(quality, 0)
        cc_num, cc_val   = parameter_to_midi(note, q_index)

        send_note_on(midi_note)
        send_cc(cc_num, cc_val)

        print(f"[MIDI] Note: {note} ({midi_note}) | CC {cc_num} = {cc_val} | Quality: {quality}")
    except ValueError as e:
        print(f"[MIDI Error] {e}")
