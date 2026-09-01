from __future__ import annotations

from collections import Counter
import os

from config import CATEGORIES, GRADE_CATEGORIES, SUBJECT_CATEGORIES, SUBJECT_GRADE_CATEGORIES
from sitegen.content_builder import fallback_content, school_intro
from sitegen.models import Page, Region
from sitegen.render import individualize_priority_region_body, individualize_secondary_region_body
from sitegen.title_rules import HOME_SEO_TITLE, build_page_title
from sitegen.utils import excerpt, page_slug, region_meta_description


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
            body = content.get(slug, "")
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
            if not page.body:
                page.body = fallback_content(page)
            page.body = individualize_secondary_region_body(page.body, page)
            page.body = individualize_priority_region_body(page.body, page)
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
            body=content.get(slug, "") or school_intro(slug),
            meta_description=excerpt(content.get(slug, "")) or f"{slug} 학교별 내신과 고등 학습 준비를 정리한 EduNext 과외 정보입니다.",
        )
        pages[slug] = page
        stats["school"] += 1

    for page in list(pages.values()):
        if page.page_type != "school" or not page.parent_slug or page.parent_slug not in pages:
            continue
        parent = pages[page.parent_slug]
        if page.slug not in parent.child_slugs:
            parent.child_slugs.append(page.slug)
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
