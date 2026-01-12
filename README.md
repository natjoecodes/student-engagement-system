# 🎓 Multimodal Student Engagement Analytics System

## Overview

This project implements a **real-time student attention monitoring system** using computer vision and a live dashboard.  
The system follows a **microservice architecture**, separating attention inference from visualization for clarity, scalability, and maintainability.

Instead of emotion recognition or heavy machine learning models, the system relies on **explainable geometric facial cues** such as eye openness and head orientation to estimate attention in real time.

---

## System Architecture

The project consists of two independent services:

student-engagement-system/
├── attention-engine/      # Computer vision & attention inference
└── dashboard-server/      # Visualization & user interface

### 1. Attention Engine (Port 5001)
- Headless Flask service
- Captures webcam frames
- Performs face analysis
- Computes attention score
- Exposes results via REST API

### 2. Dashboard Server (Port 5000)
- Flask-based web server
- Displays real-time graphs and heatmaps
- Integrates IoT sensor data (ESP32)
- Fetches attention values from attention-engine

---

## Attention Inference Pipeline

The attention score is computed using the following steps:

1. Capture frame from webcam (OpenCV)
2. Detect face presence (MediaPipe)
3. Extract facial landmarks (MediaPipe Face Mesh)
4. Compute attention-related features:
   - Eye openness (drowsiness detection)
   - Head yaw (looking away detection)
5. Apply rule-based attention scoring
6. Apply temporal smoothing using a sliding window
7. Return attention score (0–100) via REST API

This pipeline ensures robustness against noise such as blinking or brief head movements.

---

## Attention Scoring Logic (Rule-Based)

| Condition | Effect |
|--------|--------|
| No face detected | Attention = 0 |
| Eyes mostly closed | −30 |
| Head turned away | −40 |
| Face present & attentive | High attention |
| Short disturbances | Smoothed out |

Temporal smoothing prevents sharp fluctuations due to momentary actions.

---

## Why Rule-Based Instead of Machine Learning?

A rule-based approach was chosen as the **baseline** for the following reasons:

- Fully explainable and transparent
- Low computational overhead
- Easier to validate during evaluation
- Suitable for real-time deployment

The system is designed to log features, allowing **machine learning–based refinement** as future work.

---

## Technologies Used

### Attention Engine
- Python 3.11
- Flask
- OpenCV
- MediaPipe (Face Detection & Face Mesh)
- NumPy

### Dashboard Server
- Python
- Flask
- HTML, CSS, JavaScript
- Chart.js
- ESP32 (for environmental sensing)

---

## Running the Project

### 1. Start the Attention Engine
```bash
cd attention-engine
source venv/bin/activate
python app.py

### 2. Start the Dashboard Server
```bash
cd dashboard-server
source venv/bin/activate
python app.py

3. Open Dashboard

Open a browser and navigate to:
http://127.0.0.1:5000
Click Start to begin attention monitoring.

Key Features
	•	Real-time attention estimation
	•	Headless computer vision processing
	•	Live graphs and heatmaps
	•	Temporal smoothing for stability
	•	Modular and scalable architecture
	•	Explainable decision logic
	•	IoT sensor integration (optional)

⸻

Limitations
	•	Designed for single-student monitoring
	•	Performance depends on camera placement and lighting
	•	Assumes frontal or near-frontal face visibility
	•	Privacy considerations (no video is stored)

⸻

Future Enhancements
	•	Multi-student attention aggregation
	•	Feature logging and ML-based regression
	•	Seat-wise classroom heatmaps
	•	Edge deployment (Jetson / Edge TPU)
	•	Long-term engagement analytics
	•	Automated session reports

⸻

Project Motivation

The goal of this project is to demonstrate how Edge AI and computer vision can be applied to educational environments using lightweight, explainable techniques rather than opaque black-box models.

⸻

License

This project is developed for academic and research purposes.

---