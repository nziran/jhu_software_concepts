"""
load_py.py

Loads cleaned/extended GradCafe applicant entries from a JSON file and inserts them into a
PostgreSQL table named `applicants`. Uses an "upsert-like" strategy: insert new rows and
silently skip duplicates based on `url` (unique constraint).
"""

import json
from pathlib import Path
from datetime import datetime
import psycopg
import os

# ----------------------------
# Database connection settings
# ----------------------------
# These constants define where and how to connect to Postgres.
DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432

# ----------------------------
# Input data location
# ----------------------------
# Path to the cleaned/enriched JSON produced in module_2.
# (Relative to this script's location / working directory when executed.)
ROOT_DIR = Path(__file__).resolve().parents[1]  # module_4/
CANDIDATES = [
    ROOT_DIR / "llm_extend_applicant_data.json",
    ROOT_DIR / "src" / "llm_extend_applicant_data.json",
]

CLEANED_JSON_PATH = next((p for p in CANDIDATES if p.exists()), None)
if CLEANED_JSON_PATH is None:
    raise FileNotFoundError(
        "Missing cleaned JSON. Expected one of:\n"
        + "\n".join(str(p) for p in CANDIDATES)
    )

def parse_date(date_str):
    """
    Convert a YYYY-MM-DD string into a Python `date` object.

    Returns:
      - a `datetime.date` if parsing succeeds
      - None if the input is missing/empty or has an unexpected format
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_float(x):
    """
    Best-effort conversion of a value to float.

    Returns:
      - float(x) when possible
      - None if x is None/empty or cannot be converted
    """
    try:
        if x is None or x == "":
            return None
        return float(x)
    except:
        return None


def main():
    """
    Main ETL routine:
      1) Verify input JSON exists
      2) Load JSON into memory (expects a list of dicts)
      3) Connect to Postgres
      4) Create table `applicants` if missing
      5) Insert entries, skipping duplicates by url
      6) Commit and report how many new rows were inserted
    """
    # ---- 1) Validate input file exists ----
    if not CLEANED_JSON_PATH.exists():
        raise FileNotFoundError(f"Missing cleaned JSON: {CLEANED_JSON_PATH.resolve()}")

    # ---- 2) Load the JSON ----
    # Reads file as UTF-8 text and parses into Python objects (likely list[dict]).
    data = json.loads(CLEANED_JSON_PATH.read_text(encoding="utf-8"))

    # ---- 3) Open database connection ----
    # Context manager will close the connection automatically.
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:

        # ---- 4) Use a cursor to run SQL ----
        with conn.cursor() as cur:
            # Create the applicants table once (idempotent).
            # Note: `url` is UNIQUE, which is used to avoid duplicate inserts.
            cur.execute("""
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
            """)

            # Track how many rows were actually inserted (not skipped by conflict).
            inserted = 0

            # ---- 5) Insert each JSON entry ----
            for entry in data:
                # Parameterized INSERT protects against SQL injection and handles quoting.
                # ON CONFLICT(url) DO NOTHING means "skip" if this URL already exists.
                cur.execute("""
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
                """, {
                    # Raw scraped fields
                    "program": entry.get("program"),
                    "university": entry.get("university"),
                    "comments": entry.get("comments"),

                    # Normalize date_posted -> date_added (DATE column)
                    "date_added": parse_date(entry.get("date_posted")),

                    # Unique identifier used to dedupe entries
                    "url": entry.get("entry_url"),

                    "status": entry.get("applicant_status"),

                    # Build a single "term" string if either component exists
                    # Examples: "Fall 2025", "Spring 2024", or None if both missing.
                    "term": None if (entry.get("start_term") is None and entry.get("start_year") is None)
                            else f"{entry.get('start_term', '')} {entry.get('start_year', '')}".strip(),

                    "us_or_international": entry.get("US/International"),

                    # Numeric cleanup for floats (None if blank/bad)
                    "gpa": safe_float(entry.get("GPA")),
                    "gre": safe_float(entry.get("gre_total")),
                    "gre_v": safe_float(entry.get("gre_v")),
                    "gre_aw": safe_float(entry.get("gre_aw")),

                    # Prefer cleaned key degree_level if present; otherwise fall back
                    "degree": entry.get("degree_level") or entry.get("degree"),

                    # LLM-enriched fields
                    "llm_generated_program": entry.get("llm-generated-program"),
                    "llm_generated_university": entry.get("llm-generated-university"),
                })

                # rowcount == 1 means the INSERT happened; 0 means it was skipped (conflict).
                if cur.rowcount == 1:
                    inserted += 1

        # ---- 6) Commit transaction ----
        conn.commit()

    # ---- 7) Report result ----
    print(f"✅ Inserted {inserted} new rows into applicants.")


# Standard Python entrypoint guard:
# - Allows importing this file without running `main()`
# - Runs main only when executed directly: python load_py.py
if __name__ == "__main__":
    main()