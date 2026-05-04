from camera import Camera
from face_detector import FaceDetector
import cv2

cam = Camera()
detector = FaceDetector()

if not cam.open():
    print("Could not open camera")
    raise SystemExit(1)

while True:
    frame = cam.get_frame()
    if frame is None:
        break

    faces = detector.detect(frame)

    h, w, _ = frame.shape
    for box in faces:
        x = int(box.xmin * w)
        y = int(box.ymin * h)
        bw = int(box.width * w)
        bh = int(box.height * h)

        cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

    cv2.imshow("Face Detection Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
