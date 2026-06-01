"""
Job Market Analyzer — Web Interface

Users enter their background and skills, click Run, and watch five AI agents
work in real time. Results stream back live via Server-Sent Events.
"""

import os
import io
import json
import base64
import queue
import threading
from pathlib import Path
from datetime import date
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
OUTREACH_DIR = BASE_DIR / "outreach"


def _latest_file(folder):
    if not folder.exists():
        return None, None
    files = sorted(folder.glob("*.txt"), reverse=True)
    if not files:
        return None, None
    path = files[0]
    date_str = path.stem.split("_", 1)[-1]
    return path.read_text(encoding="utf-8"), date_str


@app.route("/")
def index():
    report, report_date = _latest_file(REPORTS_DIR)
    outreach, outreach_date = _latest_file(OUTREACH_DIR)
    return render_template(
        "index.html",
        report=report,
        report_date=report_date,
        outreach=outreach,
        outreach_date=outreach_date,
    )


@app.route("/parse-resume", methods=["POST"])
def parse_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    f = request.files["resume"]
    filename = f.filename.lower()
    file_bytes = f.read()

    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty."}), 400

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        if filename.endswith(".pdf"):
            # Claude natively reads PDFs — send as base64 document
            pdf_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": _resume_prompt(),
                        }
                    ],
                }]
            )

        elif filename.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": f"{_resume_prompt()}\n\nRESUME TEXT:\n{text[:6000]}"
                }]
            )

        elif filename.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="replace")
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": f"{_resume_prompt()}\n\nRESUME TEXT:\n{text[:6000]}"
                }]
            )

        else:
            return jsonify({"error": "Unsupported file type. Upload a PDF, DOCX, or TXT file."}), 400

        raw = response.content[0].text.strip()

        # Parse the two sections Claude returns
        background, skills = _parse_resume_response(raw)
        return jsonify({"background": background, "skills": skills})

    except Exception as e:
        return jsonify({"error": f"Could not read resume: {str(e)}"}), 500


def _resume_prompt():
    return """Read this resume and extract two things for a job search tool.

Reply in exactly this format (no extra text):

BACKGROUND:
[2-3 sentences: who this person is, what they've built or done, what kind of role they're seeking. Write in first person as if they are describing themselves.]

SKILLS:
[comma-separated list of their technical skills, tools, languages, and frameworks. Keep it concise — 8-15 items max.]"""


def _parse_resume_response(text):
    background, skills = "", ""
    if "BACKGROUND:" in text and "SKILLS:" in text:
        bg_start = text.index("BACKGROUND:") + len("BACKGROUND:")
        sk_start = text.index("SKILLS:")
        background = text[bg_start:sk_start].strip()
        skills = text[sk_start + len("SKILLS:"):].strip()
    else:
        background = text[:400]
    return background, skills


@app.route("/run", methods=["POST"])
def run():
    user_background = request.form.get("background", "").strip()
    user_skills_raw = request.form.get("skills", "").strip()
    user_skills = [s.strip() for s in user_skills_raw.split(",") if s.strip()]
    password = request.form.get("password", "").strip()

    demo_password = os.getenv("DEMO_PASSWORD", "")
    if demo_password and password != demo_password:
        def deny():
            yield _event("error", message="Incorrect password.")
        return Response(stream_with_context(deny()), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    if not user_background:
        def no_bg():
            yield _event("error", message="Please enter your background before running.")
        return Response(stream_with_context(no_bg()), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    q = queue.Queue()

    def run_pipeline():
        from agents.job_collector import collect_jobs
        from agents.funding_detector import detect_funding
        from agents.skills_analyzer import analyze_skills
        from agents.report_writer import write_report
        from agents.outreach_writer import write_outreach

        def cb(agent_num):
            return lambda msg: q.put({"type": "progress", "agent": agent_num, "message": msg})

        try:
            q.put({"type": "agent_start", "agent": 1})
            jobs = collect_jobs(on_progress=cb(1))
            q.put({"type": "agent_done", "agent": 1, "count": len(jobs)})

            q.put({"type": "agent_start", "agent": 2})
            funded = detect_funding(jobs, on_progress=cb(2))
            q.put({"type": "agent_done", "agent": 2, "count": len(funded)})

            q.put({"type": "agent_start", "agent": 3})
            skills_summary = analyze_skills(jobs, user_skills=user_skills or None, on_progress=cb(3))
            q.put({"type": "agent_done", "agent": 3})

            q.put({"type": "agent_start", "agent": 4})
            report = write_report(
                jobs, funded, skills_summary,
                user_background=user_background,
                user_skills=user_skills or None,
                on_progress=cb(4)
            )
            q.put({"type": "agent_done", "agent": 4})

            q.put({"type": "agent_start", "agent": 5})
            outreach = write_outreach(
                jobs, funded,
                user_background=user_background,
                user_skills=user_skills or None,
                on_progress=cb(5)
            )
            q.put({"type": "agent_done", "agent": 5})

            # Save outputs
            today = date.today()
            REPORTS_DIR.mkdir(exist_ok=True)
            OUTREACH_DIR.mkdir(exist_ok=True)
            (REPORTS_DIR / f"report_{today}.txt").write_text(report, encoding="utf-8")
            if outreach:
                (OUTREACH_DIR / f"outreach_{today}.txt").write_text(outreach, encoding="utf-8")

            q.put({"type": "result", "report": report, "outreach": outreach})
            q.put({"type": "done"})

        except Exception as e:
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put(None)  # sentinel

    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                item = q.get(timeout=25)
            except queue.Empty:
                # Keepalive comment — prevents Render's proxy from closing the connection
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield _event(**item)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )


def _event(**kwargs):
    return f"data: {json.dumps(kwargs)}\n\n"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
