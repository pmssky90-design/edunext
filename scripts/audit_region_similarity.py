from __future__ import annotations

import json
import re
from html import unescape
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SPECIAL_HUBS = {"경남과외", "경북과외"}
PRIORITY_SLUGS = {
    "구미옥계동과외",
    "부산하단동과외",
    "부산우동과외",
    "부산화명동과외",
}
SECONDARY_SLUGS = {
    "부산좌동과외",
    "부산중동과외",
    "구미남통동과외",
    "부산덕천동과외",
    "부산전포동과외",
    "부산구포동과외",
    "부산명륜동과외",
    "부산사하구과외",
    "양산중부동과외",
    "부산망미동과외",
    "부산오륜동과외",
}


def visible_article(html: str) -> str:
    match = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    if not match:
        return ""
    without_markup = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", match.group(1), flags=re.I | re.S)
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", " ", without_markup))).strip()


def shingles(text: str, size: int = 5) -> set[str]:
    return {text[index : index + size] for index in range(max(0, len(text) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def main() -> int:
    bodies: dict[str, str] = {}
    for path in OUTPUT.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        slug = path.parent.name
        if "page-type-region" not in html or slug in SPECIAL_HUBS:
            continue
        bodies[slug] = visible_article(html)

    grams = {slug: shingles(body) for slug, body in bodies.items()}
    pairs = sorted(
        (
            {
                "left": left,
                "right": right,
                "similarity_percent": round(jaccard(grams[left], grams[right]) * 100, 2),
            }
            for left, right in combinations(sorted(bodies), 2)
        ),
        key=lambda item: item["similarity_percent"],
        reverse=True,
    )

    def neighbor_rows(slugs: set[str]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for slug in sorted(slugs):
            neighbors = [item for item in pairs if slug in {item["left"], item["right"]}]
            nearest = neighbors[0] if neighbors else None
            rows.append(
                {
                    "slug": slug,
                    "characters": len(bodies.get(slug, "")),
                    "nearest_slug": (
                        nearest["right"]
                        if nearest and nearest["left"] == slug
                        else nearest["left"] if nearest else None
                    ),
                    "similarity_percent": nearest["similarity_percent"] if nearest else None,
                }
            )
        return rows

    priority = neighbor_rows(PRIORITY_SLUGS)
    secondary = neighbor_rows(SECONDARY_SLUGS)

    print(
        json.dumps(
            {
                "checked": len(bodies),
                "shingle_size": 5,
                "priority": priority,
                "secondary": secondary,
                "top_pairs": pairs[:15],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if (PRIORITY_SLUGS | SECONDARY_SLUGS) - bodies.keys() else 0


if __name__ == "__main__":
    raise SystemExit(main())
