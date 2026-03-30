import atexit
import traceback
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from database import init_db, get_connection
from session_manager import SessionManager
from logger import log_attention
from attention_engine import AttentionEngine
from report_generator import generate_session_report

app = Flask(__name__)
CORS(app)

init_db()
session_manager = SessionManager()
engine = AttentionEngine()
atexit.register(engine.stop_capture)

@app.route("/attention")
def attention():
    try:
        result = engine.get_attention()
        attention_value = result["attention"]

        if attention_value is not None and session_manager.active_session_id:
            session_manager.add_attention(attention_value)
            log_attention(
                session_manager.active_session_id,
                attention_value,
                result["eye_open"],
                result["yaw"]
            )

        return jsonify(result)

    except Exception as e:
        print("Attention error:", e)
        return jsonify({
            "attention": None,
            "eye_open": 0,
            "yaw": 0,
            "camera_active": False
        }), 500

@app.route("/session/start", methods=["POST"])
def start_session():
    if session_manager.active_session_id:
        return jsonify({
            "error": "Session already active",
            **session_manager.get_session_state(),
            "camera_active": engine.is_capture_active()
        }), 400

    data = request.get_json(silent=True) or {}
    subject = data.get("subject", "Unknown")
    faculty = data.get("faculty", "—")

    if not engine.start_capture():
        return jsonify({"error": "Camera could not be opened"}), 500

    try:
        sid = session_manager.start_session(subject, faculty)
    except Exception as e:
        engine.stop_capture()
        print("Session start error:", e)
        return jsonify({"error": "Failed to start session"}), 500

    return jsonify({"session_id": sid, "camera_active": True})

@app.route("/session/pause", methods=["POST"])
def pause_session():
    sid = session_manager.pause_session()
    if sid is None:
        return jsonify({"error": "No active session"}), 400

    engine.pause_capture()
    return jsonify({
        "paused_session": sid,
        "camera_active": False
    })

@app.route("/session/resume", methods=["POST"])
def resume_session():
    if session_manager.active_session_id is None:
        return jsonify({"error": "No active session"}), 400

    if engine.is_capture_active():
        return jsonify({
            "resumed_session": session_manager.active_session_id,
            "camera_active": True
        })

    if not engine.start_capture():
        return jsonify({"error": "Camera could not be reopened"}), 500

    sid = session_manager.resume_session()
    return jsonify({
        "resumed_session": sid,
        "camera_active": True
    })

@app.route("/session/stop", methods=["POST"])
def stop_session():
    sid = session_manager.stop_session()
    if sid is None:
        engine.stop_capture()
        return jsonify({"error": "No active session"}), 400

    engine.stop_capture()
    return jsonify({"stopped_session": sid, "camera_active": False})

@app.route("/session/state")
def session_state():
    state = session_manager.get_session_state()
    state["camera_active"] = engine.is_capture_active()
    return jsonify(state)

@app.route("/sessions")
def list_sessions():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, subject, faculty, start_time, end_time
            FROM sessions
            ORDER BY start_time DESC
            """
        ).fetchall()

    return jsonify([
        {
            "id": r[0],
            "subject": r[1],
            "faculty": r[2],
            "start_time": r[3],
            "end_time": r[4]
        }
        for r in rows
    ])

@app.route("/session/<session_id>/export")
def export_session_pdf(session_id):
    try:
        with get_connection() as conn:
            session_row = conn.execute(
                """
                SELECT id, subject, faculty, start_time, end_time, avg_attention, peak_attention
                FROM sessions
                WHERE id = ?
                """,
                (session_id,)
            ).fetchone()

            if not session_row:
                return jsonify({"error": "Session not found"}), 404

            log_rows = conn.execute(
                """
                SELECT timestamp, attention, eye_open, yaw
                FROM attention_logs
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,)
            ).fetchall()

        buffer = generate_session_report(session_row, log_rows)

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"session_{session_row[0]}.pdf"
        )
    except Exception as e:
        print("Export generation error:", e)
        traceback.print_exc()
        return jsonify({"error": "Export generation failed"}), 500

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
