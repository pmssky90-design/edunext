from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
BASELINE_CHARACTERS = {
    "부산좌동과외": 3556,
    "부산중동과외": 3487,
    "구미남통동과외": 3518,
    "부산덕천동과외": 3585,
    "부산전포동과외": 3481,
    "부산구포동과외": 3595,
    "부산명륜동과외": 3555,
    "부산사하구과외": 3439,
    "양산중부동과외": 3565,
    "부산망미동과외": 3502,
    "부산오륜동과외": 3522,
}
REQUIRED_LINKS = {
    "부산좌동과외": {"/부산부흥고과외/", "/부산신도고과외/", "/부산양운고과외/"},
    "부산중동과외": {"/#high-schools", "/부산중동영어과외/", "/부산중동수학과외/"},
    "구미남통동과외": {"/구미경북외고과외/", "/구미남통동영어과외/", "/구미남통동수학과외/"},
    "부산덕천동과외": {"/부산낙동고과외/", "/부산덕천동영어과외/", "/부산덕천동수학과외/"},
    "부산전포동과외": {"/부산동고과외/", "/부산동성고과외/", "/부산동의고과외/"},
    "부산구포동과외": {"/부산경혜여고과외/", "/부산백양고과외/", "/부산삼정고과외/", "/부산성도고과외/"},
    "부산명륜동과외": {"/부산중앙여고과외/", "/부산명륜동영어과외/", "/부산명륜동수학과외/"},
    "부산사하구과외": {"/부산신평동과외/", "/부산하단동과외/", "/부산사하구영어과외/", "/부산사하구수학과외/"},
    "양산중부동과외": {"/#high-schools", "/양산중부동영어과외/", "/양산중부동수학과외/"},
    "부산망미동과외": {"/부산남일고과외/", "/부산망미동영어과외/", "/부산망미동수학과외/"},
    "부산오륜동과외": {"/#high-schools", "/부산금정구과외/", "/부산오륜동영어과외/", "/부산오륜동수학과외/"},
}
FORBIDDEN_TEXT = ("학학부모", "학보호자", "단원와", "과제을", "실제 학생 사례입니다")


def article_body(html: str) -> str:
    match = re.search(r'<article\s+class="content-body">(.*?)</article>', html, flags=re.I | re.S)
    return match.group(1) if match else ""


def compact_text(fragment: str) -> str:
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def readable_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def shingles(text: str, size: int = 5) -> set[str]:
    return {text[index : index + size] for index in range(max(0, len(text) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def main() -> int:
    all_bodies: dict[str, str] = {}
    for path in OUTPUT.glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        if "page-type-region" not in html or path.parent.name in {"경남과외", "경북과외"}:
            continue
        all_bodies[path.parent.name] = article_body(html)

    grams = {slug: shingles(compact_text(body)) for slug, body in all_bodies.items()}
    metrics: list[dict[str, object]] = []
    problems: list[dict[str, object]] = []
    first_headings: set[str] = set()
    scenario_headings: set[str] = set()

    for slug in sorted(BASELINE_CHARACTERS):
        path = OUTPUT / slug / "index.html"
        html = path.read_text(encoding="utf-8") if path.exists() else ""
        body = article_body(html)
        compact = compact_text(body)
        readable = readable_text(body)
        h2_labels = [readable_text(item) for item in re.findall(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)]
        first_heading = h2_labels[0] if h2_labels else ""
        scenarios = [label for label in h2_labels if label.startswith("가상 학습 시나리오:")]
        first_headings.add(first_heading)
        scenario_headings.update(scenarios)
        local: list[str] = []

        nearest_slug = ""
        nearest_score = 0.0
        for other, other_grams in grams.items():
            if other == slug:
                continue
            score = jaccard(grams.get(slug, set()), other_grams) * 100
            if score > nearest_score:
                nearest_slug, nearest_score = other, score

        if body.count('class="secondary-region-content') != 1:
            local.append("secondary content marker must appear once")
        if body.count('data-content-version="region-secondary-v1"') != 1:
            local.append("content version marker must appear once")
        if body.count('class="scenario-notice"') != 1 or len(scenarios) != 1:
            local.append("one labeled scenario is required")
        if body.count('class="contextual-links"') != 1 or body.count('class="regional-faq"') != 1:
            local.append("contextual links and FAQ must each appear once")
        if len(compact) < BASELINE_CHARACTERS[slug]:
            local.append(f"content shorter than baseline: {len(compact)} < {BASELINE_CHARACTERS[slug]}")
        if nearest_score >= 30:
            local.append(f"nearest-page similarity is high: {nearest_score:.2f}%")
        if body.count("<h3") != 5:
            local.append(f"FAQ H3 count is not 5: {body.count('<h3')}")
        missing_links = sorted(href for href in REQUIRED_LINKS[slug] if f'href="{href}"' not in body)
        if missing_links:
            local.append(f"required links missing: {', '.join(missing_links)}")
        if f'href="/{slug}/"' in body:
            local.append("self-link found")
        for phrase in FORBIDDEN_TEXT:
            if phrase in readable:
                local.append(f"forbidden wording: {phrase}")

        meta_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, flags=re.I)
        hero_match = re.search(r'<section\s+class="page-hero"[^>]*>.*?<h1\b[^>]*>.*?</h1>\s*<p>(.*?)</p>', html, flags=re.I | re.S)
        meta = unescape(meta_match.group(1)) if meta_match else ""
        hero = readable_text(hero_match.group(1)) if hero_match else ""
        if not meta or meta != hero:
            local.append("meta description and hero description do not match")

        metrics.append(
            {
                "slug": slug,
                "before_characters": BASELINE_CHARACTERS[slug],
                "after_characters": len(compact),
                "nearest_slug": nearest_slug,
                "similarity_percent": round(nearest_score, 2),
                "h2": len(h2_labels),
            }
        )
        if local:
            problems.append({"slug": slug, "problems": local})

    if len(first_headings) != len(BASELINE_CHARACTERS):
        problems.append({"problem": "first headings are not unique across all secondary pages"})
    if len(scenario_headings) != len(BASELINE_CHARACTERS):
        problems.append({"problem": "scenario headings are not unique across all secondary pages"})

    print(json.dumps({"checked": len(metrics), "metrics": metrics, "problems": problems}, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
