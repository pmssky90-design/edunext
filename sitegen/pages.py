from __future__ import annotations

from collections import Counter
import os
import re

from config import CATEGORIES, GRADE_CATEGORIES, SUBJECT_CATEGORIES, SUBJECT_GRADE_CATEGORIES
from sitegen.content_builder import (
    SPECIAL_SUBJECT_HUB_META_DESCRIPTIONS,
    fallback_content,
    school_intro,
    special_subject_hub_content,
)
from sitegen.models import Page, Region
from sitegen.middle_school_math import (
    build_middle_school_math_body,
    build_middle_school_math_meta,
    is_middle_school_math_slug,
    middle_school_math_contexts,
)
from sitegen.middle_school_english import (
    build_middle_school_english_body,
    build_middle_school_english_meta,
    is_middle_school_english_slug,
    middle_school_english_contexts,
)
from sitegen.render import individualize_priority_region_body, individualize_secondary_region_body
from sitegen.title_rules import HOME_SEO_TITLE, build_page_title
from sitegen.utils import excerpt, page_slug, region_meta_description, strip_tags


def normalize_source_body(body: str) -> str:
    """Repair a narrow legacy timing phrase before it reaches generated pages."""
    return body.replace(
        "학습 방식은 해설을 덮고 세 줄 요약을 쓴 뒤 24시간 후 다시 풀었다로 조정했다.",
        "학습 방식은 해설을 덮고 세 줄 요약을 쓴 뒤, 간격을 두고 다시 푸는 방식으로 조정했다.",
    )


REGIONAL_AUDIT_NOTES = {
    "부산명륜동과외": (
        "부산명륜동과외 계획을 실제 학생에게 적용할 때는 지역명만으로 학교 진도나 이동 시간을 추정하지 않습니다. 학생이 받은 교과서·학습지·평가 안내와 "
        "재학 학교의 최신 공지를 먼저 대조하고, 영어는 근거 문장과 수정 표현을, 수학은 조건 표시와 첫 식·검산을 서로 다른 기록으로 남깁니다. 수업 직후의 "
        "정답과 간격을 둔 뒤 혼자 다시 시작한 결과도 분리해야 설명을 기억한 상태와 실제 독립 수행을 구분할 수 있습니다. 과외 방식을 비교할 때는 교재 이름이나 "
        "학습량보다 도움 전에 학생이 무엇을 시작하는지, 막힌 위치를 어떻게 기록하는지, 계획이 맞지 않을 때 어떤 기준으로 과제를 줄이는지 질문합니다."
    ),
    "부산중동과외": (
        "부산중동과외 정보를 학생의 계획으로 바꿀 때는 학교·학년·과목·귀가 뒤 사용 가능한 시간을 먼저 나눕니다. 최근 학교 원본에서 마감이 있는 과제와 "
        "누적 복습을 구분하고, 학생이 도움 없이 펼친 자료와 처음 고른 행동을 지우지 않은 채 보관합니다. 영어 답안은 단어 수보다 문장 근거와 표현 수정 이유를, "
        "수학 풀이는 정답보다 조건을 읽은 순서와 첫 전략·검산을 확인합니다. 다음 점검에서는 같은 문제를 기억하는지보다 자료나 조건이 달라져도 판단 순서를 "
        "다시 꺼내 쓰는지 살피며, 변화가 없으면 공부시간을 늘리기 전에 과제 크기와 질문 시점을 조정합니다."
    ),
    "부산북구과외": "부산북구과외의 구 단위 정보는 개별 학교 일정을 대신하지 않습니다. 학생이 받은 최신 자료와 공식 공지를 확인한 뒤 과목별 첫 행동·멈춘 위치·다음 재시도를 기록해 실제 생활권 계획으로 좁힙니다.",
    "부산동래구과외": "부산동래구과외를 비교할 때는 지역 평균보다 학생의 학교 원본과 현재 답안을 먼저 봅니다. 영어 근거와 수학 첫 식을 따로 보존하고, 도움 뒤 혼자 이어 간 범위를 다음 과제의 기준으로 사용합니다.",
    "부산금정구과외": "부산금정구과외 페이지의 범위는 탐색을 돕기 위한 것이며 학교별 진도나 성취를 뜻하지 않습니다. 실제 교과서·과제 안내·첫 답안을 대조해 유지할 행동과 줄일 도움을 한 항목씩 정합니다.",
    "부산사상구과외": "부산사상구과외 계획은 학교 마감과 누적 복습을 같은 분량으로 배치하지 않습니다. 학생이 받은 안내를 기준으로 우선순위를 정하고, 간격 뒤에도 혼자 재현한 행동을 다음 학습에 유지합니다.",
    "부산수영구과외": "부산수영구과외 정보를 볼 때는 통학이나 학교 일정을 지역명으로 단정하지 않습니다. 현재 학교 자료와 학생 기록을 확인해 과목별 질문 위치, 수정 근거, 독립 재시도를 구체적인 비교 항목으로 삼습니다.",
    "부산진구과외": "부산진구과외의 다음 행동은 새 교재보다 최근 학교 자료에서 정합니다. 도움 전 시도와 수정 뒤 답안을 나란히 두고, 다른 조건에서도 같은 판단을 사용했는지 확인한 뒤 과제 범위를 넓힙니다.",
    "부산해운대구과외": "부산해운대구과외 페이지는 구 안의 학생에게 같은 계획을 권하지 않습니다. 학교·학년·과목·생활시간을 확인하고, 학생이 실제로 남긴 첫 행동과 수정 이유를 기준으로 필요한 학습만 좁혀 봅니다.",
    "부산연제구과외": "부산연제구과외를 상담 질문으로 바꿀 때는 점수 약속보다 수업 전후에 남는 기록을 확인합니다. 학교 원본, 도움 전 시작, 오류를 고친 이유, 간격 뒤 독립 수행을 설명할 수 있는지 비교합니다.",
    "부산기장군과외": "부산기장군과외 정보는 넓은 지역 범위를 하나의 학습 환경으로 일반화하지 않습니다. 학생의 실제 학교 안내와 이동·귀가 시간을 확인한 뒤, 과목별 완료 기준과 다시 볼 자료를 현실적으로 배치합니다.",
}


def add_regional_audit_note(body: str, slug: str) -> str:
    note = REGIONAL_AUDIT_NOTES.get(slug)
    if not note:
        return body
    return (
        body
        + f'<section class="regional-audit-note"><h2>{slug} 자료를 읽을 때 남길 확인 기록</h2>'
        + f"<p>{note}</p></section>"
    )


def individualize_repeated_region_subject_paragraphs(pages: dict[str, Page]) -> None:
    """Add local application context only to long paragraphs shared by 3+ region subject pages."""
    paragraph_pattern = re.compile(r"(<p\b[^>]*>)(.*?)(</p>)", flags=re.I | re.S)
    candidates = [
        page
        for page in pages.values()
        if page.page_type == "subject" and page.category in {"영어과외", "수학과외"}
    ]
    owners: dict[str, set[str]] = {}
    for page in candidates:
        for match in paragraph_pattern.finditer(page.body):
            text = strip_tags(match.group(2))
            if len(text) >= 80:
                owners.setdefault(text, set()).add(page.slug)
    repeated = {text for text, slugs in owners.items() if len(slugs) >= 3}
    if not repeated:
        return

    for page in candidates:
        location = page.slug.removesuffix(page.category)
        subject = "영어" if page.category == "영어과외" else "수학"

        def add_context(match: re.Match[str]) -> str:
            inner = match.group(2)
            if strip_tags(inner) not in repeated:
                return match.group(0)
            note = (
                f" {location}에서는 이 기준을 학생이 받은 {subject} 자료와 도움 전 첫 시도 기록에 대조해 적용한다."
            )
            return f"{match.group(1)}{inner}{note}{match.group(3)}"

        page.body = paragraph_pattern.sub(add_context, page.body)


def page_type_for(category: str, region: Region | None = None, school: bool = False) -> str:
    if school:
        return "school"
    if category in SUBJECT_GRADE_CATEGORIES:
        return "subject_grade"
    if category in SUBJECT_CATEGORIES:
        return "subject"
    if category in GRADE_CATEGORIES:
        return "grade"
    if region:
        return "region"
    return "hub"


def title_for(region: Region | None, category: str) -> str:
    if not region:
        return "전국과외" if category == "과외" else category
    return f"{region.slug}{category}"


def make_breadcrumbs(page: Page, pages: dict[str, Page]) -> list[tuple[str, str]]:
    chain: list[tuple[str, str]] = []
    current = page
    seen = set()
    while current and current.slug not in seen:
        seen.add(current.slug)
        chain.append((current.title, current.url))
        current = pages.get(current.parent_slug or "")
    return list(reversed(chain))


def existing_region_parent(info: dict[str, str], pages: dict[str, Page], category: str = "과외") -> str | None:
    candidates = [
        f"{info.get('town_slug', '')}{category}",
        f"{info.get('district_slug', '')}{category}",
        f"{info.get('city_slug', '')}{category}",
    ]
    if category != "과외":
        candidates.extend([
            f"{info.get('city_slug', '')}{category}",
            category,
        ])
    for slug in candidates:
        if slug and slug in pages:
            return slug
    return "index"


def school_base_from_slug(slug: str) -> str:
    for suffix in ["수학과외", "영어과외", "과외"]:
        if slug.endswith(suffix):
            return slug[: -len(suffix)]
    return slug


def build_pages(
    regions: dict[str, Region],
    content: dict[str, str],
    school_slugs: set[str],
    school_map: dict[str, dict[str, str]] | None = None,
) -> tuple[list[Page], Counter]:
    school_map = school_map or {}
    content_sources = getattr(__import__("sitegen.data_loader", fromlist=["load_content"]).load_content, "sources", {})
    pages: dict[str, Page] = {}
    stats: Counter = Counter()

    for region in regions.values():
        for category in CATEGORIES:
            slug = page_slug(None if region.level == "national" else region.slug, category)
            title = title_for(None if region.level == "national" else region, category)
            if slug in pages:
                stats["duplicate_slugs"] += 1
                continue
            parent_slug = None
            if region.parent:
                parent_region = regions[region.parent]
                parent_slug = page_slug(None if parent_region.level == "national" else parent_region.slug, category)
            elif category != "과외":
                parent_slug = "전국과외"
            child_slugs = [
                page_slug(None if regions[item].level == "national" else regions[item].slug, category)
                for item in region.children
            ]
            sibling_slugs = []
            if region.parent:
                sibling_slugs = [
                    page_slug(None if regions[item].level == "national" else regions[item].slug, category)
                    for item in regions[region.parent].children
                    if item != region.key
                ]
            related = [page_slug(None if region.level == "national" else region.slug, item) for item in CATEGORIES if item != category]
            body = normalize_source_body(content.get(slug, ""))
            seo_title, _ = build_page_title(slug, content_sources.get(slug))
            meta_description = (
                region_meta_description(slug, body)
                if category == "과외" and region.level not in {"national", "province"} and body
                else excerpt(body) if body
                else f"{title} 학습 환경, 내신 준비, 영어와 수학 학습 방향을 정리한 EduNext 지역 과외 정보입니다."
            )
            page = Page(
                slug=slug,
                title=title,
                page_type=page_type_for(category, None if region.level == "national" else region),
                category=category,
                seo_title=seo_title,
                region_key=region.key,
                parent_slug=parent_slug,
                child_slugs=child_slugs,
                sibling_slugs=sibling_slugs,
                related_slugs=related,
                body=body,
                meta_description=meta_description,
            )
            special_subject_body = special_subject_hub_content(slug)
            if special_subject_body:
                page.body = special_subject_body
            elif not page.body:
                page.body = fallback_content(page)
            if slug in SPECIAL_SUBJECT_HUB_META_DESCRIPTIONS:
                page.meta_description = SPECIAL_SUBJECT_HUB_META_DESCRIPTIONS[slug]
            page.body = individualize_secondary_region_body(page.body, page)
            page.body = individualize_priority_region_body(page.body, page)
            page.body = add_regional_audit_note(page.body, slug)
            if category == "과외" and region.level not in {"national", "province"}:
                page.meta_description = region_meta_description(slug, page.body)
            pages[slug] = page
            stats[page.page_type] += 1

    region_prefixes = ("부산", "양산", "구미")
    for slug in sorted(school_slugs):
        if slug in pages or not slug.startswith(region_prefixes):
            continue
        city = next(prefix for prefix in region_prefixes if slug.startswith(prefix))
        category = "고등수학과외" if "수학과외" in slug else "고등영어과외" if "영어과외" in slug else "고등과외"
        info = school_map.get(slug, {})
        base = info.get("base", school_base_from_slug(slug))
        tutoring_slug = f"{base}과외"
        parent_slug = existing_region_parent(info, pages, "과외")
        if slug != tutoring_slug and tutoring_slug in content:
            parent_slug = tutoring_slug
        mapped_region = existing_region_parent(info, pages, "과외")
        mapped_category = "수학과외" if "수학과외" in slug else "영어과외" if "영어과외" in slug else "고등과외"
        related = [
            f"{base}과외",
            f"{base}수학과외",
            f"{base}영어과외",
            mapped_region or "",
            existing_region_parent(info, pages, mapped_category) or "",
            f"{city}고등과외",
            f"{city}고등수학과외",
            f"{city}고등영어과외",
            f"{city}과외",
        ]
        page = Page(
            slug=slug,
            title=slug,
            page_type="school",
            category=category,
            seo_title=build_page_title(slug, content_sources.get(slug))[0],
            parent_slug=parent_slug,
            related_slugs=[item for item in related if item and item != slug],
            school_display_name=info.get("school_display_name", base.removeprefix(city)),
            official_school_name=info.get("official_school_name", ""),
            body=normalize_source_body(content.get(slug, "")) or school_intro(slug),
            meta_description=excerpt(content.get(slug, "")) or f"{slug} 학교별 내신과 고등 학습 준비를 정리한 EduNext 과외 정보입니다.",
        )
        pages[slug] = page
        stats["school"] += 1

    for slug, context in middle_school_math_contexts().items():
        if slug in pages:
            stats["duplicate_slugs"] += 1
            continue
        seo_title, meta_description = build_middle_school_math_meta(slug)
        pages[slug] = Page(
            slug=slug,
            title=slug,
            page_type="school",
            category="중등수학과외",
            seo_title=seo_title,
            parent_slug=context.parent_slug,
            related_slugs=list(context.internal_links),
            school_display_name=context.display_name,
            official_school_name=context.official_name,
            body=build_middle_school_math_body(slug),
            meta_description=meta_description,
        )
        stats["school"] += 1

    for slug, context in middle_school_english_contexts().items():
        if slug in pages:
            stats["duplicate_slugs"] += 1
            continue
        seo_title, meta_description = build_middle_school_english_meta(slug)
        pages[slug] = Page(
            slug=slug,
            title=slug,
            page_type="school",
            category="중등영어과외",
            seo_title=seo_title,
            parent_slug=context.parent_slug,
            related_slugs=list(context.internal_links),
            school_display_name=context.display_name,
            official_school_name=context.official_name,
            body=build_middle_school_english_body(slug),
            meta_description=meta_description,
        )
        stats["school"] += 1

    for page in list(pages.values()):
        if page.page_type != "school" or not page.parent_slug or page.parent_slug not in pages:
            continue
        parent = pages[page.parent_slug]
        if page.slug not in parent.child_slugs:
            parent.child_slugs.append(page.slug)
        if is_middle_school_math_slug(page.slug) or is_middle_school_english_slug(page.slug):
            if page.slug not in parent.school_slugs:
                parent.school_slugs.append(page.slug)
            continue
        info = school_map.get(page.slug, {})
        for region_slug in [
            existing_region_parent(info, pages, "과외"),
            existing_region_parent(info, pages, "고등과외"),
            existing_region_parent(info, pages, "수학과외"),
            existing_region_parent(info, pages, "영어과외"),
        ]:
            if region_slug and region_slug in pages and page.slug not in pages[region_slug].school_slugs:
                pages[region_slug].school_slugs.append(page.slug)

    schools_by_city = {"부산": [], "구미": [], "양산": []}
    for slug in sorted(school_slugs):
        for city in schools_by_city:
            if slug.startswith(city):
                schools_by_city[city].append(slug)

    home = Page(
        slug="index",
        title="EduNext 부산 양산 구미 과외",
        page_type="home",
        category="과외",
        seo_title=HOME_SEO_TITLE,
        child_slugs=["전국과외", "부산과외", "양산과외", "구미과외", "영어과외", "수학과외", "초등과외", "중등과외", "고등과외"],
        related_slugs=["부산영어과외", "부산수학과외", "양산영어과외", "구미수학과외"],
        school_slugs=(schools_by_city["부산"][:18] + schools_by_city["구미"][:12] + schools_by_city["양산"][:12]),
        body=(
            "<h2>부산·양산·구미 과외 학습 허브</h2>"
            "<p>EduNext는 지역별 학교생활과 학년 변화, 영어·수학 학습 방향을 한글 URL로 정리한 정적 교육 정보 사이트입니다.</p>"
            "<h2>지역과 과목을 함께 확인</h2>"
            "<p>홈에서 전국 허브, 시도 허브, 도시와 읍면동, 과목과 학년 페이지로 이어지도록 구성했습니다.</p>"
            "<h2>검증 가능한 구조</h2>"
            "<p>모든 페이지는 sitemap과 내부 링크 검사를 통과하도록 연결되며, 학교 페이지는 엑셀에 실제 본문이 있는 키워드만 생성합니다. 배포 전에도 같은 스크립트로 구조를 다시 확인할 수 있습니다.</p>"
        ),
        meta_description="부산, 양산, 구미 지역의 과외 학습 정보를 지역, 과목, 학년별로 탐색하는 EduNext 메인 허브입니다.",
    )
    pages[home.slug] = home
    stats["home"] = 1

    if os.environ.get("EDUNEXT_STRICT_SOURCE") == "1":
        allowed = set(content) | {"index"}
        pages = {slug: page for slug, page in pages.items() if slug in allowed}
        stats["strict_source_pages"] = len(pages)

    individualize_repeated_region_subject_paragraphs(pages)

    for page in pages.values():
        page.child_slugs = [item for item in page.child_slugs if item in pages and item != page.slug]
        page.sibling_slugs = [item for item in page.sibling_slugs if item in pages and item != page.slug]
        page.related_slugs = [item for item in page.related_slugs if item in pages and item != page.slug]
        page.school_slugs = [item for item in page.school_slugs if item in pages and item != page.slug]
    for page in pages.values():
        page.breadcrumbs = make_breadcrumbs(page, pages)
        if page.slug != "index" and not page.breadcrumbs:
            page.breadcrumbs = [("EduNext", "/"), (page.title, page.url)]
    return list(pages.values()), stats
