"""Unit tests for load_update date parsing and float handling."""

import pytest

from src.load_update import parse_date, safe_float


@pytest.mark.db
def test_parse_date_valid():
    d = parse_date("2026-02-10")
    assert str(d) == "2026-02-10"


@pytest.mark.db
def test_parse_date_invalid_or_missing_returns_none():
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("not-a-date") is None
    assert parse_date("2026-13-40") is None  # invalid month/day


@pytest.mark.db
def test_safe_float_valid_and_invalid():
    assert safe_float("3.14") == 3.14
    assert safe_float("0") == 0.0
    assert safe_float("") is None
    assert safe_float(None) is None
    assert safe_float("abc") is None
