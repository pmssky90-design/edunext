from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
sys.path.insert(0, str(ROOT))

from sitegen.local_high_english import (
    build_local_high_english_meta,
    individualize_local_high_english_body,
    is_local_high_english_slug,
)
from sitegen.render import enhance_content_body, faq_schema
from sitegen.utils import escape


ARTICLE_PATTERN = re.compile(r'(<article class="content-body">)(.*?)(</article>)', flags=re.I | re.S)
TOC_PATTERN = re.compile(r'<nav class="page-toc".*?</nav>', flags=re.I | re.S)
SCHEMA_PATTERN = re.compile(
    r'(<script\s+type="application/ld\+json">)(.*?)(</script>)',
    flags=re.I | re.S,
)


def _replace_schema(html: str, body: str, search_title: str, meta_description: str) -> str:
    match = SCHEMA_PATTERN.search(html)
    if not match:
        return html
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return html
    if not isinstance(data, list):
        return html
    for item in data:
        if isinstance(item, dict) and item.get("@type") == "WebPage":
            item["name"] = search_title
            item["description"] = meta_description
    data = [item for item in data if not isinstance(item, dict) or item.get("@type") != "FAQPage"]
    faq = faq_schema(body)
    if faq:
        data.append(faq)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return html[: match.start()] + match.group(1) + encoded + match.group(3) + html[match.end() :]


def _replace_search_meta(html: str, search_title: str, meta_description: str) -> str:
    title = escape(search_title)
    description = escape(meta_description)
    replacements = (
        (r"(<title>).*?(</title>)", rf"\g<1>{title}\g<2>"),
        (r'(<meta\s+name="description"\s+content=")[^"]*(">)', rf"\g<1>{description}\g<2>"),
        (r'(<meta\s+property="og:title"\s+content=")[^"]*(">)', rf"\g<1>{title}\g<2>"),
        (r'(<meta\s+property="og:description"\s+content=")[^"]*(">)', rf"\g<1>{description}\g<2>"),
        (r'(<meta\s+name="twitter:title"\s+content=")[^"]*(">)', rf"\g<1>{title}\g<2>"),
        (r'(<meta\s+name="twitter:description"\s+content=")[^"]*(">)', rf"\g<1>{description}\g<2>"),
        (
            r'(<section\s+class="page-hero">\s*<p\s+class="eyebrow">.*?</p>\s*'
            r'<h1>.*?</h1>\s*<p>).*?(</p>)',
            rf"\g<1>{description}\g<2>",
        ),
    )
    for pattern, replacement in replacements:
        html = re.sub(pattern, replacement, html, count=1, flags=re.I | re.S)
    return html


def refresh_page(html: str, slug: str) -> str:
    article = ARTICLE_PATTERN.search(html)
    if not article:
        return html
    individualized = individualize_local_high_english_body(article.group(2), slug)
    individualized = re.sub(
        r'(<h[23]\b[^>]*?)\s+id=["\'][^"\']+["\']',
        r"\1",
        individualized,
        flags=re.I,
    )
    search_title, meta_description = build_local_high_english_meta(slug, individualized)
    enhanced, toc = enhance_content_body(individualized)
    refreshed = (
        html[: article.start()]
        + article.group(1)
        + enhanced
        + article.group(3)
        + html[article.end() :]
    )
    refreshed = TOC_PATTERN.sub(toc, refreshed, count=1)
    refreshed = _replace_search_meta(refreshed, search_title, meta_description)
    return _replace_schema(refreshed, individualized, search_title, meta_description)


def main() -> int:
    checked = 0
    updated: list[str] = []
    for path in sorted(OUTPUT.glob("*/index.html")):
        slug = path.parent.name
        if not is_local_high_english_slug(slug):
            continue
        checked += 1
        html = path.read_text(encoding="utf-8")
        refreshed = refresh_page(html, slug)
        if refreshed == html:
            continue
        path.write_text(refreshed, encoding="utf-8", newline="\n")
        updated.append(slug)
    print(f"checked local high-English pages: {checked}")
    print(f"updated local high-English pages: {len(updated)}")
    return 0 if checked == 69 else 1


if __name__ == "__main__":
    raise SystemExit(main())
