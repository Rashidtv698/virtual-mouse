import os
import cv2
import time
import pyautogui
from src.camera import Camera
from src.hand_detector import HandDetector
from src.coordinate_mapper import CoordinateMapper
from src.mouse_controller import MouseController
from src.gesture_detector import GestureDetector
from src.landmarks_reference import THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP,PINKY_TIP
from datetime import datetime

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
    
    screenshot_cooldown = 3.0  # longer gap — holding the pose shouldn't spam captures
    last_screenshot_time = 0
    screenshot_dir = "assets/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    pinch_start_time = None
    DRAG_HOLD_THRESHOLD = 0.3  # seconds - pinch held longer than this = drag, not click

    prev_time = 0
    

    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        frame = detector.find_hands(frame)
        landmarks = detector.get_landmark_positions(frame)

        if landmarks:
            fingers = gesture.fingers_up(landmarks)
            lm_dict = {id: (x, y) for id, x, y in landmarks}
            index_pos = lm_dict[INDEX_TIP]
            current_time = time.time()

            only_index_up = fingers == [False, True, False, False, False]
            index_middle_up = fingers == [False, True, True, False, False]
            index_pinky_up=fingers == [False, True, False, False, True]
            only_thumb_up = fingers == [True, False, False, False, False]
            all_fingers_up = fingers == [True, True, True, True, True]

            is_pinching_thumb_index = gesture.is_pinching(landmarks, THUMB_TIP, INDEX_TIP)

            if is_pinching_thumb_index:
                # --- Thumb+index pinch: tap = left click, hold = drag ---
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
                mouse.scroll_ref_y = None

            elif only_index_up:
                screen_x, screen_y = mapper.map_to_screen(*index_pos)
                mouse.move(screen_x, screen_y)
                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                    cv2.putText(frame, "DRAG END", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)

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

            elif index_pinky_up:
                if current_time - last_click_time > click_cooldown:
                    pyautogui.doubleClick()
                    last_click_time = current_time
                    cv2.putText(frame, "DOUBLE CLICK", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            elif only_thumb_up:
                if current_time - last_click_time > click_cooldown:
                    pyautogui.rightClick()
                    last_click_time = current_time
                    cv2.putText(frame, "RIGHT CLICK", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            elif all_fingers_up:
                if current_time - last_screenshot_time > screenshot_cooldown:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")
                    pyautogui.screenshot(filepath)
                    last_screenshot_time = current_time
                    cv2.putText(frame, "SCREENSHOT SAVED", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    # still show feedback while pose is held but cooldown hasn't cleared
                    cv2.putText(frame, "OPEN PALM", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)

            else:
                mouse.scroll_ref_y = None
                # pinch just released (wasn't pinching this frame, but was pinching before)
                if pinch_start_time is not None:
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
            cv2.putText(frame, f"Fingers: {fingers}", (10, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

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