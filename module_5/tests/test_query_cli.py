"""Tests for the CLI entry point in query_data."""

import pytest

import src.query_data as qd


@pytest.mark.analysis
def test_query_data_main_prints_cards(monkeypatch, capsys):
    """
    Covers CLI main() path in query_data.py by mocking analysis cards
    and verifying printed formatting.
    """
    fake_cards = [
        {
            "id": "QX",
            "question": "Test question?",
            "answer": "42%",
        }
    ]

    # Mock DB-heavy function
    monkeypatch.setattr(qd, "get_analysis_cards", lambda: fake_cards)

    # Run CLI main
    qd.main()

    # Capture output
    out = capsys.readouterr().out

    assert "QX)" in out
    assert "Test question?" in out
    assert "Answer: 42%" in out
