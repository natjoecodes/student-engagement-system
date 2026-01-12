import cv2
import mediapipe as mp

class FaceDetector:
    def __init__(self, min_confidence=0.6):
        self.mp_face = mp.solutions.face_detection
        self.detector = self.mp_face.FaceDetection(
            model_selection=0,
            min_detection_confidence=min_confidence
        )

    def detect(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb)

        faces = []
        if results.detections:
            for det in results.detections:
                faces.append(det.location_data.relative_bounding_box)

        return faces