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
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def _normalize_none(x):
    """Convert empty strings/whitespace to None; clean strings; leave non-strings untouched."""
    if x is None:
        return None
    if isinstance(x, str):
        return _clean_text(x)
    return x


def _normalize_us_international(v):
    """
    Convert the raw is_international into rubric format:
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

    ctx_pat = r"(start|starting|begins?|beginning|program begins|term|semester|matriculat|enroll|enrollment|cohort)"
    if not re.search(ctx_pat, hay, flags=re.I):
        return None, None

    m = re.search(r"\b(spring|summer|fall|autumn|winter)\b\W*(20\d{2})\b", hay, flags=re.I)
    if m:
        season = m.group(1).lower()
        year = m.group(2)
        return _TERM_ALIASES.get(season), year

    month_pat = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    my = re.search(rf"\b{month_pat}\b\W*(20\d{{2}})\b", hay, flags=re.I)
    if my:
        month = my.group(1).lower()
        year = my.group(2)
        return _MONTH_TO_TERM.get(month), year

    return None, None


# ---------- main cleaning ----------
def clean_data(records: list[dict]) -> list[dict]:
    """
    Output fields EXACTLY as requested:
      program, university, comments, date_posted, entry_url, applicant_status,
      accepted_date, rejected_date, start_term, start_year,
      US/International, gre_total, gre_v, gre_aw, degree_level, degree, GPA,
      source_url, scraped_at
    """
    cleaned: list[dict] = []

    # expected final schema
    required_keys = [
        "program",
        "university",
        "comments",
        "date_posted",
        "entry_url",
        "applicant_status",
        "accepted_date",
        "rejected_date",
        "start_term",
        "start_year",
        "US/International",
        "gre_total",
        "gre_v",
        "gre_aw",
        "degree_level",
        "degree",
        "GPA",
        "source_url",
        "scraped_at",
    ]

    for r in records:
        # 1) start from raw record
        program = _clean_text(r.get("program_name_raw") or r.get("program"))
        university = _clean_text(r.get("university_raw") or r.get("university"))
        comments = _clean_text(r.get("comments"))

        # 2) normalize scalar/string-ish fields
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
        GPA = _normalize_none(gpa_raw)

        source_url = _normalize_none(r.get("source_url"))
        scraped_at = _normalize_none(r.get("scraped_at"))

        # 3) US/International mapping (from raw is_international)
        usintl_raw = r.get("is_international")
        usintl = _normalize_us_international(usintl_raw)

        # 4) infer start_term/start_year only if missing
        if start_term is None or start_year is None:
            term2, year2 = _extract_start_term_year(
                comments,
                applicant_status,
                program,
                university,
            )
            if start_term is None and term2 is not None:
                start_term = term2
            if start_year is None and year2 is not None:
                start_year = year2

        out = {
            "program": program,                 # keep ORIGINAL program name (traceability)
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
            "GPA": GPA,
            "source_url": source_url,
            "scraped_at": scraped_at,
        }

        # Guarantee all required keys exist
        for k in required_keys:
            out.setdefault(k, None)

        cleaned.append(out)

    return cleaned


def save_data(records: list[dict], out_path: str = OUTPUT_JSON) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_data(path: str = INPUT_JSON) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
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