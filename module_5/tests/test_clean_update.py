import json
import runpy
import sys
import pytest

@pytest.mark.db
def test_clean_data_normalizes_fields_and_infers_term_year():
    import src.clean_update as cu

    records = [
        # Record A: messy HTML + whitespace + boolean is_international + season/year inference via comments
        {
            "program_name_raw": "  <b>Computer Science</b>   ",
            "university_raw": "  Johns   Hopkins   ",
            "comments": "Starting Fall 2026 cohort. <i>Excited</i>!",
            "date_posted": " 2026-02-10 ",
            "entry_url": " https://www.thegradcafe.com/result/12345?x=1#frag ",
            "applicant_status": "Accepted on 29 Jan",
            "accepted_date": "29 Jan",
            "rejected_date": "",
            "start_term": None,
            "start_year": None,
            "is_international": True,
            "gre_total": "330",
            "gre_v": "165",
            "gre_aw": "5.0",
            "degree_level": "MS",
            "degree": "Masters",
            "gpa": "3.90",
            "source_url": " https://www.thegradcafe.com/survey/?page=1 ",
            "scraped_at": " 2026-02-10T00:00:00Z ",
        },
        # Record B: uses alternate keys (program/university), month/year inference via status (ctx present),
        # string "false" -> American, GPA via "GPA" key, keeps provided start_term but infers missing year
        {
            "program": "Biology",
            "university": "Test University",
            "comments": "No enrollment context here.",
            "applicant_status": "Program begins Aug 2026",
            "start_term": "Fall",
            "start_year": None,
            "is_international": "false",
            "GPA": "3.50",
            "entry_url": "https://www.thegradcafe.com/result/999",
        },
        # Record C: inference should NOT trigger (no ctx words) even if text contains "Fall 2026"
        {
            "program": "Physics",
            "university": "Somewhere",
            "comments": "I wrote 'Fall 2026' but this is unrelated chatter.",
            "applicant_status": "Just chatting",
            "start_term": None,
            "start_year": None,
            "is_international": "International",
            "entry_url": None,
        },
        # Record D: normalize_us_international passes through None cleanly
        {
            "program": "Chemistry",
            "university": "Elsewhere",
            "comments": None,
            "applicant_status": None,
            "start_term": None,
            "start_year": None,
            "is_international": None,
            "entry_url": "",
        },
    ]

    cleaned = cu.clean_data(records)
    assert isinstance(cleaned, list)
    assert len(cleaned) == 4

    a, b, c, d = cleaned

    # A: HTML removed, whitespace collapsed, inference worked, boolean -> International
    assert a["program"] == "Computer Science"
    assert a["university"] == "Johns Hopkins"
    assert a["comments"] == "Starting Fall 2026 cohort. Excited!"
    assert a["start_term"] == "Fall"
    assert a["start_year"] == "2026"
    assert a["US/International"] == "International"
    assert a["GPA"] == "3.90"
    assert a["rejected_date"] is None  # "" -> None via _clean_text/_normalize_none

    # B: start_term kept, year inferred from Aug 2026, "false" -> American, GPA from "GPA"
    assert b["program"] == "Biology"
    assert b["university"] == "Test University"
    assert b["start_term"] == "Fall"
    assert b["start_year"] == "2026"
    assert b["US/International"] == "American"
    assert b["GPA"] == "3.50"

    # C: no ctx match => no inference even though text contains "Fall 2026"
    assert c["start_term"] is None
    assert c["start_year"] is None
    assert c["US/International"] == "International"

    # D: None stays None, empty entry_url -> None
    assert d["US/International"] is None
    assert d["entry_url"] is None

    # Schema guarantee: required keys exist
    for row in cleaned:
        for k in [
            "program", "university", "comments",
            "date_posted", "entry_url", "applicant_status",
            "accepted_date", "rejected_date",
            "start_term", "start_year",
            "US/International",
            "gre_total", "gre_v", "gre_aw",
            "degree_level", "degree", "GPA",
            "source_url", "scraped_at",
        ]:
            assert k in row


@pytest.mark.db
def test_load_data_accepts_list_and_rows_wrapper_and_rejects_invalid(tmp_path):
    import src.clean_update as cu

    # list form
    p1 = tmp_path / "list.json"
    p1.write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")
    out1 = cu.load_data(str(p1))
    assert isinstance(out1, list)
    assert out1[0]["a"] == 1

    # {"rows": [...]} form
    p2 = tmp_path / "rows.json"
    p2.write_text(json.dumps({"rows": [{"x": 10}]}), encoding="utf-8")
    out2 = cu.load_data(str(p2))
    assert out2 == [{"x": 10}]

    # invalid structure
    p3 = tmp_path / "bad.json"
    p3.write_text(json.dumps({"nope": 123}), encoding="utf-8")
    with pytest.raises(ValueError):
        cu.load_data(str(p3))


@pytest.mark.db
def test_module_main_writes_cleaned_output_file(tmp_path, monkeypatch):
    """
    Covers the __main__ block:
      - reads INPUT_JSON (default name)
      - writes OUTPUT_JSON (default name)
      - prints status
    """
    # Run in an isolated CWD so default filenames resolve into tmp_path
    monkeypatch.chdir(tmp_path)

    raw = [
        {
            "program_name_raw": "CS",
            "university_raw": "X",
            "comments": "Program begins September 2026",
            "date_posted": "2026-02-10",
            "entry_url": "https://www.thegradcafe.com/result/abc",
            "applicant_status": "Accepted",
            "is_international": "true",
        }
    ]

    (tmp_path / "applicant_data_update.json").write_text(json.dumps(raw), encoding="utf-8")

    # Ensure runpy doesn't warn about module already imported
    sys.modules.pop("src.clean_update", None)

     # Executes src.clean_update as a script (hits __main__ block)
    runpy.run_module("src.clean_update", run_name="__main__")

    out_path = tmp_path / "cleaned_applicant_data_update.json"
    assert out_path.exists()

    # Should be valid JSON list with cleaned fields and inferred term/year
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["start_term"] == "Fall"
    assert data[0]["start_year"] == "2026"
    assert data[0]["US/International"] == "International"

@pytest.mark.db
def test_clean_update_covers_remaining_branches():
    import src.clean_update as cu

    # line 88: _normalize_none returns non-strings unchanged
    assert cu._normalize_none(123) == 123

    # line 107: False → American
    assert cu._normalize_us_international(False) == "American"

    # line 120: unknown string → None
    assert cu._normalize_us_international("maybe") is None

    # line 137: cleaned text empty → no inference
    assert cu._extract_start_term_year("   ", None, "") == (None, None)

    # line 159: context present but no parseable term/year
    assert cu._extract_start_term_year("Program begins soon, TBD") == (None, None)