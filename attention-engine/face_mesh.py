import cv2
import mediapipe as mp
import numpy as np

class FaceMeshAnalyzer:
    def __init__(self, max_num_faces=5):
        self.mp_mesh = mp.solutions.face_mesh
        self.mesh = self.mp_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=max_num_faces,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def analyze(self, frame):
        faces = self.analyze_faces(frame)
        return faces[0] if faces else None

    def analyze_faces(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.mesh.process(rgb)

        if not result.multi_face_landmarks:
            return []

        faces = []
        for face_landmarks in result.multi_face_landmarks:
            lm = face_landmarks.landmark
            center_x, center_y, width, height = self.face_box(lm)

            faces.append({
                "eye_open": self.eye_openness(lm),
                "yaw": self.head_yaw(lm),
                "center_x": center_x,
                "center_y": center_y,
                "face_width": width,
                "face_height": height,
                "face_area": width * height
            })

        return faces

    def eye_openness(self, lm):
        # Left eye vertical landmarks
        top = np.array([lm[159].x, lm[159].y])
        bottom = np.array([lm[145].x, lm[145].y])
        return np.linalg.norm(top - bottom)

    def head_yaw(self, lm):
        left_eye = lm[33].x
        right_eye = lm[263].x
        nose = lm[1].x
        return nose - (left_eye + right_eye) / 2

    def face_box(self, lm):
        xs = [point.x for point in lm]
        ys = [point.y for point in lm]

        min_x = max(0.0, min(xs))
        max_x = min(1.0, max(xs))
        min_y = max(0.0, min(ys))
        max_y = min(1.0, max(ys))

        width = max_x - min_x
        height = max_y - min_y
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        return center_x, center_y, width, height
