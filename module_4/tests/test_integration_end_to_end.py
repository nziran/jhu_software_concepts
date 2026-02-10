import json
import re
import pytest
import psycopg


TEST_URLS = [
    "https://example.com/integration-1",
    "https://example.com/integration-2",
    "https://example.com/integration-3",
]


def _connect():
    return psycopg.connect(dbname="gradcafe", user="ziran", host="localhost", port=5432)


def _delete_test_rows(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM applicants WHERE url = ANY(%s);", (TEST_URLS,))
    conn.commit()


@pytest.mark.integration
def test_end_to_end_pull_update_render(monkeypatch, tmp_path, client):
    """
    End-to-end (offline):
      - Inject fake pipeline that loads known records (no scrape)
      - POST /pull-data succeeds and rows are inserted
      - POST /update-analysis succeeds (not busy)
      - GET /analysis renders Answer: labels and (if present) two-decimal percentages
    """
    import src.app as appmod
    import src.load_update as lu

    # Ensure clean slate
    with _connect() as conn:
        _delete_test_rows(conn)

    # Fake records that load_update.py understands
    fake_records = [
        {
            "program": "Physics",
            "university": "Integration U",
            "comments": "Inserted via integration test",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[0],
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "US",
            "GPA": "3.80",
            "gre_total": "325",
            "gre_v": "162",
            "gre_aw": "4.5",
            "degree_level": "MS",
        },
        {
            "program": "Chemistry",
            "university": "Integration U",
            "comments": "Inserted via integration test",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[1],
            "applicant_status": "Rejected",
            "start_term": "Spring",
            "start_year": "2026",
            "US/International": "International",
            "GPA": "3.40",
            "gre_total": "315",
            "gre_v": "158",
            "gre_aw": "4.0",
            "degree_level": "PhD",
        },
    ]

    cleaned_path = tmp_path / "cleaned_applicant_data_update.json"
    cleaned_path.write_text(json.dumps(fake_records), encoding="utf-8")

    # Point loader at our temp file
    monkeypatch.setattr(lu, "CLEANED_UPDATE_PATH", cleaned_path)

    # Make /pull-data synchronous + offline by overriding pipeline
    def fake_pipeline():
        lu.main()

    monkeypatch.setattr(appmod, "run_update_pipeline", fake_pipeline)

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(appmod.threading, "Thread", ImmediateThread)

    # Ensure not busy
    appmod.job_running = False

    # 1) Pull (JSON request)
    resp = client.post("/pull-data", headers={"Accept": "application/json"})
    assert resp.status_code in (200, 202)

    # Verify DB rows exist
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants WHERE url = ANY(%s);", (TEST_URLS,))
            count = cur.fetchone()[0]
        assert count == 2

    # 2) Update analysis (JSON request)
    resp2 = client.post("/update-analysis", headers={"Accept": "application/json"})
    assert resp2.status_code == 200

    # 3) Render
    resp3 = client.get("/analysis")
    assert resp3.status_code == 200
    html = resp3.get_data(as_text=True)

    # Must show Answer labels
    assert "Answer:" in html

    # Percent formatting: if there are percentages, they must be NN.NN%
    percents = re.findall(r"\b\d+(?:\.\d+)?%\b", html)
    if percents:
        assert all(re.match(r"^\d+\.\d{2}%$", p) for p in percents)

    # Cleanup
    with _connect() as conn:
        _delete_test_rows(conn)


@pytest.mark.integration
def test_multiple_pulls_overlapping_data_is_idempotent(monkeypatch, tmp_path, client):
    """
    Multiple pulls:
      - run /pull-data twice with overlapping urls
      - DB should not duplicate rows (ON CONFLICT(url) DO NOTHING)
    """
    import src.app as appmod
    import src.load_update as lu

    with _connect() as conn:
        _delete_test_rows(conn)

    # First pull inserts url[0], url[1]
    records_1 = [
        {
            "program": "CS",
            "university": "Integration U",
            "comments": "first pull",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[0],
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "US",
            "GPA": "4.00",
            "gre_total": "330",
            "gre_v": "165",
            "gre_aw": "5.0",
            "degree_level": "MS",
        },
        {
            "program": "Bio",
            "university": "Integration U",
            "comments": "first pull",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[1],
            "applicant_status": "Rejected",
            "start_term": "Spring",
            "start_year": "2026",
            "US/International": "International",
            "GPA": "3.50",
            "gre_total": "320",
            "gre_v": "160",
            "gre_aw": "4.0",
            "degree_level": "PhD",
        },
    ]

    # Second pull overlaps url[1] and adds url[2]
    records_2 = [
        dict(records_1[1]),
        {
            "program": "Math",
            "university": "Integration U",
            "comments": "second pull",
            "date_posted": "2026-02-10",
            "entry_url": TEST_URLS[2],
            "applicant_status": "Accepted",
            "start_term": "Fall",
            "start_year": "2026",
            "US/International": "US",
            "GPA": "3.70",
            "gre_total": "318",
            "gre_v": "159",
            "gre_aw": "4.5",
            "degree_level": "MS",
        },
    ]

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(appmod.threading, "Thread", ImmediateThread)

    def run_pull_with(records):
        cleaned_path = tmp_path / "cleaned_applicant_data_update.json"
        cleaned_path.write_text(json.dumps(records), encoding="utf-8")
        monkeypatch.setattr(lu, "CLEANED_UPDATE_PATH", cleaned_path)

        def fake_pipeline():
            lu.main()

        monkeypatch.setattr(appmod, "run_update_pipeline", fake_pipeline)
        appmod.job_running = False

        r = client.post("/pull-data", headers={"Accept": "application/json"})
        assert r.status_code in (200, 202)

    run_pull_with(records_1)
    run_pull_with(records_2)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants WHERE url = ANY(%s);", (TEST_URLS,))
            count = cur.fetchone()[0]
        # unique URLs: 0,1,2 should exist exactly once
        assert count == 3
  