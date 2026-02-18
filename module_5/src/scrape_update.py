"""
Scrape new GradCafe applicant records and write incremental update JSON.

This module scrapes GradCafe survey pages, de-duplicates entries against
existing Postgres URLs, optionally fetches per-applicant detail pages in
parallel, and writes a raw update dataset for the clean/load ETL pipeline.

Database credentials are read exclusively from environment variables.
"""
import json
import re
import time
import os
import socket
from datetime import datetime, timezone
import urllib.request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import psycopg



# -----------------------------
# Output settings
# -----------------------------
UPDATE_OUTPUT_JSON = "applicant_data_update.json"

# Stop scraping once we hit N consecutive survey pages that contain zero new entries
STOP_AFTER_PAGES_WITH_NO_NEW = 2


def load_existing_urls_from_db() -> set[str]:
    """
    Load all previously stored GradCafe entry URLs from Postgres.

    This is the core de-duplication mechanism:
    - survey rows are parsed
    - each /result/<id> URL is canonicalized
    - if it already exists in the database, it is skipped
    """
    urls = set()
    with psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    ) as conn:

        with conn.cursor() as cur:
            cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL;")
            for (u,) in cur.fetchall():
                u = _canonical_result_url(u)  # normalize DB URLs to match scraped URLs
                if u:
                    urls.add(u)
    return urls


# -----------------------------
# Network + scraping configuration
# -----------------------------
BASE_URL = "https://www.thegradcafe.com/survey/"
USER_AGENT = "Mozilla/5.0"
TIMEOUT_S = 30

# The GradCafe survey supports pagination; this is the max page we attempt
SURVEY_PAGES = 1550
DELAY_BETWEEN_SURVEY_PAGES_S = 0.25

# /result/<id> detail scraping (parallel)
FETCH_DETAILS = True
MAX_WORKERS = 8          # moderate concurrency to reduce throttling risk
RETRIES = 3
BACKOFF_S = 1.5

# Chunking: scrape a block of survey pages, then fetch details for that block
CHUNK_SURVEY_PAGES = 25
DETAIL_FUTURE_TIMEOUT_S = 60  # per detail-page future timeout


# -----------------------------
# Helpers: HTTP fetching
# -----------------------------
def _fetch_html(url: str, timeout: int = TIMEOUT_S) -> str:
    req = urllib_request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def _safe_fetch_html(url: str) -> str | None:
    """
    Fetch HTML with retries + backoff.
    Returns None if all attempts fail.
    """
    for attempt in range(1, RETRIES + 1):
        try:
            return _fetch_html(url)
        except (HTTPError, URLError, socket.timeout, TimeoutError) as e:
            print(f"[fetch fail {attempt}/{RETRIES}] {url} :: {e}")
            time.sleep(BACKOFF_S * attempt)
    return None


# -----------------------------
# Helpers: normalization
# -----------------------------
# These are labels that sometimes appear in parsed text where values should be.
LABEL_GARBAGE = {
    "GRE General:", "GRE Verbal:", "Analytical Writing:", "Notes",
    "Undergrad GPA", "Degree Type", "Degree's Country of Origin",
    "Timeline", "Admissions", "Results", "Logo"
}


def _normalize_none(s: str | None) -> str | None:
    """Strip strings; convert empty/whitespace-only strings to None."""
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def _canonical_result_url(url: str | None) -> str | None:
    """
    Canonicalize result URLs into a consistent format:
      https://www.thegradcafe.com/result/<id>
    This also removes query params and fragments.
    """
    if not url:
        return None
    try:
        p = urlparse(url)
        clean = p._replace(fragment="", query="")

        # enforce https and www
        scheme = "https"
        netloc = clean.netloc or "www.thegradcafe.com"
        if netloc == "thegradcafe.com":
            netloc = "www.thegradcafe.com"

        clean = clean._replace(scheme=scheme, netloc=netloc)
        return clean.geturl()
    except Exception:
        return url


def _valid_result_url(url: str | None) -> bool:
    """Basic validation: must be /result/<id> on thegradcafe.com."""
    if not url:
        return False
    try:
        p = urlparse(url)
        return (p.netloc.endswith("thegradcafe.com") and p.path.startswith("/result/"))
    except Exception:
        return False


def _clean_bad_label_values(v: str | None) -> str | None:
    """Drop values that are actually UI/label artifacts."""
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
    """Extract a float-like substring from a string (e.g., 'GPA: 3.41' -> '3.41')."""
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return m.group(1) if m else None


def _extract_int(s: str | None) -> str | None:
    """Extract first integer substring from a string."""
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return m.group(1) if m else None


def _zero_to_none(s: str | None) -> str | None:
    """Treat explicit zero values as missing (common placeholder noise)."""
    if s is None:
        return None
    t = s.strip()
    if t in {"0", "0.0", "0.00"}:
        return None
    return t


def _degree_level(degree_type: str | None) -> str | None:
    """
    Normalize degree types into broad categories:
    - "PhD" for doctoral/professional doctorate-like strings
    - "Masters" for common master's strings
    """
    if not degree_type:
        return None
    t = degree_type.strip().lower()

    if any(
    x in t
    for x in [
        "phd",
        "dphil",
        "doctor",
        "psyd",
        "edd",
        "drph",
        "dpt",
        "md",
        "jd",
        "dds",
        "dmd",
        ]
    ):
        return "PhD"

    if "master" in t or re.search(r"\b(ma|ms|mfa|meng|mpa|mpp|mph|msc|mme|msw|mha)\b", t):
        return "Masters"

    return None


# -----------------------------
# Survey page parsing
# -----------------------------
def _clean_listpage_comments(txt: str | None) -> str | None:
    """Remove common UI phrases from the survey list-page comment column."""
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
    """Find the first /result/<id> link inside a survey row."""
    for a in row_soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("/result/") or "/result/" in href:
            full = urljoin(source_url, href)
            return _canonical_result_url(full)
    return None


def _parse_decision(decision_text: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Parse decision text from the survey list page.

    Returns:
      (status, accepted_date, rejected_date)

    Examples:
      "Accepted on 29 Jan" -> status="Accepted", accepted_date="29 Jan"
      "Rejected on 28 Jan" -> status="Rejected", rejected_date="28 Jan"
      "Waitlisted on ..."  -> status="Waitlisted"
    """
    if not decision_text:
        return None, None, None

    accepted_date = None
    rejected_date = None
    status = None

    m = re.search(
        r"^(Accepted|Rejected|Wait listed|Waitlisted)\s+on\s+(.+)$",
        decision_text,
        flags=re.I,
    )
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
    """
    Parse a survey list page and return a list of raw records.
    Note: detail fields (GPA/GRE/etc.) are filled later from /result/<id>.
    """
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

        records.append(
            {
                "program_name_raw": program,
                "university_raw": university,
                "comments": comments_text,
                "date_posted": date_posted,
                "entry_url": entry_url,
                "applicant_status": status,
                "accepted_date": accepted_date,
                "rejected_date": rejected_date,

                # Filled from detail pages later
                "start_term": None,
                "start_year": None,

                # Stored as a raw boolean; cleaned later into "American"/"International"
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
        )

    return records


# -----------------------------
# Detail page parsing (/result/<id>)
# -----------------------------
def _parse_result_page(entry_url: str) -> dict:
    """
    Fetch and parse a single /result/<id> page and return detail fields.

    Output is intentionally limited to fields that are merged into the raw record:
      - degree / degree_level
      - is_international (derived from origin)
      - gpa, gre_total, gre_v, gre_aw
      - detail_comments (to optionally replace list-page comments)
      - start_term / start_year (if present)
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

    # Helper: GradCafe result pages are label/value sequences in the full text,
    # so we search for a label and read the next line as the value.
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

    # These may be missing on many entries; keep None if absent
    start_term = _normalize_none(get_after("Term"))
    start_year = _normalize_none(get_after("Year"))

    # Metric extraction: strip placeholders, drop label artifacts, then parse numbers
    gpa_raw = _clean_bad_label_values(_zero_to_none(get_after("Undergrad GPA")))
    gre_total_raw = _clean_bad_label_values(_zero_to_none(get_after("GRE General:")))
    gre_v_raw = _clean_bad_label_values(_zero_to_none(get_after("GRE Verbal:")))
    gre_aw_raw = _clean_bad_label_values(_zero_to_none(get_after("Analytical Writing:")))

    gpa = _extract_float(gpa_raw)
    gre_total = _extract_int(gre_total_raw)
    gre_v = _extract_int(gre_v_raw)
    gre_aw = _extract_float(gre_aw_raw)

    # Convert origin into a strict boolean:
    # - "American" -> False
    # - anything else (non-empty) -> True
    is_international = None
    if origin:
        is_international = origin.strip().lower() != "american"

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
# JSON I/O
# -----------------------------
def save_data(records: list[dict], out_path: str = UPDATE_OUTPUT_JSON) -> None:
    """Write raw update records to disk as JSON."""
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def load_data(path: str = UPDATE_OUTPUT_JSON) -> list[dict]:
    """Load raw update records from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# Parallel detail fetch for a subset of records
# -----------------------------
def _fetch_details_for_indices(records: list[dict], indices: list[int]) -> tuple[int, int]:
    """
    Fetch /result/<id> detail pages in parallel for only the specified record indices.

    Returns:
      (updated_count, failed_count)
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
        # Map each future back to its record index and URL
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

            # Prefer the detail "Notes" over list-page comments when available
            if extra.get("detail_comments"):
                r["comments"] = extra["detail_comments"]

            # Overwrite the detail fields in the raw record
            for k in [
                "degree",
                "degree_level",
                "gpa",
                "gre_total",
                "gre_v",
                "gre_aw",
                "start_term",
                "start_year",
            ]:
                r[k] = extra.get(k)

            # Store international status as raw boolean
            r["is_international"] = extra.get("is_international")

            # Final safety cleanup for numeric-ish fields
            for k in ["gpa", "gre_total", "gre_v", "gre_aw"]:
                r[k] = _clean_bad_label_values(r.get(k))

            updated += 1

    return updated, failed


# -----------------------------
# Main scrape pipeline (pull NEW rows only)
# -----------------------------
def scrape_data(resume: bool = True) -> None:
    """
    Scrape survey pages from newest to older, collecting only entries that are
    not already present in Postgres. Optionally fetch detail pages in chunks.
    """
    existing_urls = load_existing_urls_from_db()
    print(f"[db] loaded {len(existing_urls)} existing urls from postgres")

    # New records found during this run
    records: list[dict] = []

    # In-memory duplicate tracking begins with database URLs
    seen_urls: set[str] = set(existing_urls)

    # Track which newly-added records still need detail fetching
    chunk_new_indices: list[int] = []
    total_failed_details = 0

    # Early stop tracking
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

                # Skip rows already in DB (or already seen during this run)
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

            # If we hit consecutive pages with no new rows, stop scanning older pages
            if added == 0:
                pages_with_no_new += 1
            else:
                pages_with_no_new = 0

            if pages_with_no_new >= STOP_AFTER_PAGES_WITH_NO_NEW:
                print(
                    f"[early stop] {STOP_AFTER_PAGES_WITH_NO_NEW} consecutive pages "
                    "with no new rows. Stopping."
                )
                # Before stopping, fetch details for any remaining new rows in this chunk
                if FETCH_DETAILS and chunk_new_indices:
                    print(f"[details] early-stop final fetch for {len(chunk_new_indices)} rows ...")
                    updated, failed = _fetch_details_for_indices(records, chunk_new_indices)
                    total_failed_details += failed
                    print(f"[details] early-stop done: updated={updated}, failed={failed}")
                    chunk_new_indices = []

                    save_data(records, UPDATE_OUTPUT_JSON)
                    print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

                break

            # Chunk boundary: fetch details for accumulated new rows
            if (
                FETCH_DETAILS
                and (page % CHUNK_SURVEY_PAGES == 0)
                and chunk_new_indices
            ):
                print(
                    f"[details] fetching details for last "
                    f"{len(chunk_new_indices)} new rows "
                    f"(workers={MAX_WORKERS}) ..."
                )

                updated, failed = _fetch_details_for_indices(
                    records,
                    chunk_new_indices,
                )

                total_failed_details += failed

                print(
                    f"[details] chunk done: updated={updated}, "
                    f"failed={failed}, "
                    f"total_failed_details={total_failed_details}"
                )

                chunk_new_indices = []

                save_data(records, UPDATE_OUTPUT_JSON)
                print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

            # If detail fetching is disabled, still checkpoint on the same schedule
            if page % CHUNK_SURVEY_PAGES == 0 and not FETCH_DETAILS:
                save_data(records, UPDATE_OUTPUT_JSON)
                print(f"[checkpoint] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

            time.sleep(DELAY_BETWEEN_SURVEY_PAGES_S)

    except KeyboardInterrupt:
        # Save partial results on Ctrl-C so progress isn't lost
        print("\n[interrupt] Ctrl-C received. Saving update data...")
        save_data(records, UPDATE_OUTPUT_JSON)
        print(f"[interrupt] saved {len(records)} rows -> {UPDATE_OUTPUT_JSON}")

    # Final detail fetch for any records still pending detail extraction
    if FETCH_DETAILS and chunk_new_indices:
        print(f"[details] final fetch for remaining {len(chunk_new_indices)} rows ...")
        updated, failed = _fetch_details_for_indices(records, chunk_new_indices)
        total_failed_details += failed
        print(
            f"[details] final done: updated={updated}, "
            f"failed={failed}, "
            f"total_failed_details={total_failed_details}"
        )

    # Defensive schema: guarantee keys exist even if some pages were missing fields
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
    # Pulls only NEW GradCafe entries (de-duped against Postgres URLs)
    scrape_data()
