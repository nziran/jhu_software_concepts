import json
import pytest

import src.scrape_update as su


@pytest.mark.analysis
def test_parse_decision_variants():
    status, acc, rej = su._parse_decision("Accepted on 29 Jan")
    assert status == "Accepted"
    assert acc == "29 Jan"
    assert rej is None

    status, acc, rej = su._parse_decision("Rejected on 02 Feb")
    assert status == "Rejected"
    assert acc is None
    assert rej == "02 Feb"

    status, acc, rej = su._parse_decision("Wait listed on 03 Feb")
    assert status == "Waitlisted"


@pytest.mark.analysis
def test_clean_listpage_comments_strips_ui():
    txt = "Total comments Open options See More Report  hello   world "
    assert su._clean_listpage_comments(txt) == "hello world"


@pytest.mark.web
def test_parse_survey_page_extracts_rows_and_urls():
    html = """
    <html><body>
    <table>
      <tr>
        <td>Test University</td>
        <td>Computer Science</td>
        <td>2026-02-10</td>
        <td>Accepted on 29 Jan</td>
        <td>Total comments See More My comment</td>
        <td><a href="/result/12345">link</a></td>
      </tr>
      <tr>
        <td>Other University</td>
        <td>Biology</td>
        <td>2026-02-10</td>
        <td>Rejected on 28 Jan</td>
        <td>Report Another comment</td>
        <td><a href="https://www.thegradcafe.com/result/999">link</a></td>
      </tr>
    </table>
    </body></html>
    """
    source_url = "https://www.thegradcafe.com/survey/?page=1"
    records = su._parse_survey_page(html, source_url)

    assert len(records) == 2
    assert records[0]["university_raw"] == "Test University"
    assert records[0]["program_name_raw"] == "Computer Science"
    assert records[0]["applicant_status"] == "Accepted"
    assert records[0]["accepted_date"] == "29 Jan"
    assert records[0]["entry_url"].startswith("https://www.thegradcafe.com/result/")

    assert records[1]["applicant_status"].lower().startswith("rejected")
    assert records[1]["rejected_date"] == "28 Jan"


@pytest.mark.analysis
def test_save_and_load_data_round_trip(tmp_path, monkeypatch):
    out = tmp_path / "update.json"
    monkeypatch.setattr(su, "UPDATE_OUTPUT_JSON", str(out))

    rows = [{"entry_url": "https://www.thegradcafe.com/result/1", "program_name_raw": "CS"}]
    su.save_data(rows, out_path=str(out))

    loaded = su.load_data(path=str(out))
    assert loaded == rows