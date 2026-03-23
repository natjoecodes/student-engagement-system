from config import (
    EYE_CLOSED_THRESH,
    YAW_AWAY_THRESH,
    PENALTY_EYES_CLOSED,
    PENALTY_LOOKING_AWAY
)

def get_sensor_data():
    try:
        res = requests.get("http://127.0.0.1:5000/sensor-data", timeout=1)
        return res.json()
    except Exception as e:
        print("Sensor fetch error:", e)
        return None

def clamp(value, min_val=0.0, max_val=1.0):
    return max(min_val, min(max_val, value))


def compute_camera_score(features):
    """
    Returns normalized camera score (0–1)
    """
    if features is None:
        return 0.0

    score = 100

    # Eyes closed / drowsy
    if features["eye_open"] < EYE_CLOSED_THRESH:
        score -= PENALTY_EYES_CLOSED

    # Looking away
    if abs(features["yaw"]) > YAW_AWAY_THRESH:
        score -= PENALTY_LOOKING_AWAY

    score = max(0, min(100, score))

    return score / 100.0  # normalize


def compute_sensor_score(sensor_data):
    """
    Returns normalized sensor score (0–1)
    Uses temperature, noise, CO2, light
    """

    if sensor_data is None:
        return 1.0

    temp = sensor_data.get("temperature", 25)
    noise = sensor_data.get("noise", 40)
    co2 = sensor_data.get("co2", 600)
    light = sensor_data.get("light", 400)

    score = 1.0

    # --- TEMPERATURE (stronger impact) ---
    if temp > 28:
        score -= min((temp - 28) * 0.05, 0.5)
    elif temp < 20:
        score -= min((20 - temp) * 0.05, 0.5)

    # --- NOISE (stronger impact) ---
    if noise > 50:
        score -= min((noise - 50) * 0.02, 0.5)

    # --- CO2 (important for drowsiness) ---
    if co2 > 1000:
        score -= min((co2 - 1000) * 0.0005, 0.4)

    # --- LIGHT (too dim → sleepy) ---
    if light < 300:
        score -= min((300 - light) * 0.002, 0.3)

    return clamp(score)


def compute_attention(features, sensor_data=None, prev_score=None):
    """
    Final attention score (0–100)

    features: dict with keys 'eye_open', 'yaw'
    sensor_data: dict with environmental values
    prev_score: previous frame score (for smoothing)
    """

    camera_score = compute_camera_score(features)
    sensor_score = compute_sensor_score(sensor_data)

    fused_score = camera_score * sensor_score

    #SMOOTHING 
    if prev_score is not None:
        prev_norm = prev_score / 100.0
        fused_score = (0.8 * prev_norm) + (0.2 * fused_score)

    # Convert back to 0–100
    final_score = int(clamp(fused_score) * 100)

    return final_score