import pytest


@pytest.mark.web
def test_main_calls_flask_run(monkeypatch):
    import src.app as appmod

    called = {"ran": False}
    monkeypatch.setattr(appmod.app, "run", lambda *a, **k: called.__setitem__("ran", True))

    appmod.main()
    assert called["ran"] is True


@pytest.mark.buttons
def test_run_update_pipeline_success_without_inserted_match(monkeypatch):
    import src.app as appmod
    import subprocess
    from pathlib import Path

    appmod.job_running = False

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: "no inserted line here")

    appmod.run_update_pipeline()
    assert "Update completed successfully" in appmod.job_last_message


@pytest.mark.buttons
def test_run_update_pipeline_generic_exception(monkeypatch):
    import src.app as appmod
    import subprocess

    appmod.job_running = False

    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(subprocess, "run", boom)

    appmod.run_update_pipeline()
    assert "Update crashed" in appmod.job_last_message