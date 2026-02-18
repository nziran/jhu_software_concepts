"""
Scrape new GradCafe applicant records and write incremental update JSON.

This module fetches raw records, performs minimal extraction, optionally checks
the DB for already-seen URLs, and saves the update dataset for the clean/load
pipeline.
"""

# pylint: disable=too-many-locals

import json
import os
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
import urllib.request as urllib_request

from bs4 import BeautifulSoup
import psycopg

# -----------------------------
# Database connection (Step 3)
# -----------------------------
def _connect():
    """
    Create a DB connection using env vars only.
    No hard-coded credentials.
    """
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

# -----------------------------
# Output settings
# -----------------------------
UPDATE_OUTPUT_JSON = "applicant_data_update.json"

# Stop scraping once we hit N consecutive survey pages that contain zero new entries
STOP_AFTER_PAGES_WITH_NO_NEW = 2

# Maximum number of URLs fetched from DB (Step 2 SQL safety clamp)
MAX_DB_URL_FETCH = 100


def load_existing_urls_from_db() -> set[str]:
    """
    Load all previously stored GradCafe entry URLs from Postgres.

    This is the core de-duplication mechanism.
    """
    urls = set()

    with _connect() as conn:
        with conn.cursor() as cur:
            limit = max(1, min(int(MAX_DB_URL_FETCH), 100))  # clamp 1–100
            cur.execute(
                "SELECT url FROM applicants WHERE url IS NOT NULL LIMIT %s;",
                (limit,),
            )
            for (u,) in cur.fetchall():
                u = _canonical_result_url(u)
                if u:
                    urls.add(u)

    return urls


# -----------------------------
# Network + scraping configuration
# -----------------------------
BASE_URL = "https://www.thegradcafe.com/survey/"
USER_AGENT = "Mozilla/5.0"
TIMEOUT_S = 30

SURVEY_PAGES = 1550
DELAY_BETWEEN_SURVEY_PAGES_S = 0.25

FETCH_DETAILS = True
MAX_WORKERS = 8
RETRIES = 3
BACKOFF_S = 1.5

CHUNK_SURVEY_PAGES = 25
DETAIL_FUTURE_TIMEOUT_S = 60


# -----------------------------
# Helpers: HTTP fetching
# -----------------------------
def _fetch_html(url: str, timeout: int = TIMEOUT_S) -> str:
    req = urllib_request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
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
# Helpers: normalization
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
    except (TypeError, ValueError):
        return url


def _valid_result_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        return p.netloc.endswith("thegradcafe.com") and p.path.startswith("/result/")
    except (TypeError, ValueError):
        return False


# -----------------------------
# (rest of file unchanged)
# -----------------------------

if __name__ == "__main__":
    scrape_data()
