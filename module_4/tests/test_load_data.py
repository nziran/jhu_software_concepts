import json
import pytest
import psycopg
import runpy
import os

TEST_URLS = [
    "https://example.com/gradcafe-loaddata-1",
    "https://example.com/gradcafe-loaddata-2",
]


def _connect():
    return psycopg.connect(
    dbname=os.getenv("PGDATABASE", "gradcafe"),
    user=os.getenv("PGUSER", "ziran"),
    password=os.getenv("PGPASSWORD", "ziran"),
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
)

def _delete_test_rows(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM applicants WHERE url = ANY(%s);", (TEST_URLS,))
    conn.commit()


@pytest.mark.db
def test_load_data_main_inserts_and_is_idempotent(monkeypatch, tmp_path):
    import src.load_data as ld

    # --- fake input JSON (matches keys load_data expects) ---
    fake = [
        {
            "program": "CS",
            "university": "LoadData U",
            "comments": "hi",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[0],
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "American",
            "GPA": "3.90",
            "gre_total": "330",
            "gre_v": "165",
            "gre_aw": "5.0",
            "degree_level": "MS",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Johns Hopkins University",
        },
        {
            "program": "Physics",
            "university": "LoadData U",
            "comments": "yo",
            "date_posted": "bad-date",  # should become None
            "entry_url": TEST_URLS[1],
            "applicant_status": "Rejected",
            "start_term": None,
            "start_year": None,
            "US/International": "International",
            "GPA": "",                 # should become None
            "gre_total": "not-a-num",   # should become None
            "gre_v": "160",
            "gre_aw": "4.0",
            "degree": "PhD",
            "llm-generated-program": None,
            "llm-generated-university": None,
        },
    ]

    p = tmp_path / "llm_extend_applicant_data.json"
    p.write_text(json.dumps(fake), encoding="utf-8")

    monkeypatch.setattr(ld, "CLEANED_JSON_PATH", p)

    # clean slate
    with _connect() as conn:
        _delete_test_rows(conn)

    # run twice (idempotency via UNIQUE(url))
    ld.main()
    ld.main()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT url, program, university, status, term, date_added, gpa, gre
                FROM applicants
                WHERE url = ANY(%s)
                ORDER BY url;
                """,
                (TEST_URLS,),
            )
            rows = cur.fetchall()

        assert len(rows) == 2

        # spot-check inserted content
        url0, program0, uni0, status0, term0, date0, gpa0, gre0 = rows[0]
        assert url0 in TEST_URLS
        assert program0 is not None
        assert uni0 is not None
        assert status0 is not None

        # term should be constructed for first record
        assert any(r[4] == "Fall 2026" for r in rows)

        # second record had bad date + empty GPA + bad gre_total -> should be None-ish
        # (we don't know which row index due to ordering, so search)
        bad = [r for r in rows if r[0] == TEST_URLS[1]][0]
        assert bad[5] is None      # date_added
        assert bad[6] is None      # gpa
        assert bad[7] is None      # gre

        # cleanup
        _delete_test_rows(conn)

@pytest.mark.db
def test_load_data_runs_as_script_hits_main_guard(tmp_path, monkeypatch):
    """
    Covers: if __name__ == "__main__": main()
    We do it by:
      1) writing the expected default JSON file into src/ next to load_data.py
      2) running the module as __main__
      3) cleaning up the inserted DB row + the temp JSON file
    """
    # Import to locate the real src directory on disk
    import src.load_data as ld

    # real path: <project>/src/llm_extend_applicant_data.json
    default_json = ld.Path(ld.__file__).parent / "llm_extend_applicant_data.json"

    # Write minimal data (one row) to default location
    payload = [
        {
            "program": "ScriptRun",
            "university": "Guard U",
            "comments": "script run",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[0],
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "American",
        }
    ]
    default_json.write_text(json.dumps(payload), encoding="utf-8")

    # clean slate for our URL
    with _connect() as conn:
        _delete_test_rows(conn)

    # Execute module as a script (hits __main__ guard)
    runpy.run_module("src.load_data", run_name="__main__")

    # verify row exists, then cleanup
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants WHERE url = %s;", (TEST_URLS[0],))
            assert cur.fetchone()[0] == 1
        _delete_test_rows(conn)

    # cleanup the json file we dropped in src/
    default_json.unlink(missing_ok=True)

@pytest.mark.db
def test_load_data_helpers_handle_empty_inputs():
    import src.load_data as ld

    # parse_date: empty/missing should return None (covers the "if not date_str" branch)
    assert ld.parse_date("") is None
    assert ld.parse_date(None) is None

    # safe_float: None/"" should return None (covers the "if x is None or x == ''" branch)
    assert ld.safe_float("") is None
    assert ld.safe_float(None) is None

@pytest.mark.db
def test_load_data_main_raises_when_input_file_missing(monkeypatch, tmp_path):
    import src.load_data as ld

    # point loader at a file that does NOT exist
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(ld, "CLEANED_JSON_PATH", missing)

    with pytest.raises(FileNotFoundError):
        ld.main()