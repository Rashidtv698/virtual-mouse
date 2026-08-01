import cv2
import time
import pyautogui
from src.camera import Camera
from src.hand_detector import HandDetector
from src.coordinate_mapper import CoordinateMapper
from src.mouse_controller import MouseController
from src.landmarks_reference import INDEX_TIP

def main():
    cam_width, cam_height = 640, 480
    screen_width, screen_height = pyautogui.size()

    camera = Camera(width=cam_width, height=cam_height)
    detector = HandDetector()
    mapper = CoordinateMapper(cam_width, cam_height, screen_width, screen_height, margin=100)
    mouse = MouseController(smoothing_factor=0.5)

    prev_time = 0

    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        frame = detector.find_hands(frame)
        landmarks = detector.get_landmark_positions(frame)

        if landmarks:
            index_tip = next((l for l in landmarks if l[0] == INDEX_TIP), None)
            if index_tip:
                _, cam_x, cam_y = index_tip
                screen_x, screen_y = mapper.map_to_screen(cam_x, cam_y)
                mouse.move(screen_x, screen_y)

                cv2.circle(frame, (cam_x, cam_y), 10, (0, 255, 0), cv2.FILLED)

        # Draw the active region boundary for visual reference
        cv2.rectangle(frame, (100, 100), (cam_width - 100, cam_height - 100),
                      (255, 0, 0), 2)

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