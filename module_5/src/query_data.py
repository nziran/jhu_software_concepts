"""
query_data.py

Runs a set of SQL queries against the `applicants` table in the `gradcafe` Postgres DB
and returns results formatted as “analysis cards” (id/question/answer dicts) for the
Analysis web page (and also supports printing them from CLI).
"""

from __future__ import annotations

import os

import psycopg

# ----------------------------
# Database connection settings
# ----------------------------
DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432


def _db_params():
    """Return DATABASE_URL if set, otherwise a keyword-args dict for psycopg.connect()."""
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


def get_analysis_cards():  # pylint: disable=too-many-locals
    """
    Run a curated set of analysis queries and return them as a list of dicts::

        [
            {"id": "Q1", "question": "...", "answer": "..."},
            {"id": "Q2", "question": "...", "answer": "..."},
            ...
        ]
    """
    cards: list[dict[str, str]] = []

    db = _db_params()
    connect_kwargs = db if isinstance(db, str) else None

    with psycopg.connect(connect_kwargs) if isinstance(db, str) else psycopg.connect(**db) as conn:
        with conn.cursor() as cur:
            # Q0: Total rows
            cur.execute("SELECT COUNT(*) FROM applicants;")
            total_rows = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q0",
                    "question": "How many total GradCafe entries are in your database?",
                    "answer": str(total_rows),
                }
            )

            # Q1: Count Fall 2026 entries
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%';
                """
            )
            q1 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q1",
                    "question": (
                        "How many entries do you have in your database who have applied for "
                        "Fall 2026?"
                    ),
                    "answer": str(q1),
                }
            )

            # Q2: Percent international (excluding American/Other)
            cur.execute("SELECT COUNT(*) FROM applicants;")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE us_or_international ILIKE '%international%'
                  AND us_or_international NOT ILIKE '%american%'
                  AND us_or_international NOT ILIKE '%other%';
                """
            )
            intl = cur.fetchone()[0]
            pct_intl = (intl / total) * 100 if total else 0.0
            cards.append(
                {
                    "id": "Q2",
                    "question": (
                        "What percentage of entries are from international students "
                        "(not American or Other) (to two decimal places)?"
                    ),
                    "answer": f"{pct_intl:.2f}%",
                }
            )

            # Q3: Averages for GPA and GRE metrics (with plausible range filters)
            cur.execute(
                """
                SELECT
                  AVG(gpa) AS avg_gpa,
                  AVG(gre) AS avg_gre_total,
                  AVG(gre_v) AS avg_gre_section,
                  AVG(gre_aw) AS avg_aw
                FROM applicants
                WHERE (gre BETWEEN 300 AND 340 OR gre IS NULL)
                  AND (gre_v BETWEEN 130 AND 170 OR gre_v IS NULL)
                  AND (gre_aw BETWEEN 0 AND 6 OR gre_aw IS NULL);
                """
            )
            avg_gpa, avg_gre_total, avg_gre_section, avg_aw = cur.fetchone()

            def _fmt(x, spec):
                return "N/A" if x is None else format(x, spec)

            cards.append(
                {
                    "id": "Q3",
                    "question": (
                        "What is the average GPA, GRE (Total), GRE (Section), and GRE AW "
                        "of applicants who provide these metrics?"
                    ),
                    "answer": (
                        f"Avg GPA: {_fmt(avg_gpa, '.3f')}, "
                        f"Avg GRE Total: {_fmt(avg_gre_total, '.2f')}, "
                        f"Avg GRE (Section): {_fmt(avg_gre_section, '.2f')}, "
                        f"Avg GRE AW: {_fmt(avg_aw, '.2f')}"
                    ),
                }
            )

            # Q4: Average GPA of American Fall 2026 applicants
            cur.execute(
                """
                SELECT AVG(gpa)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND us_or_international ILIKE '%american%'
                  AND gpa IS NOT NULL;
                """
            )
            q4 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q4",
                    "question": "What is the average GPA of American students in Fall 2026?",
                    "answer": "N/A" if q4 is None else f"{q4:.2f}",
                }
            )

            # Q5: Acceptance % among Fall 2026 entries
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%';
                """
            )
            f26_total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND status ILIKE '%accept%';
                """
            )
            f26_accept = cur.fetchone()[0]
            pct_accept = (f26_accept / f26_total) * 100 if f26_total else 0.0
            cards.append(
                {
                    "id": "Q5",
                    "question": (
                        "What percent of entries for Fall 2026 are Acceptances "
                        "(to two decimal places)?"
                    ),
                    "answer": f"{pct_accept:.2f}%",
                }
            )

            # Q6: Average GPA for Fall 2026 acceptances
            cur.execute(
                """
                SELECT AVG(gpa)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND status ILIKE '%accept%'
                  AND gpa IS NOT NULL;
                """
            )
            q6 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q6",
                    "question": (
                        "What is the average GPA of applicants who applied for Fall 2026 "
                        "who are Acceptances?"
                    ),
                    "answer": "N/A" if q6 is None else f"{q6:.2f}",
                }
            )

            # Q7: JHU Masters in CS count (program OR llm_generated_program)
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE university ILIKE ANY (ARRAY[
                    '%johns hopkins%',
                    '%john hopkins%',
                    '%jhu%'
                    ])
                AND degree ILIKE ANY (ARRAY[
                    '%master%',
                    '%ms%',
                    '%m.s%'
                    ])
                AND (
                    program ILIKE ANY (ARRAY[
                        '%computer science%',
                        '%computer sciences%',
                        '%computer sci%',
                        '%comp sci%',
                        '%cs%'
                    ])
                    OR llm_generated_program ILIKE ANY (ARRAY[
                        '%computer science%',
                        '%computer sciences%',
                        '%computer sci%',
                        '%comp sci%',
                        '%cs%'
                    ])
                    );
                """
            )
            q7 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q7",
                    "question": (
                        "How many entries are from applicants who applied to JHU for a "
                        "masters degree in Computer Science?"
                    ),
                    "answer": str(q7),
                }
            )

            # Q8: 2026 PhD CS acceptances at selected universities (downloaded fields)
            cur.execute(
                r"""
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%2026%'
                  AND status ILIKE ANY (ARRAY['%accept%','%admit%'])
                  AND degree ~* '\m(phd|ph\.d\.)\M'
                  AND program ~* '(computer\s*science|computer\s*sci|comp\s*sci|\mcs\M)'
                  AND university ILIKE ANY (ARRAY[
                        '%georgetown%',
                        '%massachusetts institute of technology%',
                        '%mit%',
                        '%stanford%',
                        '%carnegie mellon%',
                        '%cmu%'
                  ]);
                """
            )
            q8 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q8",
                    "question": (
                        "How many 2026 acceptances are from applicants who applied to "
                        "Georgetown, MIT, Stanford, or Carnegie Mellon University for a "
                        "PhD in Computer Science?"
                    ),
                    "answer": str(q8),
                }
            )

            # Q9: Same idea as Q8 but using ONLY LLM-generated fields
            cur.execute(
                r"""
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%2026%'
                  AND status ILIKE ANY (ARRAY['%accept%','%admit%'])
                  AND degree ~* '\m(phd|ph\.d\.)\M'
                  AND llm_generated_program ~* (
                      '(computer\s*science|computer\s*sci|'
                      'comp\s*sci|\mcs\M)'
                    )
                  AND llm_generated_university ILIKE ANY (ARRAY[
                        '%georgetown%',
                        '%mit%',
                        '%massachusetts institute of technology%',
                        '%stanford%',
                        '%carnegie mellon%',
                        '%cmu%'
                  ]);
                """
            )
            q9 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q9",
                    "question": (
                        "Do the numbers for Q8 change if you use the LLM generated fields "
                        "(rather than downloaded fields)?"
                    ),
                    "answer": f"Using LLM fields, count = {q9}",
                }
            )

            # Q10 (custom 1): Top 5 most popular programs
            cur.execute(
                """
                SELECT program, COUNT(*) AS count
                FROM applicants
                WHERE program IS NOT NULL AND program <> ''
                GROUP BY program
                ORDER BY count DESC
                LIMIT 5;
                """
            )
            top5_programs = cur.fetchall()
            top5_programs_str = "\n".join(f"{c} - {p}" for (p, c) in top5_programs)
            cards.append(
                {
                    "id": "Q10",
                    "question": (
                        "Custom Question: What are the top 5 most popular programs "
                        "applied to?"
                    ),
                    "answer": top5_programs_str,
                }
            )

            # Q11 (custom 2): Top 5 universities for Physics PhD
            cur.execute(
                r"""
                SELECT university, COUNT(*) AS count
                FROM applicants
                WHERE program ~* '(\mphysics\M.*\m(phd|ph\.d\.)\M|\m(phd|ph\.d\.)\M.*\mphysics\M)'
                  AND university IS NOT NULL
                  AND university <> ''
                GROUP BY university
                ORDER BY count DESC
                LIMIT 5;
                """
            )
            top5_physics_unis = cur.fetchall()
            top5_physics_unis_str = "\n".join(f"{c} - {u}" for (u, c) in top5_physics_unis)
            cards.append(
                {
                    "id": "Q11",
                    "question": (
                        "Custom Question: What are the top 5 universities applied to "
                        "for Physics PhD?"
                    ),
                    "answer": top5_physics_unis_str,
                }
            )

    return cards


def main() -> None:
    """CLI runner for printing analysis cards."""
    cards = get_analysis_cards()
    for card in cards:
        print(
            f"{card['id']}) {card['question']}\n    Answer: {card['answer']}\n"
        )


if __name__ == "__main__":
    main()
