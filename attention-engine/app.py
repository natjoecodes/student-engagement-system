from flask import Flask, jsonify, request
from flask_cors import CORS

from database import init_db, get_connection
from session_manager import SessionManager
from logger import log_attention
from attention_engine import AttentionEngine

app = Flask(__name__)
CORS(app)

init_db()
session_manager = SessionManager()
engine = AttentionEngine()

@app.route("/attention")
def attention():
    try:
        result = engine.get_attention()
        attention_value = result["attention"]

        session_manager.add_attention(attention_value)

        if session_manager.active_session_id:
            log_attention(
                session_manager.active_session_id,
                attention_value,
                result["eye_open"],
                result["yaw"]
            )

        return jsonify({"attention": attention_value})

    except Exception as e:
        print("Attention error:", e)
        return jsonify({"attention": None}), 500

@app.route("/session/start", methods=["POST"])
def start_session():
    if session_manager.active_session_id:
        return jsonify({"error": "Session already active"}), 400
    subject = request.json.get("subject", "Unknown")
    sid = session_manager.start_session(subject)
    return jsonify({"session_id": sid})

@app.route("/session/stop", methods=["POST"])
def stop_session():
    sid = session_manager.stop_session()
    return jsonify({"stopped_session": sid})

@app.route("/sessions")
def list_sessions():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, subject, start_time, end_time FROM sessions ORDER BY start_time DESC"
        ).fetchall()

    return jsonify([
        {
            "id": r[0],
            "subject": r[1],
            "start_time": r[2],
            "end_time": r[3]
        }
        for r in rows
    ])

@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM attention_logs WHERE session_id=?",
            (session_id,)
        )
        conn.execute(
            "DELETE FROM sessions WHERE id=?",
            (session_id,)
        )
        conn.commit()

    return jsonify({"deleted": session_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)