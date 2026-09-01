from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_HUBS = {"경남과외", "경북과외"}


def main() -> int:
    rows: list[dict[str, object]] = []
    descriptions: dict[str, list[str]] = {}
    for path in OUTPUT.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        if "page-type-region" not in html or path.parent.name in SPECIAL_HUBS:
            continue
        values = []
        for pattern in (
            r'<meta name="description" content="([^"]*)">',
            r'<meta property="og:description" content="([^"]*)">',
            r'<meta name="twitter:description" content="([^"]*)">',
        ):
            match = re.search(pattern, html, flags=re.I)
            values.append(unescape(match.group(1)) if match else "")
        description = values[0]
        descriptions.setdefault(description, []).append(path.parent.name)
        json_match = re.search(r'<script\s+type="application/ld\+json">(.*?)</script>', html, flags=re.I | re.S)
        web_description = ""
        if json_match:
            data = json.loads(json_match.group(1))
            items = data if isinstance(data, list) else [data]
            web_page = next((item for item in items if isinstance(item, dict) and item.get("@type") == "WebPage"), {})
            web_description = str(web_page.get("description", ""))
        problems = []
        if not description or len(description) > 80:
            problems.append("length")
        if description.endswith("…"):
            problems.append("ellipsis")
        if len(set(values)) != 1 or web_description != description:
            problems.append("metadata_mismatch")
        if problems:
            rows.append({"slug": path.parent.name, "length": len(description), "problems": problems})

    duplicates = {text: slugs for text, slugs in descriptions.items() if len(slugs) > 1}
    result = {
        "checked": len(descriptions),
        "min_length": min(map(len, descriptions)) if descriptions else 0,
        "max_length": max(map(len, descriptions)) if descriptions else 0,
        "duplicates": duplicates,
        "problems": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if duplicates or rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
