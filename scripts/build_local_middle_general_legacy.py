from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup


SLUG_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등과외$")
REPLACEMENTS = {
    "준비을": "준비를",
    "대화과": "대화와",
    "과정입니다 이": "과정입니다. 이",
    "하기을": "하기를",
    "바꾸기을": "바꾸기를",
    "정하기을": "정하기를",
    "만들기을": "만들기를",
    "연결하기을": "연결하기를",
}


def _clean(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    for before, after in REPLACEMENTS.items():
        value = value.replace(before, after)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    pages: dict[str, list[str]] = {}
    counts: Counter[str] = Counter()
    for path in sorted(args.source.glob("*/index.html")):
        slug = path.parent.name
        if not SLUG_PATTERN.fullmatch(slug):
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        article = soup.select_one("article.content-body")
        if not article:
            continue
        paragraphs = [_clean(node.get_text(" ", strip=True)) for node in article.select("p")]
        paragraphs = [value for value in paragraphs if len(value) >= 60]
        pages[slug] = paragraphs
        counts.update(set(paragraphs))
    selected: dict[str, list[str]] = {}
    for slug, paragraphs in pages.items():
        location = slug.removesuffix("중등과외")
        selected[slug] = [
            value + (f" 이 장면은 {location} 중등 학습 자료를 확인할 때 참고합니다." if counts[value] == 3 else "")
            for value in paragraphs
            if counts[value] <= 3
        ]
    payload = {
        "source": "pre-middle-general baseline",
        "selection": "paragraphs occurring on no more than three of 69 pages; three-occurrence paragraphs receive a local context note",
        "pages": selected,
    }
    args.destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"source pages: {len(pages)}")
    print(f"selected paragraphs: {sum(len(values) for values in selected.values())}")
    print(f"destination: {args.destination}")
    return 0 if len(pages) == 69 and all(selected.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
