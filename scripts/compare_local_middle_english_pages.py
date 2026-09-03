from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path


TARGET = re.compile(r"^(부산|구미|양산).+(?:동|읍|면)중등영어과외$")


def article_metrics(path: Path) -> dict[str, int]:
    html = path.read_text(encoding="utf-8")
    match = re.search(r'<article class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    article = match.group(1) if match else ""
    text = unescape(re.sub(r"<[^>]+>", " ", article))
    return {
        "characters": len(re.sub(r"\s+", "", text)),
        "paragraphs": len(re.findall(r"<p\b", article, flags=re.I)),
        "headings": len(re.findall(r"<h[23]\b", article, flags=re.I)),
        "list_items": len(re.findall(r"<li\b", article, flags=re.I)),
        "table_rows": len(re.findall(r"<tr\b", article, flags=re.I)),
        "links": len(re.findall(r"<a\b[^>]*href=", article, flags=re.I)),
        "external_links": len(re.findall(r'<a\b[^>]*href=["\']https?://', article, flags=re.I)),
    }


def average(rows: dict[str, dict[str, int]], key: str) -> float:
    values = [row[key] for row in rows.values()]
    return round(sum(values) / len(values), 1) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two local middle-English output directories.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()

    before: dict[str, dict[str, int]] = {}
    after: dict[str, dict[str, int]] = {}
    for directory in sorted(args.after.iterdir()):
        if not directory.is_dir() or not TARGET.fullmatch(directory.name):
            continue
        before_path = args.before / directory.name / "index.html"
        after_path = directory / "index.html"
        if not before_path.exists():
            raise RuntimeError(f"missing before page: {before_path}")
        before[directory.name] = article_metrics(before_path)
        after[directory.name] = article_metrics(after_path)

    keys = ("characters", "paragraphs", "headings", "list_items", "table_rows", "links", "external_links")
    decreases = [
        {
            "slug": slug,
            "before": before[slug]["characters"],
            "after": after[slug]["characters"],
        }
        for slug in before
        if after[slug]["characters"] < before[slug]["characters"]
    ]
    increases = [after[slug]["characters"] - before[slug]["characters"] for slug in before]
    result = {
        "checked": len(before),
        "averages": {
            key: {
                "before": average(before, key),
                "after": average(after, key),
                "change": round(average(after, key) - average(before, key), 1),
            }
            for key in keys
        },
        "character_change": {
            "minimum": min(increases) if increases else 0,
            "average": round(sum(increases) / len(increases), 1) if increases else 0,
            "maximum": max(increases) if increases else 0,
            "decreased_pages": decreases,
            "increased_pages": sum(value > 0 for value in increases),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if len(before) != 69 or decreases else 0


if __name__ == "__main__":
    raise SystemExit(main())
