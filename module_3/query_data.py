import psycopg

DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432


def get_analysis_cards():
    """
    Returns a list of dicts:
    [{"id": "Q1", "question": "...", "answer": "..."} , ...]
    """
    cards = []

    with psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        host=DB_HOST,
        port=DB_PORT,
    ) as conn:
        with conn.cursor() as cur:
            # Q1
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
                    "question": "How many entries do you have in your database who have applied for Fall 2026?",
                    "answer": str(q1),
                }
            )

            # Q2
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
                    "question": "What percentage of entries are from international students (not American or Other) (to two decimal places)?",
                    "answer": f"{pct_intl:.2f}%",
                }
            )

            # Q3 (filtered to plausible ranges due to mixed GRE encoding in source data)
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
            cards.append(
                {
                    "id": "Q3",
                    "question": "What is the average GPA, GRE (Total), GRE (Section), and GRE AW of applicants who provide these metrics?",
                    "answer": (
                        f"Avg GPA: {avg_gpa:.3f}, "
                        f"Avg GRE Total: {avg_gre_total:.2f}, "
                        f"Avg GRE (Section): {avg_gre_section:.2f}, "
                        f"Avg GRE AW: {avg_aw:.2f}"
                    ),
                }
            )

            # Q4
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

            # Q5
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
                    "question": "What percent of entries for Fall 2026 are Acceptances (to two decimal places)?",
                    "answer": f"{pct_accept:.2f}%",
                }
            )

            # Q6
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
                    "question": "What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?",
                    "answer": "N/A" if q6 is None else f"{q6:.2f}",
                }
            )

            # Q7
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE university ILIKE '%johns hopkins%'
                  AND degree ILIKE '%master%'
                  AND (
                        program ILIKE '%computer science%'
                     OR llm_generated_program ILIKE '%computer science%'
                  );
                """
            )
            q7 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q7",
                    "question": "How many entries are from applicants who applied to JHU for a masters degree in Computer Science?",
                    "answer": str(q7),
                }
            )

            # Q8
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%2026%'
                  AND status ILIKE '%accept%'
                  AND degree ILIKE '%phd%'
                  AND (
                        program ILIKE '%computer science%'
                     OR llm_generated_program ILIKE '%computer science%'
                  )
                  AND (
                        university ILIKE '%georgetown%'
                     OR university ILIKE '%massachusetts institute of technology%'
                     OR university ILIKE '%mit%'
                     OR university ILIKE '%stanford%'
                     OR university ILIKE '%carnegie mellon%'
                  );
                """
            )
            q8 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q8",
                    "question": "How many 2026 acceptances are from applicants who applied to Georgetown, MIT, Stanford, or Carnegie Mellon University for a PhD in Computer Science?",
                    "answer": str(q8),
                }
            )

            # Q9 (LLM fields)
            cur.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%2026%'
                  AND status ILIKE '%accept%'
                  AND degree ILIKE '%phd%'
                  AND llm_generated_program ILIKE '%computer science%'
                  AND (
                        llm_generated_university ILIKE '%georgetown%'
                     OR llm_generated_university ILIKE '%mit%'
                     OR llm_generated_university ILIKE '%stanford%'
                     OR llm_generated_university ILIKE '%carnegie mellon%'
                  );
                """
            )
            q9 = cur.fetchone()[0]
            cards.append(
                {
                    "id": "Q9",
                    "question": "Do the numbers for Q8 change if you use the LLM generated fields (rather than downloaded fields)?",
                    "answer": f"Using LLM fields, count = {q9}",
                }
            )

            # Q10 (custom 1): Top 5 programs
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
            top5_programs_str = "\n".join([f"{c} - {p}" for (p, c) in top5_programs])
            cards.append(
                {
                    "id": "Q10",
                    "question": "Custom Question: What are the top 5 most popular programs applied to?",
                    "answer": top5_programs_str,
                }
            )

            # Q11 (custom 2): Top 5 universities for Physics PhD
            cur.execute(
                """
                SELECT university, COUNT(*) AS count
                FROM applicants
                WHERE program = 'Physics PhD'
                  AND university IS NOT NULL AND university <> ''
                GROUP BY university
                ORDER BY count DESC
                LIMIT 5;
                """
            )
            top5_physics_unis = cur.fetchall()
            top5_physics_unis_str = "\n".join([f"{c} - {u}" for (u, c) in top5_physics_unis])
            cards.append(
                {
                    "id": "Q11",
                    "question": "Custom Question: What are the top 5 universities applied to for Physics PhD?",
                    "answer": top5_physics_unis_str,
                }
            )

    return cards


def main():
    cards = get_analysis_cards()
    for c in cards:
        print(f"{c['id']}) {c['question']}\n    Answer: {c['answer']}\n")


if __name__ == "__main__":
    main()