import json
from pathlib import Path
from datetime import datetime
import psycopg

DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432

CLEANED_UPDATE_PATH = Path("cleaned_applicant_data_update.json")


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def main():
    if not CLEANED_UPDATE_PATH.exists():
        raise FileNotFoundError(f"Missing update JSON: {CLEANED_UPDATE_PATH.resolve()}")

    data = json.loads(CLEANED_UPDATE_PATH.read_text(encoding="utf-8"))

    inserted = 0
    with psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        host=DB_HOST,
        port=DB_PORT,
    ) as conn:
        with conn.cursor() as cur:
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
                        "term": f"{entry.get('start_term', '')} {entry.get('start_year', '')}".strip(),
                        "us_or_international": entry.get("US/International"),
                        "gpa": safe_float(entry.get("GPA")),
                        "gre": safe_float(entry.get("gre_total")),
                        "gre_v": safe_float(entry.get("gre_v")),
                        "gre_aw": safe_float(entry.get("gre_aw")),
                        "degree": entry.get("degree_level") or entry.get("degree"),
                        # instructor said: no LLM on updates → leave as None
                        "llm_generated_program": None,
                        "llm_generated_university": None,
                    },
                )

                if cur.rowcount == 1:
                    inserted += 1

        conn.commit()

    print(f"✅ Inserted {inserted} new rows into applicants.")


if __name__ == "__main__":
    main()