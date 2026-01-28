import json
import re

INPUT_JSON = "applicant_data.json"
OUTPUT_JSON = "applicant_data.json"  # you can overwrite or write a separate cleaned file


def _clean_text(s: str | None) -> str | None:
    """Private helper: normalize whitespace and strip junk."""
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def clean_data(records: list[dict]) -> list[dict]:
    """
    Convert raw scraped records into a structured, consistent format.
    Keep *_raw fields for traceability.
    """
    cleaned = []
    for r in records:
        r2 = dict(r)

        # Minimal baseline cleaning now; we’ll expand later once we know exact fields.
        r2["program_name_raw"] = _clean_text(r2.get("program_name_raw"))
        r2["university_raw"] = _clean_text(r2.get("university_raw"))
        r2["comments"] = _clean_text(r2.get("comments"))

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