import pytest


@pytest.mark.web
def test_post_pull_data_html_not_busy_redirects(client):
    """
    Covers the HTML (non-JSON) success path for /pull-data:
    should start thread + redirect (302).
    """
    import src.app as appmod
    import threading

    appmod.job_running = False

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            # do nothing; just prove we got here
            pass

    # patch the Thread used by the module (threading.Thread is what appmod uses)
    pytest.MonkeyPatch().setattr(threading, "Thread", DummyThread)

    resp = client.post("/pull-data")  # no Accept header => HTML path
    assert resp.status_code == 302


@pytest.mark.web
def test_post_update_analysis_html_not_busy_redirects_and_updates(monkeypatch, client):
    """
    Covers the HTML (non-JSON) success path for /update-analysis:
    should refresh analysis_cache + set timestamp + redirect (302).
    """
    import src.app as appmod

    appmod.job_running = False

    monkeypatch.setattr(appmod, "get_analysis_results", lambda: [{"id": "Q1", "question": "q", "answer": "a"}])

    resp = client.post("/update-analysis")  # HTML path
    assert resp.status_code == 302

    assert appmod.analysis_cache  # now non-empty
    assert appmod.analysis_last_updated is not None
