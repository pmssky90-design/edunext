from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
sys.path.insert(0, str(ROOT))

from sitegen.render import enhance_content_body, faq_schema
from sitegen.school_english import (
    build_school_english_body,
    build_school_english_meta,
    is_school_english_slug,
    school_english_contexts,
)
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
    body = build_school_english_body(slug)
    body = re.sub(r'(<h[23]\b[^>]*?)\s+id=["\'][^"\']+["\']', r"\1", body, flags=re.I)
    search_title, meta_description = build_school_english_meta(slug, body)
    enhanced, toc = enhance_content_body(body)
    refreshed = html[: article.start()] + article.group(1) + enhanced + article.group(3) + html[article.end() :]
    refreshed = TOC_PATTERN.sub(toc, refreshed, count=1)
    refreshed = _replace_search_meta(refreshed, search_title, meta_description)
    return _replace_schema(refreshed, body, search_title, meta_description)


def main() -> int:
    expected = set(school_english_contexts())
    updated: list[str] = []
    missing: list[str] = []
    for slug in sorted(expected):
        path = OUTPUT / slug / "index.html"
        if not path.exists():
            missing.append(slug)
            continue
        html = path.read_text(encoding="utf-8")
        refreshed = refresh_page(html, slug)
        if refreshed != html:
            path.write_text(refreshed, encoding="utf-8", newline="\n")
            updated.append(slug)
    extra = [path.parent.name for path in OUTPUT.glob("*/index.html") if is_school_english_slug(path.parent.name) and path.parent.name not in expected]
    print(f"expected school English pages: {len(expected)}")
    print(f"updated school English pages: {len(updated)}")
    print(f"missing school English pages: {len(missing)}")
    print(f"unexpected school English pages: {len(extra)}")
    return 0 if len(expected) == 143 and not missing and not extra else 1


if __name__ == "__main__":
    raise SystemExit(main())
