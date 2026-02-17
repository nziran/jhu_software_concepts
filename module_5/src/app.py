"""
Flask web application that displays GradCafe analysis results and manages
an update pipeline that pulls new survey data, cleans it, and loads it into
PostgreSQL.

The web interface allows users to:
- View analysis cards generated from the database
- Trigger a background data update (scrape → clean → load)
- Refresh analysis results safely while preventing concurrent updates

Long-running update work is executed in a background thread so the web
interface remains responsive.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from src.query_data import get_analysis_cards

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")  # required for Flask flash messaging

STATE: dict[str, object] = {
    "analysis_cache": [],
    "analysis_last_updated": None,
    "job_running": False,
    "job_last_message": "No update run yet.",
}

JOB_LOCK = threading.Lock()

BASE_DIR = Path(__file__).resolve().parents[1]  # .../module_5
JOB_LOG_PATH = BASE_DIR / "update_job.log"

SCRIPT_DIR = BASE_DIR / "src"
SCRAPE_CMD = [sys.executable, str(SCRIPT_DIR / "scrape_update.py")]
CLEAN_CMD = [sys.executable, str(SCRIPT_DIR / "clean_update.py")]
LOAD_CMD = [sys.executable, str(SCRIPT_DIR / "load_update.py")]


def wants_json() -> bool:
    """Return True if the client prefers JSON responses."""
    return request.accept_mimetypes.best == "application/json"


def run_update_pipeline() -> None:
    """
    Execute the scrape → clean → load pipeline as subprocesses.

    Output from each stage is written to a log file. While running, job state is
    updated so the UI can prevent overlapping update requests.
    """
    with JOB_LOCK:
        if STATE["job_running"]:
            return
        STATE["job_running"] = True
        STATE["job_last_message"] = "Update started..."
        JOB_LOG_PATH.write_text("", encoding="utf-8")

    try:
        with JOB_LOG_PATH.open("a", encoding="utf-8") as log:

            def run_one(cmd: list[str], label: str) -> None:
                """Run a pipeline stage and log its output."""
                print(f"\n--- {label}: {' '.join(cmd)} ---\n", file=log, flush=True)
                subprocess.run(cmd, stdout=log, stderr=log, text=True, check=True)

            run_one(SCRAPE_CMD, "SCRAPE")
            run_one(CLEAN_CMD, "CLEAN")
            run_one(LOAD_CMD, "LOAD")

            log.flush()
            text = JOB_LOG_PATH.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"Inserted\s+(\d+)\s+new rows", text)
            inserted = int(match.group(1)) if match else None

        if inserted is None:
            STATE["job_last_message"] = "✅ Update completed successfully."
        else:
            STATE["job_last_message"] = (
                f"✅ Update completed successfully. Inserted {inserted} new rows."
            )

    except subprocess.CalledProcessError:
        STATE["job_last_message"] = "❌ Update failed. Check update_job.log."
    except Exception as exc:  # pylint: disable=broad-exception-caught
        STATE["job_last_message"] = f"❌ Update crashed: {exc}"
    finally:
        with JOB_LOCK:
            STATE["job_running"] = False


def get_analysis_results():
    """Retrieve formatted analysis cards from the database."""
    return get_analysis_cards()


@app.route("/")
@app.route("/analysis")
def analysis():
    """Render the analysis page with cached analysis and job status."""
    if not STATE["analysis_cache"]:
        STATE["analysis_cache"] = get_analysis_cards()

    return render_template(
        "index.html",
        cards=STATE["analysis_cache"],
        job_running=STATE["job_running"],
        job_last_message=STATE["job_last_message"],
        analysis_last_updated=STATE["analysis_last_updated"],
    )


@app.route("/pull-data", methods=["POST"])
def pull_data():
    """Start background update pipeline if not already running."""
    with JOB_LOCK:
        if STATE["job_running"]:
            if wants_json():
                return jsonify(busy=True), 409
            flash("Pull Data is already running.")
            return redirect(url_for("analysis"))

        t = threading.Thread(target=run_update_pipeline, daemon=True)
        t.start()

    if wants_json():
        return jsonify(ok=True), 202

    flash("Pull Data started. Check status below.")
    return redirect(url_for("analysis"))


@app.route("/update-analysis", methods=["POST"])
def update_analysis():
    """Refresh cached analysis snapshot unless an update job is running."""
    if STATE["job_running"]:
        if wants_json():
            return jsonify(busy=True), 409
        flash("Cannot update analysis while Pull Data is running.")
        return redirect(url_for("analysis"))

    STATE["analysis_cache"] = get_analysis_results()
    STATE["analysis_last_updated"] = datetime.now()

    if wants_json():
        return jsonify(ok=True), 200

    flash("Analysis refreshed.")
    return redirect(url_for("analysis"))


def create_app() -> Flask:
    """Flask app factory hook for tests and WSGI usage."""
    return app


def main() -> None:
    """Entry point for running the Flask app locally."""
    if os.getenv("APP_DRY_RUN") == "1":
        print("APP_DRY_RUN: skipping app.run()")
        return

    app.run(debug=True, use_reloader=False, port=5050)


if __name__ == "__main__":
    main()
