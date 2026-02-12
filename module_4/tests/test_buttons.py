import os
import subprocess

import psycopg
import pytest

import src.app as appmod


def _db_count_applicants() -> int:
    db_url = os.environ["DATABASE_URL"]
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            return int(cur.fetchone()[0])


@pytest.mark.buttons
def test_post_pull_data_returns_202_json_when_not_busy(monkeypatch, client):
    """
    POST /pull-data
    - returns 202 with {"ok": true} when not busy (JSON client)
    - does NOT actually run the pipeline (thread is mocked)
    """
    started = {"called": False}

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            # simulate starting background work without running it
            started["called"] = True

    # Patch the Thread used by src.app
    monkeypatch.setattr(appmod.threading, "Thread", DummyThread)

    resp = client.post("/pull-data", headers={"Accept": "application/json"})

    assert resp.status_code == 202
    assert resp.is_json
    assert resp.get_json() == {"ok": True}
    assert started["called"] is True


@pytest.mark.buttons
def test_post_pull_data_returns_409_when_busy(monkeypatch, client):
    """
    When a pull is in progress, POST /pull-data should return 409 {"busy": true}
    for JSON clients, and should not start a new thread.
    """
    appmod.job_running = True

    started = {"called": False}

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            started["called"] = True

    monkeypatch.setattr(appmod.threading, "Thread", DummyThread)

    resp = client.post("/pull-data", headers={"Accept": "application/json"})

    assert resp.status_code == 409
    assert resp.is_json
    assert resp.get_json() == {"busy": True}
    assert started["called"] is False

    # reset for other tests
    appmod.job_running = False


@pytest.mark.buttons
def test_post_update_analysis_returns_200_json_when_not_busy(monkeypatch, client):
    """
    POST /update-analysis
    - returns 200 with {"ok": true} when not busy (JSON client)
    - does not hit the real database (mock get_analysis_results)
    """
    appmod.job_running = False

    # mock analysis refresh to avoid DB dependency
    monkeypatch.setattr(
        appmod,
        "get_analysis_results",
        lambda: [{"id": "QX", "question": "q", "answer": "a"}],
    )

    resp = client.post("/update-analysis", headers={"Accept": "application/json"})

    assert resp.status_code == 200
    assert resp.is_json
    assert resp.get_json() == {"ok": True}


@pytest.mark.buttons
def test_post_update_analysis_returns_409_when_busy(monkeypatch, client):
    appmod.job_running = True

    # If update ran, it would call get_analysis_results; ensure it doesn't
    called = {"ran": False}
    monkeypatch.setattr(appmod, "get_analysis_results", lambda: called.__setitem__("ran", True))

    resp = client.post("/update-analysis", headers={"Accept": "application/json"})

    assert resp.status_code == 409
    assert resp.is_json
    assert resp.get_json() == {"busy": True}
    assert called["ran"] is False

    appmod.job_running = False


@pytest.mark.buttons
@pytest.mark.db
def test_pull_data_failure_sets_message_and_does_not_write_db(client, monkeypatch, tmp_path):
    """
    Failure-path test:
    - /pull-data returns 202 immediately (async design)
    - pipeline fails internally
    - job_running resets False
    - job_last_message indicates failure
    - DB row count does not change (no partial writes)
    """
    # Ensure clean starting state
    appmod.analysis_cache = []
    appmod.analysis_last_updated = None
    appmod.job_last_message = "No update run yet."
    appmod.job_running = False

    before = _db_count_applicants()

    # Keep logs out of your repo during tests
    appmod.job_log_path = tmp_path / "update_job.log"

    captured = {"target": None, "started": False}

    class CaptureThread:
        """Thread stub that captures the target but does NOT run it in start()."""
        def __init__(self, target=None, daemon=None):
            captured["target"] = target
            self.daemon = daemon

        def start(self):
            captured["started"] = True
            # do NOT call target here (avoids deadlock with job_lock)

    monkeypatch.setattr(appmod.threading, "Thread", CaptureThread)

    # Force subprocess.run to fail (simulating a pipeline failure)
    def boom(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="SCRAPE")

    monkeypatch.setattr(appmod.subprocess, "run", boom)

    # 1) Endpoint returns immediately
    resp = client.post("/pull-data", headers={"Accept": "application/json"})
    assert resp.status_code == 202
    assert resp.get_json() == {"ok": True}
    assert captured["started"] is True
    assert callable(captured["target"])

    # 2) Now run the captured "background" work AFTER the request lock is released
    captured["target"]()

    assert appmod.job_running is False
    assert "Update failed" in appmod.job_last_message

    after = _db_count_applicants()
    assert after == before