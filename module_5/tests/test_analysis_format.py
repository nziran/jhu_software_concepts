"""Tests for analysis page formatting and percentage rendering."""

import re

import pytest


@pytest.mark.analysis
def test_page_contains_answer_labels(client):
    resp = client.get("/analysis")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # must include at least one Answer label
    assert "Answer:" in html


@pytest.mark.analysis
def test_percentages_are_two_decimals(client):
    resp = client.get("/analysis")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Find all percentages like 39.28%
    percents = re.findall(r"\b\d+\.\d+%\b", html)

    # If your page currently renders zero percentages sometimes, this can be empty.
    for p in percents:
        assert re.match(r"^\d+\.\d{2}%$", p), f"Bad percent format: {p}"
