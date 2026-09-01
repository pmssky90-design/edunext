from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_REGION_HUBS = {"경남과외", "경북과외"}


def page_type(html: str) -> str:
    match = re.search(r'class="[^"]*\bpage-type-([^\s"]+)', html, flags=re.I)
    return match.group(1) if match else ""


def href_slugs(fragment: str) -> list[str]:
    return [unescape(href).strip("/") for href in re.findall(r'href="(/[^"#?]+/)"', fragment, flags=re.I)]


def main() -> int:
    paths = {path.parent.name: path for path in OUTPUT.glob("*/index.html")}
    html_by_slug = {slug: path.read_text(encoding="utf-8") for slug, path in paths.items()}
    types = {slug: page_type(html) for slug, html in html_by_slug.items()}
    rows: list[dict[str, object]] = []
    link_counts: list[int] = []
    pages_with_school_links = 0
    pages_with_nearby_fallback = 0
    checked = 0

    for slug, html in html_by_slug.items():
        if types[slug] != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        checked += 1
        problems: list[str] = []
        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        article_body = article.group(1) if article else ""
        section_matches = list(re.finditer(r'<section\s+class="contextual-links"[^>]*>(.*?)</section>', article_body, flags=re.I | re.S))
        if len(section_matches) != 1:
            problems.append(f"section_count:{len(section_matches)}")
            section = ""
        else:
            section = section_matches[0].group(1)
            first_heading = re.search(r"<h2\b", article_body, flags=re.I)
            faq_heading = re.search(
                r'<section\s+class="regional-faq"[^>]*>',
                article_body,
                flags=re.I,
            )
            if not faq_heading:
                faq_heading = re.search(
                    r"<h2\b[^>]*>(?:(?!</h2>).)*(?:FAQ|자주\s*묻는\s*질문)(?:(?!</h2>).)*</h2>",
                    article_body,
                    flags=re.I | re.S,
                )
            if first_heading and section_matches[0].start() <= first_heading.start():
                problems.append("section_before_main_content")
            if faq_heading and section_matches[0].start() > faq_heading.start():
                problems.append("section_after_faq")
        links = href_slugs(section)
        link_counts.append(len(links))
        if len(links) < 3:
            problems.append(f"too_few_links:{len(links)}")
        if len(links) != len(set(links)):
            problems.append("duplicate_links")
        if slug in links:
            problems.append("self_link")
        missing = [item for item in links if item not in paths]
        if missing:
            problems.append(f"missing_targets:{','.join(missing)}")

        base = slug[: -len("과외")] if slug.endswith("과외") else slug
        for required in (f"{base}영어과외", f"{base}수학과외"):
            if required in paths and required not in links:
                problems.append(f"missing_subject:{required}")

        breadcrumb = re.search(r'<nav\s+class="breadcrumb".*?</nav>', html, flags=re.I | re.S)
        parents = [item for item in href_slugs(breadcrumb.group(0)) if item in paths and item != slug] if breadcrumb else []
        if parents and parents[-1] not in links:
            problems.append(f"missing_parent:{parents[-1]}")

        school_links = [
            item
            for item in links
            if types.get(item) == "school" and not item.endswith("영어과외") and not item.endswith("수학과외")
        ]
        if school_links:
            pages_with_school_links += 1
            if len(school_links) > 3:
                problems.append("too_many_school_links")
        else:
            region_links = [item for item in links if types.get(item) == "region" and item not in parents]
            if region_links:
                pages_with_nearby_fallback += 1

        anchors = re.findall(r'<a\b[^>]*>(.*?)</a>', section, flags=re.I | re.S)
        if any(not re.sub(r"<[^>]+>", "", anchor).strip() or re.sub(r"<[^>]+>", "", anchor).strip() in {"여기", "자세히"} for anchor in anchors):
            problems.append("generic_anchor")
        if problems:
            rows.append({"slug": slug, "problems": problems, "links": links})

    result = {
        "checked": checked,
        "min_links": min(link_counts) if link_counts else 0,
        "max_links": max(link_counts) if link_counts else 0,
        "pages_with_school_links": pages_with_school_links,
        "pages_with_nearby_fallback": pages_with_nearby_fallback,
        "problems": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
