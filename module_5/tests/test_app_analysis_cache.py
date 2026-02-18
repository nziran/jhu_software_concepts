"""
Tests for analysis cache behavior in the Flask app.
"""

import pytest
import src.app as appmod


@pytest.mark.web
def test_get_analysis_populates_cache_when_empty(monkeypatch, client):
    # force empty cache branch
    appmod.analysis_cache = []

    monkeypatch.setattr(
        appmod,
        "get_analysis_cards",
        lambda: [{"id": "Q1", "question": "q", "answer": "a"}],
    )

    resp = client.get("/analysis")
    assert resp.status_code == 200
    assert appmod.analysis_cache  # now filled


@pytest.mark.web
def test_get_analysis_does_not_repopulate_cache_when_already_filled(monkeypatch, client):
    # pre-fill cache so branch is skipped
    appmod.analysis_cache = [{"id": "QX", "question": "q", "answer": "a"}]

    called = {"hit": False}
    monkeypatch.setattr(
        appmod,
        "get_analysis_cards",
        lambda: called.__setitem__("hit", True),
    )

    resp = client.get("/analysis")
    assert resp.status_code == 200
    assert called["hit"] is False
