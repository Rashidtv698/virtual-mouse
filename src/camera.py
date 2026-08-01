import cv2

class Camera:
    def __init__(self, cam_index=0, width=640, height=480):
        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if not self.cap.isOpened():
            raise RuntimeError("Could not open webcam")

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)  # mirror view — feels natural for a mouse
        return frame

    def release(self):
        self.cap.release()