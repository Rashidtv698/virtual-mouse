import cv2
import time
import pyautogui
from src.camera import Camera
from src.hand_detector import HandDetector
from src.coordinate_mapper import CoordinateMapper
from src.mouse_controller import MouseController
from src.gesture_detector import GestureDetector
from src.landmarks_reference import THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP

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

            if only_index_up:
                # MOVE MODE: only move the cursor, skip all click checks this frame
                screen_x, screen_y = mapper.map_to_screen(*index_pos)
                mouse.move(screen_x, screen_y)

            else:
                # CLICK MODE: only check pinches when NOT in the move pose
                if gesture.is_pinching(landmarks, THUMB_TIP, INDEX_TIP):
                    if current_time - last_click_time > click_cooldown:
                        pyautogui.click()
                        last_click_time = current_time
                        cv2.putText(frame, "LEFT CLICK", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                elif gesture.is_pinching(landmarks, THUMB_TIP, MIDDLE_TIP):
                    if current_time - last_click_time > click_cooldown:
                        pyautogui.rightClick()
                        last_click_time = current_time
                        cv2.putText(frame, "RIGHT CLICK", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

                elif gesture.is_pinching(landmarks, THUMB_TIP, RING_TIP):
                    if current_time - last_click_time > click_cooldown:
                        pyautogui.doubleClick()
                        last_click_time = current_time
                        cv2.putText(frame, "DOUBLE CLICK", (10, 110),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

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