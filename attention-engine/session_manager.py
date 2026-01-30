import uuid
from datetime import datetime
from database import get_connection

class SessionManager:
    def __init__(self):
        self.active_session_id = None
        self.attention_values = []

    def start_session(self, subject, faculty):
        if self.active_session_id is not None:
            raise RuntimeError("Session already running")

        self.active_session_id = str(uuid.uuid4())
        self.attention_values = []

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO sessions (id, start_time, subject, faculty)
            VALUES (?, ?, ?, ?)
            """,
            (
                self.active_session_id,
                datetime.now().isoformat(),
                subject,
                faculty
            )
        )
        conn.commit()
        conn.close()

        return self.active_session_id

    def add_attention(self, value):
        if self.active_session_id:
            self.attention_values.append(value)

    def stop_session(self):
        if self.active_session_id is None:
            return None

        avg_attention = (
            sum(self.attention_values) / len(self.attention_values)
            if self.attention_values else 0
        )
        peak_attention = max(self.attention_values, default=0)

        conn = get_connection()
        conn.execute("""
            UPDATE sessions
            SET end_time=?, avg_attention=?, peak_attention=?
            WHERE id=?
        """, (
            datetime.now().isoformat(),
            avg_attention,
            peak_attention,
            self.active_session_id
        ))
        conn.commit()
        conn.close()

        sid = self.active_session_id
        self.active_session_id = None
        self.attention_values = []

        return sid