from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sitegen.data_loader import load_content, load_school_region_map


OUTPUT = ROOT / os.environ.get("EDUNEXT_HOME_AUDIT_OUTPUT", "output")
AUDIT = ROOT / "audit"


def normalize_href(href: str) -> str:
    path = unquote(urlparse(href).path)
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path or "/"


def page_exists(url: str) -> bool:
    if url == "/":
        return (OUTPUT / "index.html").exists()
    return (OUTPUT / url.strip("/") / "index.html").exists()


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    _, school_slugs = load_content()
    school_map = load_school_region_map()
    home = (OUTPUT / "index.html").read_text(encoding="utf-8", errors="ignore")
    hrefs = [normalize_href(href) for href in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', home, flags=re.I)]
    counts = Counter(hrefs)
    rows = []
    city_cards: defaultdict[str, set[str]] = defaultdict(set)

    for slug in sorted(school_slugs):
        info = school_map.get(slug, {})
        url = f"/{slug}/"
        base = info.get("base") or re.sub(r"(수학과외|영어과외|과외)$", "", slug)
        city = info.get("city", "")
        district = info.get("district", "")
        linked = counts[url] > 0
        if linked:
            city_cards[city].add(base)
        rows.append(
            {
                "city": city,
                "district": district,
                "school_name": info.get("school_display_name", base),
                "school_tutoring_url": f"/{base}과외/",
                "school_math_url": f"/{base}수학과외/",
                "school_english_url": f"/{base}영어과외/",
                "current_url": url,
                "page_exists": page_exists(url),
                "linked_from_home": linked,
                "duplicate_count": counts[url],
                "status": "ok" if linked and counts[url] == 1 and page_exists(url) else "error",
            }
        )

    missing = [row for row in rows if not row["linked_from_home"]]
    duplicates = [row for row in rows if int(row["duplicate_count"]) != 1]
    broken = [row for row in rows if not row["page_exists"]]
    summary = {
        "school_pages_expected": len(school_slugs),
        "school_pages_linked_from_home": sum(1 for row in rows if row["linked_from_home"]),
        "school_cards": sum(len(items) for items in city_cards.values()),
        "missing_school_links": len(missing),
        "duplicate_school_link_rows": len(duplicates),
        "broken_school_links": len(broken),
        "busan_school_cards": len(city_cards.get("부산", set())),
        "gumi_school_cards": len(city_cards.get("구미", set())),
        "yangsan_school_cards": len(city_cards.get("양산", set())),
    }
    write_csv(
        AUDIT / "home-school-links.csv",
        rows,
        [
            "city",
            "district",
            "school_name",
            "school_tutoring_url",
            "school_math_url",
            "school_english_url",
            "current_url",
            "page_exists",
            "linked_from_home",
            "duplicate_count",
            "status",
        ],
    )
    lines = ["# Home Link Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (AUDIT / "home-link-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if missing or duplicates or broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
