import atexit
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import init_db, get_connection
from session_manager import SessionManager
from logger import log_attention
from attention_engine import AttentionEngine

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
        return jsonify({"error": "Session already active"}), 400

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
    if session_manager.active_session_id is None:
        return jsonify({"error": "No active session"}), 400

    engine.pause_capture()
    return jsonify({
        "paused_session": session_manager.active_session_id,
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

    return jsonify({
        "resumed_session": session_manager.active_session_id,
        "camera_active": True
    })

@app.route("/session/stop", methods=["POST"])
def stop_session():
    sid = session_manager.stop_session()
    engine.stop_capture()
    return jsonify({"stopped_session": sid, "camera_active": False})

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

    sid, subject, faculty, start_time, end_time, avg_attention, peak_attention = session_row

    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None

    duration_text = "N/A"
    if start_dt and end_dt:
        duration_minutes = round((end_dt - start_dt).total_seconds() / 60, 2)
        duration_text = f"{duration_minutes} min"

    sample_count = len(log_rows)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 60
    line_gap = 24

    pdf.setTitle(f"Session Summary - {sid}")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "Session Summary")
    y -= 40

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Session ID: {sid}")
    y -= line_gap
    pdf.drawString(50, y, f"Subject: {subject or 'N/A'}")
    y -= line_gap
    pdf.drawString(50, y, f"Faculty: {faculty or 'N/A'}")
    y -= line_gap
    pdf.drawString(50, y, f"Start Time: {start_time or 'N/A'}")
    y -= line_gap
    pdf.drawString(50, y, f"End Time: {end_time or 'N/A'}")
    y -= line_gap
    pdf.drawString(50, y, f"Duration: {duration_text}")
    y -= line_gap
    pdf.drawString(50, y, f"Average Attention: {round(avg_attention or 0, 2)}")
    y -= line_gap
    pdf.drawString(50, y, f"Peak Attention: {round(peak_attention or 0, 2)}")
    y -= line_gap
    pdf.drawString(50, y, f"Attention Samples: {sample_count}")
    y -= 36

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Recent Attention Logs")
    y -= 28

    pdf.setFont("Helvetica", 10)

    if not log_rows:
        pdf.drawString(50, y, "No attention logs available for this session.")
    else:
        for ts, attention, eye_open, yaw in log_rows[:20]:
            line = (
                f"{ts} | attention={round(attention or 0, 2)} | "
                f"eye_open={round(eye_open or 0, 2)} | yaw={round(yaw or 0, 2)}"
            )
            pdf.drawString(50, y, line[:110])
            y -= 18

            if y < 60:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica", 10)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"session_{sid}.pdf"
    )

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
