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

    score = 100

    eye = features.get("eye_open", 1.0)
    yaw = abs(features.get("yaw", 0.0))

    # --- Eyes (moderate, non-linear penalty) ---
    if eye < EYE_CLOSED_THRESH:
        eye_ratio = 1 - (eye / EYE_CLOSED_THRESH)
        score -= eye_ratio * PENALTY_EYES_CLOSED
        if eye < (0.75 * EYE_CLOSED_THRESH):
            score -= 8
        if eye < (0.5 * EYE_CLOSED_THRESH):
            score -= 8

    # --- Yaw (moderate penalty after threshold) ---
    yaw_ratio = max(0.0, (yaw - YAW_AWAY_THRESH) / 0.16)
    yaw_ratio = min(yaw_ratio, 1.0)
    score -= yaw_ratio * PENALTY_LOOKING_AWAY
    if yaw > (1.8 * YAW_AWAY_THRESH):
        score -= 5
    if yaw > (2.5 * YAW_AWAY_THRESH):
        score -= 5

    # clamp
    score = max(0, min(100, score))

    return score / 100.0


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

    # Clamping sensor values to reasonable ranges
    temp = max(10, min(temp, 45))
    noise = max(20, min(noise, 120))
    co2 = max(300, min(co2, 5000))
    light = max(0, min(light, 2000))
    humidity = max(10, min(humidity, 100))

    # --- TEMPERATURE (stronger impact) ---
    if temp > 28:
        score -= min((temp - 28) * 0.02, 0.25)
    elif temp < 20:
        score -= min((20 - temp) * 0.05, 0.5)

    # --- NOISE (stronger impact) ---
    if noise > 50:
        score -= min((noise - 50) * 0.01, 0.25)
    # --- CO2 (important for drowsiness) ---
    if co2 > 1000:
        score -= min((co2 - 1000) * 0.0002, 0.2)

    # --- LIGHT (too dim → sleepy) ---
    if light < 300:
        score -= min((300 - light) * 0.001, 0.15)

    # --- HUMIDITY (too high → sleepy) ---
    if humidity > 70:
        score -= 0.05

    return max(0.65, clamp(score))


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

    fused_score = (0.7 * camera_score) + (0.3 * sensor_score)
    fused_score = max(fused_score, 0.1)

    #SMOOTHING 

    if prev_score is not None:
        prev_norm = prev_score / 100.0
        fused_score = (0.6 * prev_norm) + (0.4 * fused_score)

    # Convert back to 0–100
    final_score = int(clamp(fused_score) * 100)

    return final_score
