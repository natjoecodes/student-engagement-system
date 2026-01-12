from camera import Camera
from face_mesh import FaceMeshAnalyzer
from scorer import compute_attention
from collections import deque

class AttentionEngine:
    def __init__(self):
        self.camera = Camera()
        self.analyzer = FaceMeshAnalyzer()
        self.buffer = deque(maxlen=10)  # last 10 readings

    def get_attention(self):
        frame = self.camera.get_frame()
        if frame is None:
            return 0

        features = self.analyzer.analyze(frame)
        score = compute_attention(features)

        self.buffer.append(score)
        return int(sum(self.buffer) / len(self.buffer))