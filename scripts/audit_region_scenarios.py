from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_HUBS = {"경남과외", "경북과외"}
OLD_PHRASES = (
    "학생 사례입니다.",
    "이 사례의 관찰 기준은",
    "이 변화는 점수 보장이 아니라",
)


def main() -> int:
    checked = 0
    problems: list[dict[str, object]] = []
    for path in OUTPUT.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        slug = path.parent.name
        if "page-type-region" not in html or slug in SPECIAL_HUBS:
            continue
        checked += 1
        notices = html.count('class="scenario-notice"')
        headings = len(re.findall(r"<h2\b[^>]*>가상 학습 시나리오:", html))
        old_phrases = [phrase for phrase in OLD_PHRASES if phrase in html]
        heading_uses_case = bool(re.search(r"<h2\b[^>]*>가상 학습 시나리오:[^<]*사례", html))
        if notices != 1 or headings != 1 or old_phrases or heading_uses_case:
            problems.append(
                {
                    "slug": slug,
                    "notices": notices,
                    "headings": headings,
                    "old_phrases": old_phrases,
                    "heading_uses_case": heading_uses_case,
                }
            )

    print(json.dumps({"checked": checked, "problems": problems}, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
