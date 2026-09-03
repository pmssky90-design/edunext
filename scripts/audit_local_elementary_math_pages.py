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

from sitegen.local_elementary_math import (
    CONTENT_VERSION,
    ELEMENTARY_SCHOOL_CONTEXT,
    build_local_elementary_math_meta,
)


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)초등수학과외$")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def load_pages(root: Path) -> dict[str, dict[str, object]]:
    pages: dict[str, dict[str, object]] = {}
    for path in sorted(root.glob("*/index.html")):
        slug = path.parent.name
        if not SLUG_PATTERN.fullmatch(slug):
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
            "text": text,
            "chars": len(text),
            "paragraphs": [_clean(node.get_text(" ", strip=True)) for node in article.select("p")],
            "headings": [_clean(node.get_text(" ", strip=True)) for node in article.select("h2,h3")],
            "items": len(article.select("li")),
            "links": len(article.select("a[href]")),
            "tables": len(article.select("table")),
            "grams": {" ".join(words[i : i + 5]) for i in range(max(0, len(words) - 4))},
            "ids": [str(node.get("id")) for node in soup.select("[id]")],
            "heading_ids": [str(node.get("id") or "") for node in article.select("h2,h3")],
            "toc_targets": [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")],
            "h1_count": len(soup.select("h1")),
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
        }
    return pages


def _focus(soup: BeautifulSoup) -> str:
    marker = soup.select_one("article [data-elementary-math-focus]")
    return str(marker.get("data-elementary-math-focus") or "").strip() if marker else ""


def max_similarity(pages: dict[str, dict[str, object]]) -> tuple[float, tuple[str, str]]:
    best = (-1.0, ("", ""))
    for left, right in combinations(sorted(pages), 2):
        a = pages[left]["grams"]
        b = pages[right]["grams"]
        assert isinstance(a, set) and isinstance(b, set)
        score = len(a & b) / len(a | b) if a or b else 1.0
        if score > best[0]:
            best = (score, (left, right))
    return best


def repeated_values(pages: dict[str, dict[str, object]], key: str) -> Counter[str]:
    values: Counter[str] = Counter()
    for page in pages.values():
        entries = page[key]
        assert isinstance(entries, list)
        values.update(set(entry for entry in entries if entry))
    return Counter({value: count for value, count in values.items() if count >= 3})


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


def _visible_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    heading = soup.select_one("article h2.elementary-math-faq[data-faq-focus]")
    if not heading:
        return []
    pairs: list[tuple[str, str]] = []
    node = heading.find_next_sibling()
    while node is not None:
        if getattr(node, "name", None) == "h2":
            break
        if getattr(node, "name", None) == "h3":
            answer = node.find_next_sibling()
            if answer is not None and getattr(answer, "name", None) == "p":
                pairs.append((_clean(node.get_text(" ", strip=True)), _clean(answer.get_text(" ", strip=True))))
        node = node.find_next_sibling()
    return pairs


def _schema_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    faq_items = [item for item in _json_ld(soup) if item.get("@type") == "FAQPage"]
    if len(faq_items) != 1:
        return []
    entities = faq_items[0].get("mainEntity", [])
    if not isinstance(entities, list):
        return []
    result: list[tuple[str, str]] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        answer = entity.get("acceptedAnswer", {})
        result.append(
            (
                str(entity.get("name") or "").strip(),
                str(answer.get("text") or "").strip() if isinstance(answer, dict) else "",
            )
        )
    return result


def audit_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    questions: Counter[str] = Counter()
    answers: Counter[str] = Counter()
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        article = soup.select_one("article.content-body")
        if not article:
            errors.append(f"{slug}: article missing")
            continue
        location = slug.removesuffix("초등수학과외")
        city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
        focus = _focus(soup)
        if not focus:
            errors.append(f"{slug}: focus missing")
        markers = article.select(f'[data-content-version="{CONTENT_VERSION}"]')
        if len(markers) != 1:
            errors.append(f"{slug}: content marker count {len(markers)}")

        ids = page["ids"]
        heading_ids = page["heading_ids"]
        toc_targets = page["toc_targets"]
        assert isinstance(ids, list) and isinstance(heading_ids, list) and isinstance(toc_targets, list)
        if len(ids) != len(set(ids)):
            errors.append(f"{slug}: duplicate id")
        if any(not value for value in heading_ids):
            errors.append(f"{slug}: heading without id")
        if any(target not in ids for target in toc_targets):
            errors.append(f"{slug}: missing TOC target")
        if int(page["h1_count"]) != 1:
            errors.append(f"{slug}: h1 count {page['h1_count']}")
        if int(page["chars"]) < 8500:
            errors.append(f"{slug}: short article {page['chars']}")
        if len(page["paragraphs"]) < 30 or len(page["headings"]) < 24:
            errors.append(f"{slug}: thin structure")
        if int(page["tables"]) != 3:
            errors.append(f"{slug}: table count {page['tables']}")

        search = article.select("section.elementary-math-search-intent")
        if len(search) != 1:
            errors.append(f"{slug}: search intent section count {len(search)}")
        else:
            text = search[0].get_text(" ", strip=True)
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from search intent")
            if len(search[0].select("tbody tr")) != 3 or len(search[0].select("ol > li")) != 4:
                errors.append(f"{slug}: search intent structure")
            if search[0].select("a[href]"):
                errors.append(f"{slug}: link inside search intent")

        grade = article.select("section.elementary-math-grade")
        if len(grade) != 1 or len(grade[0].select("h3")) != 3:
            errors.append(f"{slug}: grade section")
        concept = article.select("section.elementary-math-concept-map")
        if len(concept) != 1 or len(concept[0].select("h3")) != 3:
            errors.append(f"{slug}: concept map section")

        school_sections = article.select("section.elementary-math-school-context")
        if len(school_sections) != 1:
            errors.append(f"{slug}: school section count {len(school_sections)}")
        else:
            expected_schools = ELEMENTARY_SCHOOL_CONTEXT.get(location, [])[:4]
            expected_links = [str(school.get("homepage") or "") for school in expected_schools if school.get("homepage")]
            links = school_sections[0].select("a.source-link[href]")
            hrefs = [str(link.get("href") or "") for link in links]
            if school_sections[0].get("data-school-count") != str(len(expected_schools)):
                errors.append(f"{slug}: school count mismatch")
            if hrefs != expected_links:
                errors.append(f"{slug}: school official links mismatch")
            for link in links:
                rel = set(link.get("rel") or [])
                if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(rel):
                    errors.append(f"{slug}: unsafe school link")

        cases = article.select("section.elementary-math-student-case")
        if len(cases) != 1:
            errors.append(f"{slug}: student case section count {len(cases)}")
        else:
            case = cases[0]
            text = case.get_text(" ", strip=True)
            if case.get("data-case-model") != "composite" or "합성 사례" not in text:
                errors.append(f"{slug}: composite case disclosure")
            if case.get("data-case-grade") not in {"1~2학년", "3~4학년", "5~6학년"}:
                errors.append(f"{slug}: case grade")
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from case")
            if len(case.select("tbody tr")) != 3 or len(case.select("ol > li")) != 3:
                errors.append(f"{slug}: case structure")
            if case.select("a[href]"):
                errors.append(f"{slug}: link inside case")

        context = article.select("aside.elementary-math-context-links")
        if len(context) != 1:
            errors.append(f"{slug}: context link section count {len(context)}")
        else:
            links = context[0].select("a[href]")
            expected = [f"/{city}초등수학과외/", f"/{location}수학과외/"]
            hrefs = [str(link.get("href") or "") for link in links]
            if context[0].get("data-link-count") != "2" or hrefs != expected:
                errors.append(f"{slug}: contextual links mismatch")
            for href in hrefs:
                if not (ROOT / "output" / href.strip("/") / "index.html").exists():
                    errors.append(f"{slug}: missing internal target {href}")

        expected_article_links = 2 + sum(
            1 for school in ELEMENTARY_SCHOOL_CONTEXT.get(location, [])[:4] if school.get("homepage")
        )
        if int(page["links"]) != expected_article_links:
            errors.append(f"{slug}: unexpected article links {page['links']} != {expected_article_links}")

        visible = _visible_faq(soup)
        schema = _schema_faq(soup)
        if len(visible) != 5:
            errors.append(f"{slug}: FAQ count {len(visible)}")
        if visible != schema:
            errors.append(f"{slug}: FAQ schema mismatch")
        for question, answer in visible:
            questions[question] += 1
            answers[answer] += 1
            if location not in question or focus not in question or not question.endswith("?"):
                errors.append(f"{slug}: FAQ question lacks local focus")
            if len(answer) < 115:
                errors.append(f"{slug}: short FAQ answer")
        faq_heading = article.select_one("h2.elementary-math-faq")
        if faq_heading:
            for sibling in faq_heading.find_next_siblings():
                if getattr(sibling, "name", None) == "h2":
                    break
                if getattr(sibling, "select", None) and sibling.select("a[href]"):
                    errors.append(f"{slug}: link inside FAQ")

        expected_title, expected_description = build_local_elementary_math_meta(slug, str(article))
        title = str(page["title"])
        description = str(page["description"])
        if title != expected_title or not (18 <= len(title) <= 60):
            errors.append(f"{slug}: title mismatch or length {len(title)}")
        if description != expected_description or not (90 <= len(description) <= 160):
            errors.append(f"{slug}: description mismatch or length {len(description)}")
        canonical = f"https://edunext.co.kr/{slug}/"
        expected_tags = {
            'link[rel="canonical"]': ("href", canonical),
            'meta[property="og:title"]': ("content", title),
            'meta[property="og:description"]': ("content", description),
            'meta[property="og:url"]': ("content", canonical),
            'meta[name="twitter:title"]': ("content", title),
            'meta[name="twitter:description"]': ("content", description),
        }
        for selector, (attribute, expected) in expected_tags.items():
            tags = soup.select(selector)
            value = str(tags[0].get(attribute) or "") if tags else ""
            if len(tags) != 1 or value != expected:
                errors.append(f"{slug}: metadata mismatch {selector}")
        webpage = [item for item in _json_ld(soup) if item.get("@type") == "WebPage"]
        if len(webpage) != 1 or webpage[0].get("name") != title or webpage[0].get("description") != description:
            errors.append(f"{slug}: WebPage schema mismatch")
        h1 = soup.select_one("main h1")
        hero = h1.find_next_sibling("p") if h1 else None
        if not h1 or h1.get_text(" ", strip=True) != slug or not hero or hero.get_text(" ", strip=True) != description:
            errors.append(f"{slug}: hero metadata mismatch")

    for value, count in questions.items():
        if count > 1:
            errors.append(f"repeated FAQ question x{count}: {value}")
    for value, count in answers.items():
        if count > 1:
            errors.append(f"repeated FAQ answer x{count}: {value[:80]}")
    if any(count > 1 for count in Counter(str(page["title"]) for page in pages.values()).values()):
        errors.append("duplicate search title")
    if any(count > 1 for count in Counter(str(page["description"]) for page in pages.values()).values()):
        errors.append("duplicate meta description")
    return errors


def summarize(label: str, pages: dict[str, dict[str, object]]) -> None:
    chars = [int(page["chars"]) for page in pages.values()]
    paragraphs = [len(page["paragraphs"]) for page in pages.values()]
    headings = [len(page["headings"]) for page in pages.values()]
    items = [int(page["items"]) for page in pages.values()]
    tables = [int(page["tables"]) for page in pages.values()]
    similarity, pair = max_similarity(pages)
    repeated_paragraphs = repeated_values(pages, "paragraphs")
    repeated_headings = repeated_values(pages, "headings")
    print(f"[{label}]")
    print(f"pages={len(pages)}")
    print(f"chars min={min(chars)} max={max(chars)} avg={sum(chars) / len(chars):.1f}")
    print(f"paragraphs min={min(paragraphs)} max={max(paragraphs)} avg={sum(paragraphs) / len(paragraphs):.1f}")
    print(f"headings min={min(headings)} max={max(headings)} avg={sum(headings) / len(headings):.1f}")
    print(f"list_items min={min(items)} max={max(items)} avg={sum(items) / len(items):.1f}")
    print(f"tables min={min(tables)} max={max(tables)} avg={sum(tables) / len(tables):.1f}")
    print(f"article_links={sum(int(page['links']) for page in pages.values())}")
    print(f"search_titles_unique={len(set(str(page['title']) for page in pages.values()))}")
    print(f"meta_descriptions_unique={len(set(str(page['description']) for page in pages.values()))}")
    print(f"max_5gram_similarity={similarity * 100:.2f}% pair={pair[0]} | {pair[1]}")
    print(f"repeated_paragraphs_3plus={len(repeated_paragraphs)}")
    print(f"repeated_headings_3plus={len(repeated_headings)}")
    errors = audit_errors(pages) if label == "current" else []
    print(f"quality_errors={len(errors) if label == 'current' else 'not_applicable'}")
    for error in errors[:30]:
        print(f"  {error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    current = load_pages(args.current)
    summarize("current", current)
    errors = audit_errors(current)
    if args.before:
        before = load_pages(args.before)
        summarize("before", before)
        common = sorted(set(current) & set(before))
        deltas = {slug: int(current[slug]["chars"]) - int(before[slug]["chars"]) for slug in common}
        print("[comparison]")
        print(f"common_pages={len(common)}")
        print(f"char_delta min={min(deltas.values())} max={max(deltas.values())} avg={sum(deltas.values()) / len(deltas):.1f}")
        print(f"decreased_pages={sum(delta < 0 for delta in deltas.values())}")
        largest_slug = max(deltas, key=deltas.get)
        print(
            f"largest_increase={largest_slug} before={before[largest_slug]['chars']} "
            f"current={current[largest_slug]['chars']} delta=+{deltas[largest_slug]}"
        )
        errors.extend(slug for slug, delta in deltas.items() if delta < 0)
    similarity, _ = max_similarity(current)
    if similarity > 0.30:
        errors.append(f"maximum similarity above 30%: {similarity:.4f}")
    if repeated_values(current, "paragraphs"):
        errors.append("repeated paragraphs on 3+ pages")
    if repeated_values(current, "headings"):
        errors.append("repeated headings on 3+ pages")
    return 0 if len(current) == 69 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
