from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from html import unescape
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SUBJECT_MARKER = '<main id="main" class="page-main page-type-subject">'
EXCLUDED_HUBS = {"수학과외", "경남수학과외", "경북수학과외"}
GRADE_PATTERN = re.compile(r"(초등|중등|고등)수학과외$")
BAD_PHRASES = (
    "학습 메모하는가",
    "학습 메모한다",
    "학습 메모하고",
    "학습 메모에서",
    "학습 메모을",
    "학습 메모과",
    "학습 메모은",
    "학습 메모해",
    "시험 학습가",
    "수학 학습는",
    "수학학습",
    "출발점에서는 풀고",
    "처음에는 정한다",
    "기초부터심화까지",
)


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def one(pattern: str, html: str) -> str:
    match = re.search(pattern, html, flags=re.I | re.S)
    return unescape(match.group(1)).strip() if match else ""


def grams(value: str, size: int = 5) -> set[str]:
    value = compact(value)
    return {value[index : index + size] for index in range(max(0, len(value) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def link_exists(href: str) -> bool:
    target = href.split("#", 1)[0]
    if not target or target == "/":
        return True
    return (OUTPUT / target.strip("/") / "index.html").exists()


def is_priority_math_page(slug: str, html: str) -> bool:
    return (
        slug.endswith("수학과외")
        and slug not in EXCLUDED_HUBS
        and not GRADE_PATTERN.search(slug)
        and SUBJECT_MARKER in html
    )


def location_tier(location: str) -> str:
    if location in {"부산", "구미", "양산"}:
        return "city"
    if location.endswith(("동", "읍", "면")):
        return "neighborhood"
    if location.endswith(("구", "군")):
        return "district"
    return "other"


def main() -> int:
    pages: dict[str, dict[str, object]] = {}
    paragraph_owners: defaultdict[str, set[str]] = defaultdict(set)
    title_owners: defaultdict[str, list[str]] = defaultdict(list)
    description_owners: defaultdict[str, list[str]] = defaultdict(list)
    problems: list[str] = []

    for path in OUTPUT.glob("*/index.html"):
        slug = path.parent.name
        html = path.read_text(encoding="utf-8")
        if not is_priority_math_page(slug, html):
            continue

        article_html = one(r'<article class="content-body">(.*?)</article>', html)
        article_text = plain(article_html)
        title = plain(one(r"<title>(.*?)</title>", html))
        description = plain(one(r'<meta name="description" content="([^"]*)">', html))
        title_owners[title].append(slug)
        description_owners[description].append(slug)
        paragraphs = [plain(item) for item in re.findall(r"<p\b[^>]*>(.*?)</p>", article_html, flags=re.I | re.S)]
        for paragraph in paragraphs:
            if len(paragraph) >= 80:
                paragraph_owners[paragraph].add(slug)

        toc_html = one(r'(<nav class="page-toc".*?</nav>)', html)
        toc_targets = re.findall(r'href="#([^"]+)"', toc_html)
        related_html = one(r'(<nav class="related-navigation".*?</nav>)', html)
        links = re.findall(r'<a\b[^>]*href="(/[^"]*)"', related_html)
        location = slug.removesuffix("수학과외")
        bad = [phrase for phrase in BAD_PHRASES if phrase in article_text or phrase in title]
        pages[slug] = {
            "tier": location_tier(location),
            "characters": len(article_text),
            "h2": len(re.findall(r"<h2\b", article_html)),
            "h3": len(re.findall(r"<h3\b", article_html)),
            "paragraphs": len(paragraphs),
            "location_mentions": article_text.count(location),
            "toc_links": len(toc_targets),
            "missing_toc_targets": [target for target in toc_targets if f'id="{target}"' not in html],
            "related_links": len(links),
            "duplicate_related_links": sorted({link for link in links if links.count(link) > 1}),
            "broken_related_links": sorted(link for link in set(links) if not link_exists(link)),
            "bad_phrases": bad,
            "title": title,
            "description": description,
            "text": article_text,
            "grams": grams(article_text),
        }

    pairs = sorted(
        (
            {
                "left": left,
                "right": right,
                "similarity_percent": round(jaccard(pages[left]["grams"], pages[right]["grams"]) * 100, 2),
            }
            for left, right in combinations(sorted(pages), 2)
        ),
        key=lambda item: item["similarity_percent"],
        reverse=True,
    )
    nearest: dict[str, dict[str, object]] = {}
    for slug in pages:
        candidate = next((pair for pair in pairs if slug in {pair["left"], pair["right"]}), None)
        if candidate:
            nearest[slug] = {
                "other": candidate["right"] if candidate["left"] == slug else candidate["left"],
                "similarity_percent": candidate["similarity_percent"],
            }

    repeated_paragraphs = sorted(
        (
            {"pages": len(owners), "characters": len(paragraph), "sample": paragraph[:120], "slugs": sorted(owners)[:12]}
            for paragraph, owners in paragraph_owners.items()
            if len(owners) >= 3
        ),
        key=lambda item: (item["pages"], item["characters"]),
        reverse=True,
    )
    duplicate_titles = {title: slugs for title, slugs in title_owners.items() if len(slugs) > 1}
    duplicate_descriptions = {description: slugs for description, slugs in description_owners.items() if len(slugs) > 1}

    for slug, data in pages.items():
        if data["characters"] < 3000:
            problems.append(f"thin:{slug}")
        if data["h2"] < 8:
            problems.append(f"few_headings:{slug}")
        if data["location_mentions"] < 2:
            problems.append(f"weak_location_context:{slug}")
        if data["missing_toc_targets"] or data["duplicate_related_links"] or data["broken_related_links"]:
            problems.append(f"navigation:{slug}")
        if data["bad_phrases"]:
            problems.append(f"bad_phrase:{slug}")
        if nearest.get(slug, {}).get("similarity_percent", 0) >= 70:
            problems.append(f"high_similarity:{slug}")
    if duplicate_titles:
        problems.append("duplicate_titles")
    if duplicate_descriptions:
        problems.append("duplicate_descriptions")

    lengths = [int(data["characters"]) for data in pages.values()]
    similarity_bands = Counter(
        ">=90" if pair["similarity_percent"] >= 90 else
        "80-89.99" if pair["similarity_percent"] >= 80 else
        "70-79.99" if pair["similarity_percent"] >= 70 else
        "50-69.99" if pair["similarity_percent"] >= 50 else
        "<50"
        for pair in pairs
    )
    result = {
        "checked": len(pages),
        "tiers": Counter(str(data["tier"]) for data in pages.values()),
        "characters": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "average": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        },
        "similarity_bands": similarity_bands,
        "top_similarity_pairs": pairs[:25],
        "pages_with_similarity_at_least_70": sorted(
            ({"slug": slug, **item} for slug, item in nearest.items() if item["similarity_percent"] >= 70),
            key=lambda item: item["similarity_percent"],
            reverse=True,
        ),
        "repeated_paragraphs_on_3_plus_pages": repeated_paragraphs[:20],
        "duplicate_titles": duplicate_titles,
        "duplicate_descriptions": duplicate_descriptions,
        "pages_with_bad_phrases": [slug for slug, data in pages.items() if data["bad_phrases"]],
        "problems": problems,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
