"""Pytest configuration and shared fixtures for Module 5 tests."""

import os

import pytest
import psycopg

from src.app import create_app


def _pg_env(name: str, fallback: str | None = None) -> str | None:
    """Return a Postgres environment variable with sensible fallbacks."""
    return (
        os.getenv(name)
        or os.getenv(name.replace("PG", "POSTGRES_"))
        or fallback
    )


def _connect():
    """Create a Postgres connection using environment variables."""
    return psycopg.connect(
        dbname=_pg_env("PGDATABASE", "gradcafe"),
        user=_pg_env("PGUSER", "ziran"),
        password=_pg_env("PGPASSWORD", "ziran"),  # CI has it; graders can set env too
        host=_pg_env("PGHOST", "localhost"),
        port=int(_pg_env("PGPORT", "5432") or 5432),
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
    """Ensure the applicants table exists before any tests run."""
    ddl = """
    CREATE TABLE IF NOT EXISTS applicants (
        p_id BIGSERIAL PRIMARY KEY,
        program TEXT,
        university TEXT,
        comments TEXT,
        date_added DATE,
        url TEXT UNIQUE,
        status TEXT,
        term TEXT,
        us_or_international TEXT,
        gpa FLOAT,
        gre FLOAT,
        gre_v FLOAT,
        gre_aw FLOAT,
        degree TEXT,
        llm_generated_program TEXT,
        llm_generated_university TEXT
    );
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


@pytest.fixture()
def client():
    """Return a Flask test client."""
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()
