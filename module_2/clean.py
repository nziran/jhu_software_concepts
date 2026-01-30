# clean.py
import json
import re

INPUT_JSON = "applicant_data.json"
OUTPUT_JSON = "cleaned_applicant_data.json"  # do NOT overwrite raw


def _clean_text(s: str | None) -> str | None:
    """Normalize whitespace + strip + remove any remnant HTML tags."""
    if s is None:
        return None
    s = re.sub(r"<[^>]+>", "", s)          # strip HTML tags (defensive)
    s = re.sub(r"\s+", " ", s).strip()     # normalize whitespace
    return s if s else None


def _normalize_none(x):
    """Convert empty strings to None; leave non-strings untouched."""
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

    Also accept string booleans ("true"/"false") defensively.
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


def clean_data(records: list[dict]) -> list[dict]:
    """
    Clean + structure output dataset.
    - Remove HTML (defensive), normalize whitespace
    - Convert empty strings to None
    - Convert is_international -> "International"/"American"/None
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

    for r in records:
        r2 = dict(r)

        # Clean primary text fields
        r2["program_name_raw"] = _clean_text(r2.get("program_name_raw"))
        r2["university_raw"] = _clean_text(r2.get("university_raw"))
        r2["comments"] = _clean_text(r2.get("comments"))

        # Normalize expected string fields (leave non-strings alone)
        for key in [
            "date_posted", "entry_url", "applicant_status",
            "accepted_date", "rejected_date",
            "start_term", "start_year",
            "gre_total", "gre_v", "gre_aw",
            "degree", "degree_level", "gpa",
            "source_url", "scraped_at",
        ]:
            if key in r2:
                r2[key] = _normalize_none(r2.get(key))

        # Fix: rubric wants "International"/"American" (not True/False)
        r2["is_international"] = _normalize_international(r2.get("is_international"))

        # Combined "program" field required by LLM tool (avoid leading comma)
        prog = r2.get("program_name_raw") or ""
        uni = r2.get("university_raw") or ""
        if prog and uni:
            r2["program"] = f"{prog}, {uni}"
        else:
            r2["program"] = prog or uni or None

        # Guarantee all required keys exist
        for k in required_keys:
            r2.setdefault(k, None)

        cleaned.append(r2)

    return cleaned


def save_data(records: list[dict], out_path: str = OUTPUT_JSON) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def load_data(path: str = INPUT_JSON) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    data = load_data(INPUT_JSON)
    cleaned = clean_data(data)
    save_data(cleaned, OUTPUT_JSON)
    print(f"Cleaned {len(cleaned)} records -> {OUTPUT_JSON}")