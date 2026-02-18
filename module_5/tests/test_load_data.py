"""Tests for src.load_data main() behavior and helper functions."""

import importlib
import json
import os
import runpy

import psycopg
import pytest

from src import load_data


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
def test_missing_json_path_raises(monkeypatch):
    # Force all candidate paths to appear missing
    monkeypatch.setattr(load_data.Path, "exists", lambda self: False)

    # Reload module so import-time logic re-runs
    with pytest.raises(FileNotFoundError):
        importlib.reload(load_data)


@pytest.mark.db
def test_load_data_main_inserts_and_is_idempotent(monkeypatch, tmp_path):  # pylint: disable=too-many-locals
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
            "date_posted": "bad-date",
            "entry_url": TEST_URLS[1],
            "applicant_status": "Rejected",
            "start_term": None,
            "start_year": None,
            "US/International": "International",
            "GPA": "",
            "gre_total": "not-a-num",
            "gre_v": "160",
            "gre_aw": "4.0",
            "degree": "PhD",
            "llm-generated-program": None,
            "llm-generated-university": None,
        },
    ]

    p = tmp_path / "llm_extend_applicant_data.json"
    p.write_text(json.dumps(fake), encoding="utf-8")

    monkeypatch.setattr(load_data, "CLEANED_JSON_PATH", p)

    with _connect() as conn:
        _delete_test_rows(conn)

    load_data.main()
    load_data.main()

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

        assert any(r[4] == "Fall 2026" for r in rows)

        bad = [r for r in rows if r[0] == TEST_URLS[1]][0]
        assert bad[5] is None
        assert bad[6] is None
        assert bad[7] is None

        _delete_test_rows(conn)


@pytest.mark.filterwarnings(
    "ignore:'src\\.load_data' found in sys\\.modules.*:RuntimeWarning"
)
@pytest.mark.db
def test_load_data_runs_as_script_hits_main_guard():
    default_json = load_data.Path(load_data.__file__).parent / "llm_extend_applicant_data.json"

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

    with _connect() as conn:
        _delete_test_rows(conn)

    runpy.run_module("src.load_data", run_name="__main__")

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants WHERE url = %s;", (TEST_URLS[0],))
            assert cur.fetchone()[0] in (0, 1)
        _delete_test_rows(conn)

    default_json.unlink(missing_ok=True)


@pytest.mark.db
def test_load_data_helpers_handle_empty_inputs():
    assert load_data.parse_date("") is None
    assert load_data.parse_date(None) is None
    assert load_data.safe_float("") is None
    assert load_data.safe_float(None) is None


@pytest.mark.db
def test_load_data_main_raises_when_input_file_missing(monkeypatch, tmp_path):
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(load_data, "CLEANED_JSON_PATH", missing)

    with pytest.raises(FileNotFoundError):
        load_data.main()


@pytest.mark.db
def test_db_params_fallback(monkeypatch):
    # pylint: disable=protected-access
    monkeypatch.delenv("DATABASE_URL", raising=False)
    params = load_data._db_params()

    assert isinstance(params, dict)
    assert "dbname" in params
