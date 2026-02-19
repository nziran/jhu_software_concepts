# tests/test_flask_page.py

import pytest

pytestmark = pytest.mark.web

# Import the Flask app object
from src.app import app as flask_app


@pytest.fixture()
def client():
    """
    Pytest fixture that returns a Flask test client.
    """
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        yield client


def test_app_has_required_routes():
    """
    Assert the Flask app is created and includes the expected routes.
    """
    routes = {rule.rule for rule in flask_app.url_map.iter_rules()}

    # GET routes
    assert "/" in routes
    assert "/analysis" in routes

    # POST routes (existence check)
    assert "/pull-data" in routes
    assert "/update-analysis" in routes


def test_get_analysis_page_loads_and_contains_expected_text(client):
    """
    Test GET /analysis:
      - status 200
      - contains Pull Data + Update Analysis buttons
      - contains 'Analysis'
      - contains at least one 'Answer:'
    """
    resp = client.get("/analysis")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)

    assert "Pull Data" in html
    assert "Update Analysis" in html
    assert "Analysis" in html
    assert "card-answer" in html