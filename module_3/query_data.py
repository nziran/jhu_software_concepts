import psycopg

DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432


def main():
    with psycopg.connect(
        dbname=DB_NAME, user=DB_USER, host=DB_HOST, port=DB_PORT
    ) as conn:
        with conn.cursor() as cur:
            # Q1
            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%';
            """)
            fall_2026 = cur.fetchone()[0]
            print(f"Q1) Fall 2026 entries: {fall_2026}")

            # Q2
            cur.execute("SELECT COUNT(*) FROM applicants;")
            total = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE us_or_international ILIKE '%international%'
                  AND us_or_international NOT ILIKE '%american%'
                  AND us_or_international NOT ILIKE '%other%';
            """)
            intl = cur.fetchone()[0]
            pct = (intl / total) * 100 if total else 0
            print(f"Q2) % international (not American/Other): {pct:.2f}%")

            # Q3: averages computed over non-null values (each AVG ignores NULLs)
            cur.execute("""
                 SELECT
                 AVG(gpa) AS avg_gpa,
                 AVG(gre) AS avg_gre_total,
                 AVG(gre_v) AS avg_gre_section,
                 AVG(gre_aw) AS avg_aw
                FROM applicants
                WHERE (gre BETWEEN 300 AND 340 OR gre IS NULL)
                AND (gre_v BETWEEN 130 AND 170 OR gre_v IS NULL)
                AND (gre_aw BETWEEN 0 AND 6 OR gre_aw IS NULL);
                """)

            avg_gpa, avg_gre, avg_gre_v, avg_aw = cur.fetchone()

            print("Q3) Average metrics (filtered to plausible ranges):")
            print(f"    Avg GPA:        {avg_gpa}")
            print(f"    Avg GRE Total:  {avg_gre}")
            print(f"    Avg GRE (Sect): {avg_gre_v}")
            print(f"    Avg GRE AW:     {avg_aw}")

            # Q4
            cur.execute("""
                SELECT AVG(gpa)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND us_or_international ILIKE '%american%'
                  AND gpa IS NOT NULL;
            """)
            avg_gpa_american_f26 = cur.fetchone()[0]
            print(
                f"Q4) Avg GPA of American students (Fall 2026): {avg_gpa_american_f26}"
            )

            # Q5
            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%';
            """)
            f26_total = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND status ILIKE '%accept%';
            """)
            f26_accept = cur.fetchone()[0]

            pct_accept = (f26_accept / f26_total) * 100 if f26_total else 0
            print(f"Q5) % Fall 2026 acceptances: {pct_accept:.2f}%")

            # Q6
            cur.execute("""
                SELECT AVG(gpa)
                FROM applicants
                WHERE term ILIKE '%fall%' AND term ILIKE '%2026%'
                  AND status ILIKE '%accept%'
                  AND gpa IS NOT NULL;
            """)
            avg_gpa_f26_accept = cur.fetchone()[0]
            print(f"Q6) Avg GPA of Fall 2026 acceptances: {avg_gpa_f26_accept}")

            # Q7
            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE university ILIKE '%johns hopkins%'
                  AND degree ILIKE '%master%'
                  AND (
                        program ILIKE '%computer science%'
                     OR llm_generated_program ILIKE '%computer science%'
                  );
            """)
            q7 = cur.fetchone()[0]
            print(f"Q7) JHU MS Computer Science entries: {q7}")

            # Q8
            cur.execute("""
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
            """)
            q8 = cur.fetchone()[0]
            print(f"Q8) 2026 PhD CS acceptances (Georgetown/MIT/Stanford/CMU): {q8}")

            # Q9
            cur.execute("""
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
            """)
            q9 = cur.fetchone()[0]
            print(f"Q9) Using LLM fields, count becomes: {q9}")


if __name__ == "__main__":
    main()
