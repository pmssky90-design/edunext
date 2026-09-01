from __future__ import annotations

from collections import Counter
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
sys.path.insert(0, str(ROOT))

from sitegen.data_loader import SOURCE_TEXT_REPLACEMENTS, normalize_source_text


SUBJECT_PAGE_MARKER = '<main id="main" class="page-main page-type-subject">'
STUDENT_DUPLICATION = re.compile(r"(초등학생|중학생|고등학생)에게는\s+\1은")


def is_region_english_page(path: Path, html: str) -> bool:
    slug = path.parent.name
    return slug != "영어과외" and slug.endswith("영어과외") and SUBJECT_PAGE_MARKER in html


def main() -> int:
    checked = 0
    updated_pages: list[str] = []
    replacements: Counter[str] = Counter()

    for path in sorted(OUTPUT.glob("*/index.html")):
        html = path.read_text(encoding="utf-8")
        if not is_region_english_page(path, html):
            continue
        checked += 1

        for malformed in SOURCE_TEXT_REPLACEMENTS:
            replacements[malformed] += html.count(malformed)
        replacements["학생 역할 중복"] += len(STUDENT_DUPLICATION.findall(html))

        refreshed = normalize_source_text(html)
        if refreshed == html:
            continue
        path.write_text(refreshed, encoding="utf-8", newline="\n")
        updated_pages.append(path.parent.name)

    print(f"checked regional English pages: {checked}")
    print(f"refreshed regional English pages: {len(updated_pages)}")
    for malformed, count in replacements.items():
        if count:
            print(f"- {malformed}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
