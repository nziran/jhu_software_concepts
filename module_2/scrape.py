import json
import time
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com/survey/"
OUTPUT_JSON = "applicant_data.json"


def _fetch_html(url: str) -> str:
    """Private helper: fetch HTML using urllib (required)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    req = Request(url, headers=headers)
    with urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_result_page(entry_url: str) -> dict:
    """
    Given a GradCafe /result/<id> page, return additional fields required by the rubric.
    Strategy: grab text as lines, then for each label take the next line as the value.
    """
    html = _fetch_html(entry_url)
    soup = BeautifulSoup(html, "html.parser")
    lines = soup.get_text("\n", strip=True).splitlines()

    def get_after(label: str) -> str | None:
        for i, ln in enumerate(lines):
            if ln.strip() == label and i + 1 < len(lines):
                val = lines[i + 1].strip()
                return val if val else None
        return None

    degree = get_after("Degree Type")
    origin = get_after("Degree's Country of Origin")  # "American" or other

    gpa = get_after("Undergrad GPA")
    gre_total = get_after("GRE General:")
    gre_v = get_after("GRE Verbal:")
    gre_aw = get_after("Analytical Writing:")

    # Notes/comments: sometimes the next line is just "Timeline" (no real notes)
    notes = get_after("Notes")
    if notes and notes.lower() in {"timeline", "logo", "admissions", "results"}:
        notes = None

    # These exist on some results, not all
    start_term = get_after("Term")
    start_year = get_after("Year")

    # International / American
    is_international = None
    if origin:
        if origin.lower() == "american":
            is_international = False
        else:
            is_international = True

    # Many blank fields on GradCafe show as 0 / 0.00
    def zero_to_none(x: str | None) -> str | None:
        if x is None:
            return None
        if x.strip() in {"0", "0.0", "0.00"}:
            return None
        return x

    return {
        "degree": degree,
        "is_international": is_international,
        "gpa": zero_to_none(gpa),
        "gre_total": zero_to_none(gre_total),
        "gre_v": zero_to_none(gre_v),
        "gre_aw": zero_to_none(gre_aw),
        "start_term": start_term,
        "start_year": start_year,
        "comments": notes if notes else None,
    }


def _parse_page(html: str, source_url: str, fetch_details: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")

    records: list[dict] = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        university = cols[0].get_text(" ", strip=True)
        program = cols[1].get_text(" ", strip=True)
        date_posted = cols[2].get_text(" ", strip=True)
        decision_text = cols[3].get_text(" ", strip=True)
        comments_text = cols[4].get_text(" ", strip=True)

        # Clean comments cell text (list page is usually just UI words)
        comments_text = re.sub(r"\bTotal comments\b", "", comments_text, flags=re.I)
        comments_text = re.sub(r"\bOpen options\b", "", comments_text, flags=re.I)
        comments_text = re.sub(r"\bSee More\b", "", comments_text, flags=re.I)
        comments_text = re.sub(r"\bReport\b", "", comments_text, flags=re.I)
        comments_text = re.sub(r"\s+", " ", comments_text).strip()
        if comments_text == "":
            comments_text = None

        # Status + decision date
        status = None
        accepted_date = None
        rejected_date = None

        m = re.search(
            r"^(Accepted|Rejected|Wait listed|Waitlisted)\s+on\s+(.+)$",
            decision_text,
            flags=re.I,
        )
        if m:
            status = m.group(1).strip().title().replace("Wait Listed", "Waitlisted")
            decision_date = m.group(2).strip()

            if status.lower() == "accepted":
                accepted_date = decision_date
            elif status.lower() == "rejected":
                rejected_date = decision_date
        else:
            status = decision_text or None

        # Find entry URL: /result/<id>
        entry_url = None
        for a in row.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/result/") or "/result/" in href:
                entry_url = urljoin(source_url, href)
                break

        # Pull extra fields from the result page (slower: makes extra requests)
        extra = {}
        if fetch_details and entry_url:
            extra = _parse_result_page(entry_url)

        record = {
            "program_name_raw": program or None,
            "university_raw": university or None,
            "comments": extra.get("comments") or comments_text,
            "date_posted": date_posted or None,
            "entry_url": entry_url,
            "applicant_status": status,
            "accepted_date": accepted_date,
            "rejected_date": rejected_date,
            "start_term": extra.get("start_term"),
            "start_year": extra.get("start_year"),
            "is_international": extra.get("is_international"),
            "gre_total": extra.get("gre_total"),
            "gre_v": extra.get("gre_v"),
            "gre_aw": extra.get("gre_aw"),
            "degree": extra.get("degree"),
            "gpa": extra.get("gpa"),
            "source_url": source_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        records.append(record)

    return records


def scrape_data(
    pages: int = 1,
    delay_s: float = 0.2,
    checkpoint_every: int = 25,
    checkpoint_path: str = OUTPUT_JSON,
) -> list[dict]:
    """
    Fast pass: scrape ONLY the survey pages (no /result/ fetching).
    Saves a checkpoint JSON every N pages so you can resume if interrupted.
    """
    all_records: list[dict] = []

    for page in range(1, pages + 1):
        url = f"{BASE_URL}?page={page}"
        print(f"Scraping page {page}: {url}")

        html = _fetch_html(url)

        if page == 1:
            with open("page1.html", "w", encoding="utf-8") as f:
                f.write(html)

        page_records = _parse_page(html, url, fetch_details=False)
        print(f"  Parsed {len(page_records)} records")
        all_records.extend(page_records)

        # checkpoint save
        if page % checkpoint_every == 0:
            save_data(all_records, checkpoint_path)
            print(f"  Checkpoint saved: {len(all_records)} records -> {checkpoint_path}")

        time.sleep(delay_s)

    return all_records


def save_data(records: list[dict], out_path: str = OUTPUT_JSON) -> None:
    """Save records to JSON."""
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def load_data(path: str = OUTPUT_JSON) -> list[dict]:
    """Load records from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # Phase 1 test: scrape 1 page
    records = scrape_data(pages=1550)
    save_data(records, OUTPUT_JSON)
    print(f"Saved {len(records)} records to {OUTPUT_JSON}")