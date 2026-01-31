import time
import random
import requests

SERVER_URL = "http://127.0.0.1:5000/update-sensor"

def generate_sensor_data():
    return {
        "temperature": round(random.uniform(24.0, 30.0), 1),   # °C
        "humidity": round(random.uniform(40.0, 70.0), 1),      # %
        "light": random.randint(200, 600),                     # lux
        "noise": random.randint(25, 55),                       # dB
        "co2": random.randint(500, 1200)                       # ppm
    }

print("🚀 Fake sensor started (Ctrl+C to stop)")

while True:
    data = generate_sensor_data()

    try:
        res = requests.post(SERVER_URL, json=data, timeout=2)
        print("📡 Sent:", data)
    except Exception as e:
        print("❌ Failed to send data:", e)

    time.sleep(3)