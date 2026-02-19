import pytest

from src.scrape_update import (
    _normalize_none,
    _canonical_result_url,
    _valid_result_url,
    _extract_float,
    _extract_int,
    _degree_level,
)


@pytest.mark.analysis
def test_normalize_none():
    assert _normalize_none(" hi ") == "hi"
    assert _normalize_none("   ") is None
    assert _normalize_none(None) is None


@pytest.mark.analysis
def test_canonical_url():
    url = "http://thegradcafe.com/result/123?x=1"
    clean = _canonical_result_url(url)

    assert clean.startswith("https://www.thegradcafe.com/result/")
    assert "?" not in clean


@pytest.mark.analysis
def test_valid_url():
    assert _valid_result_url("https://www.thegradcafe.com/result/123")
    assert not _valid_result_url("https://example.com/test")


@pytest.mark.analysis
def test_extract_numbers():
    assert _extract_float("GPA 3.45") == "3.45"
    assert _extract_int("GRE 320") == "320"
    assert _extract_float(None) is None


@pytest.mark.analysis
def test_degree_level():
    assert _degree_level("PhD Physics") == "PhD"
    assert _degree_level("MS Computer Science") == "Masters"
    assert _degree_level("Certificate") is None