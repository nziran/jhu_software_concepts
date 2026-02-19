import pytest
import subprocess


@pytest.mark.buttons
def test_run_update_pipeline_success_sets_message(monkeypatch):
    import src.app as appmod
    from pathlib import Path

    appmod.job_running = False
    appmod.job_last_message = "No update run yet."

    # fake subprocess success
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: None
    )

    # fake log contents (patch class method)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *args, **kwargs: "Inserted 5 new rows"
    )

    appmod.run_update_pipeline()

    assert appmod.job_running is False
    assert "Update completed successfully" in appmod.job_last_message

@pytest.mark.buttons
def test_run_update_pipeline_failure_sets_failed_message(monkeypatch):
    import src.app as appmod

    appmod.job_running = False
    appmod.job_last_message = "No update run yet."

    def boom(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="x")

    monkeypatch.setattr(subprocess, "run", boom)

    appmod.run_update_pipeline()

    assert appmod.job_running is False
    assert "Update failed" in appmod.job_last_message