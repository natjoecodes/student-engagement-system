from datetime import datetime
from database import get_connection

def log_attention(session_id, attention, eye_open, yaw):
    if not session_id:
        return

    conn = get_connection()
    conn.execute("""
        INSERT INTO attention_logs
        VALUES (?, ?, ?, ?, ?)
    """, (
        session_id,
        datetime.now().isoformat(),
        attention,
        eye_open,
        yaw
    ))
    conn.commit()
    conn.close()