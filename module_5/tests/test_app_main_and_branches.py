"""
Tests for app main execution and update pipeline branch behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
import subprocess

import pytest

# Ensure src/ is importable for pylint
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import src.app as appmod  # pylint: disable=wrong-import-position


@pytest.mark.web
def test_main_calls_flask_run(monkeypatch):
    called = {"ran": False}
    monkeypatch.setattr(
        appmod.app,
        "run",
        lambda *args, **kwargs: called.__setitem__("ran", True),
    )

    appmod.main()
    assert called["ran"] is True


@pytest.mark.buttons
def test_run_update_pipeline_success_without_inserted_match(monkeypatch):
    appmod.job_running = False

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: "no inserted line here")

    appmod.run_update_pipeline()
    assert "Update completed successfully" in appmod.job_last_message


@pytest.mark.buttons
def test_run_update_pipeline_generic_exception(monkeypatch):
    appmod.job_running = False

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(subprocess, "run", boom)

    appmod.run_update_pipeline()
    assert "Update crashed" in appmod.job_last_message
