import sqlite3
from pathlib import Path

DB_PATH = Path("data/sessions.db")

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        start_time TEXT,
        end_time TEXT,
        subject TEXT,
        avg_attention REAL,
        peak_attention REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attention_logs (
        session_id TEXT,
        timestamp TEXT,
        attention REAL,
        eye_open REAL,
        yaw REAL,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)

    conn.commit()
    conn.close()