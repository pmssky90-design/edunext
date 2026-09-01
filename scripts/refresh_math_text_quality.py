from __future__ import annotations

import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
sys.path.insert(0, str(ROOT))

from sitegen.data_loader import normalize_source_text
from sitegen.render import enhance_content_body, structure_priority_math_body


SUBJECT_PAGE_MARKER = '<main id="main" class="page-main page-type-subject">'
EXCLUDED_HUBS = {"수학과외", "경남수학과외", "경북수학과외"}
GRADE_PATTERN = re.compile(r"(초등|중등|고등)수학과외$")
OLD_MATH_TITLE_SUFFIX = "기초부터심화까지 내신 수능 전문 과외"
NEW_MATH_TITLE_SUFFIX = "기초부터 심화까지 · 내신·수능 학습 가이드"


def is_priority_math_page(path: Path, html: str) -> bool:
    slug = path.parent.name
    return (
        slug.endswith("수학과외")
        and slug not in EXCLUDED_HUBS
        and not GRADE_PATTERN.search(slug)
        and SUBJECT_PAGE_MARKER in html
    )


def refresh_page(html: str) -> str:
    refreshed = normalize_source_text(html).replace(OLD_MATH_TITLE_SUFFIX, NEW_MATH_TITLE_SUFFIX)
    article_match = re.search(
        r'(<article class="content-body">)(.*?)(</article>)',
        refreshed,
        flags=re.I | re.S,
    )
    if not article_match:
        return refreshed

    structured = structure_priority_math_body(article_match.group(2))
    enhanced, toc = enhance_content_body(structured)
    refreshed = (
        refreshed[: article_match.start()]
        + article_match.group(1)
        + enhanced
        + article_match.group(3)
        + refreshed[article_match.end() :]
    )
    refreshed = re.sub(
        r'<nav class="page-toc".*?</nav>',
        toc,
        refreshed,
        count=1,
        flags=re.I | re.S,
    )
    return refreshed


def main() -> int:
    checked = 0
    updated_pages: list[str] = []

    for path in sorted(OUTPUT.glob("*/index.html")):
        html = path.read_text(encoding="utf-8")
        if not is_priority_math_page(path, html):
            continue
        checked += 1
        refreshed = refresh_page(html)
        if refreshed == html:
            continue
        path.write_text(refreshed, encoding="utf-8", newline="\n")
        updated_pages.append(path.parent.name)

    print(f"checked priority regional math pages: {checked}")
    print(f"refreshed priority regional math pages: {len(updated_pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
