from __future__ import annotations

import json
import re
from html import unescape
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
SLUGS = ("전국과외", "경남과외", "경북과외")


def visible(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def grams(value: str, size: int = 5) -> set[str]:
    compact = re.sub(r"\s+", "", value)
    return {compact[index : index + size] for index in range(max(0, len(compact) - size + 1))}


def main() -> int:
    pages = {}
    problems = []
    for slug in SLUGS:
        html = (OUTPUT / slug / "index.html").read_text(encoding="utf-8")
        article_match = re.search(r'(?s)<article class="content-body">(.*?)</article>', html)
        if not article_match:
            problems.append(f"missing article: {slug}")
            continue
        article = article_match.group(1)
        text = visible(article)
        json_items = []
        for raw in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', html):
            parsed = json.loads(raw)
            json_items.extend(parsed if isinstance(parsed, list) else [parsed])
        faq = next((item for item in json_items if item.get("@type") == "FAQPage"), None)
        toc_targets = re.findall(r'<nav class="page-toc".*?</nav>', html, flags=re.S)
        missing_targets = []
        if toc_targets:
            for target in re.findall(r'href="#([^"]+)"', toc_targets[0]):
                if f'id="{target}"' not in html:
                    missing_targets.append(target)
        pages[slug] = {
            "length": len(text),
            "h2": len(re.findall(r"<h2\b", article)),
            "h3": len(re.findall(r"<h3\b", article)),
            "faq_schema": len(faq.get("mainEntity", [])) if faq else 0,
            "missing_toc_targets": missing_targets,
            "grams": grams(text),
        }
        if len(text) < 2000 or pages[slug]["h3"] < 4 or pages[slug]["faq_schema"] != 4 or missing_targets:
            problems.append(f"quality check failed: {slug}")

    similarities = {}
    for left, right in combinations(SLUGS, 2):
        union = pages[left]["grams"] | pages[right]["grams"]
        score = len(pages[left]["grams"] & pages[right]["grams"]) / len(union) if union else 0
        similarities[f"{left} vs {right}"] = round(score, 4)
        if score >= 0.5:
            problems.append(f"similarity too high: {left} vs {right}")
    summary = {
        "pages": {slug: {key: value for key, value in data.items() if key != "grams"} for slug, data in pages.items()},
        "similarities": similarities,
        "problems": problems,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
