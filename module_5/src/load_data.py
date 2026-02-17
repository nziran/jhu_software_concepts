"""
load_data.py

Loads cleaned/extended GradCafe applicant entries from a JSON file and inserts them into a
PostgreSQL table named `applicants`. Uses an "upsert-like" strategy: insert new rows and
silently skip duplicates based on `url` (unique constraint).
"""

import json
import os
from pathlib import Path
from datetime import datetime

import psycopg

# ----------------------------
# Database connection settings
# ----------------------------
# Defaults are only used if DATABASE_URL is not set.
DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432

# ----------------------------
# Input data location
# ----------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # module_4/
CANDIDATES = [
    ROOT_DIR / "llm_extend_applicant_data.json",
    ROOT_DIR / "src" / "llm_extend_applicant_data.json",
]

CLEANED_JSON_PATH = next((p for p in CANDIDATES if p.exists()), None)
if CLEANED_JSON_PATH is None:
    raise FileNotFoundError(
        "Missing cleaned JSON. Expected one of:\n" + "\n".join(str(p) for p in CANDIDATES)
    )


def parse_date(date_str):
    """Convert a YYYY-MM-DD string into a datetime.date, or return None if invalid."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_float(x):
    """Best-effort conversion to float; returns None if missing/invalid."""
    try:
        if x is None or x == "":
            return None
        return float(x)
    except (ValueError, TypeError):
        return None


def _db_params():
    """
    Returns either:
      - DATABASE_URL string if set, else
      - kwargs dict from PG* env vars with fallbacks.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    return {
        "dbname": os.getenv("PGDATABASE", DB_NAME),
        "user": os.getenv("PGUSER", DB_USER),
        "password": os.getenv("PGPASSWORD"),
        "host": os.getenv("PGHOST", DB_HOST),
        "port": int(os.getenv("PGPORT", str(DB_PORT))),
    }


def main():
    """Main ETL routine: load JSON -> create table -> insert rows (skip dupes) -> commit."""
    data = json.loads(CLEANED_JSON_PATH.read_text(encoding="utf-8"))

    db = _db_params()
    with psycopg.connect(db) if isinstance(db, str) else psycopg.connect(**db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
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
            )

            inserted = 0

            for entry in data:
                cur.execute(
                    """
                    INSERT INTO applicants (
                        program, university, comments, date_added, url,
                        status, term, us_or_international,
                        gpa, gre, gre_v, gre_aw,
                        degree, llm_generated_program, llm_generated_university
                    )
                    VALUES (
                        %(program)s, %(university)s, %(comments)s, %(date_added)s, %(url)s,
                        %(status)s, %(term)s, %(us_or_international)s,
                        %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                        %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
                    )
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    {
                        "program": entry.get("program"),
                        "university": entry.get("university"),
                        "comments": entry.get("comments"),
                        "date_added": parse_date(entry.get("date_posted")),
                        "url": entry.get("entry_url"),
                        "status": entry.get("applicant_status"),
                        "term": None
                        if (entry.get("start_term") is None and entry.get("start_year") is None)
                        else f"{entry.get('start_term', '')} {entry.get('start_year', '')}".strip(),
                        "us_or_international": entry.get("US/International"),
                        "gpa": safe_float(entry.get("GPA")),
                        "gre": safe_float(entry.get("gre_total")),
                        "gre_v": safe_float(entry.get("gre_v")),
                        "gre_aw": safe_float(entry.get("gre_aw")),
                        "degree": entry.get("degree_level") or entry.get("degree"),
                        "llm_generated_program": entry.get("llm-generated-program"),
                        "llm_generated_university": entry.get("llm-generated-university"),
                    },
                )

                if cur.rowcount == 1:
                    inserted += 1

        conn.commit()

    print(f"✅ Inserted {inserted} new rows into applicants.")


if __name__ == "__main__":
    main()
