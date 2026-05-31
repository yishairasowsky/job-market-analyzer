"""
Job Market Analyzer — Web Interface

Reads the latest pre-generated report and outreach files and displays them
at a public URL. No live API calls on the server.

Run locally:
  python app.py

Deploy on Render: see render.yaml
"""

import os
from pathlib import Path
from flask import Flask, render_template

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
OUTREACH_DIR = BASE_DIR / "outreach"


def _latest_file(folder):
    """Return the content of the most recently generated file in a folder."""
    if not folder.exists():
        return None, None
    files = sorted(folder.glob("*.txt"), reverse=True)
    if not files:
        return None, None
    path = files[0]
    # Date is the filename stem after the underscore: report_2026-05-31 -> 2026-05-31
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
