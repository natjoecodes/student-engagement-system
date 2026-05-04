from camera import Camera
from face_mesh import FaceMeshAnalyzer
from scorer import compute_camera_score, compute_sensor_score
from collections import deque
from math import sqrt
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
        self.tracked_faces = {}
        self.next_face_id = 1
        self.max_track_distance = 0.18
        self.max_missed_frames = 2

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
            self.tracked_faces.clear()
            self.next_face_id = 1

    def _distance(self, face_a, face_b):
        return sqrt(
            ((face_a["center_x"] - face_b["center_x"]) ** 2) +
            ((face_a["center_y"] - face_b["center_y"]) ** 2)
        )

    def _match_faces(self, detected_faces):
        remaining_ids = set(self.tracked_faces.keys())
        matched = []

        for face in sorted(detected_faces, key=lambda item: item.get("face_area", 0), reverse=True):
            best_id = None
            best_distance = None

            for track_id in remaining_ids:
                prev_face = self.tracked_faces[track_id]
                distance = self._distance(face, prev_face)
                if distance > self.max_track_distance:
                    continue

                if best_distance is None or distance < best_distance:
                    best_id = track_id
                    best_distance = distance

            if best_id is None:
                track_id = self.next_face_id
                self.next_face_id += 1
                tracking_confidence = 0.6
                previous_score = None
            else:
                track_id = best_id
                remaining_ids.remove(best_id)
                tracking_confidence = max(0.75, 1.0 - (best_distance / self.max_track_distance))
                previous_score = self.tracked_faces[track_id].get("score")

            enriched_face = dict(face)
            enriched_face["id"] = track_id
            enriched_face["tracking_confidence"] = tracking_confidence
            enriched_face["previous_score"] = previous_score
            matched.append(enriched_face)

        stale_tracks = {}
        for track_id in remaining_ids:
            stale_face = dict(self.tracked_faces[track_id])
            stale_face["missed_frames"] = stale_face.get("missed_frames", 0) + 1
            if stale_face["missed_frames"] <= self.max_missed_frames:
                stale_tracks[track_id] = stale_face

        return matched, stale_tracks

    def _compute_face_weight(self, face):
        area_ratio = max(0.0, face.get("face_area", 0.0) / 0.08)
        area_weight = min(1.0, max(0.3, sqrt(area_ratio)))
        center_distance = sqrt(
            ((face.get("center_x", 0.5) - 0.5) ** 2) +
            ((face.get("center_y", 0.5) - 0.5) ** 2)
        )
        center_weight = max(0.5, 1.0 - (center_distance / 0.8))
        tracking_weight = face.get("tracking_confidence", 0.6)

        return (0.4 * area_weight) + (0.3 * center_weight) + (0.3 * tracking_weight)

    def _smooth_individual_score(self, raw_score, previous_score):
        if previous_score is None:
            return raw_score

        if raw_score < previous_score:
            return int((0.35 * previous_score) + (0.65 * raw_score))

        return int((0.65 * previous_score) + (0.35 * raw_score))

    def _compute_classroom_camera_score(self, scored_faces):
        if not scored_faces:
            return 0, 0, 0

        total_weight = sum(face["weight"] for face in scored_faces)
        weighted_average = sum(face["attention"] * face["weight"] for face in scored_faces) / total_weight

        low_weight = sum(face["weight"] for face in scored_faces if face["attention"] < 40)
        distracted_weight = sum(face["weight"] for face in scored_faces if face["attention"] < 60)

        low_ratio = low_weight / total_weight
        distracted_ratio = distracted_weight / total_weight

        penalty = (18 * low_ratio) + (10 * distracted_ratio)
        classroom_score = max(0, min(100, int(weighted_average - penalty)))

        return classroom_score, low_ratio, distracted_ratio

    def get_attention(self):
        if not self.is_capture_active():
            return {
                "attention": None,
                "eye_open": 0,
                "yaw": 0,
                "num_faces": 0,
                "faces": [],
                "camera_active": False
            }

        frame = self.camera.get_frame()

        if frame is None:
            return {
                "attention": None,
                "eye_open": 0,
                "yaw": 0,
                "num_faces": 0,
                "faces": [],
                "camera_active": self.is_capture_active()
            }

        detected_faces = self.analyzer.analyze_faces(frame)

        #No face detected
        if not detected_faces:
            if self.prev_score is not None:
                fallback = int(self.prev_score * 0.85)
            else:
                fallback = 0

            # 🔥 maintain system state
            self.prev_score = fallback
            self.attention_state = fallback
            self.buffer.append(fallback)
            self.tracked_faces = {
                track_id: {
                    **face,
                    "missed_frames": face.get("missed_frames", 0) + 1
                }
                for track_id, face in self.tracked_faces.items()
                if face.get("missed_frames", 0) + 1 <= self.max_missed_frames
            }

            return {
                "attention": int(sum(self.buffer) / len(self.buffer)),
                "eye_open": 0,
                "yaw": 0,
                "num_faces": 0,
                "faces": [],
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

        matched_faces, stale_tracks = self._match_faces(detected_faces)

        total_weight = 0.0
        weighted_eye_open = 0.0
        weighted_yaw = 0.0
        tracked_faces = {}
        response_faces = []

        for face in matched_faces:
            raw_camera_score = int(compute_camera_score(face) * 100)
            previous_score = face.get("previous_score")
            individual_score = self._smooth_individual_score(raw_camera_score, previous_score)

            weight = self._compute_face_weight(face)
            total_weight += weight
            weighted_eye_open += face.get("eye_open", 0) * weight
            weighted_yaw += face.get("yaw", 0) * weight

            tracked_face = {
                **face,
                "score": individual_score,
                "missed_frames": 0
            }
            tracked_faces[face["id"]] = tracked_face
            response_faces.append({
                "id": face["id"],
                "attention": individual_score,
                "eye_open": round(face.get("eye_open", 0), 4),
                "yaw": round(face.get("yaw", 0), 4),
                "weight": round(weight, 3)
            })

        tracked_faces.update(stale_tracks)
        self.tracked_faces = tracked_faces

        classroom_camera_score, low_ratio, distracted_ratio = self._compute_classroom_camera_score(response_faces)
        sensor_score = int(compute_sensor_score(avg_sensor) * 100)
        score = int((0.78 * classroom_camera_score) + (0.22 * sensor_score))

        # 🔥 NEW: attention inertia
        if score < self.attention_state:
            alpha = 0.3
        else:
            alpha = 0.72
        self.attention_state = int(alpha * self.attention_state + (1 - alpha) * score)

        score = self.attention_state

        #SAVE FOR SMOOTHING
        self.prev_score = score
        self.buffer.append(score)

        avg_eye_open = (weighted_eye_open / total_weight) if total_weight else 0
        avg_yaw = (weighted_yaw / total_weight) if total_weight else 0

        return {
            "attention": score,
            "eye_open": avg_eye_open,
            "yaw": avg_yaw,
            "num_faces": len(response_faces),
            "faces": response_faces,
            "camera_score": classroom_camera_score,
            "sensor_score": sensor_score,
            "low_attention_ratio": round(low_ratio, 3),
            "distracted_ratio": round(distracted_ratio, 3),
            "camera_active": True
        }
