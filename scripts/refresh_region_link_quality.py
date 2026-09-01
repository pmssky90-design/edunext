from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR
from sitegen.render import (
    SPECIAL_REGION_HUBS,
    deduplicate_region_body_links,
    enhance_content_body,
    plain_text,
    render_related_navigation,
)
from scripts.refresh_region_contextual_links import (
    linked_slugs,
    load_region_relationships,
    load_school_relationships,
    page_from_html,
    replace_toc,
)
from scripts.refresh_region_faqs import update_json_ld


SUBJECT_GRADES = (
    "초등영어과외",
    "중등영어과외",
    "고등영어과외",
    "초등수학과외",
    "중등수학과외",
    "고등수학과외",
)

def infer_category(slug: str, page_type: str) -> str:
    if page_type == "school":
        if slug.endswith("수학과외"):
            return "고등수학과외"
        if slug.endswith("영어과외"):
            return "고등영어과외"
        return "고등과외"
    for suffix in SUBJECT_GRADES:
        if slug.endswith(suffix):
            return suffix
    for suffix in ("영어과외", "수학과외", "초등과외", "중등과외", "고등과외"):
        if slug.endswith(suffix):
            return suffix
    return "과외"


def school_base(slug: str) -> str:
    for suffix in ("수학과외", "영어과외", "과외"):
        if slug.endswith(suffix):
            return slug[: -len(suffix)]
    return slug


def related_groups(fragment: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for section in re.finditer(r'<section\b[^>]*>(.*?)</section>', fragment, flags=re.I | re.S):
        heading = re.search(r'<h2\b[^>]*>(.*?)</h2>', section.group(1), flags=re.I | re.S)
        if not heading:
            continue
        groups[plain_text(heading.group(1))] = linked_slugs(section.group(0))
    return groups


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def main() -> int:
    html_by_slug: dict[str, str] = {}
    path_by_slug: dict[str, Path] = {}
    page_map = {}
    for path in OUTPUT_DIR.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        page = page_from_html(path, html)
        if not page:
            continue
        page.category = infer_category(page.slug, page.page_type)
        if page.page_type == "school":
            page.school_display_name = school_base(page.slug)
        html_by_slug[page.slug] = html
        path_by_slug[page.slug] = path
        page_map[page.slug] = page

    load_school_relationships(page_map)
    load_region_relationships(page_map, html_by_slug)

    changed = 0
    checked = 0
    for slug, page in sorted(page_map.items()):
        if page.page_type != "region" or page.category != "과외" or slug in SPECIAL_REGION_HUBS:
            continue
        checked += 1
        html = html_by_slug[slug]

        related = re.search(r'<nav\s+class="related-navigation".*?</nav>', html, flags=re.I | re.S)
        groups = related_groups(related.group(0)) if related else {}
        all_related = unique([item for values in groups.values() for item in values if item in page_map])
        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        if not article:
            print(f"missing article: {slug}")
            return 1
        page.related_slugs = [item for item in all_related if page_map[item].page_type != "school"]
        body = deduplicate_region_body_links(article.group(1), page)
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios=True)
        enhanced_body = enhanced_body.strip()
        updated = html[: article.start(1)] + enhanced_body + html[article.end(1) :]
        updated = replace_toc(updated, toc)
        updated = update_json_ld(updated, enhanced_body)
        updated = updated.replace(
            'href="/assets/css/style.css"',
            'href="/assets/css/style.css?v=20260901-link-quality"',
        )

        new_navigation = render_related_navigation(page, page_map, enhanced_body)
        existing_navigation = re.search(
            r'\s*<nav\s+class="related-navigation"[^>]*>.*?</nav>\s*',
            updated,
            flags=re.I | re.S,
        )
        if existing_navigation:
            replacement = f"\n    {new_navigation}\n  " if new_navigation else "\n  "
            updated = updated[: existing_navigation.start()] + replacement + updated[existing_navigation.end() :]
        elif new_navigation:
            main_end = updated.find("</main>")
            updated = updated[:main_end] + f"    {new_navigation}\n  " + updated[main_end:]

        if updated != html:
            path_by_slug[slug].write_text(updated, encoding="utf-8", newline="\n")
            changed += 1

    print(f"checked region pages: {checked}")
    print(f"refreshed region link quality: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
