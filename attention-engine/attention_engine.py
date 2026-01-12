from camera import Camera
from face_mesh import FaceMeshAnalyzer
from scorer import compute_attention
from collections import deque


class AttentionEngine:
    def __init__(self):
        self.camera = Camera()
        self.analyzer = FaceMeshAnalyzer()
        self.buffer = deque(maxlen=10)

    def get_attention(self):
        frame = self.camera.get_frame()

        if frame is None:
            return {
                "attention": 0,
                "eye_open": 0,
                "yaw": 0
            }

        features = self.analyzer.analyze(frame)

        # 🔴 REQUIRED: face not detected
        if features is None:
            return {
                "attention": 0,
                "eye_open": 0,
                "yaw": 0
            }

        score = compute_attention(features)

        return {
            "attention": score,
            "eye_open": features.get("eye_open", 0),
            "yaw": features.get("yaw", 0)
        }