from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR, SITE_NAME, SITE_URL
from sitegen.render import enhance_content_body, faq_schema, render_not_found


def text_of(pattern: str, html: str, default: str = "") -> str:
    match = re.search(pattern, html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(1))).strip() if match else default


def enhance_json_ld(html: str, body: str) -> str:
    pattern = r'(<script\s+type=["\']application/ld\+json["\']>)(.*?)(</script>)'
    match = re.search(pattern, html, flags=re.I | re.S)
    if not match:
        return html
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return html
    items = data if isinstance(data, list) else [data]
    items = [item for item in items if not isinstance(item, dict) or item.get("@type") not in {"Organization", "FAQPage"}]
    items.insert(0, {"@context": "https://schema.org", "@type": "Organization", "@id": f"{SITE_URL}/#organization", "name": SITE_NAME, "url": SITE_URL + "/"})
    faq = faq_schema(body)
    if faq:
        items.append(faq)
    replacement = match.group(1) + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + match.group(3)
    return html[: match.start()] + replacement + html[match.end() :]


def enhance_page(path: Path) -> bool:
    html = path.read_text(encoding="utf-8")
    original = html
    article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    body = article.group(1) if article else ""

    if body:
        enhanced_body, toc = enhance_content_body(body, clarify_scenarios="page-type-region" in html)
        html = html[: article.start(1)] + enhanced_body + html[article.end(1) :]
        existing_toc = re.search(r'<nav\s+class="page-toc".*?</nav>\s*', html, flags=re.I | re.S)
        if existing_toc:
            html = html[: existing_toc.start()] + (toc + "\n    " if toc else "") + html[existing_toc.end() :]
        elif toc:
            article_start = html.find('<article class="content-body">')
            html = html[:article_start] + toc + "\n    " + html[article_start:]

    if 'property="og:image:alt"' not in html:
        title = text_of(r"<h1\b[^>]*>(.*?)</h1>", html, SITE_NAME)
        html = re.sub(
            r'(<meta\s+property="og:image"\s+content="[^"]*">)',
            rf'\1\n  <meta property="og:image:alt" content="{title} 대표 이미지">',
            html,
            count=1,
            flags=re.I,
        )

    html = enhance_json_ld(html, enhanced_body if body else "")
    if html != original:
        path.write_text(html, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    changed = sum(enhance_page(path) for path in OUTPUT_DIR.rglob("index.html"))
    shutil.copy2(ROOT / "assets" / "css" / "style.css", OUTPUT_DIR / "assets" / "css" / "style.css")
    (OUTPUT_DIR / "404.html").write_text(render_not_found(), encoding="utf-8", newline="\n")
    print(f"enhanced pages: {changed}")
    print(f"404 page: {OUTPUT_DIR / '404.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
