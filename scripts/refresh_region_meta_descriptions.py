from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import OUTPUT_DIR
from sitegen.utils import region_meta_description


SPECIAL_HUBS = {"경남과외", "경북과외"}
META_PATTERNS = (
    r'(<meta name="description" content=")([^"]*)(">)',
    r'(<meta property="og:description" content=")([^"]*)(">)',
    r'(<meta name="twitter:description" content=")([^"]*)(">)',
)


def update_json_ld(html: str, description: str) -> str:
    pattern = r'(<script\s+type=["\']application/ld\+json["\']>)(.*?)(</script>)'
    match = re.search(pattern, html, flags=re.I | re.S)
    if not match:
        return html
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return html
    items = data if isinstance(data, list) else [data]
    for item in items:
        if isinstance(item, dict) and item.get("@type") == "WebPage":
            item["description"] = description
    replacement = match.group(1) + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + match.group(3)
    return html[: match.start()] + replacement + html[match.end() :]


def refresh(path: Path) -> bool:
    html = path.read_text(encoding="utf-8")
    if "page-type-region" not in html or path.parent.name in SPECIAL_HUBS:
        return False
    article = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    if not article:
        return False
    description = region_meta_description(path.parent.name, article.group(1))
    updated = html
    encoded = escape(description, quote=True)
    for pattern in META_PATTERNS:
        updated = re.sub(pattern, rf"\g<1>{encoded}\g<3>", updated, count=1, flags=re.I)
    updated = update_json_ld(updated, description)
    if updated == html:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    changed = sum(refresh(path) for path in OUTPUT_DIR.glob("*/index.html"))
    print(f"refreshed region meta descriptions: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
