from __future__ import annotations

from collections import defaultdict
from html import unescape
from itertools import combinations
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sitegen.render import faq_schema
from sitegen.local_middle_english import (
    LOCAL_MIDDLE_ENGLISH_FOCUS,
    build_local_middle_english_meta,
)


OUTPUT = ROOT / os.environ.get("EDUNEXT_AUDIT_OUTPUT", "output")
CONTEXT_PATH = ROOT / "data" / "local_middle_school_context.json"
MARKER = "local-middle-english-content"
TARGET = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등영어과외$")


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def grams(value: str, size: int = 5) -> set[str]:
    value = compact(value)
    return {value[index : index + size] for index in range(max(0, len(value) - size + 1))}


def similarity(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def main() -> int:
    context_data = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    context_pages = context_data.get("pages", {})
    pages: dict[str, dict[str, object]] = {}
    paragraph_owners: defaultdict[str, list[str]] = defaultdict(list)
    context_errors: list[dict[str, object]] = []
    pages_with_school_rows = 0
    school_rows = 0
    official_links = 0
    faq_schema_mismatches: list[str] = []
    search_intent_errors: list[dict[str, object]] = []
    search_intent_pages = 0
    student_case_errors: list[dict[str, object]] = []
    student_case_pages = 0
    heading_faq_errors: list[dict[str, object]] = []
    main_heading_values: list[str] = []
    internal_link_errors: list[dict[str, object]] = []
    internal_link_counts: list[int] = []
    metadata_errors: list[dict[str, object]] = []
    metadata_titles: list[str] = []
    metadata_descriptions: list[str] = []
    for path in sorted(OUTPUT.glob("*/index.html")):
        slug = path.parent.name
        if not TARGET.fullmatch(slug):
            continue
        html = path.read_text(encoding="utf-8")
        expected_title, expected_description = build_local_middle_english_meta(slug)
        metadata_page_errors: list[str] = []
        title_matches = re.findall(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        title_text = plain(title_matches[0]) if title_matches else ""
        if len(title_matches) != 1:
            metadata_page_errors.append(f"expected one title element, found {len(title_matches)}")

        def meta_content(attribute: str, value: str) -> str:
            match = re.search(
                rf'<meta\s+{attribute}="{re.escape(value)}"\s+content="([^"]*)"\s*/?>',
                html,
                flags=re.I,
            )
            return unescape(match.group(1)).strip() if match else ""

        description_text = meta_content("name", "description")
        og_title = meta_content("property", "og:title")
        og_description = meta_content("property", "og:description")
        twitter_title = meta_content("name", "twitter:title")
        twitter_description = meta_content("name", "twitter:description")
        hero_match = re.search(
            r'<section\s+class="page-hero">.*?<h1>.*?</h1>\s*<p>(.*?)</p>',
            html,
            flags=re.I | re.S,
        )
        hero_description = plain(hero_match.group(1)) if hero_match else ""
        metadata_titles.append(title_text)
        metadata_descriptions.append(description_text)
        if title_text != expected_title:
            metadata_page_errors.append("title does not match generated value")
        if description_text != expected_description:
            metadata_page_errors.append("description does not match generated value")
        if og_title != title_text or twitter_title != title_text:
            metadata_page_errors.append("social titles are not synchronized")
        if og_description != description_text or twitter_description != description_text:
            metadata_page_errors.append("social descriptions are not synchronized")
        if hero_description != description_text:
            metadata_page_errors.append("hero summary is not synchronized")
        if not 20 <= len(title_text) <= 45:
            metadata_page_errors.append(f"title length outside quality range: {len(title_text)}")
        if not 80 <= len(description_text) <= 160:
            metadata_page_errors.append(
                f"description length outside quality range: {len(description_text)}"
            )
        if title_text.count(slug) != 1 or description_text.count(slug) != 1:
            metadata_page_errors.append("primary local keyword must appear exactly once")
        if "…" in description_text or "학습 길잡이" in title_text:
            metadata_page_errors.append("truncated or generic metadata text")
        article_match = re.search(r'<article class="content-body">(.*?)</article>', html, flags=re.I | re.S)
        article = article_match.group(1) if article_match else ""
        text = plain(article)
        expected_faq = faq_schema(article)
        heading_page_errors: list[str] = []
        h2_values = [plain(value) for value in re.findall(r"<h2\b[^>]*>(.*?)</h2>", article, flags=re.I | re.S)]
        location = slug.removesuffix("중등영어과외")
        focus = LOCAL_MIDDLE_ENGLISH_FOCUS.get(slug, "")
        if not h2_values:
            heading_page_errors.append("missing h2")
        else:
            main_heading_values.append(h2_values[0])
            subject_present = "중등영어" in h2_values[0] or "중학생 영어" in h2_values[0]
            if location not in h2_values[0] or not subject_present or focus not in h2_values[0]:
                heading_page_errors.append("main heading missing location, subject, or focus")
        faq_entities = expected_faq.get("mainEntity", []) if isinstance(expected_faq, dict) else []
        if len(faq_entities) != 7:
            heading_page_errors.append(f"expected seven FAQ pairs, found {len(faq_entities)}")
        if heading_page_errors:
            heading_faq_errors.append({"slug": slug, "errors": heading_page_errors})
        embedded_faq = None
        embedded_webpage = None
        for encoded in re.findall(r'<script\s+type="application/ld\+json">(.*?)</script>', html, flags=re.I | re.S):
            try:
                schema = json.loads(encoded)
            except json.JSONDecodeError:
                continue
            candidates = schema if isinstance(schema, list) else [schema]
            embedded_faq = next(
                (item for item in candidates if isinstance(item, dict) and item.get("@type") == "FAQPage"),
                embedded_faq,
            )
            embedded_webpage = next(
                (item for item in candidates if isinstance(item, dict) and item.get("@type") == "WebPage"),
                embedded_webpage,
            )
        if not isinstance(embedded_webpage, dict):
            metadata_page_errors.append("missing WebPage structured data")
        elif (
            embedded_webpage.get("name") != title_text
            or embedded_webpage.get("description") != description_text
        ):
            metadata_page_errors.append("WebPage structured data is not synchronized")
        if metadata_page_errors:
            metadata_errors.append({"slug": slug, "errors": metadata_page_errors})
        if embedded_faq != expected_faq:
            faq_schema_mismatches.append(slug)
        context = context_pages.get(slug, {})
        schools = context.get("schools", []) if isinstance(context, dict) else []
        peers = context.get("peer_slugs", []) if isinstance(context, dict) else []
        parent = str(context.get("parent_slug", "")) if isinstance(context, dict) else ""
        town = str(context.get("town", "")) if isinstance(context, dict) else ""
        errors: list[str] = []
        intent_match = re.search(
            r'<section class="middle-english-search-intent"\s+data-intent-kind="[^"]+">(.*?)</section>',
            article,
            flags=re.I | re.S,
        )
        intent_page_errors: list[str] = []
        if not intent_match:
            intent_page_errors.append("missing search-intent section")
        else:
            search_intent_pages += 1
            intent_html = intent_match.group(1)
            if "2주 계획" not in plain(intent_html):
                intent_page_errors.append("missing two-week heading")
            if len(re.findall(r"<tbody>.*?<tr>", intent_html, flags=re.I | re.S)) != 1:
                intent_page_errors.append("missing intent plan table")
            if len(re.findall(r"<tr>", intent_html, flags=re.I)) != 5:
                intent_page_errors.append("intent plan must have four body rows")
            if len(re.findall(r"<li>", intent_html, flags=re.I)) != 4:
                intent_page_errors.append("intent checklist must have four items")
        if intent_page_errors:
            search_intent_errors.append({"slug": slug, "errors": intent_page_errors})
        case_match = re.search(
            r'<section class="middle-english-student-case"\s+data-case-kind="[^"]+">(.*?)</section>',
            article,
            flags=re.I | re.S,
        )
        case_page_errors: list[str] = []
        if not case_match:
            case_page_errors.append("missing student-case section")
        else:
            student_case_pages += 1
            case_html = case_match.group(1)
            case_text = plain(case_html)
            if "가상 학생 관찰 예시" not in case_text:
                case_page_errors.append("missing virtual-case heading")
            if "실제 학생 후기나 성적 향상 사례가 아닙니다" not in case_text:
                case_page_errors.append("missing virtual-case disclosure")
            if len(re.findall(r"<tr>", case_html, flags=re.I)) != 5:
                case_page_errors.append("student-case table must have four body rows")
        if case_page_errors:
            student_case_errors.append({"slug": slug, "errors": case_page_errors})
        if "학교 일정과 생활시간을 학습표로 바꾸는 방법" not in text:
            errors.append("missing local schedule section")
        if schools:
            pages_with_school_rows += 1
            school_rows += len(schools)
            for school in schools:
                name = str(school.get("school_name", ""))
                if name and name not in text:
                    errors.append(f"missing school name: {name}")
            for school in schools[:4]:
                homepage = str(school.get("homepage", ""))
                if homepage:
                    official_links += 1
                    if f'href="{homepage}"' not in article:
                        errors.append(f"missing official homepage: {homepage}")
        elif town and f"주소가 {town}로 정확히 일치하는 중학교 행을 확인하지 못했습니다" not in text:
            errors.append("missing no-exact-school disclosure")
        for peer in peers:
            if f'href="/{peer}/"' not in article:
                errors.append(f"missing comparison link: {peer}")
        link_page_errors: list[str] = []
        internal_hrefs = re.findall(r'<a\b[^>]*href="(/[^"#?]+)"', article, flags=re.I)
        internal_link_counts.append(len(internal_hrefs))
        expected_links = [
            ("parent", parent),
            ("subject", f"{location}영어과외"),
            ("grade", f"{location}중등과외"),
            *(("peer", str(peer)) for peer in peers),
        ]
        context_links = re.findall(
            r'<a\s+class="context-link"\s+data-link-role="([^"]+)"\s+href="/([^"/]+)/">(.*?)</a>',
            article,
            flags=re.I | re.S,
        )
        role_targets = [(role, target) for role, target, _ in context_links]
        for role, target in expected_links:
            if not target:
                link_page_errors.append(f"empty expected {role} link")
                continue
            if role_targets.count((role, target)) != 1:
                link_page_errors.append(f"expected one {role} link to {target}")
        targets = [target for _, target, _ in context_links]
        if len(targets) != len(set(targets)):
            link_page_errors.append("duplicate contextual target")
        if slug in targets or f"/{slug}/" in internal_hrefs:
            link_page_errors.append("self link")
        for _, target, label_html in context_links:
            label = plain(label_html)
            if label == target:
                link_page_errors.append(f"keyword-only anchor: {target}")
            if not (OUTPUT / target / "index.html").exists():
                link_page_errors.append(f"missing target page: {target}")
        if len(context_links) != 3 + len(peers):
            link_page_errors.append(
                f"expected {3 + len(peers)} contextual links, found {len(context_links)}"
            )
        if link_page_errors:
            internal_link_errors.append({"slug": slug, "errors": link_page_errors})
        for awkward in ("감소으로", "적용으로으로", "이동으로으로"):
            if awkward in text:
                errors.append(f"awkward expression: {awkward}")
        if errors:
            context_errors.append({"slug": slug, "errors": errors})
        for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", article, flags=re.I | re.S):
            paragraph = plain(paragraph)
            if len(paragraph) >= 80:
                paragraph_owners[paragraph].append(slug)
        pages[slug] = {
            "characters": len(compact(text)),
            "marked": MARKER in article,
            "grams": grams(text),
        }

    pairs = sorted(
        (
            round(similarity(pages[left]["grams"], pages[right]["grams"]) * 100, 2),
            left,
            right,
        )
        for left, right in combinations(sorted(pages), 2)
    )
    pairs.reverse()
    repeated = [
        {"pages": len(owners), "characters": len(paragraph), "sample": paragraph[:100], "slugs": owners[:6]}
        for paragraph, owners in paragraph_owners.items()
        if len(owners) >= 3
    ]
    lengths = [int(item["characters"]) for item in pages.values()]
    result = {
        "checked": len(pages),
        "marked": sum(bool(item["marked"]) for item in pages.values()),
        "characters": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "average": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        },
        "maximum_similarity_percent": pairs[0][0] if pairs else 0,
        "highest_similarity_pair": list(pairs[0][1:]) if pairs else [],
        "top_similarity_pairs": [
            {"similarity_percent": score, "left": left, "right": right}
            for score, left, right in pairs[:10]
        ],
        "pairs_at_least_70_percent": sum(score >= 70 for score, _, _ in pairs),
        "repeated_paragraphs_on_3_plus_pages": sorted(repeated, key=lambda item: item["pages"], reverse=True),
        "local_context": {
            "mapped_pages": len(context_pages),
            "pages_with_exact_town_middle_schools": pages_with_school_rows,
            "exact_town_middle_school_rows": school_rows,
            "official_homepage_links_checked": official_links,
            "errors": context_errors,
        },
        "search_intent": {
            "marked_pages": search_intent_pages,
            "errors": search_intent_errors,
        },
        "student_case": {
            "marked_pages": student_case_pages,
            "errors": student_case_errors,
        },
        "heading_and_faq": {
            "unique_main_headings": len(set(main_heading_values)),
            "errors": heading_faq_errors,
        },
        "internal_links": {
            "minimum_per_page": min(internal_link_counts) if internal_link_counts else 0,
            "maximum_per_page": max(internal_link_counts) if internal_link_counts else 0,
            "average_per_page": round(sum(internal_link_counts) / len(internal_link_counts), 1)
            if internal_link_counts
            else 0,
            "errors": internal_link_errors,
        },
        "metadata": {
            "unique_titles": len(set(metadata_titles)),
            "unique_descriptions": len(set(metadata_descriptions)),
            "title_length": {
                "minimum": min(map(len, metadata_titles)) if metadata_titles else 0,
                "maximum": max(map(len, metadata_titles)) if metadata_titles else 0,
                "average": round(sum(map(len, metadata_titles)) / len(metadata_titles), 1)
                if metadata_titles
                else 0,
            },
            "description_length": {
                "minimum": min(map(len, metadata_descriptions)) if metadata_descriptions else 0,
                "maximum": max(map(len, metadata_descriptions)) if metadata_descriptions else 0,
                "average": round(
                    sum(map(len, metadata_descriptions)) / len(metadata_descriptions), 1
                )
                if metadata_descriptions
                else 0,
            },
            "errors": metadata_errors,
        },
        "faq_schema_mismatches": faq_schema_mismatches,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    failed = (
        result["checked"] != 69
        or result["marked"] != 69
        or result["maximum_similarity_percent"] >= 70
        or bool(result["repeated_paragraphs_on_3_plus_pages"])
        or len(context_pages) != 69
        or bool(context_errors)
        or search_intent_pages != 69
        or bool(search_intent_errors)
        or student_case_pages != 69
        or bool(student_case_errors)
        or len(set(main_heading_values)) != 69
        or bool(heading_faq_errors)
        or bool(internal_link_errors)
        or len(set(metadata_titles)) != 69
        or len(set(metadata_descriptions)) != 69
        or bool(metadata_errors)
        or bool(faq_schema_mismatches)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
