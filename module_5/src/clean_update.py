# clean_update.py
#
# This script takes raw scraped applicant records and normalizes them into a
# consistent schema suitable for database loading and downstream analysis.
#
# Responsibilities:
# - Remove HTML remnants and normalize text fields
# - Convert empty/invalid values to None
# - Standardize international status labels
# - Infer missing start term/year from contextual text when possible
# - Guarantee a stable output schema
#
"""
Normalize raw scraped GradCafe applicant records into a consistent schema.

This module cleans and standardizes fields, converts invalid values to None,
infers missing term/year when possible, and writes cleaned output to JSON so the
raw scrape is preserved.
"""

import json
import re

INPUT_JSON = "applicant_data_update.json"
OUTPUT_JSON = "cleaned_applicant_data_update.json"  # raw data is never overwritten


# -------------------------------------------------------------------
# Term normalization helpers
# -------------------------------------------------------------------
# Maps seasonal aliases to a canonical representation.
# This ensures consistent labeling regardless of source formatting.
_TERM_ALIASES = {
    "spring": "Spring",
    "summer": "Summer",
    "fall": "Fall",
    "autumn": "Fall",
    "winter": "Winter",
}

# Converts month references into approximate academic terms.
# Used when a record mentions a start month instead of a season.
_MONTH_TO_TERM = {
    "jan": "Spring", "january": "Spring",
    "feb": "Spring", "february": "Spring",
    "mar": "Spring", "march": "Spring",
    "apr": "Spring", "april": "Spring",
    "may": "Summer",
    "jun": "Summer", "june": "Summer",
    "jul": "Summer", "july": "Summer",
    "aug": "Fall", "august": "Fall",
    "sep": "Fall", "sept": "Fall", "september": "Fall",
    "oct": "Fall", "october": "Fall",
    "nov": "Fall", "november": "Fall",
    "dec": "Winter", "december": "Winter",
}


# -------------------------------------------------------------------
# Text normalization utilities
# -------------------------------------------------------------------
def _clean_text(s: str | None) -> str | None:
    """
    Normalize whitespace, remove HTML tags, and trim strings.

    Returns None for empty or invalid values.
    """
    if s is None:
        return None

    # Remove HTML fragments that may remain after scraping
    s = re.sub(r"<[^>]+>", "", s)

    # Collapse repeated whitespace into single spaces
    s = re.sub(r"\s+", " ", s).strip()

    return s if s else None


def _normalize_none(x):
    """
    Standardize missing values.

    - Strings are cleaned
    - Empty strings become None
    - Non-strings pass through unchanged
    """
    if x is None:
        return None

    if isinstance(x, str):
        return _clean_text(x)

    return x


# -------------------------------------------------------------------
# International status normalization
# -------------------------------------------------------------------
def _normalize_us_international(v):
    """
    Convert raw international indicators into consistent labels.

    Output values:
      "International"
      "American"
      None
    """
    if v in (True, False, None):
        if v is True:
            return "International"
        if v is False:
            return "American"
        return None

    if isinstance(v, str):
        t = v.strip().lower()

        if t == "true":
            return "International"
        if t == "false":
            return "American"
        if t in ("international", "american"):
            return t.title()

    return None


# -------------------------------------------------------------------
# Start term/year inference
# -------------------------------------------------------------------
def _extract_start_term_year(*texts: str | None) -> tuple[str | None, str | None]:
    """
    Attempt to infer an applicant's start term/year from surrounding text.

    Only activates when start-related context is detected to avoid false
    matches from unrelated mentions.
    """
    hay = " ".join(t for t in (texts or []) if t)
    hay = _clean_text(hay)

    if not hay:
        return None, None

    # Only search if enrollment context is present
    ctx_pat = (
    r"(start|starting|begins?|beginning|program begins|term|semester|"
    r"matriculat|enroll|enrollment|cohort)"
    )
    if not re.search(ctx_pat, hay, flags=re.I):
        return None, None

    # Season + year pattern
    m = re.search(r"\b(spring|summer|fall|autumn|winter)\b\W*(20\d{2})\b", hay, flags=re.I)
    if m:
        season = m.group(1).lower()
        year = m.group(2)
        return _TERM_ALIASES.get(season), year

    # Month + year pattern fallback
    month_pat = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    )
    my = re.search(rf"\b{month_pat}\b\W*(20\d{{2}})\b", hay, flags=re.I)
    if my:
        month = my.group(1).lower()
        year = my.group(2)
        return _MONTH_TO_TERM.get(month), year

    return None, None


# -------------------------------------------------------------------
# Core cleaning pipeline
# -------------------------------------------------------------------
def clean_data(records: list[dict]) -> list[dict]:
    """
    Transform raw scraped records into normalized output rows.

    Each record is cleaned, standardized, and validated against a fixed schema.
    """
    cleaned_rows: list[dict] = []

    # Stable output schema guarantees downstream compatibility
    required_keys = [
        "program", "university", "comments",
        "date_posted", "entry_url", "applicant_status",
        "accepted_date", "rejected_date",
        "start_term", "start_year",
        "US/International",
        "gre_total", "gre_v", "gre_aw",
        "degree_level", "degree", "GPA",
        "source_url", "scraped_at",
    ]

    for r in records:

        # Core identity fields
        program = _clean_text(r.get("program_name_raw") or r.get("program"))
        university = _clean_text(r.get("university_raw") or r.get("university"))
        comments = _clean_text(r.get("comments"))

        # Scalar normalization
        date_posted = _normalize_none(r.get("date_posted"))
        entry_url = _normalize_none(r.get("entry_url"))
        applicant_status = _normalize_none(r.get("applicant_status"))
        accepted_date = _normalize_none(r.get("accepted_date"))
        rejected_date = _normalize_none(r.get("rejected_date"))

        start_term = _normalize_none(r.get("start_term"))
        start_year = _normalize_none(r.get("start_year"))

        gre_total = _normalize_none(r.get("gre_total"))
        gre_v = _normalize_none(r.get("gre_v"))
        gre_aw = _normalize_none(r.get("gre_aw"))

        degree_level = _normalize_none(r.get("degree_level"))
        degree = _normalize_none(r.get("degree"))

        gpa_raw = r.get("gpa") if "gpa" in r else r.get("GPA")
        gpa = _normalize_none(gpa_raw)

        source_url = _normalize_none(r.get("source_url"))
        scraped_at = _normalize_none(r.get("scraped_at"))

        # International label conversion
        usintl = _normalize_us_international(r.get("is_international"))

        # Attempt start term/year inference when missing
        if start_term is None or start_year is None:
            term2, year2 = _extract_start_term_year(
                comments, applicant_status, program, university
            )
            if start_term is None:
                start_term = term2
            if start_year is None:
                start_year = year2

        out = {
            "program": program,
            "university": university,
            "comments": comments,
            "date_posted": date_posted,
            "entry_url": entry_url,
            "applicant_status": applicant_status,
            "accepted_date": accepted_date,
            "rejected_date": rejected_date,
            "start_term": start_term,
            "start_year": start_year,
            "US/International": usintl,
            "gre_total": gre_total,
            "gre_v": gre_v,
            "gre_aw": gre_aw,
            "degree_level": degree_level,
            "degree": degree,
            "GPA": gpa,
            "source_url": source_url,
            "scraped_at": scraped_at,
        }

        # Guarantee all schema fields exist
        for k in required_keys:
            out.setdefault(k, None)

        cleaned_rows.append(out)

    return cleaned_rows


# -------------------------------------------------------------------
# File IO helpers
# -------------------------------------------------------------------
def save_data(records: list[dict], out_path: str = OUTPUT_JSON) -> None:
    """Write cleaned records to disk."""
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_data(path: str = INPUT_JSON) -> list[dict]:
    """
    Load raw JSON data.

    Accepts either:
      - list of dicts
      - dict containing key "rows"
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]

    raise ValueError("Invalid input JSON structure.")


# -------------------------------------------------------------------
# Script entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    raw_data = load_data(INPUT_JSON)
    cleaned_output = clean_data(raw_data)
    save_data(cleaned_output, OUTPUT_JSON)
    print(f"Cleaned {len(cleaned_output)} records -> {OUTPUT_JSON}")
