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

from sitegen.local_high_english import SCHOOL_CONTEXT
from sitegen.local_high_general import CONTENT_VERSION, build_local_high_general_meta


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)고등과외$")


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
            "chars": len(text),
            "paragraphs": [_clean(node.get_text(" ", strip=True)) for node in article.select("p")],
            "headings": [_clean(node.get_text(" ", strip=True)) for node in article.select("h2,h3")],
            "items": len(article.select("li")),
            "links": len(article.select("a[href]")),
            "tables": len(article.select("table")),
            "grams": {" ".join(words[index : index + 5]) for index in range(max(0, len(words) - 4))},
            "ids": [str(node.get("id")) for node in soup.select("[id]")],
            "heading_ids": [str(node.get("id") or "") for node in article.select("h2,h3")],
            "toc_targets": [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")],
            "h1_count": len(soup.select("h1")),
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
        }
    return pages


def _focus(soup: BeautifulSoup) -> str:
    marker = soup.select_one("article [data-high-general-focus]")
    return str(marker.get("data-high-general-focus") or "").strip() if marker else ""


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
    heading = soup.select_one("article h2.high-general-faq[data-faq-focus]")
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
        location = slug.removesuffix("고등과외")
        city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
        town = location.removeprefix(city)
        focus = _focus(soup)
        if not focus:
            errors.append(f"{slug}: focus missing")
        if len(article.select(f'[data-content-version="{CONTENT_VERSION}"]')) != 1:
            errors.append(f"{slug}: content marker")

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
        if int(page["chars"]) < 9000:
            errors.append(f"{slug}: short article {page['chars']}")
        if len(page["paragraphs"]) < 45 or len(page["headings"]) < 36:
            errors.append(f"{slug}: thin structure")
        if int(page["tables"]) != 3:
            errors.append(f"{slug}: table count {page['tables']}")

        search = article.select("section.high-general-search-intent")
        if len(search) != 1:
            errors.append(f"{slug}: search section count {len(search)}")
        else:
            text = search[0].get_text(" ", strip=True)
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from search")
            if len(search[0].select("tbody tr")) != 3 or len(search[0].select("ol > li")) != 4:
                errors.append(f"{slug}: search structure")
            if search[0].select("a[href]"):
                errors.append(f"{slug}: link inside search")

        expected_sections = {
            "section.high-general-grade": 3,
            "section.high-general-subjects": 3,
            "section.high-general-assessment": 3,
            "section.high-general-error-map": 5,
            "section.high-general-protocol": 6,
            "section.high-general-local-experiment": 4,
        }
        for selector, count in expected_sections.items():
            sections = article.select(selector)
            if len(sections) != 1 or len(sections[0].select("h3")) != count:
                errors.append(f"{slug}: bad section {selector}")
        protocol = article.select_one("section.high-general-protocol")
        if not protocol or protocol.get("data-protocol-cards") != "6":
            errors.append(f"{slug}: protocol marker")
        experiment = article.select_one("section.high-general-local-experiment")
        if (
            not experiment
            or experiment.get("data-experiment-sessions") != "4"
            or "가상" not in experiment.get_text(" ", strip=True)
        ):
            errors.append(f"{slug}: experiment disclosure or marker")

        school = article.select_one("section.high-general-school-context")
        if not school:
            errors.append(f"{slug}: school section missing")
        else:
            expected_schools = SCHOOL_CONTEXT.get((city, town), [])[:4]
            expected_links = [str(item["homepage"]) for item in expected_schools]
            links = school.select("a.source-link[href]")
            hrefs = [str(link.get("href") or "") for link in links]
            if school.get("data-school-count") != str(len(expected_schools)) or hrefs != expected_links:
                errors.append(f"{slug}: school data mismatch")
            for link in links:
                if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(set(link.get("rel") or [])):
                    errors.append(f"{slug}: unsafe school link")

        cases = article.select("section.high-general-student-case")
        if len(cases) != 1:
            errors.append(f"{slug}: student case count {len(cases)}")
        else:
            case = cases[0]
            text = case.get_text(" ", strip=True)
            if case.get("data-case-model") != "composite" or "합성 사례" not in text:
                errors.append(f"{slug}: case disclosure")
            if case.get("data-case-grade") not in {"고1", "고2", "고3"}:
                errors.append(f"{slug}: case grade")
            if location not in text or focus not in text:
                errors.append(f"{slug}: local focus missing from case")
            if len(case.select("tbody tr")) != 3 or len(case.select("ol > li")) != 3:
                errors.append(f"{slug}: case structure")
            if case.select("a[href]"):
                errors.append(f"{slug}: link inside case")

        context = article.select("aside.high-general-context-links")
        if len(context) != 1:
            errors.append(f"{slug}: context link section count {len(context)}")
        else:
            hrefs = [str(link.get("href") or "") for link in context[0].select("a[href]")]
            expected = [f"/{city}고등과외/", f"/{location}고등영어과외/", f"/{location}고등수학과외/"]
            if context[0].get("data-link-count") != "3" or hrefs != expected:
                errors.append(f"{slug}: contextual links mismatch")
            for href in hrefs:
                if not (ROOT / "output" / href.strip("/") / "index.html").exists():
                    errors.append(f"{slug}: missing internal target {href}")

        expected_article_links = 3 + len(SCHOOL_CONTEXT.get((city, town), [])[:4])
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
            if location not in question or not question.endswith("?"):
                errors.append(f"{slug}: FAQ question lacks local focus")
            if len(answer) < 150:
                errors.append(f"{slug}: short FAQ answer")

        expected_title, expected_description = build_local_high_general_meta(slug, str(article))
        title = str(page["title"])
        description = str(page["description"])
        if title != expected_title or not (18 <= len(title) <= 60):
            errors.append(f"{slug}: title mismatch or length {len(title)}")
        if description != expected_description or not (90 <= len(description) <= 160):
            errors.append(f"{slug}: description mismatch or length {len(description)}")
        canonical = f"https://edunext.co.kr/{slug}/"
        tags = {
            'link[rel="canonical"]': ("href", canonical),
            'meta[property="og:title"]': ("content", title),
            'meta[property="og:description"]': ("content", description),
            'meta[property="og:url"]': ("content", canonical),
            'meta[name="twitter:title"]': ("content", title),
            'meta[name="twitter:description"]': ("content", description),
        }
        for selector, (attribute, expected) in tags.items():
            nodes = soup.select(selector)
            value = str(nodes[0].get(attribute) or "") if nodes else ""
            if len(nodes) != 1 or value != expected:
                errors.append(f"{slug}: metadata mismatch {selector}")
        webpage = [item for item in _json_ld(soup) if item.get("@type") == "WebPage"]
        if len(webpage) != 1 or webpage[0].get("name") != title or webpage[0].get("description") != description:
            errors.append(f"{slug}: WebPage schema mismatch")
        h1 = soup.select_one("main h1")
        hero = h1.find_next_sibling("p") if h1 else None
        if not h1 or h1.get_text(" ", strip=True) != slug or not hero or hero.get_text(" ", strip=True) != description:
            errors.append(f"{slug}: hero mismatch")

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
    print(f"repeated_paragraphs_3plus={len(repeated_values(pages, 'paragraphs'))}")
    print(f"repeated_headings_3plus={len(repeated_values(pages, 'headings'))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    current = load_pages(args.current)
    summarize("current", current)
    errors = audit_errors(current)
    print(f"quality_errors={len(errors)}")
    for error in errors[:60]:
        print(f"  {error}")
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
        print(f"largest_increase={largest_slug} before={before[largest_slug]['chars']} current={current[largest_slug]['chars']} delta=+{deltas[largest_slug]}")
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
