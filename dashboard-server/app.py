from flask import Flask, jsonify, render_template, request, redirect, session, Response
from flask_cors import CORS
import requests

# Initialize the Flask application
app = Flask(__name__)
# Set the secret key for session management
app.secret_key = "edge-ai-demo-secret"
# Enable Cross-Origin Resource Sharing (CORS) to allow requests from the browser
CORS(app)

# Simple in-memory users dictionary
USERS = {
    "teacher1": "pass123",
    "teacher2": "demo456",
    "hod": "admin789"
}

# A dictionary to store the most recent sensor data
sensor_data = {
    "temperature": 0,
    "humidity": 0,
    "light": 0,
    "noise": 0,
    "co2": 0
}

# Route for the login page
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling login POST requests
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username in USERS and USERS[username] == password:
        session['user'] = username
        return redirect('/dashboard')
    else:
        return render_template(
        "index.html",
        error="Invalid username or password"
    )

# Protected dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')

@app.route("/sessions")
def sessions():
    if 'user' not in session:
        return redirect('/')
    return render_template("sessions.html")

ENGINE_BASE_URL = "http://127.0.0.1:5001"

def proxy_engine_request(method, path, *, json_body=None, timeout=3):
    url = f"{ENGINE_BASE_URL}{path}"
    return requests.request(method, url, json=json_body, timeout=timeout)

@app.route("/api/sessions")
def api_sessions():
    if 'user' not in session:
        return jsonify([]), 401

    try:
        res = proxy_engine_request("GET", "/sessions", timeout=3)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session proxy error:", e)
        return jsonify([]), 500

@app.route("/api/attention")
def api_attention():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("GET", "/attention", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Attention proxy error:", e)
        return jsonify({"error": "Attention fetch failed"}), 500

@app.route("/api/session/state")
def api_session_state():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("GET", "/session/state", timeout=3)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session state proxy error:", e)
        return jsonify({"error": "State fetch failed"}), 500

@app.route("/api/session/start", methods=["POST"])
def api_session_start():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        payload = request.get_json(silent=True) or {}
        res = proxy_engine_request("POST", "/session/start", json_body=payload, timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session start proxy error:", e)
        return jsonify({"error": "Failed to start session"}), 500

@app.route("/api/session/pause", methods=["POST"])
def api_session_pause():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("POST", "/session/pause", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session pause proxy error:", e)
        return jsonify({"error": "Failed to pause session"}), 500

@app.route("/api/session/resume", methods=["POST"])
def api_session_resume():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("POST", "/session/resume", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session resume proxy error:", e)
        return jsonify({"error": "Failed to resume session"}), 500

@app.route("/api/session/stop", methods=["POST"])
def api_session_stop():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("POST", "/session/stop", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("Session stop proxy error:", e)
        return jsonify({"error": "Failed to stop session"}), 500
    
@app.route("/api/sessions/<session_id>/export")
def api_export_session(session_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        res = proxy_engine_request("GET", f"/session/{session_id}/export", timeout=60)

        if not res.ok:
            return jsonify({
                "error": "Export failed",
                "details": res.text[:500]
            }), res.status_code

        return Response(
            res.content,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="session_{session_id}.pdf"'
            }
        )

    except Exception as e:
        print("Export proxy error:", e)
        return jsonify({"error": "Export failed"}), 500

    
@app.route("/api/sessions/delete", methods=["POST"])
def api_delete_sessions():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "ids" not in data:
        return jsonify({"error": "No session IDs provided"}), 400

    ids = data["ids"]

    try:
        for sid in ids:
            res = proxy_engine_request("DELETE", f"/session/{sid}", timeout=3)
            if not res.ok:
                return jsonify({"error": "Delete failed"}), res.status_code

        return jsonify({"deleted": ids}), 200

    except Exception as e:
        print("Delete proxy error:", e)
        return jsonify({"error": "Delete failed"}), 500

# logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Route for the ESP32 to send data to
@app.route('/update-sensor', methods=['POST'])
def update_sensor():
    """Receives sensor data from the ESP32 via a POST request."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    # Update the global sensor_data dictionary with new values
    for key in sensor_data.keys():
        if key in data:
            sensor_data[key] = data[key]

    print(f"Received data: {sensor_data}") # Log received data to the console
    return jsonify({"status": "success", "message": "Data received"}), 200

# Route for the dashboard's JavaScript to fetch data from
@app.route('/sensor-data')
def get_sensor_data():
    """Provides the latest sensor data to the frontend."""
    return jsonify(sensor_data)

# Run the app
if __name__ == '__main__':
    # Running on 0.0.0.0 makes the server accessible from other devices on your network
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
