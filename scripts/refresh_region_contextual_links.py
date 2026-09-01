from __future__ import annotations

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

    changed = 0
    school_pages = 0
    nearby_pages = 0
    for slug, page in page_map.items():
        if page.page_type != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        html = html_by_slug[slug]
        breadcrumb = re.search(r'<nav\s+class="breadcrumb".*?</nav>', html, flags=re.I | re.S)
        breadcrumb_slugs = linked_slugs(breadcrumb.group(0)) if breadcrumb else []
        parent_candidates = [item for item in breadcrumb_slugs if item in page_map and item != slug]
        page.parent_slug = parent_candidates[-1] if parent_candidates else None

        related = re.search(r'<nav\s+class="related-navigation".*?</nav>', html, flags=re.I | re.S)
        related_slugs = linked_slugs(related.group(0)) if related else []
        page.school_slugs = [
            item
            for item in related_slugs
            if item in page_map
            and page_map[item].page_type == "school"
            and not item.endswith("영어과외")
            and not item.endswith("수학과외")
        ]
        region_links = [
            item
            for item in related_slugs
            if item in page_map
            and page_map[item].page_type == "region"
            and item not in {slug, page.parent_slug}
        ]
        page.child_slugs = region_links
        page.sibling_slugs = region_links

        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        if not article:
            continue
        body = add_contextual_region_links(article.group(1), page, page_map)
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios=True)
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
