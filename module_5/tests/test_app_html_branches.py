"""
HTML-branch tests for Flask app routes and pipeline guard behavior.
"""

import subprocess
import pytest

import src.app as appmod


@pytest.mark.web
def test_pull_data_busy_html_redirects_with_flash(client):
    appmod.job_running = True

    resp = client.post("/pull-data")  # no Accept header => HTML branch
    assert resp.status_code == 302  # redirect back to /analysis

    appmod.job_running = False


@pytest.mark.web
def test_update_analysis_busy_html_redirects(client):
    appmod.job_running = True

    resp = client.post("/update-analysis")  # HTML branch
    assert resp.status_code == 302

    appmod.job_running = False


@pytest.mark.buttons
def test_run_update_pipeline_returns_immediately_if_already_running(monkeypatch):
    # force "already running" before calling
    appmod.job_running = True
    before = appmod.job_last_message

    # if it tried to run subprocess we'd know
    called = {"ran": False}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: called.__setitem__("ran", True),
    )

    appmod.run_update_pipeline()

    assert called["ran"] is False
    assert appmod.job_last_message == before

    # cleanup
    appmod.job_running = False
