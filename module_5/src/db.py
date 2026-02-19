"""
db.py

Single source of truth for Postgres connection configuration.

Priority:
1) If DATABASE_URL is set, use it (backward compatible for existing tests/dev).
2) Otherwise, read DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD and connect.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg


def connect_db() -> psycopg.Connection[Any]:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg.connect(db_url)

    required = ["DB_HOST", "DB_NAME", "DB_USER"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required DB env vars: {', '.join(missing)}")

    kwargs: dict[str, Any] = {
        "host": os.environ["DB_HOST"],
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "port": int(os.getenv("DB_PORT", "5432")),
    }

    password = os.getenv("DB_PASSWORD")
    if password:
        kwargs["password"] = password

    return psycopg.connect(**kwargs)

