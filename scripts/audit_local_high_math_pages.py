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

from sitegen.local_high_math import SCHOOL_CONTEXT, build_local_high_math_meta


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)고등수학과외$")


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
    marker = soup.select_one("article [data-high-math-focus]")
    return str(marker.get("data-high-math-focus") or "").strip() if marker else ""


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
    heading = soup.select_one("article h2.high-math-faq[data-faq-focus]")
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
        location = slug.removesuffix("고등수학과외")
        city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
        town = location.removeprefix(city)
        focus = _focus(soup)
        if not focus:
            errors.append(f"{slug}: focus missing")
        markers = article.select('[data-content-version="high-math-individual-v6"]')
        if len(markers) != 1:
            errors.append(f"{slug}: content marker count {len(markers)}")
        article_text = article.get_text(" ", strip=True)
        last_code = ord(focus[-1]) if focus else 0
        has_final = 0xAC00 <= last_code <= 0xD7A3 and (last_code - 0xAC00) % 28 != 0
        wrong_subject = "가" if has_final else "이"
        wrong_naming = "라는" if has_final else "이라는"
        for prefix in (focus, f"‘{focus}’"):
            for malformed in (f"{prefix}{wrong_naming}", f"{prefix}{wrong_subject}"):
                if malformed in article_text:
                    errors.append(f"{slug}: malformed focus particle {malformed}")
        for forbidden in ("중학생", "중학교", "중1", "중2", "중3", "middle-math"):
            if forbidden in str(article):
                errors.append(f"{slug}: middle-school residue {forbidden}")
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

        school_sections = article.select("section.high-math-school-context")
        if len(school_sections) != 1:
            errors.append(f"{slug}: school section count {len(school_sections)}")
        else:
            school_links = school_sections[0].select("a.source-link[href]")
            expected_links = [
                school["homepage"]
                for school in SCHOOL_CONTEXT.get((city, town), [])[:4]
                if school["homepage"]
            ]
            hrefs = [str(link.get("href") or "") for link in school_links]
            if hrefs != expected_links:
                errors.append(f"{slug}: school official links mismatch")
            for link in school_links:
                rel = set(link.get("rel") or [])
                if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(rel):
                    errors.append(f"{slug}: unsafe school link")

        search_sections = article.select("section.high-math-search-intent")
        if len(search_sections) != 1:
            errors.append(f"{slug}: search intent section count {len(search_sections)}")
        else:
            section = search_sections[0]
            text = section.get_text(" ", strip=True)
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from search intent")
            if len(section.select("table")) != 1 or len(section.select("tbody tr")) != 3:
                errors.append(f"{slug}: search intent table")
            if len(section.select("ol")) != 1 or len(section.select("ol > li")) != 4:
                errors.append(f"{slug}: search intent steps")
            if section.select("a[href]"):
                errors.append(f"{slug}: link inside search intent")

        case_sections = article.select("section.high-math-student-case")
        if len(case_sections) != 1:
            errors.append(f"{slug}: student case section count {len(case_sections)}")
        else:
            section = case_sections[0]
            text = section.get_text(" ", strip=True)
            if section.get("data-case-model") != "composite" or "합성" not in text and "가상" not in text:
                errors.append(f"{slug}: composite case disclosure")
            if section.get("data-case-grade") not in {"고1", "고2", "고3"}:
                errors.append(f"{slug}: case grade")
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from case")
            if len(section.select("tbody tr")) != 3 or len(section.select("ol > li")) != 3:
                errors.append(f"{slug}: case structure")
            if section.select("a[href]"):
                errors.append(f"{slug}: link inside case")

        context_sections = article.select("aside.high-math-context-links")
        if len(context_sections) != 1:
            errors.append(f"{slug}: context link section count {len(context_sections)}")
        else:
            links = context_sections[0].select("a[href]")
            expected = [f"/{city}고등수학과외/", f"/{location}수학과외/"]
            hrefs = [str(link.get("href") or "") for link in links]
            if context_sections[0].get("data-link-count") != "2" or hrefs != expected:
                errors.append(f"{slug}: contextual links mismatch")
            for href in hrefs:
                if not (ROOT / "output" / href.strip("/") / "index.html").exists():
                    errors.append(f"{slug}: missing internal target {href}")

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
            if len(answer) < 105:
                errors.append(f"{slug}: short FAQ answer")
        faq_heading = article.select_one("h2.high-math-faq")
        if faq_heading:
            for sibling in faq_heading.find_next_siblings():
                if getattr(sibling, "name", None) == "h2":
                    break
                if getattr(sibling, "select", None) and sibling.select("a[href]"):
                    errors.append(f"{slug}: link inside FAQ")

        expected_title, expected_description = build_local_high_math_meta(slug, str(article))
        title = str(page["title"])
        description = str(page["description"])
        if title != expected_title or not (18 <= len(title) <= 60):
            errors.append(f"{slug}: title mismatch")
        if description != expected_description or not (90 <= len(description) <= 160):
            errors.append(f"{slug}: description mismatch")
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
    titles = Counter(str(page["title"]) for page in pages.values())
    descriptions = Counter(str(page["description"]) for page in pages.values())
    if any(count > 1 for count in titles.values()):
        errors.append("duplicate search title")
    if any(count > 1 for count in descriptions.values()):
        errors.append("duplicate meta description")
    return errors


def summarize(label: str, pages: dict[str, dict[str, object]]) -> None:
    chars = [int(page["chars"]) for page in pages.values()]
    paragraphs = [len(page["paragraphs"]) for page in pages.values()]
    headings = [len(page["headings"]) for page in pages.values()]
    items = [int(page["items"]) for page in pages.values()]
    similarity, pair = max_similarity(pages)
    repeated_paragraphs = repeated_values(pages, "paragraphs")
    repeated_headings = repeated_values(pages, "headings")
    print(f"[{label}]")
    print(f"pages={len(pages)}")
    print(f"chars min={min(chars)} max={max(chars)} avg={sum(chars) / len(chars):.1f}")
    print(f"paragraphs min={min(paragraphs)} max={max(paragraphs)} avg={sum(paragraphs) / len(paragraphs):.1f}")
    print(f"headings min={min(headings)} max={max(headings)} avg={sum(headings) / len(headings):.1f}")
    print(f"list_items min={min(items)} max={max(items)} avg={sum(items) / len(items):.1f}")
    print(f"article_links={sum(int(page['links']) for page in pages.values())}")
    print(f"search_titles_unique={len(set(str(page['title']) for page in pages.values()))}")
    print(f"meta_descriptions_unique={len(set(str(page['description']) for page in pages.values()))}")
    print(f"max_5gram_similarity={similarity * 100:.2f}% pair={pair[0]} | {pair[1]}")
    print(f"repeated_paragraphs_3plus={len(repeated_paragraphs)}")
    print(f"repeated_headings_3plus={len(repeated_headings)}")
    errors = audit_errors(pages) if label == "current" else []
    print(f"quality_errors={len(errors) if label == 'current' else 'not_applicable'}")
    for error in errors[:20]:
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
