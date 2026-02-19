import os
import pytest
import psycopg
from src.app import create_app

def _pg_env(name: str, fallback: str | None = None) -> str | None:
    # Prefer standard libpq env vars, then POSTGRES_* from actions services
    return (
        os.getenv(name)
        or os.getenv(name.replace("PG", "POSTGRES_"))
        or fallback
    )

def _connect():
    return psycopg.connect(
        dbname=_pg_env("PGDATABASE", "gradcafe"),
        user=_pg_env("PGUSER", "ziran"),
        password=_pg_env("PGPASSWORD", "ziran"),  # CI has it; graders can set env too
        host=_pg_env("PGHOST", "localhost"),
        port=int(_pg_env("PGPORT", "5432") or 5432),
    )

@pytest.fixture(scope="session", autouse=True)
def _set_db_env_for_tests():
    """
    Ensure DB env vars exist for graders/CI so connect_db() never KeyErrors.
    """
    os.environ.setdefault("DB_HOST", _pg_env("PGHOST", "localhost") or "localhost")
    os.environ.setdefault("DB_PORT", _pg_env("PGPORT", "5432") or "5432")
    os.environ.setdefault("DB_NAME", _pg_env("PGDATABASE", "gradcafe") or "gradcafe")
    os.environ.setdefault("DB_USER", _pg_env("PGUSER", "ziran") or "ziran")

    # Optional: only set if present (many local setups use peer auth and no password)
    pgpass = _pg_env("PGPASSWORD", None)
    if pgpass:
        os.environ.setdefault("DB_PASSWORD", pgpass)

@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
    """Make CI/graders portable: ensure applicants table exists before any tests."""
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
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()