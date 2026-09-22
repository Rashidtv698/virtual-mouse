import os
import time
import threading
import cv2
import numpy as np
import pyautogui
import screen_brightness_control as sbc
import subprocess
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
from pycaw.pycaw import AudioUtilities
import win32gui

from src.camera import Camera
from src.hand_detector import HandDetector
from src.coordinate_mapper import CoordinateMapper
from src.mouse_controller import MouseController
from src.gesture_detector import GestureDetector
from src.landmarks_reference import THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
DARK_BG = "#0d1117"
PANEL_BG = "#161b22"
BORDER = "#30363d"
TEXT_MAIN = "#e6edf3"
TEXT_DIM = "#8b949e"
ACCENT_GREEN = "#2ea043"
ACCENT_RED = "#da3633"
ACCENT_GRAY = "#4b5563"

# Static legend of your actual implemented gestures
GESTURE_LEGEND = [
    ("☝", "Index Finger Up", "Move Cursor"),
    ("🤏", "Thumb+Index Tap", "Left Click"),
    ("🤏", "Thumb+Index Hold", "Drag"),
    ("👍", "Thumb Only (Right hand)", "Right Click"),
    ("✌", "Index+Middle Up", "Scroll"),
    ("🤙", "Index+Pinky Up", "Double Click"),
    ("🖖", "4 Fingers, No Thumb", "Screenshot"),
    ("🖐", "Open Palm (hold)", "Toggle Slideshow"),
    ("👉", "Thumb+Index Extended (R/L)", "Next / Prev Slide"),
    ("🎚", "Thumb+Index Pinch (Left)", "Brightness / Volume"),
    ("🌐", "Thumb+Index+Pinky (Left)", "Open Chrome"),
    ("🖥", "Index+Middle+Pinky (Left)", "Show Desktop"),
]

def is_powerpoint_active():
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return "PowerPoint" in title
        except Exception:
            return False
def make_black_placeholder(width=640, height=480):
    black = Image.new("RGB", (width, height), (0, 0, 0))
    return ImageTk.PhotoImage(black)

class VirtualMouseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Virtual Mouse")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1150, screen_w - 60)
        win_h = min(760, screen_h - 80)  # leaves room for taskbar
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(True, True)

        self.running = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()

        self._init_gesture_state()
        self._build_layout()

    # ---------------- GUI LAYOUT ----------------
    def _build_layout(self):
            self.root.configure(bg=DARK_BG)

            # ---------- Header ----------
            header = tk.Frame(self.root, bg=DARK_BG)
            header.pack(fill="x", padx=20, pady=(15, 10))

            tk.Label(header, text="✋", font=("Segoe UI Emoji", 28), bg=DARK_BG, fg=TEXT_MAIN).pack(side="left", padx=(0, 12))
            title_box = tk.Frame(header, bg=DARK_BG)
            title_box.pack(side="left")
            tk.Label(title_box, text="Virtual Mouse", font=("Segoe UI", 18, "bold"), bg=DARK_BG, fg=TEXT_MAIN).pack(anchor="w")
            tk.Label(title_box, text="Control your computer with hand gestures", font=("Segoe UI", 10), bg=DARK_BG, fg=TEXT_DIM).pack(anchor="w")

            # ---------- Main content: video (left) + status/legend (right) ----------
            content = tk.Frame(self.root, bg=DARK_BG)
            content.pack(fill="both", expand=True, padx=20, pady=10)

            # ----- Left: video panel -----
            video_panel = tk.Frame(content, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1)
            video_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))

            badge_row = tk.Frame(video_panel, bg=PANEL_BG)
            badge_row.pack(fill="x", padx=10, pady=8)
            self.status_dot = tk.Label(badge_row, text="●", font=("Segoe UI", 10), bg=PANEL_BG, fg=ACCENT_RED)
            self.status_dot.pack(side="left")
            self.status_text = tk.Label(badge_row, text="Camera Off", font=("Segoe UI", 9, "bold"), bg=PANEL_BG, fg=TEXT_DIM)
            self.status_text.pack(side="left", padx=(5, 0))

            self.video_label = tk.Label(video_panel, bg="black")
            self.video_label.pack(padx=10, pady=(0, 10))
            self.placeholder_img = make_black_placeholder(640, 480)
            self.video_label.config(image=self.placeholder_img)
            self.video_label.image = self.placeholder_img

            # ----- Right: status + legend -----
            right_col = tk.Frame(content, bg=DARK_BG, width=340)
            right_col.pack(side="left", fill="y")
            right_col.pack_propagate(False)

            # Current Gesture panel
            cg_panel = tk.Frame(right_col, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1)
            cg_panel.pack(fill="x", pady=(0, 12))
            tk.Label(cg_panel, text="Current Gesture", font=("Segoe UI", 11, "bold"), bg=PANEL_BG, fg=TEXT_MAIN).pack(anchor="w", padx=12, pady=(10, 5))

            cg_row = tk.Frame(cg_panel, bg=PANEL_BG)
            cg_row.pack(fill="x", padx=12, pady=(0, 12))
            self.cg_icon = tk.Label(cg_row, text="✋", font=("Segoe UI Emoji", 22), bg="#21262d", fg=TEXT_MAIN, width=2)
            self.cg_icon.pack(side="left", padx=(0, 10))
            cg_text_box = tk.Frame(cg_row, bg=PANEL_BG)
            cg_text_box.pack(side="left")
            self.gesture_var = tk.StringVar(value="—")
            tk.Label(cg_text_box, textvariable=self.gesture_var, font=("Segoe UI", 12, "bold"), bg=PANEL_BG, fg=TEXT_MAIN).pack(anchor="w")
            self.hand_fps_var = tk.StringVar(value="Hand: — | FPS: —")
            tk.Label(cg_text_box, textvariable=self.hand_fps_var, font=("Segoe UI", 9), bg=PANEL_BG, fg=TEXT_DIM).pack(anchor="w")

            # Available Gestures panel
            legend_panel = tk.Frame(right_col, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1)
            legend_panel.pack(fill="both", expand=True)
            tk.Label(legend_panel, text="Available Gestures", font=("Segoe UI", 11, "bold"), bg=PANEL_BG, fg=TEXT_MAIN).pack(anchor="w", padx=12, pady=(10, 8))

            for icon, gesture_name, action in GESTURE_LEGEND:
                row = tk.Frame(legend_panel, bg=PANEL_BG)
                row.pack(fill="x", padx=12, pady=3)
                tk.Label(row, text=icon, font=("Segoe UI Emoji", 11), bg=PANEL_BG, fg=TEXT_MAIN, width=2).pack(side="left")
                tk.Label(row, text=gesture_name, font=("Segoe UI", 9), bg=PANEL_BG, fg=TEXT_MAIN, width=24, anchor="w").pack(side="left")
                tk.Label(row, text=action, font=("Segoe UI", 9), bg=PANEL_BG, fg=TEXT_DIM, anchor="w").pack(side="left")

            # ---------- Bottom controls ----------
            button_frame = tk.Frame(self.root, bg=DARK_BG)
            button_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 18))

            self.start_btn = tk.Button(button_frame, text="▶  Start", width=14, bg=ACCENT_GREEN, fg="white",
                                        font=("Segoe UI", 10, "bold"), relief="flat", activebackground="#2c974b",
                                        command=self.start)
            self.start_btn.pack(side="left", padx=(0, 8), ipady=6)

            self.stop_btn = tk.Button(button_frame, text="■  Stop", width=14, bg=ACCENT_RED, fg="white",
                                    font=("Segoe UI", 10, "bold"), relief="flat", activebackground="#f85149",
                                    command=self.stop, state="disabled")
            self.stop_btn.pack(side="left", padx=8, ipady=6)

            exit_btn = tk.Button(button_frame, text="⏻  Exit", width=14, bg=ACCENT_GRAY, fg="white",
                                font=("Segoe UI", 10, "bold"), relief="flat", activebackground="#6e7681",
                                command=self.on_exit)
            exit_btn.pack(side="left", padx=8, ipady=6)

    # ---------------- GESTURE STATE (mirrors your old main.py) ----------------
    def _init_gesture_state(self):
        self.camera = None
        self.detector = HandDetector()
        self.mapper = None
        self.mouse = MouseController(smoothing_factor=0.4)
        self.gesture = GestureDetector(pinch_threshold=40)

        self.click_cooldown = 0.4
        self.last_click_time = 0
        self.is_dragging = False

        self.media_cooldown = 1.0
        self.last_media_time = 0

        self.slide_cooldown = 0.8
        self.last_slide_time = 0
        self.slideshow_active = False

        self.screenshot_cooldown = 3.0
        self.last_screenshot_time = 0
        self.screenshot_dir = "assets/screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

        self.shortcut_cooldown = 4.0
        self.last_shortcut_time = 0

        self.pinch_start_time = None
        self.DRAG_HOLD_THRESHOLD = 0.4

        self.brightness_cooldown = 0.15
        self.last_brightness_time = 0
        self.left_brightness_active = False
        self.brightness_anchor_y = None
        self.brightness_baseline = 50
        self.BRIGHTNESS_DRAG_RANGE = 150

        device = AudioUtilities.GetSpeakers()
        self.volume_ctrl = device.EndpointVolume
        self.locked_axis = None
        self.AXIS_LOCK_THRESHOLD = 15
        self.volume_anchor_x = None
        self.volume_baseline = 50
        self.VOLUME_DRAG_RANGE = 150
        self.volume_cooldown = 0.15
        self.last_volume_time = 0

        self.prev_time = 0

    # ---------------- START / STOP / EXIT ----------------
    def start(self):
        if self.running:
            return
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_dot.config(fg=ACCENT_GREEN)
        self.status_text.config(text="Camera Active", fg=TEXT_MAIN)
        self.gesture_var.set("Starting camera...")

        cam_width, cam_height = 640, 480
        self.camera = Camera(width=cam_width, height=cam_height)
        screen_width, screen_height = pyautogui.size()
        self.mapper = CoordinateMapper(cam_width, cam_height, screen_width, screen_height, margin=100)

        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        self._update_gui_frame()

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_dot.config(fg=ACCENT_RED)
        self.status_text.config(text="Camera Off", fg=TEXT_DIM)
        if self.is_dragging:
            pyautogui.mouseUp()
            self.is_dragging = False
        if self.camera:
            self.camera.release()

        # Show black placeholder instead of leaving the label blank
        self.video_label.config(image=self.placeholder_img)
        self.video_label.image = self.placeholder_img
        self.gesture_var.set("—")
        self.hand_fps_var.set("Hand: — | FPS: —")

    def on_exit(self):
        self.running = False
        if self.is_dragging:
            pyautogui.mouseUp()
        if self.camera:
            self.camera.release()
        self.root.destroy()

    # ---------------- BACKGROUND THREAD: capture + gesture logic ----------------
    def _camera_loop(self):
        while self.running:
            frame = self.camera.get_frame()
            if frame is None:
                continue

            frame = self.detector.find_hands(frame)
            landmarks = self.detector.get_landmark_positions(frame)

            gesture_text = "—"
            hand_text = "—"

            if landmarks:
                current_time = time.time()
                handedness = self.detector.get_handedness()
                hand_text = handedness or "Unknown"
                fingers = self.gesture.fingers_up(landmarks, handedness)
                lm_dict = {id: (x, y) for id, x, y in landmarks}
                index_pos = lm_dict[INDEX_TIP]
                is_pinching_thumb_index = self.gesture.is_pinching(landmarks, THUMB_TIP, INDEX_TIP)

                only_index_up = fingers == [False, True, False, False, False]
                index_middle_up = fingers == [False, True, True, False, False]
                index_pinky_up = fingers == [False, True, False, False, True]
                only_thumb_up = fingers == [True, False, False, False, False]
                four_fingers_up = fingers == [False, True, True, True, True]
                all_fingers_up = fingers == [True, True, True, True, True]
                thumb_index_extended = fingers[0] and fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]

                right_pinch_click_drag = (handedness != "Left") and is_pinching_thumb_index
                left_thumb_index_shape = (handedness == "Left") and thumb_index_extended
                right_slide_next = (handedness != "Left") and thumb_index_extended and not is_pinching_thumb_index
                right_only_thumb_up = (handedness != "Left") and only_thumb_up
                left_pinching = left_thumb_index_shape and is_pinching_thumb_index
                left_extended_only = left_thumb_index_shape and not is_pinching_thumb_index
                left_chrome_shortcut = (handedness == "Left") and fingers == [True, True, False, False, True]
                left_desktop_shortcut = (handedness == "Left") and fingers == [False, True, True, False, True]

                if not index_middle_up:
                    self.mouse.scroll_ref_y = None

                if not right_pinch_click_drag and self.pinch_start_time is not None:
                    held_duration = current_time - self.pinch_start_time
                    if self.is_dragging:
                        pyautogui.mouseUp()
                        self.is_dragging = False
                        gesture_text = "DRAG END"
                    elif held_duration <= self.DRAG_HOLD_THRESHOLD:
                        if current_time - self.last_click_time > self.click_cooldown:
                            pyautogui.click()
                            self.last_click_time = current_time
                            gesture_text = "LEFT CLICK"
                    self.pinch_start_time = None

                if right_pinch_click_drag:
                    if self.pinch_start_time is None:
                        self.pinch_start_time = current_time
                    held_duration = current_time - self.pinch_start_time
                    if held_duration > self.DRAG_HOLD_THRESHOLD:
                        if not self.is_dragging:
                            pyautogui.mouseDown()
                            self.is_dragging = True
                        else:
                            sx, sy = self.mapper.map_to_screen(*index_pos)
                            self.mouse.move(sx, sy)
                        gesture_text = "DRAGGING"

                elif left_pinching:
                    thumb_pos_l = lm_dict[THUMB_TIP]
                    index_pos_l = lm_dict[INDEX_TIP]
                    pinch_mid_y = (thumb_pos_l[1] + index_pos_l[1]) // 2
                    pinch_mid_x = (thumb_pos_l[0] + index_pos_l[0]) // 2

                    if not self.left_brightness_active:
                        self.left_brightness_active = True
                        self.brightness_anchor_y = pinch_mid_y
                        self.volume_anchor_x = pinch_mid_x
                        self.locked_axis = None
                        try:
                            self.brightness_baseline = sbc.get_brightness()[0]
                        except Exception:
                            self.brightness_baseline = 50
                        self.volume_baseline = int(self.volume_ctrl.GetMasterVolumeLevelScalar() * 100)
                    else:
                        delta_y = self.brightness_anchor_y - pinch_mid_y
                        delta_x = pinch_mid_x - self.volume_anchor_x

                        if self.locked_axis is None:
                            if abs(delta_x) > self.AXIS_LOCK_THRESHOLD or abs(delta_y) > self.AXIS_LOCK_THRESHOLD:
                                self.locked_axis = "x" if abs(delta_x) > abs(delta_y) else "y"

                        brightness_pct = self.brightness_baseline
                        volume_pct = self.volume_baseline

                        if self.locked_axis == "y":
                            brightness_pct = int(np.interp(delta_y, [-self.BRIGHTNESS_DRAG_RANGE, self.BRIGHTNESS_DRAG_RANGE], [-100, 100])) + self.brightness_baseline
                            brightness_pct = max(0, min(100, brightness_pct))
                            if current_time - self.last_brightness_time > self.brightness_cooldown:
                                sbc.set_brightness(brightness_pct)
                                self.last_brightness_time = current_time
                        elif self.locked_axis == "x":
                            volume_pct = int(np.interp(delta_x, [-self.VOLUME_DRAG_RANGE, self.VOLUME_DRAG_RANGE], [-100, 100])) + self.volume_baseline
                            volume_pct = max(0, min(100, volume_pct))
                            if current_time - self.last_volume_time > self.volume_cooldown:
                                self.volume_ctrl.SetMasterVolumeLevelScalar(volume_pct / 100, None)
                                self.last_volume_time = current_time

                        gesture_text = f"BRIGHTNESS: {brightness_pct}%  VOLUME: {volume_pct}%"

                elif left_extended_only:
                    if self.left_brightness_active:
                        self.left_brightness_active = False
                        self.brightness_anchor_y = None
                        self.volume_anchor_x = None
                        self.locked_axis = None
                    else:
                        if current_time - self.last_slide_time > self.slide_cooldown:
                            pyautogui.press('left')
                            gesture_text = "PREVIOUS SLIDE (Left hand)"
                            self.last_slide_time = current_time

                elif right_slide_next:
                    if is_powerpoint_active():
                        if current_time - self.last_slide_time > self.slide_cooldown:
                            pyautogui.press('right')
                            gesture_text = "NEXT SLIDE (Right hand)"
                            self.last_slide_time = current_time
                    else:
                        gesture_text = "NEXT SLIDE gesture (PowerPoint not active)"
                elif left_chrome_shortcut:
                    if current_time - self.last_shortcut_time > self.shortcut_cooldown:
                        subprocess.Popen('start chrome', shell=True)
                        self.last_shortcut_time = current_time
                        gesture_text = "OPENING CHROME"

                elif left_desktop_shortcut:
                    if current_time - self.last_shortcut_time > self.shortcut_cooldown:
                        pyautogui.hotkey('win', 'd')
                        self.last_shortcut_time = current_time
                        gesture_text = "SHOW DESKTOP"

                elif only_index_up:
                    sx, sy = self.mapper.map_to_screen(*index_pos)
                    self.mouse.move(sx, sy)
                    gesture_text = "MOVE"

                elif index_middle_up:
                    middle_pos = lm_dict[MIDDLE_TIP]
                    ref_y = (index_pos[1] + middle_pos[1]) // 2
                    if self.mouse.scroll_ref_y is not None:
                        delta = self.mouse.scroll_ref_y - ref_y
                        if abs(delta) > 5:
                            pyautogui.scroll(int(delta * 2))
                    self.mouse.scroll_ref_y = ref_y
                    gesture_text = "SCROLL MODE"

                elif index_pinky_up:
                    if current_time - self.last_click_time > self.click_cooldown:
                        pyautogui.doubleClick()
                        self.last_click_time = current_time
                        gesture_text = "DOUBLE CLICK"

                elif right_only_thumb_up:
                    if current_time - self.last_click_time > self.click_cooldown:
                        pyautogui.rightClick()
                        self.last_click_time = current_time
                        gesture_text = "RIGHT CLICK"

                elif four_fingers_up:
                    if current_time - self.last_screenshot_time > self.screenshot_cooldown:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filepath = os.path.join(self.screenshot_dir, f"screenshot_{timestamp}.png")
                        pyautogui.screenshot(filepath)
                        self.last_screenshot_time = current_time
                        gesture_text = "SCREENSHOT SAVED"
                    else:
                        gesture_text = "SCREENSHOT (cooldown)"

                elif all_fingers_up:
                    if current_time - self.last_media_time > self.media_cooldown:
                        if not self.slideshow_active:
                            pyautogui.press('f5')
                            self.slideshow_active = True
                            gesture_text = "SLIDESHOW STARTED"
                        else:
                            pyautogui.press('esc')
                            self.slideshow_active = False
                            gesture_text = "SLIDESHOW ENDED"
                        self.last_media_time = current_time
                    else:
                        gesture_text = "OPEN PALM"

            else:
                # Hand lost — safely release all active state
                if self.is_dragging:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                self.pinch_start_time = None
                self.left_brightness_active = False
                self.brightness_anchor_y = None
                self.volume_anchor_x = None
                self.locked_axis = None
                self.mouse.scroll_ref_y = None
                gesture_text = "NO HAND DETECTED"

            # FPS calculation
            curr_time = time.time()
            fps = 1 / (curr_time - self.prev_time) if self.prev_time else 0
            self.prev_time = curr_time

            with self.frame_lock:
                self.latest_frame = frame
                self._latest_gesture = gesture_text
                self._latest_hand = hand_text
                self._latest_fps = fps
        time.sleep(0.001)  # tiny yield, prevents the thread from spinning at 100% and starving the main thread

        if self.camera:
            self.camera.release()

    # ---------------- MAIN THREAD: render only ----------------
    def _update_gui_frame(self):
        if not self.running:
            return

        with self.frame_lock:
            frame = self.latest_frame
            gesture_text = getattr(self, "_latest_gesture", "—")
            hand_text = getattr(self, "_latest_hand", "—")
            fps = getattr(self, "_latest_fps", 0)

        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

            self.gesture_var.set(gesture_text)
            self.hand_fps_var.set(f"Hand: {hand_text} | FPS: {int(fps)}")
        self.root.after(33, self._update_gui_frame)  # ~30fps polling ceiling, matches realistic camera output


def run_app():
    root = tk.Tk()
    app = VirtualMouseGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()