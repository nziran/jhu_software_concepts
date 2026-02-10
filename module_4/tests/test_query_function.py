import pytest
from src.query_data import get_analysis_cards


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