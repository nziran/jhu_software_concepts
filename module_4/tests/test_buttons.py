import threading
import pytest


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

    # Replace threading.Thread in src.app with our dummy
    monkeypatch.setattr(threading, "Thread", DummyThread)

    resp = client.post(
        "/pull-data",
        headers={"Accept": "application/json"},
    )

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

    # Force the app into "busy" state
    import src.app as appmod
    appmod.job_running = True

    started = {"called": False}

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            started["called"] = True

    monkeypatch.setattr(threading, "Thread", DummyThread)

    resp = client.post(
        "/pull-data",
        headers={"Accept": "application/json"},
    )

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
        import src.app as appmod

    # ensure not busy
    appmod.job_running = False

    # mock analysis refresh to avoid DB dependency
    monkeypatch.setattr(appmod, "get_analysis_results", lambda: [{"id": "QX", "question": "q", "answer": "a"}])

    resp = client.post(
        "/update-analysis",
        headers={"Accept": "application/json"},
    )

    assert resp.status_code == 200
    assert resp.is_json
    assert resp.get_json() == {"ok": True}

@pytest.mark.buttons
def test_post_update_analysis_returns_409_when_busy(monkeypatch, client):
    import src.app as appmod

    appmod.job_running = True

    # If update ran, it would call get_analysis_results; ensure it doesn't
    called = {"ran": False}
    monkeypatch.setattr(appmod, "get_analysis_results", lambda: called.__setitem__("ran", True))

    resp = client.post(
        "/update-analysis",
        headers={"Accept": "application/json"},
    )

    assert resp.status_code == 409
    assert resp.is_json
    assert resp.get_json() == {"busy": True}
    assert called["ran"] is False

    appmod.job_running = False