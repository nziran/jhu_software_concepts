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

from src.db import connect_db


# ----------------------------
# Input data location
# ----------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # module_5/
CANDIDATES = [
    ROOT_DIR / "llm_extend_applicant_data.json",
    ROOT_DIR / "src" / "llm_extend_applicant_data.json",
]

CLEANED_JSON_PATH = next((p for p in CANDIDATES if p.exists()), None)
if CLEANED_JSON_PATH is None:
    raise FileNotFoundError(
        "Missing cleaned JSON. Expected one of:\n" + "\n".join(str(p) for p in CANDIDATES)
    )


def _db_params():
    """
    Backward-compat helper for tests.
    If DATABASE_URL is set, return it; otherwise return a fallback dict
    (tests may assert this structure exists).
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    return dict(
        dbname=os.getenv("PGDATABASE", "gradcafe"),
        user=os.getenv("PGUSER", "ziran"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
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
    except Exception:
        return None


def main():
    """Main ETL routine: load JSON -> insert rows (skip dupes) -> commit."""
    data = json.loads(CLEANED_JSON_PATH.read_text(encoding="utf-8"))

    # IMPORTANT: least-privilege users cannot CREATE TABLE.
    # The applicants table is assumed to already exist (created during setup).
    with connect_db() as conn:
        with conn.cursor() as cur:
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
