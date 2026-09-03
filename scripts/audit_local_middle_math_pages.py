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

from sitegen.local_middle_math import build_local_middle_math_meta


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등수학과외$")
CONTEXT_PATH = Path(__file__).resolve().parents[1] / "data" / "local_middle_school_context.json"


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
        text = re.sub(r"\s+", " ", article.get_text(" ", strip=True)).strip()
        paragraphs = [re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() for node in article.select("p")]
        headings = [re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() for node in article.select("h2,h3")]
        words = text.split()
        grams = {" ".join(words[i : i + 5]) for i in range(max(0, len(words) - 4))}
        pages[slug] = {
            "html": html,
            "text": text,
            "chars": len(text),
            "paragraphs": paragraphs,
            "headings": headings,
            "links": len(article.select("a[href]")),
            "items": len(article.select("li")),
            "grams": grams,
            "marker": bool(article.select_one('[data-content-version="middle-math-individual-v7"]')),
            "school_context": bool(article.select_one("section.middle-math-school-context")),
            "school_links": len(article.select("section.middle-math-school-context a.source-link[href]")),
            "search_intent": bool(article.select_one("section.middle-math-search-intent")),
            "student_case": bool(article.select_one("section.middle-math-student-case")),
            "faq_marker": bool(article.select_one("h2.middle-math-faq[data-faq-focus]")),
            "context_links": bool(article.select_one("aside.middle-math-context-links")),
            "context_link_count": len(article.select("aside.middle-math-context-links a[href]")),
            "all_ids": [str(node.get("id")) for node in soup.select("[id]")],
            "heading_ids": [str(node.get("id") or "") for node in article.select("h2,h3")],
            "toc_targets": [str(node.get("href"))[1:] for node in soup.select("nav.page-toc a[href^='#']")],
            "h1_count": len(soup.select("h1")),
            "search_title": soup.title.get_text(strip=True) if soup.title else "",
            "meta_description": str((soup.select_one('meta[name="description"]') or {}).get("content", "")),
            "canonical": str((soup.select_one('link[rel="canonical"]') or {}).get("href", "")),
        }
    return pages


def max_similarity(pages: dict[str, dict[str, object]]) -> tuple[float, tuple[str, str]]:
    best_score = -1.0
    best_pair = ("", "")
    for left, right in combinations(sorted(pages), 2):
        a = pages[left]["grams"]
        b = pages[right]["grams"]
        assert isinstance(a, set) and isinstance(b, set)
        score = len(a & b) / len(a | b) if a or b else 1.0
        if score > best_score:
            best_score = score
            best_pair = (left, right)
    return best_score, best_pair


def repeated_values(pages: dict[str, dict[str, object]], key: str, minimum: int = 3) -> Counter[str]:
    counter: Counter[str] = Counter()
    for page in pages.values():
        values = page[key]
        assert isinstance(values, list)
        counter.update(set(value for value in values if value))
    return Counter({value: count for value, count in counter.items() if count >= minimum})


def schema_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        scripts = soup.select('script[type="application/ld+json"]')
        if not scripts:
            errors.append(f"{slug}: no JSON-LD")
            continue
        try:
            data = json.loads(scripts[0].string or scripts[0].get_text())
        except json.JSONDecodeError:
            errors.append(f"{slug}: invalid JSON-LD")
            continue
        faq_items = [item for item in data if isinstance(item, dict) and item.get("@type") == "FAQPage"] if isinstance(data, list) else []
        if len(faq_items) != 1:
            errors.append(f"{slug}: FAQ schema count {len(faq_items)}")
    return errors


def structure_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for slug, page in pages.items():
        ids = page["all_ids"]
        heading_ids = page["heading_ids"]
        toc_targets = page["toc_targets"]
        assert isinstance(ids, list) and isinstance(heading_ids, list) and isinstance(toc_targets, list)
        if len(ids) != len(set(ids)):
            errors.append(f"{slug}: duplicate id")
        if any(not item for item in heading_ids):
            errors.append(f"{slug}: heading without id")
        if any(target not in ids for target in toc_targets):
            errors.append(f"{slug}: missing TOC target")
        if int(page["h1_count"]) != 1:
            errors.append(f"{slug}: h1 count {page['h1_count']}")
    return errors


def focus_from_before(page: dict[str, object]) -> str:
    headings = page["headings"]
    assert isinstance(headings, list)
    if not headings:
        return ""
    match = re.search(r",\s*(.+?)(?:을|를) 중심으로", headings[0])
    if match:
        return match.group(1).strip()
    for heading in headings:
        faq = re.search(r"중등수학과외에서는\s*(.+?)(?:을|를)\s*어떻게 복습해야 하나요\?", heading)
        if faq:
            return faq.group(1).strip()
    return ""


def particle_errors(current: dict[str, dict[str, object]], before: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for slug in sorted(set(current) & set(before)):
        focus = focus_from_before(before[slug])
        if not focus:
            continue
        last = ord(focus[-1])
        has_final = 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 != 0
        wrong_object = "를" if has_final else "을"
        wrong_topic = "는" if has_final else "은"
        text = str(current[slug]["text"])
        if f"{focus}{wrong_object}" in text or f"‘{focus}’{wrong_object}" in text:
            errors.append(f"{slug}: wrong object particle after {focus}")
        if f"{focus}{wrong_topic}" in text or f"‘{focus}’{wrong_topic}" in text:
            errors.append(f"{slug}: wrong topic particle after {focus}")
    return errors


def school_context_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    source = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    contexts = source.get("pages", {}) if isinstance(source, dict) else {}
    expected: dict[str, list[str]] = {}
    for english_slug, context in contexts.items():
        math_slug = str(english_slug).removesuffix("중등영어과외") + "중등수학과외"
        schools = context.get("schools", []) if isinstance(context, dict) else []
        expected[math_slug] = [
            str(item.get("homepage") or "").strip()
            for item in schools[:4]
            if isinstance(item, dict) and str(item.get("homepage") or "").strip()
        ]
    if set(expected) != set(pages):
        errors.append("school context slug set does not match 69 math pages")
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        sections = soup.select("article section.middle-math-school-context")
        if len(sections) != 1:
            errors.append(f"{slug}: school context section count {len(sections)}")
            continue
        links = sections[0].select("a.source-link[href]")
        hrefs = [str(link.get("href") or "") for link in links]
        if hrefs != expected.get(slug, []):
            errors.append(f"{slug}: school homepage links differ from source data")
        for link in links:
            href = str(link.get("href") or "")
            rel = set(link.get("rel") or [])
            if not href.startswith(("http://", "https://")):
                errors.append(f"{slug}: invalid school link {href}")
            if link.get("target") != "_blank" or not {"noopener", "noreferrer", "external"}.issubset(rel):
                errors.append(f"{slug}: unsafe external-link attributes")
    return errors


def search_intent_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        sections = soup.select("article section.middle-math-search-intent")
        if len(sections) != 1:
            errors.append(f"{slug}: search intent section count {len(sections)}")
            continue
        section = sections[0]
        location = slug.removesuffix("중등수학과외")
        focus = focus_from_before(page)
        text = section.get_text(" ", strip=True)
        if location not in text:
            errors.append(f"{slug}: location missing from search intent")
        if not focus or text.count(focus) < 6:
            errors.append(f"{slug}: math focus insufficient in search intent")
        if len(section.select(":scope > h2")) != 1 or len(section.select(":scope > h3")) != 4:
            errors.append(f"{slug}: search intent heading structure")
        if len(section.select("table")) != 1 or len(section.select("ol")) != 1 or len(section.select("ul")) != 1:
            errors.append(f"{slug}: search intent learning structure")
        if section.select("a[href]"):
            errors.append(f"{slug}: premature links in search intent")
    return errors


def student_case_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        sections = soup.select("article section.middle-math-student-case")
        if len(sections) != 1:
            errors.append(f"{slug}: student case section count {len(sections)}")
            continue
        section = sections[0]
        location = slug.removesuffix("중등수학과외")
        focus = focus_from_before(page)
        text = section.get_text(" ", strip=True)
        if section.get("data-case-model") != "composite":
            errors.append(f"{slug}: student case is not labeled composite")
        if section.get("data-case-grade") not in {"중1", "중2", "중3"}:
            errors.append(f"{slug}: invalid student case grade")
        if section.get("data-case-kind") not in {"algebra", "function", "geometry", "data", "routine"}:
            errors.append(f"{slug}: invalid student case kind")
        if location not in text:
            errors.append(f"{slug}: location missing from student case")
        if not focus or text.count(focus) < 5:
            errors.append(f"{slug}: math focus insufficient in student case")
        if not any(label in text for label in ("합성", "가상")) or not any(
            label in text for label in ("실제", "특정 학생", "공통 성향")
        ):
            errors.append(f"{slug}: student case disclaimer insufficient")
        if len(section.select(":scope > h3")) != 1:
            errors.append(f"{slug}: student case heading structure")
        if len(section.select("table")) != 1 or len(section.select("tbody tr")) != 3:
            errors.append(f"{slug}: student case comparison table")
        if len(section.select("ol")) != 1 or len(section.select("ol > li")) != 3:
            errors.append(f"{slug}: student case decision branches")
        if section.select("a[href]"):
            errors.append(f"{slug}: premature links in student case")
        for phrase in (".’을", ".’과", ".’입니다"):
            if phrase in str(section):
                errors.append(f"{slug}: misplaced punctuation in student case ({phrase})")
    return errors


def _visible_middle_math_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    heading = soup.select_one("article h2.middle-math-faq[data-faq-focus]")
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
                question_text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                answer_text = re.sub(r"\s+", " ", answer.get_text(" ", strip=True)).strip()
                pairs.append((question_text, answer_text))
        node = node.find_next_sibling()
    return pairs


def _schema_faq_pairs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    faq_items: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        faq_items.extend(
            item for item in candidates if isinstance(item, dict) and item.get("@type") == "FAQPage"
        )
    if len(faq_items) != 1:
        return []
    entities = faq_items[0].get("mainEntity", [])
    if not isinstance(entities, list):
        return []
    pairs: list[tuple[str, str]] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        answer = entity.get("acceptedAnswer", {})
        answer_text = answer.get("text", "") if isinstance(answer, dict) else ""
        pairs.append((str(entity.get("name", "")).strip(), str(answer_text).strip()))
    return pairs


def middle_math_faq_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    all_questions: Counter[str] = Counter()
    all_answers: Counter[str] = Counter()
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        headings = soup.select("article h2.middle-math-faq[data-faq-focus]")
        if len(headings) != 1:
            errors.append(f"{slug}: individualized FAQ heading count {len(headings)}")
            continue
        location = slug.removesuffix("중등수학과외")
        focus = focus_from_before(page)
        if str(headings[0].get("data-faq-focus") or "") != focus:
            errors.append(f"{slug}: FAQ focus attribute mismatch")
        visible_pairs = _visible_middle_math_faq(soup)
        if len(visible_pairs) != 5:
            errors.append(f"{slug}: visible FAQ pair count {len(visible_pairs)}")
        for question, answer in visible_pairs:
            all_questions[question] += 1
            all_answers[answer] += 1
            if not question.endswith("?"):
                errors.append(f"{slug}: FAQ question without question mark")
            if location not in question or focus not in question:
                errors.append(f"{slug}: FAQ question lacks local focus")
            if len(answer) < 110:
                errors.append(f"{slug}: short FAQ answer")
        if headings[0].find_parent("article").select("h2.middle-math-faq a[href]"):
            errors.append(f"{slug}: link inside FAQ heading")
        faq_parent = headings[0].parent
        faq_links = []
        for sibling in headings[0].find_next_siblings():
            if getattr(sibling, "name", None) == "h2":
                break
            faq_links.extend(sibling.select("a[href]") if hasattr(sibling, "select") else [])
        if faq_links:
            errors.append(f"{slug}: links inside individualized FAQ")
        if _schema_faq_pairs(soup) != visible_pairs:
            errors.append(f"{slug}: FAQ schema differs from visible FAQ")
    for question, count in all_questions.items():
        if count > 1:
            errors.append(f"repeated FAQ question x{count}: {question}")
    for answer, count in all_answers.items():
        if count > 1:
            errors.append(f"repeated FAQ answer x{count}: {answer[:80]}")
    return errors


def context_link_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    source = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    contexts = source.get("pages", {}) if isinstance(source, dict) else {}
    expected: dict[str, list[str]] = {}
    for english_slug, context in contexts.items():
        if not isinstance(context, dict):
            continue
        math_slug = str(english_slug).removesuffix("중등영어과외") + "중등수학과외"
        location = math_slug.removesuffix("중등수학과외")
        parent_english = str(context.get("parent_slug") or "")
        parent_math = (
            parent_english.removesuffix("중등영어과외") + "중등수학과외"
            if parent_english.endswith("중등영어과외")
            else str(context.get("city") or location[:2]) + "중등수학과외"
        )
        expected[math_slug] = [f"/{parent_math}/", f"/{location}수학과외/"]
    output_root = Path(__file__).resolve().parents[1] / "output"
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        sections = soup.select("article aside.middle-math-context-links")
        if len(sections) != 1:
            errors.append(f"{slug}: contextual link section count {len(sections)}")
            continue
        section = sections[0]
        links = section.select("a[href]")
        hrefs = [str(link.get("href") or "") for link in links]
        if hrefs != expected.get(slug, []):
            errors.append(f"{slug}: contextual link targets differ from expected")
        if section.get("data-link-count") != "2" or len(links) != 2:
            errors.append(f"{slug}: contextual link count {len(links)}")
        if len(hrefs) != len(set(hrefs)) or f"/{slug}/" in hrefs:
            errors.append(f"{slug}: duplicate or self contextual link")
        for link in links:
            href = str(link.get("href") or "")
            target_slug = href.strip("/")
            if not href.startswith("/") or href.startswith("//") or not target_slug:
                errors.append(f"{slug}: invalid internal href {href}")
            elif not (output_root / target_slug / "index.html").exists():
                errors.append(f"{slug}: missing internal target {href}")
            if link.get("target") is not None or link.get("rel") is not None:
                errors.append(f"{slug}: internal link has external attributes")
            if len(link.get_text(" ", strip=True)) < 8:
                errors.append(f"{slug}: context anchor text too short")
        html = str(page["html"])
        context_position = html.find('class="middle-math-context-links"')
        faq_position = html.find('class="middle-math-faq"')
        if context_position < 0 or faq_position < 0 or context_position > faq_position:
            errors.append(f"{slug}: contextual links not placed before FAQ")
    return errors


def search_metadata_errors(pages: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    titles: Counter[str] = Counter()
    descriptions: Counter[str] = Counter()
    for slug, page in pages.items():
        soup = BeautifulSoup(str(page["html"]), "html.parser")
        article = soup.select_one("article.content-body")
        if not article:
            errors.append(f"{slug}: article missing for search metadata")
            continue
        expected_title, expected_description = build_local_middle_math_meta(slug, str(article))
        title = soup.title.get_text(strip=True) if soup.title else ""
        description_tag = soup.select_one('meta[name="description"]')
        description = str(description_tag.get("content") or "") if description_tag else ""
        titles[title] += 1
        descriptions[description] += 1
        if title != expected_title:
            errors.append(f"{slug}: search title differs from generated title")
        if description != expected_description:
            errors.append(f"{slug}: meta description differs from generated description")
        if not (18 <= len(title) <= 60) or not title.startswith(f"{slug} | "):
            errors.append(f"{slug}: search title length or prefix")
        if not (90 <= len(description) <= 160) or "…" in description or description.endswith("..."):
            errors.append(f"{slug}: meta description length or truncation")
        focus = focus_from_before(page)
        if slug not in description or not focus or focus not in description:
            errors.append(f"{slug}: meta description lacks slug or focus")
        expected_canonical = f"https://edunext.co.kr/{slug}/"
        canonical_tags = soup.select('link[rel="canonical"]')
        canonical = str(canonical_tags[0].get("href") or "") if canonical_tags else ""
        if len(canonical_tags) != 1 or canonical != expected_canonical:
            errors.append(f"{slug}: canonical mismatch")
        expected_tags = {
            'meta[property="og:title"]': title,
            'meta[property="og:description"]': description,
            'meta[property="og:url"]': expected_canonical,
            'meta[name="twitter:title"]': title,
            'meta[name="twitter:description"]': description,
        }
        for selector, expected_value in expected_tags.items():
            tags = soup.select(selector)
            value = str(tags[0].get("content") or "") if tags else ""
            if len(tags) != 1 or value != expected_value:
                errors.append(f"{slug}: social metadata mismatch {selector}")
        robots = soup.select('meta[name="robots"]')
        if len(robots) != 1 or str(robots[0].get("content") or "") != "index,follow":
            errors.append(f"{slug}: robots metadata mismatch")
        h1 = soup.select_one("main h1")
        if not h1 or h1.get_text(" ", strip=True) != slug:
            errors.append(f"{slug}: H1 differs from slug")
        hero_description = h1.find_next_sibling("p") if h1 else None
        if not hero_description or hero_description.get_text(" ", strip=True) != description:
            errors.append(f"{slug}: hero description differs from meta description")
        webpage_items: list[dict[str, object]] = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
            except json.JSONDecodeError:
                continue
            candidates = data if isinstance(data, list) else [data]
            webpage_items.extend(
                item for item in candidates if isinstance(item, dict) and item.get("@type") == "WebPage"
            )
        if len(webpage_items) != 1:
            errors.append(f"{slug}: WebPage schema count {len(webpage_items)}")
        else:
            webpage = webpage_items[0]
            if (
                webpage.get("name") != title
                or webpage.get("description") != description
                or webpage.get("url") != expected_canonical
            ):
                errors.append(f"{slug}: WebPage schema metadata mismatch")
    for title, count in titles.items():
        if count > 1:
            errors.append(f"repeated search title x{count}: {title}")
    for description, count in descriptions.items():
        if count > 1:
            errors.append(f"repeated meta description x{count}: {description[:80]}")
    return errors


def summarize(label: str, pages: dict[str, dict[str, object]]) -> None:
    chars = [int(page["chars"]) for page in pages.values()]
    paragraph_counts = [len(page["paragraphs"]) for page in pages.values()]
    heading_counts = [len(page["headings"]) for page in pages.values()]
    item_counts = [int(page["items"]) for page in pages.values()]
    similarity, pair = max_similarity(pages)
    repeated_paragraphs = repeated_values(pages, "paragraphs")
    repeated_headings = repeated_values(pages, "headings")
    title_lengths = [len(str(page["search_title"])) for page in pages.values()]
    description_lengths = [len(str(page["meta_description"])) for page in pages.values()]
    print(f"[{label}]")
    print(f"pages={len(pages)}")
    print(f"chars min={min(chars)} max={max(chars)} avg={sum(chars) / len(chars):.1f}")
    print(f"paragraphs min={min(paragraph_counts)} max={max(paragraph_counts)} avg={sum(paragraph_counts) / len(paragraph_counts):.1f}")
    print(f"headings min={min(heading_counts)} max={max(heading_counts)} avg={sum(heading_counts) / len(heading_counts):.1f}")
    print(f"list_items min={min(item_counts)} max={max(item_counts)} avg={sum(item_counts) / len(item_counts):.1f}")
    print(f"article_links={sum(int(page['links']) for page in pages.values())}")
    print(f"marker_pages={sum(bool(page['marker']) for page in pages.values())}")
    print(f"school_context_pages={sum(bool(page['school_context']) for page in pages.values())}")
    print(f"school_links={sum(int(page['school_links']) for page in pages.values())}")
    print(f"search_intent_pages={sum(bool(page['search_intent']) for page in pages.values())}")
    print(f"student_case_pages={sum(bool(page['student_case']) for page in pages.values())}")
    print(f"individualized_faq_pages={sum(bool(page['faq_marker']) for page in pages.values())}")
    print(f"context_link_pages={sum(bool(page['context_links']) for page in pages.values())}")
    print(f"context_internal_links={sum(int(page['context_link_count']) for page in pages.values())}")
    print(f"search_titles_unique={len(set(str(page['search_title']) for page in pages.values()))}")
    print(f"search_title_length min={min(title_lengths)} max={max(title_lengths)}")
    print(f"meta_descriptions_unique={len(set(str(page['meta_description']) for page in pages.values()))}")
    print(f"meta_description_length min={min(description_lengths)} max={max(description_lengths)}")
    print(f"max_5gram_similarity={similarity * 100:.2f}% pair={pair[0]} | {pair[1]}")
    print(f"repeated_paragraphs_3plus={len(repeated_paragraphs)}")
    print(f"repeated_headings_3plus={len(repeated_headings)}")
    if repeated_paragraphs:
        for value, count in repeated_paragraphs.most_common(12):
            print(f"  paragraph x{count}: {value[:100]}")
    if repeated_headings:
        for value, count in repeated_headings.most_common(12):
            print(f"  heading x{count}: {value[:100]}")
    print(f"schema_errors={len(schema_errors(pages))}")
    print(f"structure_errors={len(structure_errors(pages))}")
    if any(bool(page["school_context"]) for page in pages.values()):
        print(f"school_context_errors={len(school_context_errors(pages))}")
    else:
        print("school_context_errors=not_applicable")
    if any(bool(page["search_intent"]) for page in pages.values()):
        print(f"search_intent_errors={len(search_intent_errors(pages))}")
    else:
        print("search_intent_errors=not_applicable")
    if any(bool(page["student_case"]) for page in pages.values()):
        print(f"student_case_errors={len(student_case_errors(pages))}")
    else:
        print("student_case_errors=not_applicable")
    if any(bool(page["faq_marker"]) for page in pages.values()):
        print(f"individualized_faq_errors={len(middle_math_faq_errors(pages))}")
    else:
        print("individualized_faq_errors=not_applicable")
    if any(bool(page["context_links"]) for page in pages.values()):
        print(f"context_link_errors={len(context_link_errors(pages))}")
    else:
        print("context_link_errors=not_applicable")
    print(f"search_metadata_errors={len(search_metadata_errors(pages))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    current = load_pages(args.current)
    summarize("current", current)
    if args.before:
        before = load_pages(args.before)
        summarize("before", before)
        common = sorted(set(before) & set(current))
        deltas = {slug: int(current[slug]["chars"]) - int(before[slug]["chars"]) for slug in common}
        print("[comparison]")
        print(f"common_pages={len(common)}")
        print(f"char_delta min={min(deltas.values())} max={max(deltas.values())} avg={sum(deltas.values()) / len(deltas):.1f}")
        print(f"decreased_pages={sum(delta < 0 for delta in deltas.values())}")
        print(f"particle_errors={len(particle_errors(current, before))}")
        for error in particle_errors(current, before)[:10]:
            print(f"  {error}")
        for slug, delta in sorted(deltas.items(), key=lambda item: item[1])[:5]:
            print(f"  smallest_delta {slug}: {delta:+d}")
    current_errors = (
        schema_errors(current)
        + structure_errors(current)
        + school_context_errors(current)
        + search_intent_errors(current)
        + student_case_errors(current)
        + middle_math_faq_errors(current)
        + context_link_errors(current)
        + search_metadata_errors(current)
    )
    if args.before:
        current_errors += particle_errors(current, before)
        current_errors += [slug for slug, delta in deltas.items() if delta < 0]
    return 0 if len(current) == 69 and not current_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
