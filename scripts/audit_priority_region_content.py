from __future__ import annotations

import json
import re
from html import unescape
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
PRIORITY_SLUGS = {
    "구미옥계동과외",
    "부산하단동과외",
    "부산우동과외",
    "부산화명동과외",
}
REQUIRED_REFERENCES = {
    "구미옥계동과외": "https://www.gumi.go.kr/yangpo/",
    "부산하단동과외": "https://www.saha.go.kr/hadan2/",
    "부산우동과외": "https://www.haeundae.go.kr/",
    "부산화명동과외": "/부산화명고과외/",
}
FORBIDDEN_TEXT = ("학학", "학보호자", "단원와", "과제을", "실제 학생 사례입니다")


def article_body(html: str) -> str:
    match = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    return match.group(1) if match else ""


def visible_text(fragment: str) -> str:
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def readable_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def shingles(text: str, size: int = 5) -> set[str]:
    return {text[index : index + size] for index in range(max(0, len(text) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def main() -> int:
    bodies: dict[str, str] = {}
    problems: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    first_headings: set[str] = set()

    for slug in sorted(PRIORITY_SLUGS):
        path = OUTPUT / slug / "index.html"
        if not path.exists():
            problems.append({"slug": slug, "problem": "missing page"})
            continue
        html = path.read_text(encoding="utf-8")
        body = article_body(html)
        bodies[slug] = body
        text = visible_text(body)
        readable = readable_text(body)
        h2_labels = [visible_text(item) for item in re.findall(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)]
        first_heading = h2_labels[0] if h2_labels else ""
        first_headings.add(first_heading)
        local_problems: list[str] = []

        if body.count('class="priority-region-content') != 1:
            local_problems.append("priority content marker must appear once")
        if body.count('data-content-version="region-individual-v1"') != 1:
            local_problems.append("content version marker must appear once")
        if body.count('class="scenario-notice"') != 1:
            local_problems.append("scenario notice must appear once")
        if len(re.findall(r"<h2\b[^>]*>가상 학습 시나리오:", body, flags=re.I)) != 1:
            local_problems.append("scenario heading must appear once")
        if body.count('class="contextual-links"') != 1:
            local_problems.append("contextual links must appear once")
        if body.count('class="regional-faq"') != 1:
            local_problems.append("regional FAQ must appear once")
        if len(text) < 3500:
            local_problems.append(f"visible text is short: {len(text)}")
        if len(h2_labels) < 10:
            local_problems.append(f"not enough H2 sections: {len(h2_labels)}")
        if body.count("<h3") != 5:
            local_problems.append(f"FAQ H3 count is not 5: {body.count('<h3')}")
        if REQUIRED_REFERENCES[slug] not in body:
            local_problems.append("required official or school reference is missing")
        for phrase in FORBIDDEN_TEXT:
            if phrase in readable:
                local_problems.append(f"forbidden wording: {phrase}")
        if f'href="/{slug}/"' in body:
            local_problems.append("self-link found")

        metrics.append(
            {
                "slug": slug,
                "characters": len(text),
                "h2": len(h2_labels),
                "h3": body.count("<h3"),
                "first_heading": first_heading,
            }
        )
        if local_problems:
            problems.append({"slug": slug, "problems": local_problems})

    if len(first_headings) != len(bodies):
        problems.append({"problem": "priority pages do not have unique first headings"})

    similarities: list[dict[str, object]] = []
    for left, right in combinations(sorted(bodies), 2):
        score = round(jaccard(shingles(visible_text(bodies[left])), shingles(visible_text(bodies[right]))) * 100, 2)
        similarities.append({"left": left, "right": right, "similarity_percent": score})
        if score >= 25:
            problems.append({"left": left, "right": right, "problem": f"similarity is high: {score}%"})

    print(
        json.dumps(
            {"checked": len(bodies), "metrics": metrics, "pair_similarities": similarities, "problems": problems},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
