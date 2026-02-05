# app.py
from flask import Flask, render_template, redirect, url_for, flash
import subprocess
import sys
import threading
from pathlib import Path
from query_data import get_analysis_cards
import re
from datetime import datetime

last_analysis_at = None

app = Flask(__name__)
app.secret_key = "dev"  # fine for class; needed for flash messages

# -------------------------
# Part B: subprocess job state
# -------------------------
job_lock = threading.Lock()
job_running = False
job_last_message = "No update run yet."
job_log_path = Path("update_job.log")

# Your update pipeline scripts (must exist in module_3)
SCRAPE_CMD = [sys.executable, "scrape_update.py"]
CLEAN_CMD  = [sys.executable, "clean_update.py"]
LOAD_CMD   = [sys.executable, "load_update.py"]  # your loader that inserts into postgres


def run_update_pipeline():
    """
    Runs scrape -> clean -> load as subprocesses.
    Writes stdout/stderr to update_job.log.
    Sets global job state so UI can block buttons while running.
    """
    global job_running, job_last_message

    with job_lock:
        if job_running:
            return
        job_running = True
        job_last_message = "Update started..."
        job_log_path.write_text("", encoding="utf-8")  # clear prior log

    try:
        with job_log_path.open("a", encoding="utf-8") as log:

            def run_one(cmd, label):
                print(f"\n--- {label}: {' '.join(cmd)} ---\n", file=log, flush=True)
                # check=True raises if exit code nonzero (good for catching errors)
                subprocess.run(cmd, stdout=log, stderr=log, text=True, check=True)

            run_one(SCRAPE_CMD, "SCRAPE")
            run_one(CLEAN_CMD, "CLEAN")
            run_one(LOAD_CMD, "LOAD")

            # After LOAD finishes, parse how many rows were inserted from the log
            log.flush()
            text = job_log_path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"Inserted\s+(\d+)\s+new rows", text)
            inserted = int(m.group(1)) if m else None

        if inserted is None:
            job_last_message = "✅ Update completed successfully. (Inserted count not found)"
        else:
            job_last_message = f"✅ Update completed successfully. Inserted {inserted} new rows."

    except subprocess.CalledProcessError:
        job_last_message = "❌ Update failed. Check update_job.log for details."
    except Exception as e:
        job_last_message = f"❌ Update crashed: {e}"
    finally:
        with job_lock:
            job_running = False


# -------------------------
# Your existing analysis logic
# -------------------------
def get_analysis_results():
    return get_analysis_cards()

@app.route("/")
@app.route("/analysis")
def analysis():
    cards = get_analysis_results()
    return render_template(
    "index.html",
    cards=cards,
    job_running=job_running,
    job_last_message=job_last_message,
    last_analysis_at=last_analysis_at,
)


@app.route("/pull-data", methods=["POST"])
def pull_data():
    global job_running

    with job_lock:
        if job_running:
            flash("Pull Data is already running. Please wait for it to finish.")
            return redirect(url_for("analysis"))

        # start background thread so Flask request returns immediately
        t = threading.Thread(target=run_update_pipeline, daemon=True)
        t.start()

    flash("Pull Data started. This may take a few minutes. Check update_job.log for progress.")
    return redirect(url_for("analysis"))


@app.route("/update-analysis", methods=["POST"])
def update_analysis():
    global last_analysis_at

    if job_running:
        flash("Cannot update analysis while Pull Data is running.")
        return redirect(url_for("analysis"))

    # Mark that analysis was explicitly refreshed
    last_analysis_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    flash("Analysis refreshed.")
    return redirect(url_for("analysis"))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)