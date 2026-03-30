import uuid
from datetime import datetime
from database import get_connection

class SessionManager:
    def __init__(self):
        self.active_session_id = None
        self.active_session_status = None
        self.recover_active_session()

    def _get_session_metrics(self, session_id):
        conn = get_connection()
        row = conn.execute(
            """
            SELECT AVG(attention), MAX(attention), MAX(timestamp)
            FROM attention_logs
            WHERE session_id=?
            """,
            (session_id,)
        ).fetchone()
        conn.close()

        avg_attention = row[0] if row and row[0] is not None else 0
        peak_attention = row[1] if row and row[1] is not None else 0
        last_timestamp = row[2] if row and row[2] is not None else None
        return avg_attention, peak_attention, last_timestamp

    def _finalize_session(self, session_id, end_time=None):
        avg_attention, peak_attention, last_timestamp = \
            self._get_session_metrics(session_id)

        final_end_time = end_time or last_timestamp or datetime.now().isoformat()

        conn = get_connection()
        conn.execute(
            """
            UPDATE sessions
            SET end_time=?, avg_attention=?, peak_attention=?, status='stopped'
            WHERE id=?
            """,
            (
                final_end_time,
                avg_attention,
                peak_attention,
                session_id
            )
        )
        conn.commit()
        conn.close()

    def recover_active_session(self):
        conn = get_connection()
        open_rows = conn.execute(
            """
            SELECT id, status
            FROM sessions
            WHERE end_time IS NULL
            ORDER BY start_time DESC
            """
        ).fetchall()
        conn.close()

        if not open_rows:
            self.active_session_id = None
            self.active_session_status = None
            return None

        latest_id, latest_status = open_rows[0]

        for stale_id, _ in open_rows[1:]:
            self._finalize_session(stale_id)

        # After a process restart, recover any open session in a safe paused state.
        if latest_status != "paused":
            conn = get_connection()
            conn.execute(
                "UPDATE sessions SET status='paused' WHERE id=?",
                (latest_id,)
            )
            conn.commit()
            conn.close()
            latest_status = "paused"

        self.active_session_id = latest_id
        self.active_session_status = latest_status
        return latest_id

    def start_session(self, subject, faculty):
        if self.active_session_id is not None:
            raise RuntimeError("Session already running")

        self.active_session_id = str(uuid.uuid4())
        self.active_session_status = "active"

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO sessions (id, start_time, subject, faculty, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.active_session_id,
                datetime.now().isoformat(),
                subject,
                faculty,
                self.active_session_status
            )
        )
        conn.commit()
        conn.close()

        return self.active_session_id

    def add_attention(self, value):
        return None

    def pause_session(self):
        if self.active_session_id is None:
            return None

        self.active_session_status = "paused"

        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET status='paused' WHERE id=?",
            (self.active_session_id,)
        )
        conn.commit()
        conn.close()

        return self.active_session_id

    def resume_session(self):
        if self.active_session_id is None:
            return None

        self.active_session_status = "active"

        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET status='active' WHERE id=?",
            (self.active_session_id,)
        )
        conn.commit()
        conn.close()

        return self.active_session_id

    def get_session_state(self):
        if self.active_session_id is None:
            return {
                "session_id": None,
                "status": "stopped",
                "subject": None,
                "faculty": None,
                "start_time": None
            }

        conn = get_connection()
        row = conn.execute(
            """
            SELECT subject, faculty, start_time, status
            FROM sessions
            WHERE id=?
            """,
            (self.active_session_id,)
        ).fetchone()
        conn.close()

        return {
            "session_id": self.active_session_id,
            "status": row[3] if row and row[3] else self.active_session_status,
            "subject": row[0] if row else None,
            "faculty": row[1] if row else None,
            "start_time": row[2] if row else None
        }

    def stop_session(self):
        if self.active_session_id is None:
            return None

        sid = self.active_session_id
        self._finalize_session(sid)
        self.active_session_id = None
        self.active_session_status = None

        return sid
