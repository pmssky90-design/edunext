from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR
from sitegen.render import (
    SPECIAL_REGION_HUBS,
    deduplicate_region_body_links,
    enhance_content_body,
    faq_schema,
    replace_regional_faq,
)
from scripts.refresh_region_contextual_links import (
    load_region_relationships,
    load_school_relationships,
    page_from_html,
    replace_toc,
)


def update_json_ld(html: str, body: str) -> str:
    pattern = r'(<script\s+type=["\']application/ld\+json["\']>)(.*?)(</script>)'
    match = re.search(pattern, html, flags=re.I | re.S)
    if not match:
        return html
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return html
    items = data if isinstance(data, list) else [data]
    items = [item for item in items if not isinstance(item, dict) or item.get("@type") != "FAQPage"]
    faq = faq_schema(body)
    if faq:
        items.append(faq)
    replacement = match.group(1) + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + match.group(3)
    return html[: match.start()] + replacement + html[match.end() :]


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

    changed = 0
    school_faqs = 0
    directory_faqs = 0
    for slug, page in page_map.items():
        if page.page_type != "region" or slug in SPECIAL_REGION_HUBS:
            continue
        html = html_by_slug[slug]
        article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        if not article:
            continue
        body = replace_regional_faq(article.group(1), page, page_map)
        body = deduplicate_region_body_links(body, page)
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios=True)
        enhanced_body = enhanced_body.strip()
        updated = html[: article.start(1)] + enhanced_body + html[article.end(1) :]
        updated = replace_toc(updated, toc)
        updated = update_json_ld(updated, enhanced_body)
        if updated != html:
            path_by_slug[slug].write_text(updated, encoding="utf-8", newline="\n")
            changed += 1
        if page.school_slugs:
            school_faqs += 1
        else:
            directory_faqs += 1

    shutil.copy2(ROOT / "assets" / "css" / "style.css", OUTPUT_DIR / "assets" / "css" / "style.css")
    print(f"refreshed regional FAQs: {changed}")
    print(f"FAQs with direct school pages: {school_faqs}")
    print(f"FAQs using the school directory: {directory_faqs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
