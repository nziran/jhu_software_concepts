"""Tests for query_data analysis card helpers."""

import pytest

from src.query_data import _db_params, get_analysis_cards


@pytest.mark.db
def test_query_returns_analysis_cards_structure():
    cards = get_analysis_cards()

    assert isinstance(cards, list)
    assert len(cards) > 0

    for c in cards:
        assert isinstance(c, dict)
        assert "id" in c
        assert "question" in c
        assert "answer" in c


@pytest.mark.db
def test_db_params_fallback(monkeypatch):
    # simulate environment with NO DATABASE_URL
    monkeypatch.delenv("DATABASE_URL", raising=False)

    params = _db_params()

    assert isinstance(params, dict)
    assert "dbname" in params
