from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_REGION_HUBS = {"경남과외", "경북과외"}


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def page_type(html: str) -> str:
    match = re.search(r'class="[^"]*\bpage-type-([^\s"]+)', html, flags=re.I)
    return match.group(1) if match else ""


def faq_schema_questions(html: str) -> list[str]:
    match = re.search(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, flags=re.I | re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else [data]
    faq_items = [item for item in items if isinstance(item, dict) and item.get("@type") == "FAQPage"]
    if len(faq_items) != 1:
        return []
    return [str(item.get("name", "")) for item in faq_items[0].get("mainEntity", []) if isinstance(item, dict)]


def main() -> int:
    paths = {path.parent.name: path for path in OUTPUT.glob("*/index.html")}
    html_by_slug = {slug: path.read_text(encoding="utf-8") for slug, path in paths.items()}
    types = {slug: page_type(html) for slug, html in html_by_slug.items()}
    questions: list[str] = []
    answers: list[str] = []
    rows: list[dict[str, object]] = []
    link_counts: list[int] = []
    checked = 0

    for slug, html in html_by_slug.items():
        if types[slug] != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        checked += 1
        problems: list[str] = []
        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        article_body = article.group(1) if article else ""
        faq_sections = list(re.finditer(r'<section\s+class="regional-faq"[^>]*>(.*?)</section>', article_body, flags=re.I | re.S))
        if len(faq_sections) != 1:
            problems.append(f"section_count:{len(faq_sections)}")
            faq_body = ""
        else:
            faq_body = faq_sections[0].group(1)
            contextual = re.search(r'<section\s+class="contextual-links"', article_body, flags=re.I)
            if contextual and contextual.start() > faq_sections[0].start():
                problems.append("faq_before_contextual_links")

        pairs = re.findall(r'<h3\b[^>]*>(.*?)</h3>\s*<p\b[^>]*>(.*?)</p>', faq_body, flags=re.I | re.S)
        visible_questions = [plain_text(question) for question, _ in pairs]
        visible_answers = [plain_text(answer) for _, answer in pairs]
        questions.extend(visible_questions)
        answers.extend(visible_answers)
        if len(pairs) != 5:
            problems.append(f"pair_count:{len(pairs)}")
        location = slug[: -len("과외")] if slug.endswith("과외") else slug
        if any(location not in question for question in visible_questions):
            problems.append("question_without_location")
        if any(len(answer) < 80 for answer in visible_answers):
            problems.append("short_answer")
        awkward = [text for text in [*visible_questions, *visible_answers] if re.search(r"(?:부산|구미|양산|읍|면|동|구|군)와 가까운|과제을|과외와 비교", text)]
        if awkward:
            problems.append("awkward_particle")

        links = [unescape(href) for href in re.findall(r'href=["\']([^"\']+)["\']', faq_body, flags=re.I)]
        link_counts.append(len(links))
        if len(links) > 1:
            problems.append(f"too_many_links:{len(links)}")
        if f"/{slug}/" in links:
            problems.append("self_link")
        missing = []
        for href in links:
            if href == "/#high-schools":
                continue
            target = href.strip("/")
            if target not in paths:
                missing.append(href)
        if missing:
            problems.append(f"missing_targets:{','.join(missing)}")

        schema_questions = faq_schema_questions(html)
        if schema_questions != visible_questions:
            problems.append("faq_schema_mismatch")
        if problems:
            rows.append({"slug": slug, "problems": problems})

    question_counts = Counter(questions)
    answer_counts = Counter(answers)
    repeated_questions = {text: count for text, count in question_counts.items() if count > 1}
    repeated_answers = {text: count for text, count in answer_counts.items() if count > 1}
    result = {
        "checked": checked,
        "questions": len(questions),
        "unique_questions": len(question_counts),
        "repeated_questions": repeated_questions,
        "repeated_answers": repeated_answers,
        "min_faq_links": min(link_counts) if link_counts else 0,
        "max_faq_links": max(link_counts) if link_counts else 0,
        "problems": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if rows or repeated_questions or repeated_answers else 0


if __name__ == "__main__":
    raise SystemExit(main())
