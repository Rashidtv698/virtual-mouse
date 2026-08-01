import cv2
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.camera import Camera
from src.hand_detector import HandDetector
from src.landmarks_reference import LANDMARK_NAMES

def main():
    camera = Camera()
    detector = HandDetector()
    selected_id = 8  # default: index fingertip

    print("Press 0-9 to select landmark groups, or use +/- to step through all 21.")
    print("Press 'q' to quit.\n")

    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        frame = detector.find_hands(frame, draw=True)
        landmarks = detector.get_landmark_positions(frame)

        if landmarks:
            for id, cx, cy in landmarks:
                if id == selected_id:
                    cv2.circle(frame, (cx, cy), 12, (0, 0, 255), cv2.FILLED)

            name = LANDMARK_NAMES.get(selected_id, "?")
            lm = next((l for l in landmarks if l[0] == selected_id), None)
            if lm:
                text = f"[{selected_id}] {name}: x={lm[1]}, y={lm[2]}"
                cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 255), 2)

        cv2.imshow("Landmark Explorer", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('+') or key == ord('='):
            selected_id = (selected_id + 1) % 21
        elif key == ord('-'):
            selected_id = (selected_id - 1) % 21

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()