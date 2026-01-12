from flask import Flask, jsonify, render_template, request, redirect, session
from flask_cors import CORS

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
    app.run(host='0.0.0.0', port=5000, debug=True)
