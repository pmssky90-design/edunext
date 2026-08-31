from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import quote

from config import NAVER_SITE_VERIFICATION, SITE_DESCRIPTION, SITE_NAME, SITE_URL
from sitegen.models import Page
from sitegen.utils import escape

ROOT = Path(__file__).resolve().parents[1]
FIXED_IMAGE_MANIFEST = ROOT / "data" / "fixed_images.json"
SEARCH_THUMBNAIL_MANIFEST = ROOT / "data" / "search_thumbnails.json"

SUBJECTS = {"영어과외", "수학과외"}
GRADES = {"초등과외", "중등과외", "고등과외"}
SUBJECT_GRADES = {"초등영어과외", "중등영어과외", "고등영어과외", "초등수학과외", "중등수학과외", "고등수학과외"}
CITIES = ("부산", "구미", "양산")


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def enhance_content_body(body: str) -> tuple[str, str]:
    """Add stable heading anchors and a compact table of contents without changing text."""
    entries: list[tuple[int, str, str]] = []
    index = 0

    def add_anchor(match: re.Match[str]) -> str:
        nonlocal index
        level, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        if re.search(r"\bid\s*=", attrs, flags=re.I):
            anchor_match = re.search(r'\bid\s*=\s*["\']([^"\']+)', attrs, flags=re.I)
            anchor = anchor_match.group(1) if anchor_match else f"content-section-{index + 1}"
        else:
            index += 1
            anchor = f"content-section-{index}"
            attrs += f' id="{anchor}"'
        entries.append((int(level), anchor, plain_text(inner)))
        return f"<h{level}{attrs}>{inner}</h{level}>"

    enhanced = re.sub(r"<h([23])(\s[^>]*)?>(.*?)</h\1>", add_anchor, body, flags=re.I | re.S)
    visible = [entry for entry in entries if entry[2]][:24]
    if len(visible) < 2:
        return enhanced, ""
    links = "".join(
        f'<li class="toc-level-{level}"><a href="#{escape(anchor)}">{escape(label)}</a></li>'
        for level, anchor, label in visible
    )
    toc = (
        '<nav class="page-toc" aria-label="이 페이지의 목차">'
        '<details><summary>이 페이지의 내용</summary>'
        f'<ol>{links}</ol></details></nav>'
    )
    return enhanced, toc


def faq_schema(body: str) -> dict[str, object] | None:
    faq_start = re.search(r"<h2\b[^>]*>.*?자주\s*묻는\s*질문.*?</h2>", body, flags=re.I | re.S)
    if not faq_start:
        return None
    section = body[faq_start.end() :]
    next_h2 = re.search(r"<h2\b", section, flags=re.I)
    if next_h2:
        section = section[: next_h2.start()]
    pairs = re.findall(r"<h3\b[^>]*>(.*?)</h3>\s*<p\b[^>]*>(.*?)</p>", section, flags=re.I | re.S)
    entities = []
    for question, answer in pairs:
        question_text, answer_text = plain_text(question), plain_text(answer)
        if question_text and answer_text:
            entities.append({"@type": "Question", "name": question_text, "acceptedAnswer": {"@type": "Answer", "text": answer_text}})
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities} if entities else None


def absolute_url(path: str) -> str:
    return SITE_URL + (path if path.startswith("/") else f"/{path}")


def load_fixed_image_manifest() -> list[dict[str, str]]:
    if not FIXED_IMAGE_MANIFEST.exists():
        return []
    data = json.loads(FIXED_IMAGE_MANIFEST.read_text(encoding="utf-8"))
    return list(data.get("images", []))


def load_search_thumbnail_manifest() -> list[str]:
    if not SEARCH_THUMBNAIL_MANIFEST.exists():
        return []
    data = json.loads(SEARCH_THUMBNAIL_MANIFEST.read_text(encoding="utf-8"))
    return list(data.get("images", []))


def build_search_thumbnail_url(src: str) -> str:
    return SITE_URL + "/" + "/".join(quote(part) for part in src.lstrip("/").split("/"))


def select_stable_search_thumbnail(page: Page) -> tuple[str, str, str]:
    thumbnails = load_search_thumbnail_manifest()
    if not thumbnails:
        fallback = "/assets/images/edunext-og.svg"
        return fallback, SITE_URL + fallback, ""
    digest = hashlib.sha256(page.slug.encode("utf-8")).hexdigest()
    src = thumbnails[int(digest, 16) % len(thumbnails)]
    return src, build_search_thumbnail_url(src), digest


def page_city(page: Page | None) -> str:
    if not page:
        return ""
    for city in CITIES:
        if page.slug.startswith(city):
            return city
    return ""


def compact_label(current: Page, target: Page, context: str = "") -> str:
    label = target.title
    if context == "parent":
        return label
    current_city = page_city(current)
    target_city = page_city(target)
    if context == "school-action":
        if target.slug.endswith("수학과외"):
            return "수학과외"
        if target.slug.endswith("영어과외"):
            return "영어과외"
        return "종합과외"
    if current_city and current_city == target_city and target.page_type != "school":
        label = label[len(target_city) :] if label.startswith(target_city) else label
    if target.page_type == "school":
        base = target.school_display_name or label
        if target.slug.endswith("수학과외"):
            return f"{base} 수학과외"
        if target.slug.endswith("영어과외"):
            return f"{base} 영어과외"
        return f"{base} 종합과외"
    return label or target.title


def unique_pages(slugs: list[str], page_map: dict[str, Page], current: Page, seen: set[str] | None = None) -> list[Page]:
    seen = seen if seen is not None else set()
    pages = []
    for slug in slugs:
        if slug in seen or slug not in page_map or slug == current.slug:
            continue
        seen.add(slug)
        pages.append(page_map[slug])
    return pages


def render_page_cards(title: str, pages: list[Page], current: Page, context: str = "") -> str:
    if not pages:
        return ""
    links = "".join(
        f'<li><a class="related-link-card" href="{escape(item.url)}">'
        f'<span>{escape(compact_label(current, item, context))}</span></a></li>'
        for item in pages
    )
    return f'<section class="related-section"><h2>{escape(title)}</h2><ul class="related-card-grid">{"".join(links)}</ul></section>'


def category_family_sections(page: Page, page_map: dict[str, Page], candidates: list[str], seen: set[str]) -> str:
    english = unique_pages([slug for slug in candidates if slug in page_map and page_map[slug].page_type != "school" and "영어" in page_map[slug].category], page_map, page, seen)
    math = unique_pages([slug for slug in candidates if slug in page_map and page_map[slug].page_type != "school" and "수학" in page_map[slug].category], page_map, page, seen)
    chunks = []
    if english:
        chunks.append(render_page_cards("영어 과목·학년별 과외", english, page))
    if math:
        chunks.append(render_page_cards("수학 과목·학년별 과외", math, page))
    return "".join(chunks)


def school_section(page: Page, page_map: dict[str, Page]) -> str:
    if not page.school_slugs:
        return ""
    title = "고등학교별 과외 찾기" if page.page_type == "home" else "관련 고등학교 학습 페이지"
    groups: dict[str, list[Page]] = {}
    for slug in page.school_slugs:
        item = page_map.get(slug)
        if not item:
            continue
        base = item.slug
        for suffix in ["수학과외", "영어과외", "과외"]:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        groups.setdefault(base, []).append(item)
    cards = []
    for base, items in sorted(groups.items()):
        items = sorted(items, key=lambda p: {"school": 0}.get(p.page_type, 1))
        links = "".join(f'<a href="{escape(item.url)}">{escape(compact_label(page, item, "school-action"))}</a>' for item in items)
        display = items[0].school_display_name or base
        official = items[0].official_school_name
        meta = f"<small>{escape(official)}</small>" if official else ""
        cards.append(f'<li class="school-card"><strong>{escape(display)}</strong>{meta}<div>{links}</div></li>')
    return f'<section class="link-section school-section" id="high-schools"><h2>{escape(title)}</h2><ul class="school-grid">{"".join(cards)}</ul></section>'


def render_related_navigation(page: Page, page_map: dict[str, Page]) -> str:
    used: set[str] = set()
    chunks = ['<nav class="related-navigation" aria-label="관련 페이지">']
    parent = unique_pages([page.parent_slug or ""], page_map, page, used)
    if parent:
        chunks.append(render_page_cards("지역 둘러보기", parent, page, "parent"))
    child_regions = unique_pages([slug for slug in page.child_slugs if slug in page_map and page_map[slug].page_type == "region"], page_map, page, used)
    chunks.append(render_page_cards("하위 지역별 과외", child_regions, page))
    subject_links = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in SUBJECTS], page_map, page, used)
    chunks.append(render_page_cards("과목별 과외", subject_links, page))
    grade_links = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in GRADES], page_map, page, used)
    chunks.append(render_page_cards("학년별 과외", grade_links, page))
    sg_links = [slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in SUBJECT_GRADES]
    chunks.append(category_family_sections(page, page_map, sg_links, used))
    school_related = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].page_type == "school"], page_map, page, used)
    chunks.append(render_page_cards("같은 학교·관련 학교", school_related, page))
    chunks.append(school_section(page, page_map))
    siblings = unique_pages([slug for slug in page.sibling_slugs if slug in page_map and page_map[slug].page_type == "region"], page_map, page, used)
    chunks.append(render_page_cards("같은 단계의 인접·형제 지역", siblings[:18], page))
    chunks.append("</nav>")
    body = "".join(chunks)
    return body if 'related-section' in body or 'school-section' in body else ""


def render_page_hero_image(page: Page) -> str:
    if page.page_type == "home" or not page.hero_image:
        return ""
    alt = page.hero_image_alt or page.title
    return f'<figure class="page-hero-image"><img src="{escape(page.hero_image)}" alt="{escape(alt)}"></figure>'


def render_fixed_images(page: Page) -> str:
    if page.page_type == "home":
        return ""
    figures = []
    for index, image in enumerate(load_fixed_image_manifest(), start=1):
        src = image.get("src", "")
        if not src:
            continue
        css_class = "representative-image" if index == 1 else "flow-image"
        alt = image.get("alt") or f"{page.title} 맞춤 과외 안내 이미지 {index:03d}"
        loading = "eager" if index == 1 else "lazy"
        priority = ' fetchpriority="high"' if index == 1 else ""
        width = f' width="{escape(str(image.get("width", "")))}"' if image.get("width") else ""
        height = f' height="{escape(str(image.get("height", "")))}"' if image.get("height") else ""
        figures.append(
            f'<figure class="{css_class}"><img src="{escape(src)}" alt="{escape(alt)}"{width}{height} loading="{loading}" decoding="async"{priority}></figure>'
        )
    if not figures:
        return ""
    return '<section class="page-fixed-images" aria-label="학습 안내 이미지">' + "".join(figures) + "</section>"


def breadcrumbs(page: Page) -> str:
    items = []
    crumbs = [("홈", "/")] + [item for item in page.breadcrumbs if item[1] != "/"]
    seen = set()
    filtered = []
    for name, url in crumbs:
        if url in seen:
            continue
        seen.add(url)
        filtered.append((name, url))
    for index, (name, url) in enumerate(filtered):
        if index == len(filtered) - 1:
            items.append(f'<li><span aria-current="page">{escape(name)}</span></li>')
        else:
            items.append(f'<li><a href="{escape(url)}">{escape(name)}</a></li>')
    return '<nav class="breadcrumb" aria-label="breadcrumb"><ol>' + "".join(items) + "</ol></nav>"


def schema(page: Page) -> str:
    crumbs = [("홈", "/")] + [item for item in page.breadcrumbs if item[1] != "/"]
    data = [
        {"@context": "https://schema.org", "@type": "Organization", "@id": f"{SITE_URL}/#organization", "name": SITE_NAME, "url": SITE_URL + "/"},
        {"@context": "https://schema.org", "@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": SITE_URL + "/", "name": SITE_NAME, "description": SITE_DESCRIPTION},
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": absolute_url(page.url) + "#webpage",
            "url": absolute_url(page.url),
            "name": page.title,
            "description": page.meta_description,
            "image": page.search_thumbnail_url,
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "inLanguage": "ko-KR",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name, "item": absolute_url(url)}
                for i, (name, url) in enumerate(crumbs)
            ],
        },
    ]
    faq = faq_schema(page.body)
    if faq:
        data.append(faq)
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def home_nav(page_map: dict[str, Page]) -> str:
    labels = [
        ("부산과외", "부산"),
        ("구미과외", "구미"),
        ("양산과외", "양산"),
        ("영어과외", "영어"),
        ("수학과외", "수학"),
        ("초등과외", "초등"),
        ("중등과외", "중등"),
        ("고등과외", "고등"),
    ]
    links = []
    for slug, label in labels:
        item = page_map.get(slug)
        if item:
            links.append(f'<a href="{escape(item.url)}">{escape(label)}</a>')
    links.append('<a href="/#high-schools">고등학교별 과외</a>')
    return "".join(links)


def home_link_list(items: list[tuple[str, str]], page_map: dict[str, Page]) -> str:
    links = []
    for slug, label in items:
        item = page_map.get(slug)
        if item:
            links.append(f'<li><a class="home-link-card" href="{escape(item.url)}">{escape(label)}</a></li>')
    return '<ul class="home-link-grid">' + "".join(links) + "</ul>" if links else ""


def primary_nav(page_map: dict[str, Page]) -> str:
    """Render the same compact global navigation on every page."""
    links = []
    for slug, label in [
        ("부산과외", "부산과외"),
        ("양산과외", "양산과외"),
        ("구미과외", "구미과외"),
    ]:
        item = page_map.get(slug)
        if item:
            links.append(f'<a href="{escape(item.url)}">{escape(label)}</a>')
    links.append('<a href="/#high-schools">고등학교별 과외</a>')
    return "".join(links)


def home_cta_grid(items: list[tuple[str, str, str]], page_map: dict[str, Page]) -> str:
    cards = []
    for slug, label, desc in items:
        href = f"/{slug}" if slug.startswith("#") else (page_map[slug].url if slug in page_map else "")
        if href:
            cards.append(f'<a class="home-cta-card" href="{escape(href)}"><strong>{escape(label)}</strong><span>{escape(desc)}</span></a>')
    return '<div class="home-cta-grid">' + "".join(cards) + "</div>"


def home_intro(title: str, body: str) -> str:
    return f'<div class="home-section-intro"><h2>{escape(title)}</h2><p>{escape(body)}</p></div>'


def home_school_groups(page_map: dict[str, Page]) -> dict[str, dict[str, list[Page]]]:
    groups: dict[str, dict[str, list[Page]]] = {"busan": {}, "gumi": {}, "yangsan": {}}
    city_keys = {CITIES[0]: "busan", CITIES[1]: "gumi", CITIES[2]: "yangsan"}
    for item in page_map.values():
        if item.page_type != "school":
            continue
        city = page_city(item)
        city_key = city_keys.get(city)
        if not city_key:
            continue
        base = item.school_display_name or item.official_school_name or item.title
        groups[city_key].setdefault(base, []).append(item)
    return groups


def render_home_school_card(name: str, items: list[Page]) -> str:
    ordered = sorted(items, key=lambda p: (0 if "怨쇱쇅" in p.slug and "?섑븰" not in p.slug and "?곸뼱" not in p.slug else 1 if "?섑븰" in p.slug else 2, p.slug))
    links = "".join(f'<a href="{escape(item.url)}">{escape(compact_label(item, item, "school-action"))}</a>' for item in ordered)
    official = next((item.official_school_name for item in ordered if item.official_school_name), "")
    meta = f"<small>{escape(official)}</small>" if official else ""
    return f'<li class="home-school-card"><strong>{escape(name)}</strong>{meta}<div>{links}</div></li>'


def render_home_school_section(section_id: str, title: str, groups: dict[str, list[Page]], visible_count: int) -> str:
    ordered = sorted(groups.items())
    visible = ordered[:visible_count]
    hidden = ordered[visible_count:]
    visible_cards = "".join(render_home_school_card(name, items) for name, items in visible)
    hidden_cards = "".join(render_home_school_card(name, items) for name, items in hidden)
    details = ""
    if hidden_cards:
        city = title.split()[0]
        details = (
            f'<details class="home-school-details"><summary>▼ {escape(city)} 고등학교 전체 보기</summary>'
            f'<ul class="home-school-grid home-school-grid-details">{hidden_cards}</ul></details>'
        )
    return (
        f'<section class="home-section home-school-section" id="{section_id}" data-visible-schools="{len(visible)}" data-hidden-schools="{len(hidden)}">'
        f'<h2>{escape(title)}</h2><p>대표 학교를 먼저 확인하고, 전체 보기를 열어 나머지 학교 페이지까지 이어서 탐색할 수 있습니다.</p>'
        f'<ul class="home-school-grid">{visible_cards}</ul>{details}</section>'
    )


def render_home_region_detail(page_map: dict[str, Page]) -> str:
    city_items = [("부산과외", "부산과외"), ("구미과외", "구미과외"), ("양산과외", "양산과외")]
    district_items = []
    for item in page_map.values():
        if item.page_type == "region" and item.parent_slug in {"부산과외", "구미과외", "양산과외"}:
            district_items.append((item.slug, item.title))
    district_items = sorted(district_items, key=lambda row: row[1])[:36]
    return (
        '<section class="home-section" id="region-detail">'
        + home_intro("지역별 과외 둘러보기", "도시별 대표 페이지와 하위 지역 페이지를 나누어 확인할 수 있습니다. 더 세부적인 동·읍·면 페이지는 각 지역 허브에서 이어서 탐색할 수 있습니다.")
        + home_link_list(city_items + district_items, page_map)
        + "</section>"
    )


def render_home(page: Page, page_map: dict[str, Page]) -> str:
    canonical = absolute_url(page.url)
    search_title = page.seo_title or page.title
    if not page.search_thumbnail_url:
        page.search_thumbnail, page.search_thumbnail_url, page.search_thumbnail_hash = select_stable_search_thumbnail(page)
    city_cards = [
        ("부산", [("부산과외", "부산과외"), ("부산영어과외", "영어과외"), ("부산수학과외", "수학과외"), ("부산초등과외", "초등과외"), ("부산중등과외", "중등과외"), ("부산고등과외", "고등과외")], "busan-high-schools"),
        ("구미", [("구미과외", "구미과외"), ("구미영어과외", "영어과외"), ("구미수학과외", "수학과외"), ("구미초등과외", "초등과외"), ("구미중등과외", "중등과외"), ("구미고등과외", "고등과외")], "gumi-high-schools"),
        ("양산", [("양산과외", "양산과외"), ("양산영어과외", "영어과외"), ("양산수학과외", "수학과외"), ("양산초등과외", "초등과외"), ("양산중등과외", "중등과외"), ("양산고등과외", "고등과외")], "yangsan-high-schools"),
    ]
    city_html = []
    for city, links, anchor in city_cards:
        city_html.append(
            f'<article class="home-feature-card home-city-card"><span class="home-card-icon" aria-hidden="true">⌁</span><h3>{escape(city)}</h3><p>{escape(city)} 지역 대표 과외 페이지에서 과목과 학년별 정보를 이어서 확인할 수 있습니다.</p>'
            + home_link_list(links, page_map)
            + f'<a class="home-anchor-link" href="/#{anchor}">{escape(city)} 고등학교 보기</a></article>'
        )
    subject_html = (
        '<article class="home-feature-card home-subject-card"><span class="home-card-icon" aria-hidden="true">A</span><h3>영어과외</h3><p>지역별 영어와 학년별 영어 페이지를 한 번에 좁혀 볼 수 있습니다.</p>'
        + home_link_list([("부산영어과외", "부산영어과외"), ("구미영어과외", "구미영어과외"), ("양산영어과외", "양산영어과외"), ("초등영어과외", "초등영어과외"), ("중등영어과외", "중등영어과외"), ("고등영어과외", "고등영어과외")], page_map)
        + '</article><article class="home-feature-card home-subject-card"><span class="home-card-icon" aria-hidden="true">∑</span><h3>수학과외</h3><p>수학 과목 페이지와 초등·중등·고등 수학 흐름을 분리해 탐색합니다.</p>'
        + home_link_list([("부산수학과외", "부산수학과외"), ("구미수학과외", "구미수학과외"), ("양산수학과외", "양산수학과외"), ("초등수학과외", "초등수학과외"), ("중등수학과외", "중등수학과외"), ("고등수학과외", "고등수학과외")], page_map)
        + "</article>"
    )
    grade_html = (
        '<article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">01</span><h3>초등</h3><p>기초 학습과 과목별 준비 흐름을 함께 확인합니다.</p>'
        + home_link_list([("부산초등과외", "부산초등과외"), ("구미초등과외", "구미초등과외"), ("양산초등과외", "양산초등과외"), ("초등영어과외", "초등영어과외"), ("초등수학과외", "초등수학과외")], page_map)
        + '</article><article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">02</span><h3>중등</h3><p>내신과 고등 준비 사이의 연결 지점을 살펴봅니다.</p>'
        + home_link_list([("부산중등과외", "부산중등과외"), ("구미중등과외", "구미중등과외"), ("양산중등과외", "양산중등과외"), ("중등영어과외", "중등영어과외"), ("중등수학과외", "중등수학과외")], page_map)
        + '</article><article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">03</span><h3>고등</h3><p>학교별 내신과 과목별 학습 페이지로 바로 이어집니다.</p>'
        + home_link_list([("부산고등과외", "부산고등과외"), ("구미고등과외", "구미고등과외"), ("양산고등과외", "양산고등과외"), ("고등영어과외", "고등영어과외"), ("고등수학과외", "고등수학과외")], page_map)
        + '<a class="home-anchor-link" href="/#high-schools">고등학교별 과외</a></article>'
    )
    school_groups = home_school_groups(page_map)
    body = f"""
    <section class="home-hero">
      <figure class="home-hero-image"><img src="/assets/images/home/home-hero.png" alt="함께 공부하는 학생과 선생님" loading="eager" decoding="async" fetchpriority="high"></figure>
      <div class="home-hero-copy">
        <p class="eyebrow">부산 · 양산 · 구미 프리미엄 과외 정보</p>
        <h1>{escape(page.title)}</h1>
        <p class="home-hero-lead">지역별 과외, 학교별 과외, 영어·수학, 학년별 과외를 한곳에서 찾을 수 있습니다.</p>
        {home_cta_grid([("부산과외", "부산과외", "지역별 대표 허브"), ("구미과외", "구미과외", "구미 학습 페이지"), ("양산과외", "양산과외", "양산 지역 탐색"), ("#high-schools", "학교별과외", "고등학교별 이동")], page_map)}
      </div>
    </section>
    <section class="home-section" id="city-tutoring">
      {home_intro("부산·구미·양산 지역별 과외", "도시별 대표 페이지에서 과목과 학년 페이지로 이어집니다. 먼저 지역을 고른 뒤 영어·수학, 초등·중등·고등 흐름을 좁혀 볼 수 있습니다.")}
      <div class="home-card-grid">{"".join(city_html)}</div>
    </section>
    <section class="home-section" id="subjects">
      {home_intro("과목별 과외 찾기", "영어와 수학 페이지를 분리해 배치했습니다. 지역별 과목 페이지와 학년 결합 페이지를 함께 확인할 수 있습니다.")}
      <div class="home-card-grid two-columns">{subject_html}</div>
    </section>
    <section class="home-section" id="grades">
      {home_intro("학년별 과외 찾기", "초등·중등·고등 단계별로 대표 지역 페이지와 과목 결합 페이지를 이어서 볼 수 있습니다.")}
      <div class="home-card-grid three-columns">{grade_html}</div>
    </section>
    <section class="home-section home-school-hub" id="high-schools">
      <h2>고등학교별 과외 찾기</h2>
      <p>부산·구미·양산의 고등학교별 종합과외, 수학과외, 영어과외 페이지를 지역별로 확인할 수 있습니다.</p>
      <nav class="home-school-jump" aria-label="도시별 고등학교 바로가기"><a href="/#busan-high-schools">부산 고등학교</a><a href="/#gumi-high-schools">구미 고등학교</a><a href="/#yangsan-high-schools">양산 고등학교</a></nav>
    </section>
    {render_home_school_section("busan-high-schools", "부산 고등학교별 과외", school_groups["busan"], 24)}
    {render_home_school_section("gumi-high-schools", "구미 고등학교별 과외", school_groups["gumi"], 12)}
    {render_home_school_section("yangsan-high-schools", "양산 고등학교별 과외", school_groups["yangsan"], 8)}
    {render_home_region_detail(page_map)}
    <section class="home-section" id="site-guide">
      <h2>사이트 이용 안내</h2>
      <p>각 링크는 실제 생성된 정적 HTML 페이지로 연결됩니다. 상담 정보, 전화번호, 가격, 평점처럼 확인되지 않은 정보는 임의로 표시하지 않습니다.</p>
    </section>
    """
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="naver-site-verification" content="{escape(NAVER_SITE_VERIFICATION)}" />
  <title>{escape(search_title)}</title>
  <meta name="description" content="{escape(page.meta_description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{escape(search_title)}">
  <meta property="og:description" content="{escape(page.meta_description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(page.search_thumbnail_url)}">
  <meta property="og:image:alt" content="{escape(page.title)} 대표 이미지">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(search_title)}">
  <meta name="twitter:description" content="{escape(page.meta_description)}">
  <meta name="twitter:image" content="{escape(page.search_thumbnail_url)}">
  <link rel="stylesheet" href="/assets/css/style.css">
  {schema(page)}
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header">
    <span class="brand" aria-current="page">EduNext</span>
    <button class="menu-toggle" type="button" aria-label="메뉴 열기">☰</button>
    <nav class="top-nav">{primary_nav(page_map)}</nav>
  </header>
  <main id="main" class="home-main">
    {body}
  </main>
  <footer class="site-footer">
    <p>© {date.today().year} EduNext. 실제 상담 정보, 전화번호, 평점은 임의로 표시하지 않습니다.</p>
    <a href="/sitemap.xml">Sitemap</a>
  </footer>
  <script src="/assets/js/main.js" defer></script>
</body>
</html>
"""


def render_page(page: Page, page_map: dict[str, Page]) -> str:
    if page.page_type == "home":
        return render_home(page, page_map)
    canonical = absolute_url(page.url)
    search_title = page.seo_title or page.title
    if not page.search_thumbnail_url:
        page.search_thumbnail, page.search_thumbnail_url, page.search_thumbnail_hash = select_stable_search_thumbnail(page)
    enhanced_body, toc = enhance_content_body(page.body)
    sections = render_related_navigation(page, page_map)
    nav = "".join(
        f'<a href="{escape(page_map[slug].url)}">{escape(page_map[slug].title)}</a>'
        for slug in ["부산과외", "양산과외", "구미과외", "영어과외", "수학과외", "초등과외", "중등과외", "고등과외"]
        if slug in page_map and page_map[slug].url != page.url
    )
    if page.page_type != "home":
        nav += '<a href="/#high-schools">고등학교별 과외</a>'
    nav = primary_nav(page_map)
    brand = '<span class="brand" aria-current="page">EduNext</span>' if page.url == "/" else '<a class="brand" href="/">EduNext</a>'
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(search_title)}</title>
  <meta name="description" content="{escape(page.meta_description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{escape(search_title)}">
  <meta property="og:description" content="{escape(page.meta_description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(page.search_thumbnail_url)}">
  <meta property="og:image:alt" content="{escape(page.title)} 대표 이미지">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(search_title)}">
  <meta name="twitter:description" content="{escape(page.meta_description)}">
  <meta name="twitter:image" content="{escape(page.search_thumbnail_url)}">
  <link rel="stylesheet" href="/assets/css/style.css">
  {schema(page)}
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header">
    {brand}
    <button class="menu-toggle" type="button" aria-label="메뉴 열기">☰</button>
    <nav class="top-nav">{nav}</nav>
  </header>
  <main id="main" class="page-main page-type-{escape(page.page_type)}">
    {breadcrumbs(page)}
    <section class="page-hero">
      <p class="eyebrow">부산·양산·구미 과외 정보</p>
      <h1>{escape(page.title)}</h1>
      <p>{escape(page.meta_description)}</p>
    </section>
    {render_page_hero_image(page)}
    {render_fixed_images(page)}
    {toc}
    <article class="content-body">{enhanced_body}</article>
    {sections}
  </main>
  <footer class="site-footer">
    <p>© {date.today().year} EduNext. 실제 상담 정보, 전화번호, 평점은 임의로 표시하지 않습니다.</p>
    <a href="/sitemap.xml">Sitemap</a>
  </footer>
  <script src="/assets/js/main.js" defer></script>
</body>
</html>
"""


def render_not_found() -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>페이지를 찾을 수 없습니다 | {SITE_NAME}</title>
  <meta name="robots" content="noindex,follow">
  <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header"><a class="brand" href="/">{SITE_NAME}</a></header>
  <main id="main" class="page-main">
    <section class="page-hero">
      <p class="eyebrow">404 · Page not found</p>
      <h1>페이지를 찾을 수 없습니다</h1>
      <p>주소가 변경되었거나 존재하지 않는 페이지입니다. 홈페이지에서 지역·과목·학교별 과외 정보를 다시 찾아보세요.</p>
      <p><a class="home-anchor-link" href="/">EduNext 홈으로 이동</a></p>
    </section>
  </main>
</body>
</html>
"""
