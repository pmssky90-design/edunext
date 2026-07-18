from __future__ import annotations

import csv
import hashlib
import html
import os
import re
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sitegen.data_loader import load_content

OUTPUT = ROOT / os.environ.get("EDUNEXT_FIDELITY_OUTPUT", "output_content_fixed")
AUDIT = ROOT / "audit"


def strip_text(value: str) -> str:
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def article_text(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'(?is)<article class="content-body">(.*?)</article>', text)
    return strip_text(match.group(1) if match else "")


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def snippet(value: str, offset: str) -> str:
    if offset == "start":
        return value[:80]
    if offset == "end":
        return value[-80:]
    start = max(0, len(value) // 2 - 40)
    return value[start : start + 80]


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    content, _ = load_content()
    rows = []
    for keyword, raw_html in sorted(content.items()):
        raw_text = strip_text(raw_html)
        page_text = article_text(OUTPUT / keyword / "index.html")
        raw_len = len(raw_text)
        page_len = len(page_text)
        ratio = round(page_len / raw_len * 100, 2) if raw_len else 0
        rows.append({
            "keyword": keyword,
            "raw_character_count": raw_len,
            "page_character_count": page_len,
            "preservation_ratio": ratio,
            "start_preserved": snippet(raw_text, "start") in page_text,
            "middle_preserved": snippet(raw_text, "middle") in page_text,
            "end_preserved": snippet(raw_text, "end") in page_text,
            "fallback_used": "학부모 확인 기준" in page_text and snippet(raw_text, "start") not in page_text,
            "output_exists": (OUTPUT / keyword / "index.html").exists(),
            "raw_sha256": sha(raw_text),
            "page_sha256": sha(page_text),
        })
    with (AUDIT / "content-fidelity-after.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    ratios = [float(row["preservation_ratio"]) for row in rows if int(row["raw_character_count"]) > 0]
    summary = {
        "pages": len(rows),
        "avg_raw_chars": round(mean([int(row["raw_character_count"]) for row in rows]), 2),
        "avg_page_chars": round(mean([int(row["page_character_count"]) for row in rows]), 2),
        "avg_ratio": round(mean(ratios), 2),
        "under_90": sum(1 for row in rows if float(row["preservation_ratio"]) < 90),
        "under_70": sum(1 for row in rows if float(row["preservation_ratio"]) < 70),
        "fallback_used": sum(1 for row in rows if str(row["fallback_used"]).lower() == "true"),
    }
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
