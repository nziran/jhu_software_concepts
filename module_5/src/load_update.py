"""
Load cleaned GradCafe update records into the PostgreSQL applicants table.

This script reads the cleaned update output and inserts new rows into the database
while avoiding duplicates (typically by URL). It is part of the module_5 update
pipeline used by the Flask app.
"""
import json
from pathlib import Path
from datetime import datetime
import psycopg  # pylint: disable=unused-import
from src.db import connect_db


# Cleaned update dataset produced by clean_update.py
CLEANED_UPDATE_PATH = Path("cleaned_applicant_data_update.json")


def parse_date(date_str):
    """
    Convert YYYY-MM-DD string into a date object.
    Returns None if the value is missing or invalid.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_float(x):
    """
    Convert numeric string to float.
    Returns None for empty or invalid values.
    """
    try:
        if x is None or x == "":
            return None
        return float(x)
    except (OSError, ValueError):
        return None


def main():
    """
    Loads cleaned update records and inserts only new entries
    into the PostgreSQL applicants table.
    Duplicate URLs are ignored.
    """

    # Ensure cleaned update file exists
    if not CLEANED_UPDATE_PATH.exists():
        raise FileNotFoundError(
            f"Missing update JSON: {CLEANED_UPDATE_PATH.resolve()}"
        )

    # Load cleaned records
    data = json.loads(
        CLEANED_UPDATE_PATH.read_text(encoding="utf-8")
    )

    inserted = 0

    # Open database connection
    with connect_db() as conn:
        with conn.cursor() as cur:

            for entry in data:

                # Build a valid term string only when meaningful data exists
                term_part = entry.get("start_term")
                year_part = entry.get("start_year")

                term_value = None
                if term_part and year_part:
                    term_value = f"{term_part} {year_part}"
                elif term_part:
                    term_value = term_part
                elif year_part:
                    term_value = year_part

                # Insert record; ignore duplicates based on URL
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
                        "date_added": parse_date(
                            entry.get("date_posted")
                        ),
                        "url": entry.get("entry_url"),
                        "status": entry.get("applicant_status"),
                        "term": term_value,
                        "us_or_international": entry.get(
                            "US/International"
                        ),
                        "gpa": safe_float(entry.get("GPA")),
                        "gre": safe_float(entry.get("gre_total")),
                        "gre_v": safe_float(entry.get("gre_v")),
                        "gre_aw": safe_float(entry.get("gre_aw")),
                        "degree": entry.get("degree_level")
                        or entry.get("degree"),

                        # No LLM processing for update records
                        "llm_generated_program": None,
                        "llm_generated_university": None,
                    },
                )

                # Count only successful inserts
                if cur.rowcount == 1:
                    inserted += 1

        conn.commit()

    print(f"✅ Inserted {inserted} new rows into applicants.")


if __name__ == "__main__":
    main()
