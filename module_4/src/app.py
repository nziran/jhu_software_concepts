"""
app.py

Flask web application that displays GradCafe analysis results and manages
an update pipeline that pulls new survey data, cleans it, and loads it
into PostgreSQL.

The web interface allows users to:

• View live analysis cards generated from the database
• Trigger a background data update (scrape → clean → load)
• Refresh analysis results safely while preventing concurrent updates

Long-running update work is executed in a background thread so the web
interface remains responsive.
"""

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
import subprocess
import sys
import threading
from pathlib import Path
from src.query_data import get_analysis_cards
import re
from datetime import datetime
import os

# Cached analysis results + timestamp
analysis_cache = []
analysis_last_updated = None

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev") # required for Flask flash messaging

def wants_json():
    return request.accept_mimetypes.best == "application/json"


# ----------------------------------------------------------
# Background update job state tracking
# ----------------------------------------------------------
# These globals track whether a data update pipeline is running
# so the UI can block duplicate requests.

job_lock = threading.Lock()
job_running = False
job_last_message = "No update run yet."

BASE_DIR = Path(__file__).resolve().parent  # .../module_4/src

job_log_path = BASE_DIR / "update_job.log"

SCRAPE_CMD = [sys.executable, str(BASE_DIR / "scrape_update.py")]
CLEAN_CMD  = [sys.executable, str(BASE_DIR / "clean_update.py")]
LOAD_CMD   = [sys.executable, str(BASE_DIR / "load_update.py")]


def run_update_pipeline():
    """
    Executes the scrape → clean → load pipeline as subprocesses.

    Output from each stage is written to a log file.
    While running, global job state is updated so the UI can prevent
    overlapping update requests.
    """
    global job_running, job_last_message

    # Prevent concurrent runs
    with job_lock:
        if job_running:
            return
        job_running = True
        job_last_message = "Update started..."
        job_log_path.write_text("", encoding="utf-8")

    try:
        with job_log_path.open("a", encoding="utf-8") as log:

            def run_one(cmd, label):
                """Run a pipeline stage and log its output."""
                print(f"\n--- {label}: {' '.join(cmd)} ---\n", file=log, flush=True)
                subprocess.run(cmd, stdout=log, stderr=log, text=True, check=True)

            run_one(SCRAPE_CMD, "SCRAPE")
            run_one(CLEAN_CMD, "CLEAN")
            run_one(LOAD_CMD, "LOAD")

            # Parse inserted row count from log output
            log.flush()
            text = job_log_path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"Inserted\s+(\d+)\s+new rows", text)
            inserted = int(m.group(1)) if m else None

        if inserted is None:
            job_last_message = "✅ Update completed successfully."
        else:
            job_last_message = f"✅ Update completed successfully. Inserted {inserted} new rows."

    except subprocess.CalledProcessError:
        job_last_message = "❌ Update failed. Check update_job.log."
    except Exception as e:
        job_last_message = f"❌ Update crashed: {e}"
    finally:
        with job_lock:
            job_running = False
            print("DEBUG: job_running reset to False")


# ----------------------------------------------------------
# Analysis data retrieval
# ----------------------------------------------------------
def get_analysis_results():
    """
    Retrieves formatted analysis cards from the database.
    """
    return get_analysis_cards()


# ----------------------------------------------------------
# Routes
# ----------------------------------------------------------
@app.route("/")
@app.route("/analysis")
def analysis():
    global analysis_cache

    # Fill cache once on first page load only.
    # This does NOT auto-refresh later; it just prevents a blank page on startup.
    if not analysis_cache:
        analysis_cache = get_analysis_cards()

    return render_template(
        "index.html",
        cards=analysis_cache,
        job_running=job_running,
        job_last_message=job_last_message,
        analysis_last_updated=analysis_last_updated,
    )


@app.route("/pull-data", methods=["POST"])
def pull_data():
    """
    Starts background update pipeline if not already running.
    """
    global job_running

    with job_lock:
        if job_running:
            if wants_json():
                return jsonify(busy=True), 409
            flash("Pull Data is already running.")
            return redirect(url_for("analysis"))

        # Launch background thread
        t = threading.Thread(target=run_update_pipeline, daemon=True)
        t.start()

    if wants_json():
        return jsonify(ok=True), 202

    flash("Pull Data started. Check status below.")
    return redirect(url_for("analysis"))



@app.route("/update-analysis", methods=["POST"])
def update_analysis():
    global analysis_last_updated, analysis_cache

    if job_running:
        if wants_json():
            return jsonify(busy=True), 409
        flash("Cannot update analysis while Pull Data is running.")
        return redirect(url_for("analysis"))

    # Refresh cached analysis snapshot
    analysis_cache = get_analysis_results()
    analysis_last_updated = datetime.now()

    if wants_json():
        return jsonify(ok=True), 200

    flash("Analysis refreshed.")
    return redirect(url_for("analysis"))



def create_app():
    return app


def main():
    app.run(debug=True, use_reloader=False, port=5050)


# ----------------------------------------------------------
# Application entry point
# ----------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    main()