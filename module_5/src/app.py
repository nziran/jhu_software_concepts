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

import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify

from src.query_data import get_analysis_cards

# Cached analysis results + timestamp
analysis_cache = []
analysis_last_updated = None   # pylint: disable=invalid-name

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev") # required for Flask flash messaging

def wants_json():
    """Return True if client prefers JSON responses."""
    return request.accept_mimetypes.best == "application/json"


# ----------------------------------------------------------
# Background update job state tracking
# ----------------------------------------------------------
# These globals track whether a data update pipeline is running
# so the UI can block duplicate requests.

job_lock = threading.Lock()
job_running = False  # pylint: disable=invalid-name
job_last_message = "No update run yet."  # pylint: disable=invalid-name

BASE_DIR = Path(__file__).resolve().parent  # .../module_4/src

job_log_path = BASE_DIR / "update_job.log"

SCRAPE_CMD = [sys.executable, "-m", "src.scrape_update"]
CLEAN_CMD  = [sys.executable, "-m", "src.clean_update"]
LOAD_CMD   = [sys.executable, "-m", "src.load_update"]


def run_update_pipeline():   # pylint: disable=global-statement
    """
    Executes the scrape → clean → load pipeline as subprocesses.

    Output from each stage is written to a log file.
    While running, global job state is updated so the UI can prevent
    overlapping update requests.
    """
    global job_running, job_last_message  # pylint: disable=global-statement

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
    except Exception as e:   # pylint: disable=broad-exception-caught
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
def analysis():  # pylint: disable=global-statement
    """Render analysis dashboard."""
    global analysis_cache  # pylint: disable=global-statement

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
def pull_data():  # pylint: disable=global-statement
    """"Start background update pipeline."""
    global job_running   # pylint: disable=global-statement,global-variable-not-assigned

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
def update_analysis():  # pylint: disable=global-statement
    """Refresh cached analysis results."""
    global analysis_last_updated, analysis_cache  # pylint: disable=global-statement

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
    """Application factory for testing."""
    return app

def main():
    """Run Flask development server."""
    if os.getenv("APP_DRY_RUN") == "1":
        print("APP_DRY_RUN: skipping app.run()")
        return

    app.run(debug=True, use_reloader=False, port=5050)

# ----------------------------------------------------------
# Application entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
