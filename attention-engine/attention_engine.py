from camera import Camera
from face_mesh import FaceMeshAnalyzer
from scorer import compute_attention
from collections import deque
import requests


# ✅ SENSOR FETCH FUNCTION (GLOBAL, NOT INSIDE CLASS)
def get_sensor_data():
    try:
        res = requests.get("http://127.0.0.1:5000/sensor-data", timeout=1)
        return res.json()
    except Exception as e:
        print("Sensor fetch error:", e)
        return None


class AttentionEngine:
    def __init__(self):
        self.camera = Camera()
        self.analyzer = FaceMeshAnalyzer()
        self.buffer = deque(maxlen=10)
        self.prev_score = None  # ✅ for smoothing

    def get_attention(self):
        frame = self.camera.get_frame()

        if frame is None:
            return {
                "attention": 0,
                "eye_open": 0,
                "yaw": 0
            }

        features = self.analyzer.analyze(frame)

        #No face detected
        if features is None:
            return {
                "attention": 0,
                "eye_open": 0,
                "yaw": 0
            }

        #FETCH SENSOR DATA HERE
        sensor_data = get_sensor_data()
        print("LIVE SENSOR:", sensor_data)

        #COMPUTE SCORE WITH SENSOR + PREV SCORE
        score = compute_attention(features, sensor_data, self.prev_score)

        #SAVE FOR SMOOTHING
        self.prev_score = score

        #OPTIONAL: BUFFER SMOOTHING (extra stability)
        self.buffer.append(score)
        smooth_score = int(sum(self.buffer) / len(self.buffer))

        return {
            "attention": smooth_score,
            "eye_open": features.get("eye_open", 0),
            "yaw": features.get("yaw", 0)
        }