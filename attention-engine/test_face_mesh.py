from camera import Camera
from face_mesh import FaceMeshAnalyzer
import cv2

cam = Camera()
analyzer = FaceMeshAnalyzer()

while True:
    frame = cam.get_frame()
    if frame is None:
        break

    data = analyzer.analyze(frame)

    if data:
        text = f"EyeOpen: {data['eye_open']:.4f} | Yaw: {data['yaw']:.4f}"
        cv2.putText(frame, text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Face Mesh Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
