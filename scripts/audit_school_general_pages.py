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

from sitegen.data_loader import load_content
from sitegen.school_general import build_school_general_meta, school_general_contexts, school_general_focus


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _json_ld(soup: BeautifulSoup) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        items.extend(item for item in candidates if isinstance(item, dict))
    return items


def _visible_faq(article: BeautifulSoup) -> list[tuple[str, str]]:
    heading = article.select_one("h2.school-general-faq")
    if not heading:
        return []
    pairs: list[tuple[str, str]] = []
    node = heading.find_next_sibling()
    while node is not None and getattr(node, "name", None) != "h2":
        if getattr(node, "name", None) == "h3":
            answer = node.find_next_sibling()
            if answer is not None and getattr(answer, "name", None) == "p":
                pairs.append((_clean(node.get_text(" ", strip=True)), _clean(answer.get_text(" ", strip=True))))
        node = node.find_next_sibling()
    return pairs


def _schema_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    pages = [item for item in _json_ld(soup) if item.get("@type") == "FAQPage"]
    if len(pages) != 1 or not isinstance(pages[0].get("mainEntity"), list):
        return []
    pairs: list[tuple[str, str]] = []
    for entity in pages[0]["mainEntity"]:
        if not isinstance(entity, dict):
            continue
        answer = entity.get("acceptedAnswer")
        pairs.append((str(entity.get("name") or ""), str(answer.get("text") or "") if isinstance(answer, dict) else ""))
    return pairs


def load_pages(root: Path) -> dict[str, dict[str, object]]:
    pages: dict[str, dict[str, object]] = {}
    for slug in sorted(school_general_contexts()):
        path = root / slug / "index.html"
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        article = soup.select_one("article.content-body")
        if not article:
            continue
        text = _clean(article.get_text(" ", strip=True))
        words = text.split()
        pages[slug] = {
            "html": html,
            "soup": soup,
            "article": article,
            "text": text,
            "chars": len(text),
            "paragraphs": [_clean(node.get_text(" ", strip=True)) for node in article.select("p")],
            "headings": [_clean(node.get_text(" ", strip=True)) for node in article.select("h2,h3")],
            "items": len(article.select("li")),
            "tables": len(article.select("table")),
            "links": len(article.select("a[href]")),
            "grams": {" ".join(words[index : index + 5]) for index in range(max(0, len(words) - 4))},
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
        }
    return pages


def repeated_values(pages: dict[str, dict[str, object]], key: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for page in pages.values():
        values = page[key]
        assert isinstance(values, list)
        counter.update(set(str(value) for value in values if value))
    return Counter({value: count for value, count in counter.items() if count >= 3})


def similarity_summary(pages: dict[str, dict[str, object]]) -> tuple[float, float, tuple[str, str]]:
    scores: list[float] = []
    best = (-1.0, ("", ""))
    for left, right in combinations(sorted(pages), 2):
        a, b = pages[left]["grams"], pages[right]["grams"]
        assert isinstance(a, set) and isinstance(b, set)
        score = len(a & b) / len(a | b) if a or b else 1.0
        scores.append(score)
        if score > best[0]:
            best = (score, (left, right))
    return (sum(scores) / len(scores) if scores else 0.0, best[0], best[1])


def audit_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    question_counts: Counter[str] = Counter()
    answer_counts: Counter[str] = Counter()
    contexts = school_general_contexts()
    source_content, _ = load_content()
    for slug, context in contexts.items():
        if slug not in pages:
            errors.append(f"{slug}: page missing")
            continue
        page = pages[slug]
        soup, article = page["soup"], page["article"]
        source_body = source_content.get(slug, "")
        focus = school_general_focus(slug, source_body)
        if len(article.select('[data-content-version="school-general-individual-v1"]')) != 1:
            errors.append(f"{slug}: content marker")
        if int(page["chars"]) < 11500:
            errors.append(f"{slug}: short content {page['chars']}")
        if int(page["tables"]) < 6 or int(page["items"]) < 9:
            errors.append(f"{slug}: weak structured content")
        if len(page["headings"]) < 18 or len(page["paragraphs"]) < 40:
            errors.append(f"{slug}: weak section density")
        for token in (
            "TODO", "FIXME", "실제 학생 A", "점수를 보장", "페이지 페이지", "기준 기준",
            "근거표을", "기록표을", "복원표을", "장부으로",
        ):
            if token in str(article):
                errors.append(f"{slug}: malformed or risky token {token}")

        ids = [str(node.get("id") or "") for node in article.select("h2,h3")]
        all_ids = [str(node.get("id")) for node in soup.select("[id]")]
        toc_targets = [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")]
        if any(not item for item in ids) or len(all_ids) != len(set(all_ids)) or any(target not in all_ids for target in toc_targets):
            errors.append(f"{slug}: heading/TOC ids")
        h1 = soup.select_one("main h1")
        if len(soup.select("main h1")) != 1 or not h1 or h1.get_text(" ", strip=True) != slug:
            errors.append(f"{slug}: h1")

        official_links = article.select(f'a.source-link[href="{context.homepage}"]')
        internal_hrefs = [str(link.get("href") or "") for link in article.select('a[href^="/"]')]
        expected_internal = [f"/{context.math_slug}/", f"/{context.english_slug}/", f"/{context.region_slug}/"]
        if len(official_links) != 1 or internal_hrefs != expected_internal or int(page["links"]) != 4:
            errors.append(f"{slug}: links mismatch {internal_hrefs}")
        for link in official_links:
            rel = set(link.get("rel") or [])
            if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(rel):
                errors.append(f"{slug}: unsafe official link")
        for href in internal_hrefs:
            if not (ROOT / "output" / href.strip("/") / "index.html").exists():
                errors.append(f"{slug}: missing internal target {href}")

        visible = _visible_faq(article)
        schema = _schema_faq(soup)
        if len(visible) != 5 or visible != schema:
            errors.append(f"{slug}: FAQ/schema mismatch")
        for question, answer in visible:
            question_counts[question] += 1
            answer_counts[answer] += 1
            if slug not in question or "과외" not in question or not question.endswith("?"):
                errors.append(f"{slug}: FAQ question focus")
            if len(answer) < 150:
                errors.append(f"{slug}: FAQ answer too short {len(answer)}")

        title, description = build_school_general_meta(slug, source_body)
        if page["title"] != title or not (20 <= len(title) <= 65):
            errors.append(f"{slug}: title {len(str(page['title']))}")
        if page["description"] != description or not (90 <= len(description) <= 180):
            errors.append(f"{slug}: description {len(str(page['description']))}")
        canonical = f"https://edunext.co.kr/{slug}/"
        expected_tags = {
            'link[rel="canonical"]': ("href", canonical),
            'meta[property="og:title"]': ("content", title),
            'meta[property="og:description"]': ("content", description),
            'meta[name="twitter:title"]': ("content", title),
            'meta[name="twitter:description"]': ("content", description),
        }
        for selector, (attribute, expected) in expected_tags.items():
            tags = soup.select(selector)
            if len(tags) != 1 or str(tags[0].get(attribute) or "") != expected:
                errors.append(f"{slug}: metadata {selector}")
        webpages = [item for item in _json_ld(soup) if item.get("@type") == "WebPage"]
        if len(webpages) != 1 or webpages[0].get("name") != title or webpages[0].get("description") != description:
            errors.append(f"{slug}: WebPage schema")
        hero = soup.select_one("section.page-hero > p:last-child")
        if not hero or hero.get_text(" ", strip=True) != description:
            errors.append(f"{slug}: hero description")

    if any(count > 1 for count in question_counts.values()):
        errors.append("repeated FAQ questions")
    if any(count > 1 for count in answer_counts.values()):
        errors.append("repeated FAQ answers")
    if len({str(page["title"]) for page in pages.values()}) != len(pages):
        errors.append("duplicate titles")
    if len({str(page["description"]) for page in pages.values()}) != len(pages):
        errors.append("duplicate descriptions")
    return errors


def print_summary(label: str, pages: dict[str, dict[str, object]], quality: bool = False) -> list[str]:
    chars = [int(page["chars"]) for page in pages.values()]
    paragraphs = [len(page["paragraphs"]) for page in pages.values()]
    headings = [len(page["headings"]) for page in pages.values()]
    average, maximum, pair = similarity_summary(pages)
    errors = audit_errors(pages) if quality else []
    print(f"[{label}]")
    print(f"pages={len(pages)}")
    print(f"chars min={min(chars)} max={max(chars)} avg={sum(chars) / len(chars):.1f}")
    print(f"paragraphs min={min(paragraphs)} max={max(paragraphs)} avg={sum(paragraphs) / len(paragraphs):.1f}")
    print(f"headings min={min(headings)} max={max(headings)} avg={sum(headings) / len(headings):.1f}")
    print(f"tables_total={sum(int(page['tables']) for page in pages.values())}")
    print(f"article_links_total={sum(int(page['links']) for page in pages.values())}")
    print(f"average_5gram_similarity={average * 100:.2f}%")
    print(f"max_5gram_similarity={maximum * 100:.2f}% pair={pair[0]} | {pair[1]}")
    print(f"repeated_paragraphs_3plus={len(repeated_values(pages, 'paragraphs'))}")
    print(f"repeated_headings_3plus={len(repeated_values(pages, 'headings'))}")
    print(f"quality_errors={len(errors) if quality else 'not_applicable'}")
    for error in errors[:80]:
        print(f"  {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    current = load_pages(args.current)
    errors = print_summary("current", current, quality=True)
    if args.before:
        before = load_pages(args.before)
        print_summary("before", before)
        common = sorted(set(current) & set(before))
        deltas = {slug: int(current[slug]["chars"]) - int(before[slug]["chars"]) for slug in common}
        print("[comparison]")
        print(f"common_pages={len(common)}")
        print(f"char_delta min={min(deltas.values())} max={max(deltas.values())} avg={sum(deltas.values()) / len(deltas):.1f}")
        print(f"decreased_pages={sum(delta < 0 for delta in deltas.values())}")
        errors.extend(slug for slug, delta in deltas.items() if delta < 0)
    _, maximum, _ = similarity_summary(current)
    if maximum > 0.40:
        errors.append(f"maximum similarity above 40%: {maximum:.4f}")
    if repeated_values(current, "paragraphs"):
        errors.append("repeated paragraphs on 3+ pages")
    if repeated_values(current, "headings"):
        errors.append("repeated headings on 3+ pages")
    return 0 if len(current) == 143 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
