from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_REGION_HUBS = {"경남과외", "경북과외"}
GENERIC_SCHOOL_ANCHORS = {"종합과외", "영어과외", "수학과외"}


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def page_type(html: str) -> str:
    match = re.search(r'class="[^"]*\bpage-type-([^\s"]+)', html, flags=re.I)
    return match.group(1) if match else ""


def internal_links(fragment: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in re.finditer(
        r'<a\b[^>]*\bhref\s*=\s*["\'](?P<href>/[^"\']*)["\'][^>]*>(?P<label>.*?)</a>',
        fragment,
        flags=re.I | re.S,
    ):
        href = unescape(match.group("href"))
        if href.startswith("//"):
            continue
        path, _, fragment_id = href.partition("#")
        path = path.split("?", 1)[0]
        target = path.strip("/")
        if not target and fragment_id:
            target = f"#{fragment_id}"
        if target:
            links.append((target, plain_text(match.group("label"))))
    return links


def main() -> int:
    rows: list[dict[str, object]] = []
    article_counts: list[int] = []
    related_counts: list[int] = []
    combined_counts: list[int] = []
    metrics: list[dict[str, object]] = []
    checked = 0

    for path in sorted(OUTPUT.glob("*/index.html")):
        slug = path.parent.name
        html = path.read_text(encoding="utf-8")
        if page_type(html) != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        checked += 1
        article_match = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        related_match = re.search(r'<nav\s+class="related-navigation"[^>]*>(.*?)</nav>', html, flags=re.I | re.S)
        faq_match = re.search(r'<section\s+class="regional-faq"[^>]*>(.*?)</section>', article_match.group(1) if article_match else "", flags=re.I | re.S)

        article_links = internal_links(article_match.group(1) if article_match else "")
        related_links = internal_links(related_match.group(1) if related_match else "")
        faq_links = internal_links(faq_match.group(1) if faq_match else "")
        article_targets = Counter(target for target, _ in article_links)
        related_targets = {target for target, _ in related_links}

        repeated_targets = {target: count for target, count in article_targets.items() if count > 1}
        overlaps = sorted(set(article_targets) & related_targets)
        generic_anchors = sorted({label for _, label in related_links if label in GENERIC_SCHOOL_ANCHORS})
        problems: list[str] = []
        if repeated_targets:
            problems.append("repeated_article_targets")
        if overlaps:
            problems.append("article_navigation_overlap")
        if len(faq_links) > 1:
            problems.append(f"too_many_faq_links:{len(faq_links)}")
        if generic_anchors:
            problems.append("generic_school_anchors")

        article_counts.append(len(article_links))
        related_counts.append(len(related_links))
        combined_counts.append(len(article_links) + len(related_links))
        metrics.append(
            {
                "slug": slug,
                "article_links": len(article_links),
                "related_links": len(related_links),
                "combined_links": len(article_links) + len(related_links),
            }
        )
        if problems:
            rows.append(
                {
                    "slug": slug,
                    "article_links": len(article_links),
                    "related_links": len(related_links),
                    "repeated_targets": repeated_targets,
                    "overlap_count": len(overlaps),
                    "generic_anchors": generic_anchors,
                    "problems": problems,
                }
            )

    result = {
        "checked": checked,
        "article_links": {
            "min": min(article_counts) if article_counts else 0,
            "median": median(article_counts) if article_counts else 0,
            "max": max(article_counts) if article_counts else 0,
        },
        "related_navigation_links": {
            "min": min(related_counts) if related_counts else 0,
            "median": median(related_counts) if related_counts else 0,
            "max": max(related_counts) if related_counts else 0,
        },
        "combined_links": {
            "min": min(combined_counts) if combined_counts else 0,
            "median": median(combined_counts) if combined_counts else 0,
            "max": max(combined_counts) if combined_counts else 0,
        },
        "highest_combined": sorted(metrics, key=lambda row: int(row["combined_links"]), reverse=True)[:10],
        "problem_pages": len(rows),
        "problems": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
