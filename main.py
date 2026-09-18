import os
import cv2
import time
import pyautogui
import subprocess
import screen_brightness_control as sbc
import numpy as np
from src.camera import Camera
from src.hand_detector import HandDetector
from src.coordinate_mapper import CoordinateMapper
from src.mouse_controller import MouseController
from src.gesture_detector import GestureDetector
from src.landmarks_reference import THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP,PINKY_TIP
from datetime import datetime
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities

def main():
    cam_width, cam_height = 640, 480
    screen_width, screen_height = pyautogui.size()

    camera = Camera(width=cam_width, height=cam_height)
    detector = HandDetector()
    mapper = CoordinateMapper(cam_width, cam_height, screen_width, screen_height, margin=100)
    mouse = MouseController(smoothing_factor=0.4)
    gesture = GestureDetector(pinch_threshold=40)

    click_cooldown = 0.4   # seconds between allowed clicks
    last_click_time = 0
    is_dragging = False
    
    media_cooldown = 1.0  # seconds between allowed media actions (slideshow start/stop)
    last_media_time = 0
    
    slide_cooldown = 0.8  # seconds between allowed slide changes
    last_slide_time = 0
    slideshow_active = False
    
    screenshot_cooldown = 3.0  # longer gap — holding the pose shouldn't spam captures
    last_screenshot_time = 0
    screenshot_dir = "assets/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    left_brightness_active = False
    
    pinch_start_time = None
    DRAG_HOLD_THRESHOLD = 0.4  # seconds - pinch held longer than this = drag, not click

    prev_time = 0
    
    brightness_cooldown = 0.15  # brightness changes rapidly, but still throttle to avoid spamming the OS call
    last_brightness_time = 0
    BRIGHTNESS_PINCH_MIN = 20   # pixel distance = 0% brightness
    BRIGHTNESS_PINCH_MAX = 150  # pixel distance = 100% brightness
    left_brightness_active = False
    brightness_anchor_y = None
    brightness_baseline = 50
    BRIGHTNESS_DRAG_RANGE = 150  # pixels of vertical movement to swing full 0-100%
    
    device = AudioUtilities.GetSpeakers()
    volume_ctrl = device.EndpointVolume  
    locked_axis = None  # None, "x", or "y"
    AXIS_LOCK_THRESHOLD = 15  # pixels of movement before committing to an axis
    
    volume_anchor_x = None
    volume_baseline = 50
    VOLUME_DRAG_RANGE = 150  # pixels of horizontal movement to swing full 0-100%
    volume_cooldown = 0.15
    last_volume_time = 0
    
    shortcut_cooldown = 4.0  # opening an app shouldn't retrigger rapidly while pose is held
    last_shortcut_time = 0
    
         

    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        frame = detector.find_hands(frame)
        landmarks = detector.get_landmark_positions(frame)

        if landmarks:
            current_time = time.time()
            handedness = detector.get_handedness()
            fingers = gesture.fingers_up(landmarks, handedness)   # pass handedness in
            lm_dict = {id: (x, y) for id, x, y in landmarks}
            index_pos = lm_dict[INDEX_TIP]
            is_pinching_thumb_index = gesture.is_pinching(landmarks, THUMB_TIP, INDEX_TIP)

            only_index_up = fingers == [False, True, False, False, False]
            index_middle_up = fingers == [False, True, True, False, False]
            index_pinky_up = fingers == [False, True, False, False, True]
            only_thumb_up = fingers == [True, False, False, False, False]
            four_fingers_up = fingers == [False, True, True, True, True]
            all_fingers_up = fingers == [True, True, True, True, True]

            thumb_index_extended = fingers[0] and fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]
            
            right_pinch_click_drag = (handedness != "Left") and is_pinching_thumb_index
            left_thumb_index_shape = (handedness == "Left") and fingers[0] and fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]
            right_slide_next = (handedness != "Left") and thumb_index_extended and not is_pinching_thumb_index
            left_slide_prev = (handedness == "Left") and thumb_index_extended and not is_pinching_thumb_index
            right_only_thumb_up = (handedness != "Left") and only_thumb_up
            left_chrome_shortcut = (handedness == "Left") and fingers == [True, True, False, False, True]
            left_desktop_shortcut = (handedness == "Left") and fingers == [False, True, True, False, True]
            left_notepad_shortcut = (handedness == "Right") and fingers == [True, True, False, False, True]

            if not index_middle_up:
                mouse.scroll_ref_y = None

            # --- Centralized pinch-release: only applies to RIGHT hand's click/drag pinch ---
            if not right_pinch_click_drag and pinch_start_time is not None:
                held_duration = current_time - pinch_start_time
                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                    cv2.putText(frame, "DRAG END", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
                elif held_duration <= DRAG_HOLD_THRESHOLD:
                    if current_time - last_click_time > click_cooldown:
                        pyautogui.click()
                        last_click_time = current_time
                        cv2.putText(frame, "LEFT CLICK", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                pinch_start_time = None

            left_pinching = left_thumb_index_shape and is_pinching_thumb_index
            left_extended_only = left_thumb_index_shape and not is_pinching_thumb_index

            # --- Single unified gesture chain: exactly one branch fires per frame ---
            if right_pinch_click_drag:
                if pinch_start_time is None:
                    pinch_start_time = current_time
                held_duration = current_time - pinch_start_time
                if held_duration > DRAG_HOLD_THRESHOLD:
                    if not is_dragging:
                        pyautogui.mouseDown()
                        is_dragging = True
                    else:
                        screen_x, screen_y = mapper.map_to_screen(*index_pos)
                        mouse.move(screen_x, screen_y)
                    cv2.putText(frame, "DRAGGING", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)

            elif left_pinching:
                thumb_pos_l = lm_dict[THUMB_TIP]
                index_pos_l = lm_dict[INDEX_TIP]
                pinch_mid_y = (thumb_pos_l[1] + index_pos_l[1]) // 2
                pinch_mid_x = (thumb_pos_l[0] + index_pos_l[0]) // 2

                if not left_brightness_active:
                    left_brightness_active = True
                    brightness_anchor_y = pinch_mid_y
                    volume_anchor_x = pinch_mid_x
                    locked_axis = None
                    try:
                        brightness_baseline = sbc.get_brightness()[0]
                    except Exception:
                        brightness_baseline = 50
                    volume_baseline = int(volume_ctrl.GetMasterVolumeLevelScalar() * 100)
                else:
                    delta_y = brightness_anchor_y - pinch_mid_y
                    delta_x = pinch_mid_x - volume_anchor_x

                    if locked_axis is None:
                        if abs(delta_x) > AXIS_LOCK_THRESHOLD or abs(delta_y) > AXIS_LOCK_THRESHOLD:
                            locked_axis = "x" if abs(delta_x) > abs(delta_y) else "y"

                    brightness_pct = brightness_baseline
                    volume_pct = volume_baseline

                    if locked_axis == "y":
                        brightness_pct = brightness_baseline + int(
                            np.interp(delta_y, [-BRIGHTNESS_DRAG_RANGE, BRIGHTNESS_DRAG_RANGE], [-100, 100])
                        )
                        brightness_pct = max(0, min(100, brightness_pct))
                        if current_time - last_brightness_time > brightness_cooldown:
                            sbc.set_brightness(brightness_pct)
                            last_brightness_time = current_time

                    elif locked_axis == "x":
                        volume_pct = volume_baseline + int(
                            np.interp(delta_x, [-VOLUME_DRAG_RANGE, VOLUME_DRAG_RANGE], [-100, 100])
                        )
                        volume_pct = max(0, min(100, volume_pct))
                        if current_time - last_volume_time > volume_cooldown:
                            volume_ctrl.SetMasterVolumeLevelScalar(volume_pct / 100, None)
                            last_volume_time = current_time

                    mode_label = f"AXIS: {locked_axis.upper()}" if locked_axis else "AXIS: (hold still)"
                    cv2.putText(frame, f"BRIGHTNESS: {brightness_pct}%  VOLUME: {volume_pct}%  {mode_label}",
                                (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)

            elif left_extended_only:
                if left_brightness_active:
                    left_brightness_active = False
                    brightness_anchor_y = None
                    volume_anchor_x = None
                    locked_axis = None
                else:
                    if current_time - last_slide_time > slide_cooldown:
                        pyautogui.press('left')
                        cv2.putText(frame, "PREVIOUS SLIDE (Left hand)", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                        last_slide_time = current_time

            elif right_slide_next:
                if current_time - last_slide_time > slide_cooldown:
                    pyautogui.press('right')
                    cv2.putText(frame, "NEXT SLIDE (Right hand)", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                    last_slide_time = current_time

            elif only_index_up:
                screen_x, screen_y = mapper.map_to_screen(*index_pos)
                mouse.move(screen_x, screen_y)

            elif index_middle_up:
                middle_pos = lm_dict[MIDDLE_TIP]
                ref_y = (index_pos[1] + middle_pos[1]) // 2
                if mouse.scroll_ref_y is not None:
                    delta = mouse.scroll_ref_y - ref_y
                    if abs(delta) > 5:
                        pyautogui.scroll(int(delta * 2))
                mouse.scroll_ref_y = ref_y
                cv2.putText(frame, "SCROLL MODE", (10, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)
            elif left_chrome_shortcut:
                if current_time - last_shortcut_time > shortcut_cooldown:
                    subprocess.Popen('start chrome', shell=True)
                    last_shortcut_time = current_time
                    cv2.putText(frame, "OPENING CHROME", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            elif left_desktop_shortcut:
                if current_time - last_shortcut_time > shortcut_cooldown:
                    pyautogui.hotkey('win', 'd')
                    last_shortcut_time = current_time
                    cv2.putText(frame, "SHOW DESKTOP", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            elif left_notepad_shortcut:
                if current_time - last_shortcut_time > shortcut_cooldown:
                    subprocess.Popen('start notepad', shell=True)
                    last_shortcut_time = current_time
                    cv2.putText(frame, "OPENING NOTEPAD", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

            elif index_pinky_up:
                if current_time - last_click_time > click_cooldown:
                    pyautogui.doubleClick()
                    last_click_time = current_time
                    cv2.putText(frame, "DOUBLE CLICK", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            elif right_only_thumb_up:
                if current_time - last_click_time > click_cooldown:
                    pyautogui.rightClick()
                    last_click_time = current_time
                    cv2.putText(frame, "RIGHT CLICK", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            elif four_fingers_up:
                if current_time - last_screenshot_time > screenshot_cooldown:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")
                    pyautogui.screenshot(filepath)
                    last_screenshot_time = current_time
                    cv2.putText(frame, "SCREENSHOT SAVED", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "SCREENSHOT", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)

            elif all_fingers_up:
                if current_time - last_media_time > media_cooldown:
                    if not slideshow_active:
                        pyautogui.press('f5')
                        slideshow_active = True
                        cv2.putText(frame, "SLIDESHOW STARTED", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                    else:
                        pyautogui.press('esc')
                        slideshow_active = False
                        cv2.putText(frame, "SLIDESHOW ENDED", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                    last_media_time = current_time
                else:
                    cv2.putText(frame, "OPEN PALM", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)

            else:
                left_brightness_active = False
                brightness_anchor_y = None
                volume_anchor_x = None
                locked_axis = None

            cv2.putText(frame, f"Hand: {handedness} | Fingers: {fingers}", (10, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        else:
    # No hand detected this frame — safely release any held state
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False
            pinch_start_time = None
            left_brightness_active = False
            brightness_anchor_y = None
            volume_anchor_x = None
            locked_axis = None
            mouse.scroll_ref_y = None
            pose_history = []  # if you add the stability buffer later, clear it here too

            cv2.putText(frame, "NO HAND DETECTED", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.rectangle(frame, (100, 100), (cam_width - 100, cam_height - 100),
                      (255, 0, 0), 1)

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time else 0
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Virtual Mouse", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()