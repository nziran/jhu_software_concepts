# scrape_update.py - to pull only new data from Grad Cafe
import json
import os
import re
import time
import socket
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import psycopg

DB_NAME = "gradcafe"
DB_USER = "ziran"
DB_HOST = "localhost"
DB_PORT = 5432

UPDATE_OUTPUT_JSON = "applicant_data_update.json"
STOP_AFTER_PAGES_WITH_NO_NEW = 2


def load_existing_urls_from_db() -> set[str]:
    """
    Connects to PostgreSQL and loads all previously scraped GradCafe entry URLs.

    This allows the scraper to compare incoming survey entries against
    what already exists in the database, ensuring that only NEW records
    are processed and stored.

    Using a Python set enables constant-time lookup for fast duplicate detection.
    """
    urls = set()
    with psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        host=DB_HOST,
        port=DB_PORT
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL;")
            for (u,) in cur.fetchall():
                u = _canonical_result_url(u)  # make DB URLs match scraped canonical format
                if u:
                    urls.add(u)
    return urls

# -----------------------------
# Config
# -----------------------------
BASE_URL = "https://www.thegradcafe.com/survey/"

USER_AGENT = "Mozilla/5.0"
TIMEOUT_S = 30

# Survey pages (serial)
SURVEY_PAGES = 1550
DELAY_BETWEEN_SURVEY_PAGES_S = 0.25

# Detail pages (parallel)
FETCH_DETAILS = True
MAX_WORKERS = 8          # 6–10 is usually safe; higher may get throttled
RETRIES = 3
BACKOFF_S = 1.5

# Chunking / checkpointing
CHUNK_SURVEY_PAGES = 25                  # scrape this many survey pages, then parallel-fetch their details
DETAIL_FUTURE_TIMEOUT_S = 60             # per-result-page future timeout (avoid hanging forever)

# -----------------------------
# Helpers: HTTP
# -----------------------------
def _fetch_html(url: str, timeout: int = TIMEOUT_S) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _safe_fetch_html(url: str) -> str | None:
    for attempt in range(1, RETRIES + 1):
        try:
            return _fetch_html(url)
        except (HTTPError, URLError, socket.timeout, TimeoutError) as e:
            print(f"[fetch fail {attempt}/{RETRIES}] {url} :: {e}")
            time.sleep(BACKOFF_S * attempt)
    return None


# -----------------------------
# Helpers: cleaning/normalizing
# -----------------------------
LABEL_GARBAGE = {
    "GRE General:", "GRE Verbal:", "Analytical Writing:", "Notes",
    "Undergrad GPA", "Degree Type", "Degree's Country of Origin",
    "Timeline", "Admissions", "Results", "Logo"
}


def _normalize_none(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def _canonical_result_url(url: str | None) -> str | None:
    """
    Ensure canonical https://www.thegradcafe.com/result/<id>
    (force https + force www + drop query/fragment)
    """
    if not url:
        return None
    try:
        p = urlparse(url)
        clean = p._replace(fragment="", query="")

        scheme = "https"
        netloc = clean.netloc or "www.thegradcafe.com"
        if netloc == "thegradcafe.com":
            netloc = "www.thegradcafe.com"

        clean = clean._replace(scheme=scheme, netloc=netloc)
        return clean.geturl()
    except Exception:
        return url


def _valid_result_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        return (p.netloc.endswith("thegradcafe.com") and p.path.startswith("/result/"))
    except Exception:
        return False


def _clean_bad_label_values(v: str | None) -> str | None:
    """Drop obvious label-as-value artifacts."""
    if v is None:
        return None
    t = v.strip()
    if not t:
        return None
    if t in LABEL_GARBAGE:
        return None
    if t.endswith(":") and len(t) <= 25:
        return None
    return t


def _extract_float(s: str | None) -> str | None:
    """Extract a float-like number from a string (e.g., GPA 3.41, AW 4.0)."""
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return m.group(1) if m else None


def _extract_int(s: str | None) -> str | None:
    """Extract first integer from a string."""
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return m.group(1) if m else None


def _zero_to_none(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    if t in {"0", "0.0", "0.00"}:
        return None
    return t


def _degree_level(degree_type: str | None) -> str | None:
    """Rubric wants Masters vs PhD. Map common doctoral degrees into 'PhD'."""
    if not degree_type:
        return None
    t = degree_type.strip().lower()

    # doctoral-ish -> "PhD"
    if any(x in t for x in ["phd", "dphil", "doctor", "psyd", "edd", "drph", "dpt", "md", "jd", "dds", "dmd"]):
        return "PhD"

    # masters-ish -> "Masters"
    if "master" in t or re.search(r"\b(ma|ms|mfa|meng|mpa|mpp|mph|msc|mme|msw|mha)\b", t):
        return "Masters"

    return None


# -----------------------------
# Survey page parsing
# -----------------------------
def _clean_listpage_comments(txt: str | None) -> str | None:
    """Clean list-page comment cell which includes UI filler."""
    if not txt:
        return None
    t = txt
    t = re.sub(r"\bTotal comments\b", "", t, flags=re.I)
    t = re.sub(r"\bOpen options\b", "", t, flags=re.I)
    t = re.sub(r"\bSee More\b", "", t, flags=re.I)
    t = re.sub(r"\bReport\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t if t else None


def _extract_entry_url(row_soup, source_url: str) -> str | None:
    """Find first /result/<id> link in the row and canonicalize."""
    for a in row_soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("/result/") or "/result/" in href:
            full = urljoin(source_url, href)
            return _canonical_result_url(full)
    return None


def _parse_decision(decision_text: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Return (status, accepted_date, rejected_date) based on survey decision column.
    Examples: "Accepted on 29 Jan", "Rejected on 28 Jan", "Waitlisted on ..."
    """
    if not decision_text:
        return None, None, None

    accepted_date = None
    rejected_date = None
    status = None

    m = re.search(r"^(Accepted|Rejected|Wait listed|Waitlisted)\s+on\s+(.+)$", decision_text, flags=re.I)
    if m:
        status = m.group(1).strip().title().replace("Wait Listed", "Waitlisted")
        d = _normalize_none(m.group(2))
        if status.lower() == "accepted":
            accepted_date = d
        elif status.lower() == "rejected":
            rejected_date = d
    else:
        status = decision_text.strip()

    return _normalize_none(status), accepted_date, rejected_date


def _parse_survey_page(html: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")

    records: list[dict] = []
    scraped_at_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        university = _normalize_none(cols[0].get_text(" ", strip=True))
        program = _normalize_none(cols[1].get_text(" ", strip=True))
        date_posted = _normalize_none(cols[2].get_text(" ", strip=True))
        decision_text = _normalize_none(cols[3].get_text(" ", strip=True))
        comments_text = _clean_listpage_comments(cols[4].get_text(" ", strip=True))

        status, accepted_date, rejected_date = _parse_decision(decision_text)
        entry_url = _extract_entry_url(row, source_url)

        record = {
            "program_name_raw": program,
            "university_raw": university,
            "comments": comments_text,
            "date_posted": date_posted,
            "entry_url": entry_url,
            "applicant_status": status,
            "accepted_date": accepted_date,
            "rejected_date": rejected_date,

            # detail fields (filled later)
            "start_term": None,
            "start_year": None,

            # IMPORTANT: keep this RAW as True/False/None for clean.py to convert
            "is_international": None,

            "gre_total": None,
            "gre_v": None,
            "gre_aw": None,
            "degree": None,
            "degree_level": None,
            "gpa": None,

            "source_url": source_url,
            "scraped_at": scraped_at_iso,
        }
        records.append(record)

    return records


# -----------------------------
# Detail page parsing (/result/<id>)
# -----------------------------
def _parse_result_page(entry_url: str) -> dict:
    """
    Returns ONLY fields we want to merge into the raw record.
    NOTE: We DO NOT include 'origin' in output.
    We compute boolean is_international from origin internally, then discard origin.
    """
    html = _safe_fetch_html(entry_url)
    if not html:
        return {
            "degree": None,
            "degree_level": None,
            "is_international": None,
            "gpa": None,
            "gre_total": None,
            "gre_v": None,
            "gre_aw": None,
            "detail_comments": None,
            "start_term": None,
            "start_year": None,
        }

    soup = BeautifulSoup(html, "html.parser")
    lines = soup.get_text("\n", strip=True).splitlines()

    def get_after(label: str) -> str | None:
        for i, ln in enumerate(lines):
            if ln.strip() == label and i + 1 < len(lines):
                return _normalize_none(lines[i + 1])
        return None

    degree = _normalize_none(get_after("Degree Type"))
    origin = _normalize_none(get_after("Degree's Country of Origin"))

    notes = _normalize_none(get_after("Notes"))
    if notes and notes.strip() in LABEL_GARBAGE:
        notes = None

    # These labels are often absent on GradCafe; keep None if missing
    start_term = _normalize_none(get_after("Term"))
    start_year = _normalize_none(get_after("Year"))

    gpa_raw = _clean_bad_label_values(_zero_to_none(get_after("Undergrad GPA")))
    gre_total_raw = _clean_bad_label_values(_zero_to_none(get_after("GRE General:")))
    gre_v_raw = _clean_bad_label_values(_zero_to_none(get_after("GRE Verbal:")))
    gre_aw_raw = _clean_bad_label_values(_zero_to_none(get_after("Analytical Writing:")))

    gpa = _extract_float(gpa_raw)
    gre_total = _extract_int(gre_total_raw)
    gre_v = _extract_int(gre_v_raw)
    gre_aw = _extract_float(gre_aw_raw)

    # Compute boolean only; do not keep origin in dataset
    is_international = None
    if origin:
        # keep it strict: only "American" maps to False, everything else -> True
        is_international = (origin.strip().lower() != "american")

    return {
        "degree": degree,
        "degree_level": _degree_level(degree),
        "is_international": is_international,
        "gpa": gpa,
        "gre_total": gre_total,
        "gre_v": gre_v,
        "gre_aw": gre_aw,
        "detail_comments": notes,
        "start_term": start_term,
        "start_year": start_year,
    }


# -----------------------------
# I/O
# -----------------------------
def save_data(records: list[dict], out_path: str = UPDATE_OUTPUT_JSON) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def load_data(path: str = UPDATE_OUTPUT_JSON) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# Parallel detail fetch (for a subset of records)
# -----------------------------
def _fetch_details_for_indices(records: list[dict], indices: list[int]) -> tuple[int, int]:
    """
    Fetch detail pages in parallel for only the records at `indices`.
    Returns (updated, failed).
    """
    tasks: list[tuple[int, str]] = []
    for i in indices:
        u = _canonical_result_url(records[i].get("entry_url"))
        if _valid_result_url(u):
            records[i]["entry_url"] = u
            tasks.append((i, u))

    if not tasks:
        return 0, 0

    updated = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        future_map = {ex.submit(_parse_result_page, url): (i, url) for (i, url) in tasks}

        for fut in as_completed(future_map):
            i, url = future_map[fut]
            try:
                extra = fut.result(timeout=DETAIL_FUTURE_TIMEOUT_S)
            except Exception as e:
                failed += 1
                print(f"[details worker error] {url} :: {e}")
                continue

            r = records[i]

            # Prefer detail notes over list-page comments
            if extra.get("detail_comments"):
                r["comments"] = extra["detail_comments"]

            # overwrite detail fields (raw storage)
            for k in ["degree", "degree_level", "gpa", "gre_total", "gre_v", "gre_aw", "start_term", "start_year"]:
                r[k] = extra.get(k)

            # IMPORTANT: always set raw boolean; no origin gating
            r["is_international"] = extra.get("is_international")

            # final safety
            for k in ["gpa", "gre_total", "gre_v", "gre_aw"]:
                r[k] = _clean_bad_label_values(r.get(k))

            updated += 1

    return updated, failed


# -----------------------------
# Main scrape pipeline (CHUNKED) - REVISED TO ONLY PULL NEW DATA FROM GRAD CAFE
# -----------------------------
def scrape_data(resume: bool = True) -> None:
    # Load all URLs already stored in PostgreSQL so we can avoid re-scraping
    # previously captured GradCafe entries
    existing_urls = load_existing_urls_from_db()
    # Diagnostic output — confirms database connection and existing record count
    print(f"[db] loaded {len(existing_urls)} existing urls from postgres")

    # Stores new records discovered during this scraping session
    records: list[dict] = []

    # Initialize in-memory duplicate tracking using database URLs
    # Ensures scraper skips entries already stored
    seen_urls: set[str] = set(existing_urls)  # reuse your existing seen_urls logic

    # Update scraper: do not resume from any local JSON checkpoint.
    # We dedupe using URLs already stored in PostgreSQL.

    chunk_new_indices: list[int] = []
    total_failed_details = 0
    pages_with_no_new = 0

    try:
        for page in range(1, SURVEY_PAGES + 1):
            url = f"{BASE_URL}?page={page}"
            print(f"[survey] page {page}: {url}")

            html = _safe_fetch_html(url)
            if not html:
                print("  -> skipped (fetch failed)")
                continue

            page_records = _parse_survey_page(html, url)

            added = 0
            for rec in page_records:
                u = _canonical_result_url(rec.get("entry_url"))
                rec["entry_url"] = u

                if not _valid_result_url(u):
                    continue

                if u in seen_urls:
                    continue

                seen_urls.add(u)
                records.append(rec)
                chunk_new_indices.append(len(records) - 1)
                added += 1

            print(
                f"  parsed={len(page_records)} added={added} total={len(records)} "
                f"chunk_pending={len(chunk_new_indices)}"
            )

            # Early stop: if we see several pages in a row with no new entries,
            # we assume we've reached older data already stored in the DB.
            if added == 0:
                pages_with_no_new += 1
            else:
                pages_with_no_new = 0

            if pages_with_no_new >= STOP_AFTER_PAGES_WITH_NO_NEW:
                print(
                    f"[early stop] {STOP_AFTER_PAGES_WITH_NO_NEW} consecutive pages with no new rows. Stopping."
                )

                # Fetch details for remaining new records before stopping
                if FETCH_DETAILS and chunk_new_indices:
                    print(f"[details] early-stop final fetch for {len(chunk_new_indices)} rows ...")
                    updated, failed = _fetch_details_for_indices(records, chunk_new_indices)
                    total_failed_details += failed
                    print(f"[details] early-stop done: updated={updated}, failed={failed}")
                    chunk_new_indices = []

                    save_data(records, UPDATE_OUTPUT_JSON)
                    print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

                break

            # If we've completed a survey chunk, fetch details for that chunk in parallel
            if FETCH_DETAILS and (page % CHUNK_SURVEY_PAGES == 0) and chunk_new_indices:
                print(f"[details] fetching details for last {len(chunk_new_indices)} new rows (workers={MAX_WORKERS}) ...")
                updated, failed = _fetch_details_for_indices(records, chunk_new_indices)
                total_failed_details += failed
                print(f"[details] chunk done: updated={updated}, failed={failed}, total_failed_details={total_failed_details}")
                chunk_new_indices = []

                save_data(records, UPDATE_OUTPUT_JSON)
                print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

            # Periodic checkpoint even if details off
            if page % CHUNK_SURVEY_PAGES == 0 and not FETCH_DETAILS:
                save_data(records, UPDATE_OUTPUT_JSON)
                print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

            time.sleep(DELAY_BETWEEN_SURVEY_PAGES_S)

    except KeyboardInterrupt:
        # Graceful exit: save what we have so far
        print("\n[interrupt] Ctrl-C received. Saving update data...")
        save_data(records, UPDATE_OUTPUT_JSON)
        print(f"[interrupt] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")
        # still attempt details for pending chunk? NO—keep it simple/fast on interrupt.

    # Final: if any remaining new records not yet detail-fetched, do them now
    if FETCH_DETAILS and chunk_new_indices:
        print(f"[details] final fetch for remaining {len(chunk_new_indices)} rows ...")
        updated, failed = _fetch_details_for_indices(records, chunk_new_indices)
        total_failed_details += failed
        print(f"[details] final done: updated={updated}, failed={failed}, total_failed_details={total_failed_details}")

    # Defensive: ensure all expected keys exist
    required_keys = [
        "program_name_raw", "university_raw", "comments", "date_posted", "entry_url",
        "applicant_status", "accepted_date", "rejected_date",
        "start_term", "start_year", "is_international",
        "gre_total", "gre_v", "gre_aw", "degree_level", "degree", "gpa",
        "source_url", "scraped_at",
    ]
    for r in records:
        for k in required_keys:
            r.setdefault(k, None)

    save_data(records, UPDATE_OUTPUT_JSON)
    print(f"[final] saved {len(records)} records -> {UPDATE_OUTPUT_JSON}")
    print(f"[final] total_failed_details={total_failed_details}")


if __name__ == "__main__":
    # Update scrape: pulls only NEW GradCafe entries (deduped against PostgreSQL)
    scrape_data()