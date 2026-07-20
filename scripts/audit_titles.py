from __future__ import annotations

import csv
import hashlib
import html
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import CONTENT_EXCEL
from sitegen.data_loader import load_content, load_content_sources
from sitegen.title_rules import HOME_SEO_TITLE, build_page_title, sheet_suffix

OLD_OUTPUT = ROOT / os.environ.get("EDUNEXT_TITLE_OLD_OUTPUT", "output")
NEW_OUTPUT = ROOT / os.environ.get("EDUNEXT_TITLE_NEW_OUTPUT", "output_title_fixed")
AUDIT = ROOT / "audit"
SITE_NAMES = ["EDUNEXT", "CLASSNOVA", "EduNext", "ClassNova"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_html(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def extract(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I | re.S)
    return html.unescape(match.group(1).strip()) if match else ""


def page_path(root: Path, keyword: str) -> Path:
    return root / "index.html" if keyword == "index" else root / keyword / "index.html"


def page_type(keyword: str, source_sheet: str) -> str:
    if source_sheet.startswith("고등 ") or "학교" in source_sheet or source_sheet.startswith("고등과외"):
        if keyword.endswith("수학과외"):
            return "school_math"
        if keyword.endswith("영어과외"):
            return "school_english"
        return "school_tutoring"
    if any(token in keyword for token in ["초등", "중등", "고등"]) and any(token in keyword for token in ["수학", "영어"]):
        return "subject_grade"
    if any(token in keyword for token in ["수학", "영어"]):
        return "subject"
    if any(token in keyword for token in ["초등", "중등", "고등"]):
        return "grade"
    return "region"


def title_has_site_name(value: str) -> bool:
    return any(name.lower() in value.lower() for name in SITE_NAMES)


def duplicated_type(value: str) -> bool:
    checks = [
        "영어과외 영어과외",
        "수학과외 수학과외",
        "고등과외 고등과외",
        "초등과외 초등과외",
        "중등과외 중등과외",
        "고등수학과외 고등수학과외",
        "고등영어과외 고등영어과외",
    ]
    return any(item in value for item in checks)


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    content, _ = load_content()
    sources = load_content_sources()
    source_counts = Counter(sources.values())
    duplicate_keywords = len(content) - len(set(content))

    title_map = []
    preview = []
    errors = []
    long_titles = []
    all_titles = []

    for keyword in sorted(content):
        source_sheet = sources.get(keyword, "")
        proposed, removed = build_page_title(keyword, source_sheet)
        old_html = read_html(page_path(OLD_OUTPUT, keyword))
        new_html = read_html(page_path(NEW_OUTPUT, keyword))
        old_title = extract(r"<title>(.*?)</title>", old_html)
        new_title = extract(r"<title>(.*?)</title>", new_html)
        og_title = extract(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']', new_html)
        tw_title = extract(r'<meta\s+name=["\']twitter:title["\']\s+content=["\']([^"\']*)["\']', new_html)
        h1 = extract(r"<h1[^>]*>(.*?)</h1>", new_html)
        canonical = extract(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']*)["\']', new_html)
        status = "changed" if old_title != new_title else "unchanged"
        if not source_sheet:
            status = "source_sheet_missing"
        if not new_title:
            status = "invalid_title"
        title_map.append({
            "keyword": keyword,
            "source_sheet": source_sheet,
            "page_type": page_type(keyword, source_sheet),
            "current_title": old_title,
            "proposed_title": proposed,
            "output_path": str(page_path(NEW_OUTPUT, keyword)),
        })
        preview.append({
            "keyword": keyword,
            "page_type": page_type(keyword, source_sheet),
            "source_sheet": source_sheet,
            "old_title": old_title,
            "new_title": new_title,
            "old_title_length": len(old_title),
            "new_title_length": len(new_title),
            "site_name_removed": title_has_site_name(old_title) and not title_has_site_name(new_title),
            "duplicated_prefix_removed": removed,
            "output_path": str(page_path(NEW_OUTPUT, keyword)),
            "status": status,
        })
        all_titles.append(new_title)
        if len(new_title) >= 61:
            long_titles.append({"keyword": keyword, "title": new_title, "length": len(new_title), "source_sheet": source_sheet})
        checks = {
            "missing_title": not new_title,
            "site_name_remaining": title_has_site_name(new_title),
            "keyword_not_prefix": not new_title.startswith(keyword),
            "type_duplicated": duplicated_type(new_title),
            "source_sheet_missing": not source_sheet,
            "og_mismatch": new_title != og_title,
            "twitter_mismatch": new_title != tw_title,
            "h1_changed": h1 != keyword,
            "canonical_changed": canonical != f"https://edunext.co.kr/{keyword}/",
        }
        for name, bad in checks.items():
            if bad:
                errors.append({"keyword": keyword, "error": name, "title": new_title, "source_sheet": source_sheet})

    home_html = read_html(NEW_OUTPUT / "index.html")
    home_title = extract(r"<title>(.*?)</title>", home_html)
    if home_title != HOME_SEO_TITLE:
        errors.append({"keyword": "index", "error": "home_title_invalid", "title": home_title, "source_sheet": ""})
    if title_has_site_name(home_title):
        errors.append({"keyword": "index", "error": "site_name_remaining", "title": home_title, "source_sheet": ""})
    all_titles.append(home_title)

    duplicates = [title for title, count in Counter(all_titles).items() if title and count > 1]
    for title in duplicates:
        errors.append({"keyword": "", "error": "duplicated_title", "title": title, "source_sheet": ""})
    for row in preview:
        if row["new_title"] in duplicates:
            row["status"] = "duplicated_title"

    write_csv(AUDIT / "title-source-map.csv", title_map)
    write_csv(AUDIT / "title-change-preview.csv", preview)
    write_csv(AUDIT / "title-errors.csv", errors, ["keyword", "error", "title", "source_sheet"])
    write_csv(AUDIT / "long-titles.csv", long_titles, ["keyword", "title", "length", "source_sheet"])

    buckets = {
        "under_30": sum(1 for title in all_titles if len(title) < 30),
        "30_45": sum(1 for title in all_titles if 30 <= len(title) <= 45),
        "46_60": sum(1 for title in all_titles if 46 <= len(title) <= 60),
        "over_61": sum(1 for title in all_titles if len(title) >= 61),
    }
    summary = {
        "source_file": str(CONTENT_EXCEL),
        "source_sha256": sha256_file(CONTENT_EXCEL),
        "title_target_sheets": len(source_counts),
        "source_keywords": len(content),
        "duplicate_keywords": duplicate_keywords,
        "changed_pages": sum(1 for row in preview if row["status"] == "changed"),
        "unchanged_pages": sum(1 for row in preview if row["status"] == "unchanged"),
        "site_name_removed_pages": sum(1 for row in preview if row["site_name_removed"]),
        "duplicated_prefix_removed_pages": sum(1 for row in preview if row["duplicated_prefix_removed"]),
        "duplicate_titles": len(duplicates),
        "source_sheet_missing": sum(1 for row in preview if not row["source_sheet"]),
        "title_errors": len(errors),
        "long_titles_61_plus": len(long_titles),
        **buckets,
    }
    lines = ["# Title Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    lines.extend(["", "## Sheets"])
    lines.extend(f"- {sheet}: {count}" for sheet, count in sorted(source_counts.items()))
    (AUDIT / "title-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
