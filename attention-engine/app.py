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

@app.route("/session/start", methods=["POST"])
def start_session():
    subject = request.json.get("subject", "Unknown")
    sid = session_manager.start_session(subject)
    return jsonify({"session_id": sid})

@app.route("/session/stop", methods=["POST"])
def stop_session():
    sid = session_manager.stop_session()
    return jsonify({"stopped_session": sid})

@app.route("/sessions")
def list_sessions():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY start_time DESC"
    ).fetchall()
    conn.close()
    return jsonify(rows)

@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM attention_logs WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": session_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)