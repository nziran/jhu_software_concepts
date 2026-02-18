"""
Tests for small helper functions in the Flask app.
"""

import pytest
import src.app as appmod


@pytest.mark.web
def test_get_analysis_results_calls_query_function(monkeypatch):
    fake_cards = [{"id": "Q1", "question": "q", "answer": "a"}]

    monkeypatch.setattr(appmod, "get_analysis_cards", lambda: fake_cards)

    result = appmod.get_analysis_results()

    assert result == fake_cards
