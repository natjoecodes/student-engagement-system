import cv2

class Camera:
    def __init__(self, src=0):
        self.src = src
        self.cap = None

    def open(self):
        if self.cap is not None and self.cap.isOpened():
            return True

        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            return False

        return True

    def is_open(self):
        return self.cap is not None and self.cap.isOpened()

    def get_frame(self):
        if not self.is_open():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
