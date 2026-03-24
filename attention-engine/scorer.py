from config import (
    EYE_CLOSED_THRESH,
    YAW_AWAY_THRESH,
    PENALTY_EYES_CLOSED,
    PENALTY_LOOKING_AWAY
)

def clamp(value, min_val=0.0, max_val=1.0):
    return max(min_val, min(max_val, value))


def compute_camera_score(features):
    """
    Returns normalized camera score (0–1)
    """
    if features is None:
        return 0.0

    eye = features.get("eye_open", 1.0)
    yaw = abs(features.get("yaw", 0.0))
    if eye < EYE_CLOSED_THRESH * 0.4 or yaw > 40:
        return 0.0
    
    score = 100

    # Eyes closed / drowsy
    eye = features.get("eye_open", 1.0)

    if eye < EYE_CLOSED_THRESH:
        eye_ratio = 1 - (eye / EYE_CLOSED_THRESH)
        score -= eye_ratio * PENALTY_EYES_CLOSED

    # Looking away
    yaw = abs(features.get("yaw", 0.0))
    yaw_ratio = min(yaw / 45, 1.0)  # normalize
    score -= yaw_ratio * PENALTY_LOOKING_AWAY

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
    humidity = sensor_data.get("humidity", 50)

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

    # --- HUMIDITY (too high → sleepy) ---
    if humidity > 70:
        score -= 0.1

    return clamp(score)


def compute_attention(features, sensor_data=None, prev_score=None):
    """
    Final attention score (0–100)

    features: dict with keys 'eye_open', 'yaw'
    sensor_data: dict with environmental values
    prev_score: previous frame score (for smoothing)
    """

    camera_score = compute_camera_score(features)
    if camera_score > 0:
        camera_score = max(camera_score, 0.1)
    sensor_score = compute_sensor_score(sensor_data)

    fused_score = (camera_score ** 0.7) * (sensor_score ** 0.3)
    fused_score = max(fused_score, 0.1)

    #SMOOTHING 
    if prev_score is not None:
        prev_norm = prev_score / 100.0
        fused_score = (0.85 * prev_norm) + (0.15 * fused_score)

    # Convert back to 0–100
    final_score = int(clamp(fused_score) * 100)

    return final_score