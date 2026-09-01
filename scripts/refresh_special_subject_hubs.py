from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sitegen.content_builder import SPECIAL_SUBJECT_HUB_META_DESCRIPTIONS, special_subject_hub_content
from sitegen.render import enhance_content_body, faq_schema
from sitegen.title_rules import build_page_title
from sitegen.utils import escape


OUTPUT = ROOT / "output"
SLUGS = ("영어과외", "초등영어과외", "중등영어과외", "고등영어과외", "경남영어과외", "경북영어과외")


def replace_once(source: str, pattern: str, replacement: str, *, label: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError(f"{label} replacement failed")
    return updated


def update_meta(html: str, slug: str, title: str, description: str) -> str:
    html = replace_once(html, r"<title>.*?</title>", f"<title>{escape(title)}</title>", label=f"{slug} title")
    for name in ("description",):
        html = replace_once(
            html,
            rf'(<meta\s+name="{re.escape(name)}"\s+content=")[^"]*(">)',
            rf"\g<1>{escape(description)}\g<2>",
            label=f"{slug} {name}",
        )
    for prop, value in (("og:title", title), ("og:description", description)):
        html = replace_once(
            html,
            rf'(<meta\s+property="{re.escape(prop)}"\s+content=")[^"]*(">)',
            rf"\g<1>{escape(value)}\g<2>",
            label=f"{slug} {prop}",
        )
    for name, value in (("twitter:title", title), ("twitter:description", description)):
        html = replace_once(
            html,
            rf'(<meta\s+name="{re.escape(name)}"\s+content=")[^"]*(">)',
            rf"\g<1>{escape(value)}\g<2>",
            label=f"{slug} {name}",
        )
    return html


def update_schema(html: str, title: str, description: str, body: str) -> str:
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.I | re.S)
    if not match:
        raise RuntimeError("JSON-LD script missing")
    parsed = json.loads(match.group(1))
    items = parsed if isinstance(parsed, list) else [parsed]
    items = [item for item in items if item.get("@type") != "FAQPage"]
    for item in items:
        if item.get("@type") == "WebPage":
            item["name"] = title
            item["description"] = description
    faq = faq_schema(body)
    if faq:
        items.append(faq)
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    return f"{html[:match.start()]}<script type=\"application/ld+json\">{payload}</script>{html[match.end():]}"


def related_navigation(slug: str) -> str:
    if slug in {"초등영어과외", "중등영어과외", "고등영어과외"}:
        grade = slug.removesuffix("영어과외")
        adjacent_by_grade = {
            "초등": ["중등영어과외"],
            "중등": ["초등영어과외", "고등영어과외"],
            "고등": ["중등영어과외"],
        }
        sections = [
            (
                f"지역별 {grade}영어과외",
                [(f"/{region}{grade}영어과외/", f"{region}{grade}영어과외") for region in ("부산", "경남", "경북", "양산", "구미")],
            ),
            (
                "과목·학년 허브",
                [("/영어과외/", "영어과외"), (f"/{grade}과외/", f"{grade}과외"), (f"/{grade}수학과외/", f"{grade}수학과외")],
            ),
            (
                "이어지는 영어 학습 단계",
                [(f"/{name}/", name) for name in adjacent_by_grade[grade]],
            ),
        ]
    elif slug == "영어과외":
        sections = [
            (
                "지역별 영어과외",
                [
                    ("/부산영어과외/", "부산영어과외"),
                    ("/경남영어과외/", "경남영어과외"),
                    ("/경북영어과외/", "경북영어과외"),
                    ("/양산영어과외/", "양산영어과외"),
                    ("/구미영어과외/", "구미영어과외"),
                ],
            ),
            (
                "학년별 영어과외",
                [(f"/{grade}영어과외/", f"{grade}영어과외") for grade in ("초등", "중등", "고등")],
            ),
            (
                "지역 종합과외",
                [(f"/{name}과외/", f"{name}과외") for name in ("부산", "양산", "구미", "경남", "경북")],
            ),
            ("다른 학습 허브", [("/전국과외/", "전국과외"), ("/수학과외/", "수학과외")]),
        ]
    elif slug == "경남영어과외":
        province, city = "경남", "양산"
        local_names = ["양산교동", "양산남부동", "양산동면", "양산물금읍", "양산중부동"]
    elif slug == "경북영어과외":
        province, city = "경북", "구미"
        local_names = ["구미고아읍", "구미남통동", "구미사곡동", "구미산동읍", "구미송정동", "구미옥계동", "구미원평동", "구미형곡동"]
    else:
        raise RuntimeError(f"missing related navigation configuration: {slug}")
    if slug not in {"영어과외", "초등영어과외", "중등영어과외", "고등영어과외"}:
        sections = [
            (
                f"{province}권 영어과외 둘러보기",
                [(f"/{province}과외/", f"{province}과외"), ("/영어과외/", "영어과외"), (f"/{city}영어과외/", f"{city}영어과외")],
            ),
            (
                f"{city} 생활권별 영어과외",
                [(f"/{name}영어과외/", f"{name}영어과외") for name in local_names],
            ),
            ("과목별 과외", [(f"/{province}수학과외/", f"{province}수학과외")]),
            (
                "학년별 과외",
                [(f"/{province}{grade}과외/", f"{province}{grade}과외") for grade in ("초등", "중등", "고등")],
            ),
            (
                "영어 과목·학년별 과외",
                [(f"/{province}{grade}영어과외/", f"{province}{grade}영어과외") for grade in ("초등", "중등", "고등")],
            ),
            (
                "수학 과목·학년별 과외",
                [(f"/{province}{grade}수학과외/", f"{province}{grade}수학과외") for grade in ("초등", "중등", "고등")],
            ),
        ]
    chunks = ['<nav class="related-navigation" aria-label="관련 페이지">']
    for heading, links in sections:
        cards = "".join(
            f'<li><a class="related-link-card" href="{escape(href)}"><span>{escape(label)}</span></a></li>'
            for href, label in links
        )
        chunks.append(f'<section class="related-section"><h2>{escape(heading)}</h2><ul class="related-card-grid">{cards}</ul></section>')
    chunks.append("</nav>")
    return "".join(chunks)


def refresh(slug: str) -> bool:
    path = OUTPUT / slug / "index.html"
    html = path.read_text(encoding="utf-8")
    source_body = special_subject_hub_content(slug)
    if source_body is None:
        raise RuntimeError(f"missing special subject content: {slug}")
    body, toc = enhance_content_body(source_body)
    title = build_page_title(slug, None)[0]
    description = SPECIAL_SUBJECT_HUB_META_DESCRIPTIONS[slug]

    updated = update_meta(html, slug, title, description)
    updated = update_schema(updated, title, description, body)
    updated = replace_once(
        updated,
        r'(<section class="page-hero">.*?<h1>.*?</h1>\s*)<p>.*?</p>',
        rf"\g<1><p>{escape(description)}</p>",
        label=f"{slug} hero description",
    )
    updated = replace_once(
        updated,
        r'\s*<nav class="page-toc".*?</nav>\s*',
        f"\n    {toc}\n    ",
        label=f"{slug} table of contents",
    )
    updated = replace_once(
        updated,
        r'(<article class="content-body">).*?(</article>)',
        rf"\g<1>{body}\g<2>",
        label=f"{slug} article",
    )
    updated = replace_once(
        updated,
        r'<nav class="related-navigation"[^>]*>.*?</nav>',
        related_navigation(slug),
        label=f"{slug} related navigation",
    )
    if updated == html:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    changed = sum(refresh(slug) for slug in SLUGS)
    print(f"refreshed special subject hubs: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
