import time
from midi_helpers import init_midi, send_note_on, send_note_off, close_midi

# connect to MIDI
port = init_midi()

print("Connected to:", port)

# play middle C
send_note_on(60)
print("Playing C4")

time.sleep(2)

send_note_off(60)
print("Stopped")

close_midi()