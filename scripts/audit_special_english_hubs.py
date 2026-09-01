from __future__ import annotations

import json
import re
from html import unescape
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
TARGETS = (
    "영어과외",
    "초등영어과외",
    "중등영어과외",
    "고등영어과외",
    "경남영어과외",
    "경북영어과외",
)


def visible(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def grams(value: str, size: int = 5) -> set[str]:
    compact = re.sub(r"\s+", "", value)
    return {compact[index : index + size] for index in range(max(0, len(compact) - size + 1))}


def similarity(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def one(pattern: str, html: str) -> str:
    match = re.search(pattern, html, flags=re.I | re.S)
    return unescape(match.group(1) if match.lastindex else match.group(0)).strip() if match else ""


def main() -> int:
    english_pages: dict[str, str] = {}
    for path in OUTPUT.glob("*/index.html"):
        slug = path.parent.name
        if not slug.endswith("영어과외"):
            continue
        html = path.read_text(encoding="utf-8")
        if not any(
            marker in html
            for marker in (
                '<main id="main" class="page-main page-type-subject">',
                '<main id="main" class="page-main page-type-subject_grade">',
            )
        ):
            continue
        article = one(r'<article class="content-body">(.*?)</article>', html)
        english_pages[slug] = visible(article)

    report: dict[str, object] = {"checked_english_pages": len(english_pages), "targets": {}}
    problems: list[str] = []
    all_grams = {slug: grams(text) for slug, text in english_pages.items()}
    for slug in TARGETS:
        path = OUTPUT / slug / "index.html"
        html = path.read_text(encoding="utf-8")
        article_html = one(r'<article class="content-body">(.*?)</article>', html)
        article_text = visible(article_html)
        title = one(r"<title>(.*?)</title>", html)
        description = one(r'<meta name="description" content="([^"]*)">', html)
        og_title = one(r'<meta property="og:title" content="([^"]*)">', html)
        og_description = one(r'<meta property="og:description" content="([^"]*)">', html)
        twitter_title = one(r'<meta name="twitter:title" content="([^"]*)">', html)
        twitter_description = one(r'<meta name="twitter:description" content="([^"]*)">', html)
        hero_description = visible(one(r'<section class="page-hero">.*?<h1>.*?</h1>\s*<p>(.*?)</p>', html))
        toc = one(r'<nav class="page-toc".*?</nav>', html)
        missing_targets = [target for target in re.findall(r'href="#([^"]+)"', toc) if f'id="{target}"' not in html]
        links = re.findall(r'<a\b[^>]*href="(/[^"]*)"', one(r'<nav class="related-navigation".*?</nav>', html))
        duplicate_links = sorted({link for link in links if links.count(link) > 1})
        broken_links = sorted(
            link
            for link in set(links)
            if link != "/" and not (OUTPUT / link.strip("/").split("#", 1)[0] / "index.html").exists()
        )
        schema_items = []
        for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S):
            parsed = json.loads(raw)
            schema_items.extend(parsed if isinstance(parsed, list) else [parsed])
        faq = next((item for item in schema_items if item.get("@type") == "FAQPage"), None)
        neighbors = sorted(
            (
                (other, similarity(all_grams[slug], other_grams))
                for other, other_grams in all_grams.items()
                if other != slug
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        row = {
            "characters": len(article_text),
            "h2": len(re.findall(r"<h2\b", article_html)),
            "h3": len(re.findall(r"<h3\b", article_html)),
            "faq_schema_questions": len(faq.get("mainEntity", [])) if faq else 0,
            "metadata_consistent": title == og_title == twitter_title
            and description == og_description == twitter_description == hero_description,
            "missing_toc_targets": missing_targets,
            "related_links": len(links),
            "duplicate_related_links": duplicate_links,
            "broken_related_links": broken_links,
            "nearest_page": neighbors[0][0] if neighbors else None,
            "nearest_similarity_percent": round(neighbors[0][1] * 100, 2) if neighbors else None,
        }
        report["targets"][slug] = row
        if row["characters"] < 2500:
            problems.append(f"thin content: {slug}")
        if row["h2"] < 8 or row["h3"] < 4:
            problems.append(f"insufficient headings: {slug}")
        if row["faq_schema_questions"] != 5:
            problems.append(f"FAQ schema mismatch: {slug}")
        if not row["metadata_consistent"]:
            problems.append(f"metadata mismatch: {slug}")
        if missing_targets or duplicate_links or broken_links:
            problems.append(f"navigation issue: {slug}")
        if neighbors and neighbors[0][1] >= 0.5:
            problems.append(f"similarity too high: {slug}")

    report["target_pair_similarities"] = {
        f"{left} vs {right}": round(similarity(all_grams[left], all_grams[right]) * 100, 2)
        for left, right in combinations(TARGETS, 2)
    }
    report["problems"] = problems
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
