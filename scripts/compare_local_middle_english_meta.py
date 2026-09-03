from __future__ import annotations

from html import unescape
from pathlib import Path
import json
import re
import sys


TARGET = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등영어과외$")


def extract(root: Path) -> dict[str, tuple[str, str]]:
    values: dict[str, tuple[str, str]] = {}
    for path in sorted(root.glob("*/index.html")):
        slug = path.parent.name
        if not TARGET.fullmatch(slug):
            continue
        html = path.read_text(encoding="utf-8")
        title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        description_match = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
            html,
            flags=re.I,
        )
        title = unescape(title_match.group(1)).strip() if title_match else ""
        description = unescape(description_match.group(1)).strip() if description_match else ""
        values[slug] = (title, description)
    return values


def length_stats(values: list[str]) -> dict[str, float | int]:
    return {
        "minimum": min(map(len, values)) if values else 0,
        "maximum": max(map(len, values)) if values else 0,
        "average": round(sum(map(len, values)) / len(values), 1) if values else 0,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_local_middle_english_meta.py BEFORE_ROOT AFTER_ROOT")
        return 2
    before = extract(Path(sys.argv[1]))
    after = extract(Path(sys.argv[2]))
    common = sorted(before.keys() & after.keys())
    before_titles = [before[slug][0] for slug in common]
    after_titles = [after[slug][0] for slug in common]
    before_descriptions = [before[slug][1] for slug in common]
    after_descriptions = [after[slug][1] for slug in common]
    result = {
        "checked": len(common),
        "changed_titles": sum(before[slug][0] != after[slug][0] for slug in common),
        "changed_descriptions": sum(before[slug][1] != after[slug][1] for slug in common),
        "titles": {
            "before_length": length_stats(before_titles),
            "after_length": length_stats(after_titles),
            "before_unique": len(set(before_titles)),
            "after_unique": len(set(after_titles)),
            "generic_before": sum("학습 길잡이" in value for value in before_titles),
            "generic_after": sum("학습 길잡이" in value for value in after_titles),
        },
        "descriptions": {
            "before_length": length_stats(before_descriptions),
            "after_length": length_stats(after_descriptions),
            "before_unique": len(set(before_descriptions)),
            "after_unique": len(set(after_descriptions)),
            "truncated_before": sum("…" in value for value in before_descriptions),
            "truncated_after": sum("…" in value for value in after_descriptions),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if len(common) == 69 else 1


if __name__ == "__main__":
    raise SystemExit(main())
