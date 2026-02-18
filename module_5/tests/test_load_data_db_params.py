"""Tests for database parameter resolution in load_data."""

import pytest

import src.load_data as ld


@pytest.mark.db
def test_load_data_db_params_uses_database_url(monkeypatch):
    # Accessing a protected member is acceptable in tests
    monkeypatch.setenv("DATABASE_URL", "postgresql://someone@localhost:5432/gradcafe")

    # pylint: disable=protected-access
    assert ld._db_params() == "postgresql://someone@localhost:5432/gradcafe"
