# Virtual Mouse — Hand Gesture Recognition

Control your computer's mouse, keyboard shortcuts, and system settings using just your hands and a webcam — no physical mouse required.

Built as an MCA mini project, this application uses real-time hand tracking to translate finger poses and pinch gestures into mouse movement, clicks, scrolling, media/presentation control, and system-level actions like brightness and volume adjustment.


---

## Features

### Mouse Control
| Gesture | Action |
|---|---|
| Index finger up (only) | Move cursor |
| Thumb + Index — quick tap | Left click |
| Thumb + Index — hold & move | Drag |
| Thumb only up (right hand) | Right click |
| Index + Middle up, move vertically | Scroll |
| Index + Pinky up | Double click |

### System & Productivity Gestures
| Gesture | Action |
|---|---|
| 4 fingers up, no thumb | Take a screenshot |
| Open palm (hold) | Start / End PowerPoint slideshow |
| Thumb + Index extended, **right hand** | Next slide |
| Thumb + Index extended, **left hand** | Previous slide |
| Thumb + Index pinch, **left hand** — move vertically | Adjust screen brightness |
| Thumb + Index pinch, **left hand** — move horizontally | Adjust system volume |
| Thumb + Index + Pinky up, **left hand** | Open Chrome |
| Index + Middle + Pinky up, **left hand** | Show Desktop (Win+D) |

All gestures work through a single webcam with real-time visual feedback showing the current recognized gesture, detected hand (left/right), and live FPS.

---

## Tech Stack

- **Language:** Python 3.11
- **Hand Tracking:** [MediaPipe](https://developers.google.com/mediapipe) (legacy Hands solution)
- **Computer Vision:** OpenCV
- **Mouse/Keyboard Simulation:** PyAutoGUI
- **System Volume Control:** pycaw
- **System Brightness Control:** screen-brightness-control
- **GUI:** Tkinter (with Pillow for video frame rendering)
- **Active Window Detection:** pywin32

---

## Project Structure

```
virtual-mouse/
│
├── assets/
│   └── screenshots/          # Auto-saved screenshots from the screenshot gesture
├── src/
│   ├── camera.py              # Webcam capture wrapper
│   ├── hand_detector.py       # MediaPipe hand detection + handedness
│   ├── gesture_detector.py    # Finger-state and pinch-distance logic
│   ├── coordinate_mapper.py   # Camera-to-screen coordinate mapping
│   ├── mouse_controller.py    # Cursor movement with smoothing
│   ├── landmarks_reference.py # Named landmark ID constants
│   └── gui.py                 # Tkinter application (video feed, controls, status)
├── requirements.txt
├── README.md
└── main.py                    # Entry point — launches the GUI
```

---

## Setup & Installation

### Prerequisites
- Windows 10/11
- Python 3.11+ ([download here](https://www.python.org/downloads/)) — make sure **"Add python.exe to PATH"** is checked during install
- A working webcam

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/Rashidtv698/virtual-mouse.git
cd virtual-mouse

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```

Click **Start** in the application window to begin gesture control, and **Stop** or **Exit** to release the camera.

---

## Known Limitations

- **Windows-only** — brightness and volume control (`screen-brightness-control`, `pycaw`) rely on Windows-specific APIs.
- **Single-hand tracking** — only one hand is processed at a time (by design, to keep gesture disambiguation reliable); switching hands mid-use is supported, but both hands cannot be tracked simultaneously.
- **Slide/media gestures require the target app to be focused** — next/previous slide and slideshow toggle gestures only act when PowerPoint is the active window, to avoid sending stray keypresses to other applications.
- **Lighting and camera distance affect accuracy** — gesture recognition performs best in consistent, well-lit conditions with the hand held at a moderate distance from the camera.
- **Screen corners** — cursor movement keeps a small margin from the exact screen edges as a safety measure.

---

## Future Scope

- Multi-hand simultaneous tracking (e.g., mouse control with one hand while adjusting volume with the other)
- On-screen, real-time gesture legend that highlights the currently active gesture
- User-configurable sensitivity settings (pinch threshold, smoothing, cooldowns) via a settings panel
- Custom, user-assignable gesture-to-shortcut mapping
- Cross-platform support (macOS/Linux) for brightness and volume control

---

## Author

**Mohammed Rashid TV**
MCA, MESCE
Ponnani, Kerala

---

## License

This project is submitted as part of an academic mini project requirement. Feel free to reference or build upon it with attribution.
