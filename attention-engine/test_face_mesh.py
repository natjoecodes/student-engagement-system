from camera import Camera
from face_mesh import FaceMeshAnalyzer
import cv2

cam = Camera()
analyzer = FaceMeshAnalyzer()

if not cam.open():
    print("Could not open camera")
    raise SystemExit(1)

while True:
    frame = cam.get_frame()
    if frame is None:
        break

    faces = analyzer.analyze_faces(frame)

    cv2.putText(
        frame,
        f"Faces: {len(faces)}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    frame_h, frame_w, _ = frame.shape
    for index, data in enumerate(faces, start=1):
        x = int((data["center_x"] - (data["face_width"] / 2)) * frame_w)
        y = int((data["center_y"] - (data["face_height"] / 2)) * frame_h)
        w = int(data["face_width"] * frame_w)
        h = int(data["face_height"] * frame_h)

        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = f"#{index} Eye:{data['eye_open']:.4f} Yaw:{data['yaw']:.4f}"
        cv2.putText(
            frame,
            text,
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1
        )

    cv2.imshow("Face Mesh Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
