from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sitegen.content_builder import special_region_hub_content


OUTPUT = ROOT / "output"
SLUGS = ("전국과외", "경남과외", "경북과외")


def main() -> int:
    changed = 0
    for slug in SLUGS:
        path = OUTPUT / slug / "index.html"
        html = path.read_text(encoding="utf-8")
        body = special_region_hub_content(slug)
        if body is None:
            raise RuntimeError(f"missing special content: {slug}")
        updated, count = re.subn(
            r'(?s)(<article class="content-body">).*?(</article>)',
            lambda match: match.group(1) + body + match.group(2),
            html,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"article replacement failed: {slug}")
        if updated != html:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"refreshed special region hubs: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
