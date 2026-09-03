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

from sitegen.local_middle_general import CONTENT_VERSION, MIDDLE_CONTEXT, build_local_middle_general_meta


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등과외$")
BAD_TEXT = ("준비을", "대화과", "과정입니다 이", "하기을", "바꾸기을", "정하기을", "만들기을", "연결하기을")


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
            "grams": {" ".join(words[index : index + 5]) for index in range(max(0, len(words) - 4))},
            "ids": [str(node.get("id")) for node in soup.select("[id]")],
            "heading_ids": [str(node.get("id") or "") for node in article.select("h2,h3")],
            "toc_targets": [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")],
            "h1_count": len(soup.select("h1")),
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
        }
    return pages


def max_similarity(pages: dict[str, dict[str, object]]) -> tuple[float, tuple[str, str]]:
    best = (-1.0, ("", ""))
    for left, right in combinations(sorted(pages), 2):
        a, b = pages[left]["grams"], pages[right]["grams"]
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


def _faq_pairs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    section = soup.select_one("section.middle-general-faq")
    if not section:
        return []
    return [
        (_clean(heading.get_text(" ", strip=True)), _clean(answer.get_text(" ", strip=True)))
        for heading in section.select("h3")
        if (answer := heading.find_next_sibling("p")) is not None
    ]


def _schema_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    faq_items = [item for item in _json_ld(soup) if item.get("@type") == "FAQPage"]
    if len(faq_items) != 1 or not isinstance(faq_items[0].get("mainEntity"), list):
        return []
    pairs: list[tuple[str, str]] = []
    for item in faq_items[0]["mainEntity"]:
        if not isinstance(item, dict):
            continue
        answer = item.get("acceptedAnswer", {})
        pairs.append((str(item.get("name") or ""), str(answer.get("text") or "") if isinstance(answer, dict) else ""))
    return pairs


def audit_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    questions: Counter[str] = Counter()
    answers: Counter[str] = Counter()
    focuses: Counter[str] = Counter()
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        article = soup.select_one("article.content-body")
        if not article:
            errors.append(f"{slug}: article missing")
            continue
        location = slug.removesuffix("중등과외")
        city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
        marker = article.select_one("[data-middle-general-focus]")
        focus = str(marker.get("data-middle-general-focus") or "").strip() if marker else ""
        focuses[focus] += 1
        if not focus or len(article.select(f'[data-content-version="{CONTENT_VERSION}"]')) != 1:
            errors.append(f"{slug}: content marker/focus")

        ids, heading_ids, toc_targets = page["ids"], page["heading_ids"], page["toc_targets"]
        assert isinstance(ids, list) and isinstance(heading_ids, list) and isinstance(toc_targets, list)
        if len(ids) != len(set(ids)) or any(not item for item in heading_ids):
            errors.append(f"{slug}: duplicate or missing heading id")
        if any(target not in ids for target in toc_targets):
            errors.append(f"{slug}: missing TOC target")
        if int(page["h1_count"]) != 1:
            errors.append(f"{slug}: h1 count {page['h1_count']}")
        if int(page["chars"]) < 9000 or len(page["paragraphs"]) < 50 or len(page["headings"]) < 47:
            errors.append(f"{slug}: thin article {page['chars']} chars/{len(page['paragraphs'])}p/{len(page['headings'])}h")
        if int(page["tables"]) != 3:
            errors.append(f"{slug}: table count {page['tables']}")
        for bad in BAD_TEXT:
            if bad in str(page["text"]):
                errors.append(f"{slug}: malformed phrase {bad}")

        section_counts = {
            "section.middle-general-search-intent": (0, 3, 4),
            "section.middle-general-grade": (3, 0, 0),
            "section.middle-general-subjects": (5, 0, 0),
            "section.middle-general-assessment": (4, 3, 0),
            "section.middle-general-student-case": (0, 3, 3),
            "section.middle-general-protocol": (6, 0, 0),
            "section.middle-general-local-experiment": (4, 0, 0),
            "section.middle-general-parent": (3, 0, 0),
            "section.middle-general-transition": (3, 0, 0),
        }
        for selector, (headings, rows, items) in section_counts.items():
            nodes = article.select(selector)
            if len(nodes) != 1:
                errors.append(f"{slug}: section count {selector}={len(nodes)}")
                continue
            if headings and len(nodes[0].select("h3")) != headings:
                errors.append(f"{slug}: heading count {selector}")
            if rows and len(nodes[0].select("tbody tr")) != rows:
                errors.append(f"{slug}: row count {selector}")
            if items and len(nodes[0].select("ol > li")) != items:
                errors.append(f"{slug}: item count {selector}")

        case = article.select_one("section.middle-general-student-case")
        if not case or case.get("data-case-model") != "composite" or case.get("data-case-grade") not in {"중1", "중2", "중3"} or "합성 사례" not in case.get_text(" ", strip=True):
            errors.append(f"{slug}: composite case disclosure")
        protocol = article.select_one("section.middle-general-protocol")
        experiment = article.select_one("section.middle-general-local-experiment")
        if not protocol or protocol.get("data-protocol-cards") != "6":
            errors.append(f"{slug}: protocol marker")
        if not experiment or experiment.get("data-experiment-sessions") != "4" or "교육용 점검" not in experiment.get_text(" ", strip=True):
            errors.append(f"{slug}: experiment disclosure")

        schools = MIDDLE_CONTEXT.get(slug, {}).get("schools", [])
        expected_schools = [item for item in schools if isinstance(item, dict)][:4] if isinstance(schools, list) else []
        school = article.select_one("section.middle-general-school-context")
        school_links = school.select("a.source-link[href]") if school else []
        expected_hrefs = [str(item.get("homepage") or "") for item in expected_schools if item.get("homepage") and item.get("school_name")]
        if not school or school.get("data-school-count") != str(len(expected_schools)) or [str(link.get("href") or "") for link in school_links] != expected_hrefs:
            errors.append(f"{slug}: school data mismatch")
        for link in school_links:
            if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(set(link.get("rel") or [])):
                errors.append(f"{slug}: unsafe school link")

        context = article.select_one("aside.middle-general-context-links")
        hrefs = [str(link.get("href") or "") for link in context.select("a[href]")] if context else []
        expected_links = [f"/{city}중등과외/", f"/{location}중등영어과외/", f"/{location}중등수학과외/"]
        if not context or context.get("data-link-count") != "3" or hrefs != expected_links:
            errors.append(f"{slug}: contextual links mismatch")
        for href in hrefs:
            if not (ROOT / "output" / href.strip("/") / "index.html").exists():
                errors.append(f"{slug}: missing internal target {href}")
        if int(page["links"]) != 3 + len(expected_hrefs):
            errors.append(f"{slug}: unexpected article links {page['links']}")

        visible, schema = _faq_pairs(soup), _schema_faq(soup)
        if len(visible) != 5 or visible != schema:
            errors.append(f"{slug}: FAQ/schema mismatch")
        for question, answer in visible:
            questions[question] += 1
            answers[answer] += 1
            if location not in question or focus not in question or not question.endswith("?"):
                errors.append(f"{slug}: FAQ lacks local focus")
            if len(answer) < 150:
                errors.append(f"{slug}: short FAQ answer {len(answer)}")

        expected_title, expected_description = build_local_middle_general_meta(slug, str(article))
        title, description = str(page["title"]), str(page["description"])
        if title != expected_title or not (18 <= len(title) <= 60):
            errors.append(f"{slug}: title mismatch/length {len(title)}")
        if description != expected_description or not (90 <= len(description) <= 160):
            errors.append(f"{slug}: description mismatch/length {len(description)}")
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
            if len(nodes) != 1 or str(nodes[0].get(attribute) or "") != expected:
                errors.append(f"{slug}: metadata mismatch {selector}")
        webpage = [item for item in _json_ld(soup) if item.get("@type") == "WebPage"]
        if len(webpage) != 1 or webpage[0].get("name") != title or webpage[0].get("description") != description:
            errors.append(f"{slug}: WebPage schema mismatch")
        h1 = soup.select_one("main h1")
        hero = h1.find_next_sibling("p") if h1 else None
        if not h1 or h1.get_text(" ", strip=True) != slug or not hero or hero.get_text(" ", strip=True) != description:
            errors.append(f"{slug}: hero mismatch")

    if any(count > 1 for count in focuses.values()) or len(focuses) != 69:
        errors.append(f"focus uniqueness {len(focuses)}")
    if any(count > 1 for count in questions.values()):
        errors.append("duplicate FAQ question")
    if any(count > 1 for count in answers.values()):
        errors.append("duplicate FAQ answer")
    if len({str(page["title"]) for page in pages.values()}) != len(pages):
        errors.append("duplicate search title")
    if len({str(page["description"]) for page in pages.values()}) != len(pages):
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
    print(f"search_titles_unique={len({str(page['title']) for page in pages.values()})}")
    print(f"meta_descriptions_unique={len({str(page['description']) for page in pages.values()})}")
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
    if args.before:
        before = load_pages(args.before)
        summarize("before", before)
        common = sorted(set(current) & set(before))
        deltas = {slug: int(current[slug]["chars"]) - int(before[slug]["chars"]) for slug in common}
        print("[comparison]")
        print(f"common_pages={len(common)}")
        print(f"char_delta min={min(deltas.values())} max={max(deltas.values())} avg={sum(deltas.values()) / len(deltas):.1f}")
        print(f"decreased_pages={sum(delta < 0 for delta in deltas.values())}")
        largest = max(deltas, key=deltas.get)
        print(f"largest_increase={largest} before={before[largest]['chars']} current={current[largest]['chars']} delta=+{deltas[largest]}")
        errors.extend(f"{slug}: content decreased" for slug, delta in deltas.items() if delta < 0)
    similarity, _ = max_similarity(current)
    if similarity > 0.30:
        errors.append(f"maximum similarity above 30%: {similarity:.4f}")
    if repeated_values(current, "paragraphs"):
        errors.append("repeated paragraphs on 3+ pages")
    if repeated_values(current, "headings"):
        errors.append("repeated headings on 3+ pages")
    print(f"quality_errors={len(errors)}")
    for error in errors[:80]:
        print(f"  {error}")
    return 0 if len(current) == 69 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
