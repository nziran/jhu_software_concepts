"""Tests for src.app module entry-point behavior."""
import runpy
import pytest


@pytest.mark.web
def test_app_main_guard_runs_without_starting_server(monkeypatch, capsys):
    """Ensure APP_DRY_RUN prevents Flask server startup."""
    monkeypatch.setenv("APP_DRY_RUN", "1")

    # Execute src.app as if "python -m src.app"
    runpy.run_module("src.app", run_name="__main__")

    out = capsys.readouterr().out
    assert "APP_DRY_RUN: skipping app.run()" in out
