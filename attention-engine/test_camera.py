from camera import Camera
import cv2

cam = Camera()

if not cam.open():
    print("Could not open camera")
    raise SystemExit(1)

while True:
    frame = cam.get_frame()
    if frame is None:
        print("No frame received")
        break

    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
