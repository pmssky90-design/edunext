from __future__ import annotations

import re
import shutil
import sys
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR
from sitegen.render import (
    PRIORITY_REGION_SLUGS,
    add_contextual_region_links,
    deduplicate_region_body_links,
    enhance_content_body,
    individualize_priority_region_body,
    replace_regional_faq,
)
from sitegen.utils import region_meta_description
from scripts.refresh_region_contextual_links import (
    load_region_relationships,
    load_school_relationships,
    page_from_html,
    replace_toc,
)
from scripts.refresh_region_faqs import update_json_ld as update_faq_json_ld
from scripts.refresh_region_meta_descriptions import META_PATTERNS, update_json_ld as update_meta_json_ld


def replace_hero_description(html: str, description: str) -> str:
    pattern = r'(<section\s+class="page-hero"[^>]*>.*?<h1\b[^>]*>.*?</h1>\s*<p>)(.*?)(</p>)'
    return re.sub(pattern, rf"\g<1>{escape(description)}\g<3>", html, count=1, flags=re.I | re.S)


def main() -> int:
    html_by_slug: dict[str, str] = {}
    path_by_slug: dict[str, Path] = {}
    page_map = {}
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

    missing = sorted(PRIORITY_REGION_SLUGS - page_map.keys())
    if missing:
        print(f"missing priority pages: {', '.join(missing)}")
        return 1

    changed = 0
    for slug in sorted(PRIORITY_REGION_SLUGS):
        page = page_map[slug]
        html = html_by_slug[slug]

        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        if not article:
            print(f"missing article: {slug}")
            return 1
        body = individualize_priority_region_body(article.group(1), page)
        body = add_contextual_region_links(body, page, page_map)
        body = replace_regional_faq(body, page, page_map)
        body = deduplicate_region_body_links(body, page)
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios=True)
        enhanced_body = enhanced_body.strip()
        updated = html[: article.start(1)] + enhanced_body + html[article.end(1) :]
        updated = replace_toc(updated, toc)
        updated = update_faq_json_ld(updated, enhanced_body)
        description = region_meta_description(slug, enhanced_body)
        encoded = escape(description, quote=True)
        for pattern in META_PATTERNS:
            updated = re.sub(pattern, rf"\g<1>{encoded}\g<3>", updated, count=1, flags=re.I)
        updated = update_meta_json_ld(updated, description)
        updated = replace_hero_description(updated, description)
        if updated != html:
            path_by_slug[slug].write_text(updated, encoding="utf-8", newline="\n")
            changed += 1

    shutil.copy2(ROOT / "assets" / "css" / "style.css", OUTPUT_DIR / "assets" / "css" / "style.css")
    print(f"refreshed priority region content: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
