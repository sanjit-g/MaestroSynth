import tkinter as tk
from tkinter import messagebox
import mido
import subprocess

def list_midi_ports():
    """List available MIDI output ports."""
    ports = mido.get_output_names()
    if ports:
        messagebox.showinfo("MIDI Ports", "\n".join(ports))
    else:
        messagebox.showwarning("MIDI Ports", "No MIDI output ports found!")

def start_hand_tracking():
    """Start the hand tracking script."""
    try:
        subprocess.Popen(["python", "main.py"])  # Replace with the path to your main script
        messagebox.showinfo("Hand Tracking", "Hand tracking started!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start hand tracking: {e}")

def stop_hand_tracking():
    """Stop the hand tracking script."""
    # This is a placeholder. You can implement a more robust way to stop the script.
    messagebox.showinfo("Hand Tracking", "Stopping hand tracking is not implemented yet.")

# Create the main window
root = tk.Tk()
root.title("Camster GUI")
root.geometry("300x200")

# Add buttons
btn_list_ports = tk.Button(root, text="List MIDI Ports", command=list_midi_ports)
btn_list_ports.pack(pady=10)

btn_start_tracking = tk.Button(root, text="Start Hand Tracking", command=start_hand_tracking)
btn_start_tracking.pack(pady=10)

btn_stop_tracking = tk.Button(root, text="Stop Hand Tracking", command=stop_hand_tracking)
btn_stop_tracking.pack(pady=10)

# Run the GUI event loop
root.mainloop()