# Lambda Gloves

Lambda Gloves is a computer-vision-based musical glove system that enables expressive, hands-free parameter control in digital audio workstations (DAWs) such as FL Studio and Ableton Live. By tracking finger tips and hand movements via webcam, Lambda Gloves translates gestures into MIDI messages, allowing for fully customizable control—ideal for live performance, studio production, or accessibility.

![Lambda Gloves in Action](docs/demo_screenshot.png)

---

## Features

- 🎹 **Real-time hand and finger tracking** using [MediaPipe](https://google.github.io/mediapipe/solutions/hands.html)
- 🎛️ **MIDI Control**: Map hand and finger positions to any MIDI-controllable parameter in your DAW
- 🖥️ **Cross-platform**: Works on Windows, macOS, and Linux
- 🧑‍🎤 **Customizable**: Easily extendable for new gestures, modes, and mappings
- 🖱️ **User-friendly GUI**: Simple interface for listing MIDI ports and launching hand tracking

---

## Demo

![Lambda Gloves In Action](docs/demo_screenshot.png)

---

## Quick Start

### 1. Clone the Repository

```sh
git clone https://github.com/Losera/Lambda-Gloves.git
cd Lambda-Gloves
```

### 2. Install Dependencies

Lambda Gloves requires Python 3.8 or higher. It's recommended to use a virtual environment. Install the required packages with:

```sh
pip install -r requirements.txt
```

### 3. Connect Your MIDI Device

Plug in your MIDI device and ensure it's recognized by your operating system. You may need to install drivers or configure settings in your DAW.

### 4. Run the Application

To start hand tracking and MIDI control, run:

```sh
python scripts/main.py
```

For the GUI version, run:

```sh
python scripts/gui.py
```

### 5. Configure Your DAW

In your DAW, set up a new MIDI track and select the Lambda Gloves MIDI output as the input for that track. Enable monitoring to hear the effects of your hand gestures.

---

## File Structure

Lambda-Gloves/
│
├── scripts/
│   ├── [main.py](http://_vscodecontentref_/2)        # Main hand tracking and MIDI control script
│   └── [gui.py](http://_vscodecontentref_/3)         # Simple GUI for non-technical users
│
├── tests/
│   └── [test.py](http://_vscodecontentref_/4)        # MIDI port test script
│
├── docs/
│   └── demo_screenshot.png  # Demo images and documentation
│
├── requirements.txt   # Python dependencies
├── [README.md](http://_vscodecontentref_/5)
└── .gitignore

---

## Troubleshooting

- **Hand Tracking Not Working**: Ensure your webcam is connected and not being used by another application. Check the console for error messages.
- **MIDI Device Not Recognized**: Make sure the device is properly connected and powered on. Try restarting the application or your computer.
- **Installation Issues**: Double-check that you're using the correct version of Python and that all dependencies are installed. Consider using a virtual environment to avoid conflicts.

For further assistance, consult the [FAQ](docs/faq.md) or open an issue on the [GitHub repository](https://github.com/Losera/Lambda-Gloves/issues).

---

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for more information on how to get involved.

---

## License

Lambda Gloves is open-source software licensed under the [MIT License](LICENSE). Feel free to use, modify, and distribute it as you wish.

---

**Next Steps for Lmbda Gloves:**
- Add more modes and gesture mappings in [main.py](http://_vscodecontentref_/6).
- Expand the GUI for easier configuration.
- Add more documentation and demo videos/screenshots in the `docs/` folder.
- Consider packaging for easy installation (`setup.py` or `pip install .`).

