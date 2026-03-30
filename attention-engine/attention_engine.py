from camera import Camera
from face_mesh import FaceMeshAnalyzer
from scorer import compute_attention
from collections import deque
import requests

def get_sensor_data():
    try:
        res = requests.get("http://127.0.0.1:5000/sensor-data", timeout=1)
        return res.json()
    except Exception as e:
        print("Sensor fetch error:", e)
        return {
            "temperature": 30,
            "noise": 60,
            "co2": 1000,
            "light": 200,
            "humidity": 70
        }

class AttentionEngine:
    def __init__(self):
        self.camera = Camera()
        self.analyzer = FaceMeshAnalyzer()
        self.buffer = deque(maxlen=10)
        self.prev_score = None  #for smoothing
        self.attention_state = 100
        self.sensor_history = deque(maxlen=5)

    def is_capture_active(self):
        return self.camera.is_open()

    def start_capture(self):
        return self.camera.open()

    def pause_capture(self):
        self.camera.release()

    def stop_capture(self, reset_state=True):
        self.camera.release()
        if reset_state:
            self.buffer.clear()
            self.prev_score = None
            self.attention_state = 100
            self.sensor_history.clear()

    def get_attention(self):
        if not self.is_capture_active():
            return {
                "attention": None,
                "eye_open": 0,
                "yaw": 0,
                "camera_active": False
            }

        frame = self.camera.get_frame()

        if frame is None:
            return {
                "attention": None,
                "eye_open": 0,
                "yaw": 0,
                "camera_active": self.is_capture_active()
            }

        features = self.analyzer.analyze(frame)
        
        #No face detected
        if features is None:
            if self.prev_score is not None:
                fallback = int(self.prev_score * 0.85)
            else:
                fallback = 0

            # 🔥 maintain system state
            self.prev_score = fallback
            self.attention_state = fallback
            self.buffer.append(fallback)

            return {
                "attention": int(sum(self.buffer) / len(self.buffer)),
                "eye_open": 0,
                "yaw": 0,
                "camera_active": True
            }

        #FETCH SENSOR DATA HERE
        sensor_data = get_sensor_data()

        #sensor smoothing
        self.sensor_history.append(sensor_data)
        avg_sensor = {
            key: sum(d[key] for d in self.sensor_history) / len(self.sensor_history)
            for key in sensor_data
        }

        score = compute_attention(features, avg_sensor, self.prev_score)

        # 🔥 NEW: attention inertia
        if score < self.attention_state:
            alpha = 0.4   # faster drop
        else:
            alpha = 0.3   # faster recovery
        self.attention_state = int(alpha * self.attention_state + (1 - alpha) * score)

        score = self.attention_state

        #SAVE FOR SMOOTHING
        self.prev_score = score

        return {
            "attention": score,
            "eye_open": features.get("eye_open", 0),
            "yaw": features.get("yaw", 0),
            "camera_active": True
        }
