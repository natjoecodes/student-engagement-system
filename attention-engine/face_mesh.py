import cv2
import mediapipe as mp
import numpy as np

class FaceMeshAnalyzer:
    def __init__(self):
        self.mp_mesh = mp.solutions.face_mesh
        self.mesh = self.mp_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def analyze(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.mesh.process(rgb)

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark

        eye_open = self.eye_openness(lm)
        yaw = self.head_yaw(lm)

        return {
            "eye_open": eye_open,
            "yaw": yaw
        }

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
