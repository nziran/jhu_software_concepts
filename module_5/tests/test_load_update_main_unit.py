"""Unit tests for src.load_update.main()."""

import json

import pytest

import src.load_update as lu


@pytest.mark.db
def test_load_update_main_inserts_and_builds_term(monkeypatch, tmp_path, capsys):
    # --- make a real temp JSON file for lu.main() to read ---
    records = [
        # term_part + year_part -> "Fall 2026"
        {
            "program": "CS",
            "university": "Test U",
            "comments": "c1",
            "date_posted": "2026-02-10",
            "entry_url": "https://example.com/u1",
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "US",
            "GPA": "3.9",
            "gre_total": "330",
            "gre_v": "165",
            "gre_aw": "5.0",
            "degree_level": "MS",
        },
        # term_part only -> "Spring"
        {
            "program": "Bio",
            "university": "Test U2",
            "comments": "c2",
            "date_posted": "2026-02-10",
            "entry_url": "https://example.com/u2",
            "applicant_status": "Rejected",
            "start_term": "Spring",
            "start_year": "",
            "US/International": "International",
            "GPA": "",
            "gre_total": "abc",  # safe_float -> None
            "gre_v": None,
            "gre_aw": "4.0",
            "degree_level": "PhD",
        },
        # year_part only -> "2027"
        {
            "program": "Math",
            "university": "Test U3",
            "comments": "c3",
            "date_posted": "bad-date",  # parse_date -> None
            "entry_url": "https://example.com/u3",
            "applicant_status": "Waitlisted",
            "start_term": "",
            "start_year": "2027",
            "US/International": "US",
            "GPA": None,
            "gre_total": None,
            "gre_v": "160",
            "gre_aw": "",
            "degree_level": "MS",
        },
    ]

    cleaned_path = tmp_path / "cleaned_applicant_data_update.json"
    cleaned_path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(lu, "CLEANED_UPDATE_PATH", cleaned_path)

    # --- fake psycopg connection + cursor (no real DB) ---
    executed = []

    class FakeCursor:
        def __init__(self):
            self.rowcount = 0

        def execute(self, sql, params):
            executed.append((sql, params))
            # pretend first 2 insert, last one "conflict" (not inserted)
            if params["url"] in ("https://example.com/u1", "https://example.com/u2"):
                self.rowcount = 1
            else:
                self.rowcount = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_connect(**_kwargs):
        return FakeConn()

    monkeypatch.setattr(lu.psycopg, "connect", fake_connect)

    # Run
    lu.main()

    # Validate we executed 3 INSERT attempts
    assert len(executed) == 3

    # Validate term building branches
    p1 = executed[0][1]
    p2 = executed[1][1]
    p3 = executed[2][1]
    assert p1["term"] == "Fall 2026"
    assert p2["term"] == "Spring"
    assert p3["term"] == "2027"

    # Validate inserted count printed = 2 (rowcount==1 for first 2)
    out = capsys.readouterr().out
    assert "Inserted 2 new rows" in out


@pytest.mark.db
def test_load_update_main_raises_when_missing_file(monkeypatch, tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(lu, "CLEANED_UPDATE_PATH", missing_path)

    with pytest.raises(FileNotFoundError):
        lu.main()
