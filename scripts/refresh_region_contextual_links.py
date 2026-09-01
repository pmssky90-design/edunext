from __future__ import annotations

import json
import re
import shutil
import sys
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR
from sitegen.models import Page
from sitegen.render import (
    SPECIAL_REGION_HUBS,
    add_contextual_region_links,
    deduplicate_region_body_links,
    enhance_content_body,
    plain_text,
)


def page_from_html(path: Path, html: str) -> Page | None:
    page_type_match = re.search(r'class="[^"]*\bpage-type-([^\s"]+)', html, flags=re.I)
    title_match = re.search(r"<h1\b[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
    if not page_type_match or not title_match:
        return None
    return Page(
        slug=path.parent.name,
        title=plain_text(title_match.group(1)),
        page_type=page_type_match.group(1),
        category="과외",
    )


def linked_slugs(fragment: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for href in re.findall(r'href=["\'](/[^"\']+/)["\']', fragment, flags=re.I):
        slug = unescape(href).strip("/")
        if slug and slug not in seen:
            seen.add(slug)
            found.append(slug)
    return found


def load_school_relationships(page_map: dict[str, Page]) -> dict[str, list[str]]:
    """Restore school metadata and source mappings during partial HTML refreshes."""
    assignments: dict[str, list[str]] = {}
    path = ROOT / "data" / "school_region_map.json"
    if not path.exists():
        return assignments
    for row in json.loads(path.read_text(encoding="utf-8")):
        keyword = str(row.get("keyword", ""))
        school = page_map.get(keyword)
        if not school:
            continue
        school.school_display_name = str(row.get("school_display_name", ""))
        school.official_school_name = str(row.get("official_school_name", ""))
        for region_slug in str(row.get("mapped_region_pages", "")).split("|"):
            if region_slug in page_map:
                assignments.setdefault(region_slug, []).append(keyword)
    for region_slug, school_slugs in assignments.items():
        page_map[region_slug].school_slugs = list(dict.fromkeys(school_slugs))
    return assignments


def load_region_relationships(page_map: dict[str, Page], html_by_slug: dict[str, str]) -> None:
    """Rebuild the region hierarchy from breadcrumbs before partial refreshes."""
    hierarchy_slugs = {
        slug for slug, page in page_map.items() if page.page_type in {"region", "hub"}
    }
    children_by_parent: dict[str, list[str]] = {}
    for slug in sorted(hierarchy_slugs):
        breadcrumb = re.search(
            r'<nav\s+class="breadcrumb".*?</nav>',
            html_by_slug[slug],
            flags=re.I | re.S,
        )
        breadcrumb_slugs = linked_slugs(breadcrumb.group(0)) if breadcrumb else []
        parents = [item for item in breadcrumb_slugs if item in hierarchy_slugs and item != slug]
        parent_slug = parents[-1] if parents else None
        page_map[slug].parent_slug = parent_slug
        if parent_slug:
            children_by_parent.setdefault(parent_slug, []).append(slug)
    for parent_slug, children in children_by_parent.items():
        page_map[parent_slug].child_slugs = children
        for slug in children:
            page_map[slug].sibling_slugs = [item for item in children if item != slug]


def replace_toc(html: str, toc: str) -> str:
    existing = re.search(r'<nav\s+class="page-toc".*?</nav>\s*', html, flags=re.I | re.S)
    if existing:
        replacement = f"{toc}\n    " if toc else ""
        return html[: existing.start()] + replacement + html[existing.end() :]
    if toc:
        article_start = html.find('<article class="content-body">')
        if article_start >= 0:
            return html[:article_start] + f"{toc}\n    " + html[article_start:]
    return html


def main() -> int:
    html_by_slug: dict[str, str] = {}
    path_by_slug: dict[str, Path] = {}
    page_map: dict[str, Page] = {}
    for path in OUTPUT_DIR.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        page = page_from_html(path, html)
        if not page:
            continue
        html_by_slug[page.slug] = html
        path_by_slug[page.slug] = path
        page_map[page.slug] = page

    load_school_relationships(page_map)
    load_region_relationships(page_map, html_by_slug)

    changed = 0
    school_pages = 0
    nearby_pages = 0
    for slug, page in page_map.items():
        if page.page_type != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        html = html_by_slug[slug]
        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        if not article:
            continue
        body = add_contextual_region_links(article.group(1), page, page_map)
        body = deduplicate_region_body_links(body, page)
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios=True)
        enhanced_body = enhanced_body.strip()
        updated = html[: article.start(1)] + enhanced_body + html[article.end(1) :]
        updated = replace_toc(updated, toc)
        if updated != html:
            path_by_slug[slug].write_text(updated, encoding="utf-8", newline="\n")
            changed += 1
        if page.school_slugs:
            school_pages += 1
        else:
            nearby_pages += 1

    shutil.copy2(ROOT / "assets" / "css" / "style.css", OUTPUT_DIR / "assets" / "css" / "style.css")
    print(f"refreshed regional contextual links: {changed}")
    print(f"pages with direct school links: {school_pages}")
    print(f"pages using nearby-region fallback: {nearby_pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
