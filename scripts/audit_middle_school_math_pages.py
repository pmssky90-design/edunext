from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import SITE_URL
from sitegen.middle_school_math import build_middle_school_math_meta, middle_school_math_contexts


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def load_json_ld(soup: BeautifulSoup) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue
        candidates = value if isinstance(value, list) else [value]
        items.extend(item for item in candidates if isinstance(item, dict))
    return items


def page_record(path: Path) -> dict[str, object]:
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.content-body")
    text = clean(article.get_text(" ", strip=True)) if article else ""
    words = text.split()
    return {
        "html": html,
        "soup": soup,
        "article": article,
        "text": text,
        "chars": len(text),
        "paragraphs": [clean(node.get_text(" ", strip=True)) for node in article.select("p")] if article else [],
        "headings": [clean(node.get_text(" ", strip=True)) for node in article.select("h2,h3")] if article else [],
        "grams": {" ".join(words[index : index + 5]) for index in range(max(0, len(words) - 4))},
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
        "canonical": str((soup.select_one('link[rel="canonical"]') or {}).get("href", "")),
    }


def repeated_values(pages: dict[str, dict[str, object]], key: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for page in pages.values():
        values = page[key]
        assert isinstance(values, list)
        counter.update(set(str(item) for item in values if item))
    return Counter({item: count for item, count in counter.items() if count >= 3})


def similarity_summary(pages: dict[str, dict[str, object]]) -> tuple[float, float, tuple[str, str]]:
    scores: list[float] = []
    best_score = -1.0
    best_pair = ("", "")
    for left, right in combinations(sorted(pages), 2):
        left_grams = pages[left]["grams"]
        right_grams = pages[right]["grams"]
        assert isinstance(left_grams, set) and isinstance(right_grams, set)
        score = len(left_grams & right_grams) / len(left_grams | right_grams) if left_grams or right_grams else 1.0
        scores.append(score)
        if score > best_score:
            best_score = score
            best_pair = (left, right)
    return (sum(scores) / len(scores), best_score, best_pair)


def audit(output: Path) -> tuple[list[str], dict[str, object]]:
    contexts = middle_school_math_contexts()
    errors: list[str] = []
    pages: dict[str, dict[str, object]] = {}
    title_counts: Counter[str] = Counter()
    description_counts: Counter[str] = Counter()

    for slug, context in contexts.items():
        path = output / slug / "index.html"
        if not path.exists():
            errors.append(f"{slug}: missing page")
            continue
        page = page_record(path)
        pages[slug] = page
        soup = page["soup"]
        article = page["article"]
        assert isinstance(soup, BeautifulSoup)
        if article is None:
            errors.append(f"{slug}: missing article")
            continue
        expected_title, expected_description = build_middle_school_math_meta(slug)
        title_counts[str(page["title"])] += 1
        description_counts[str(page["description"])] += 1
        if page["title"] != expected_title:
            errors.append(f"{slug}: title mismatch")
        if page["description"] != expected_description:
            errors.append(f"{slug}: description mismatch")
        if not (20 <= len(expected_title) <= 65):
            errors.append(f"{slug}: title length {len(expected_title)}")
        if not (90 <= len(expected_description) <= 180):
            errors.append(f"{slug}: description length {len(expected_description)}")
        if page["canonical"] != f"{SITE_URL}/{slug}/":
            errors.append(f"{slug}: canonical mismatch")
        h1 = soup.select("h1")
        if len(h1) != 1 or clean(h1[0].get_text(" ", strip=True)) != slug:
            errors.append(f"{slug}: h1 mismatch")
        if not article.select_one('[data-content-version="middle-school-math-individual-v1"]'):
            errors.append(f"{slug}: content marker missing")
        if int(page["chars"]) < 9000:
            errors.append(f"{slug}: short content {page['chars']}")
        if len(article.select("p")) < 45 or len(article.select("h2,h3")) < 20 or len(article.select("table")) < 10:
            errors.append(f"{slug}: weak content structure")
        faq_heading = article.select_one("section.middle-school-math-faq h2")
        faq_questions = article.select("section.middle-school-math-faq h3")
        if not faq_heading or len(faq_questions) != 5:
            errors.append(f"{slug}: visible FAQ mismatch")
        schema_faq = [item for item in load_json_ld(soup) if item.get("@type") == "FAQPage"]
        if len(schema_faq) != 1 or len(schema_faq[0].get("mainEntity", [])) != 5:
            errors.append(f"{slug}: FAQ schema mismatch")
        article_links = article.select("a[href]")
        if len(article_links) != 4:
            errors.append(f"{slug}: expected 4 article links, found {len(article_links)}")
        official = [link for link in article_links if str(link.get("href")) == context.homepage]
        if len(official) != 1:
            errors.append(f"{slug}: official homepage link mismatch")
        for link in article_links:
            href = str(link.get("href") or "")
            if href.startswith("/"):
                target = href.strip("/").split("#", 1)[0]
                target_path = output / target / "index.html" if target else output / "index.html"
                if not target_path.exists():
                    errors.append(f"{slug}: broken article link {href}")
        for token in (
            context.official_name,
            str(context.row["address"]),
            str(context.row["total_students"]),
            str(context.row["grade1_students"]),
            str(context.row["grade2_students"]),
            str(context.row["grade3_students"]),
            str(context.row["source_date"]),
        ):
            if token not in str(page["text"]):
                errors.append(f"{slug}: source token missing {token}")
        parent_path = output / context.parent_slug / "index.html"
        if not parent_path.exists() or f'href="/{slug}/"' not in parent_path.read_text(encoding="utf-8"):
            errors.append(f"{slug}: parent does not link to school page")
        ids = [str(node.get("id")) for node in soup.select("[id]")]
        if len(ids) != len(set(ids)):
            errors.append(f"{slug}: duplicate HTML ids")
        toc_targets = [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")]
        if any(target not in ids for target in toc_targets):
            errors.append(f"{slug}: broken TOC target")

    for title, count in title_counts.items():
        if title and count > 1:
            errors.append(f"duplicate title x{count}: {title}")
    for description, count in description_counts.items():
        if description and count > 1:
            errors.append(f"duplicate description x{count}: {description}")
    repeated_paragraphs = repeated_values(pages, "paragraphs")
    repeated_headings = repeated_values(pages, "headings")
    if repeated_paragraphs:
        errors.append(f"repeated paragraphs on 3+ pages: {len(repeated_paragraphs)}")
    if repeated_headings:
        errors.append(f"repeated headings on 3+ pages: {len(repeated_headings)}")
    average_similarity, maximum_similarity, pair = similarity_summary(pages)
    if maximum_similarity >= 0.65:
        errors.append(f"maximum 5-word similarity is {maximum_similarity:.4f}")

    sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    if len(sitemap_urls) != 1680 or len(sitemap_urls) != len(set(sitemap_urls)):
        errors.append(f"sitemap count/uniqueness mismatch: {len(sitemap_urls)}")
    for slug in contexts:
        if sitemap_urls.count(f"{SITE_URL}/{slug}/") != 1:
            errors.append(f"{slug}: sitemap entry mismatch")

    lengths = [int(page["chars"]) for page in pages.values()]
    report = {
        "expected_pages": len(contexts),
        "generated_pages": len(pages),
        "city_counts": {city: sum(1 for context in contexts.values() if context.city == city) for city in ("부산", "양산", "구미")},
        "site_pages_before": 1462,
        "site_pages_after": len(sitemap_urls),
        "visible_characters": {
            "minimum": min(lengths) if lengths else 0,
            "median": sorted(lengths)[len(lengths) // 2] if lengths else 0,
            "maximum": max(lengths) if lengths else 0,
        },
        "average_5word_similarity_percent": round(average_similarity * 100, 2),
        "maximum_5word_similarity_percent": round(maximum_similarity * 100, 2),
        "highest_similarity_pair": list(pair),
        "repeated_paragraphs_on_3_plus_pages": len(repeated_paragraphs),
        "repeated_headings_on_3_plus_pages": len(repeated_headings),
        "sitemap_urls": len(sitemap_urls),
        "errors": errors,
    }
    return errors, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    errors, report = audit(args.output)
    report_path = ROOT / "audit" / "middle-school-math-audit.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
