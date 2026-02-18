"""Tests for the Flask web pages and required routes."""

from __future__ import annotations

import pytest

from src.app import app as flask_app

pytestmark = pytest.mark.web


@pytest.fixture()
def client():
    """Return a Flask test client."""
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as test_client:
        yield test_client


def test_app_has_required_routes():
    """Assert the Flask app is created and includes the expected routes."""
    routes = {rule.rule for rule in flask_app.url_map.iter_rules()}

    assert "/" in routes
    assert "/analysis" in routes
    assert "/pull-data" in routes
    assert "/update-analysis" in routes

def test_get_analysis_page_loads_and_contains_expected_text(flask_client):
    """Test GET /analysis.

    Checks:
      - status 200
      - contains Pull Data + Update Analysis buttons
      - contains 'Analysis'
      - contains at least one 'card-answer'
    """
    resp = flask_client.get("/analysis")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)

    assert "Pull Data" in html
    assert "Update Analysis" in html
    assert "Analysis" in html
    assert "card-answer" in html
