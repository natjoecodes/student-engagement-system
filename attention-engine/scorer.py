from config import (
    EYE_CLOSED_THRESH,
    YAW_AWAY_THRESH,
    PENALTY_EYES_CLOSED,
    PENALTY_LOOKING_AWAY
)

def compute_attention(features):
    """
    features: dict with keys 'eye_open', 'yaw'
    returns: int attention score 0–100
    """

    # No face / no features → no attention
    if features is None:
        return 0

    score = 100

    # Eyes closed / drowsy
    if features["eye_open"] < EYE_CLOSED_THRESH:
        score -= PENALTY_EYES_CLOSED

    # Looking away
    if abs(features["yaw"]) > YAW_AWAY_THRESH:
        score -= PENALTY_LOOKING_AWAY

    # Clamp
    score = max(0, min(100, score))
    return score