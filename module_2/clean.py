# clean.py
import json
import re

INPUT_JSON = "applicant_data.json"
OUTPUT_JSON = "cleaned_applicant_data.json"  # do NOT overwrite raw


# ---------- helpers ----------
_TERM_ALIASES = {
    "spring": "Spring",
    "summer": "Summer",
    "fall": "Fall",
    "autumn": "Fall",
    "winter": "Winter",
}

# Rough month -> academic term mapping (for phrases like "July 2026 start date")
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


def _clean_text(s: str | None) -> str | None:
    """Normalize whitespace + strip + remove any remnant HTML tags."""
    if s is None:
        return None
    s = re.sub(r"<[^>]+>", "", s)          # strip HTML tags (defensive)
    s = re.sub(r"\s+", " ", s).strip()     # normalize whitespace
    return s if s else None


def _normalize_none(x):
    """Convert empty strings/whitespace to None; clean strings; leave non-strings untouched."""
    if x is None:
        return None
    if isinstance(x, str):
        return _clean_text(x)
    return x


def _normalize_international(v):
    """
    Convert is_international into rubric format:
      True  -> "International"
      False -> "American"
      None  -> None

    Also accept string booleans ("true"/"false") and already-normalized strings.
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


def _extract_start_term_year(*texts: str | None) -> tuple[str | None, str | None]:
    """
    Infer start_term/start_year from text, but only when start-ish context exists.
    Avoid false positives like "SURF program in summer 2025".
    """
    hay = " ".join(t for t in (texts or []) if t)
    hay = _clean_text(hay)
    if not hay:
        return None, None

    # Words/phrases that suggest an actual program start / term
    ctx_pat = r"(start|starting|begins?|beginning|program begins|term|semester|matriculat|enroll|enrollment|cohort)"

        # 1) Season + Year (most reliable)
    # e.g. "Fall 2026", "Autumn 2026", "Summer 2025!"
    m = re.search(r"\b(spring|summer|fall|autumn|winter)\b\W*(20\d{2})\b", hay, flags=re.I)
    if m:
        season = m.group(1)
        year = m.group(2)
        if season and year:
            term = _TERM_ALIASES.get(season.lower())
            return term, year

    # 2) Month + Year + 'start-ish' nearby (already guarded)
    month_pat = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    my = re.search(
        rf"(?:\b{ctx_pat}\b.{0,50}\b{month_pat}\b\W*(20\d{{2}})\b)|(?:\b{month_pat}\b\W*(20\d{{2}})\b.{0,50}\b{ctx_pat}\b)",
        hay,
        flags=re.I,
    )
    if my:
        # Depending on alternation matched, month/year are in different groups
        if my.group(2) and my.group(3):
            month = my.group(2).lower()
            year = my.group(3)
        else:
            month = my.group(4).lower()
            year = my.group(5)

        term = _MONTH_TO_TERM.get(month)
        return term, year

    return None, None

# ---------- main cleaning ----------
def clean_data(records: list[dict]) -> list[dict]:
    """
    Clean + structure output dataset.
    - Remove HTML (defensive), normalize whitespace
    - Convert empty strings to None consistently
    - Convert is_international -> "International"/"American"/None
    - Attempt to infer start_term/start_year from text when missing
    - Guarantee all required keys exist
    - Create combined "program" field (no leading comma)
    """
    cleaned: list[dict] = []

    required_keys = [
        "program_name_raw", "university_raw", "comments", "date_posted", "entry_url",
        "applicant_status", "accepted_date", "rejected_date",
        "start_term", "start_year", "is_international",
        "gre_total", "gre_v", "gre_aw", "degree", "degree_level", "gpa",
        "source_url", "scraped_at",
    ]

    # These are the fields we want cleaned/normalized to None if empty.
    normalize_keys = [
        "date_posted", "entry_url", "applicant_status",
        "accepted_date", "rejected_date",
        "start_term", "start_year",
        "gre_total", "gre_v", "gre_aw",
        "degree", "degree_level", "gpa",
        "source_url", "scraped_at",
    ]

    for r in records:
        r2 = dict(r)

        # Clean primary text fields
        r2["program_name_raw"] = _clean_text(r2.get("program_name_raw"))
        r2["university_raw"] = _clean_text(r2.get("university_raw"))
        r2["comments"] = _clean_text(r2.get("comments"))

        # Normalize expected string fields (leave non-strings alone)
        for key in normalize_keys:
            if key in r2:
                r2[key] = _normalize_none(r2.get(key))
            else:
                r2[key] = None  # ensure missing keys become None

        # Normalize international flag
        r2["is_international"] = _normalize_international(r2.get("is_international"))

        # Infer start_term/start_year if missing (only fill if currently None)
        if r2.get("start_term") is None or r2.get("start_year") is None:
            term, year = _extract_start_term_year(
                r2.get("comments"),
                r2.get("applicant_status"),
                r2.get("program_name_raw"),
                r2.get("university_raw"),
            )
            if r2.get("start_term") is None and term is not None:
                r2["start_term"] = term
            if r2.get("start_year") is None and year is not None:
                r2["start_year"] = year

        # Combined "program" field required by LLM tool (avoid leading comma)
        prog = r2.get("program_name_raw") or ""
        uni = r2.get("university_raw") or ""
        if prog and uni:
            r2["program"] = f"{prog}, {uni}"
        else:
            r2["program"] = prog or uni or None

        # Guarantee all required keys exist (and are None if absent)
        for k in required_keys:
            r2.setdefault(k, None)

        cleaned.append(r2)

    return cleaned


def save_data(records: list[dict], out_path: str = OUTPUT_JSON) -> None:
    # Pretty JSON: each field on its own line, and records separated naturally by indentation.
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")  # newline at EOF for nicer diffs


def load_data(path: str = INPUT_JSON) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Support either a raw list or {"rows": [...]}
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    raise ValueError("Input JSON must be a list of dicts or a dict with key 'rows' containing a list.")


if __name__ == "__main__":
    data = load_data(INPUT_JSON)
    cleaned = clean_data(data)
    save_data(cleaned, OUTPUT_JSON)
    print(f"Cleaned {len(cleaned)} records -> {OUTPUT_JSON}")