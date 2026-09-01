from __future__ import annotations

import html
import re


PRIORITY_REGION_META_DESCRIPTIONS = {
    "구미옥계동과외": "구미옥계동과외는 행정명과 실제 생활권을 구분하고 귀가시간에 맞춘 두 종류의 저녁표, 학년별 점검 기준과 과목 선택법을 안내합니다.",
    "부산하단동과외": "부산하단동과외는 하단1·2동과 학교 동선을 나누어 보고, 마감 충돌과 시험 14일 계획, 영어와 수학 점검법을 안내합니다.",
    "부산우동과외": "부산우동과외는 주간 일정 충돌을 먼저 찾고, 과목별 오류 기록과 학교 일정 확인, 대면·온라인 선택 기준을 안내합니다.",
    "부산화명동과외": "부산화명동과외는 고정 일정과 변동 일정을 분리해 7일 생활 기록, 학년별 자기관리와 과목별 복습 기준을 안내합니다.",
    "부산좌동과외": "부산좌동과외는 실제 재학 학교 달력을 구분하고 유지·집중·이동 과제와 수업 후 복습 기준을 안내합니다.",
    "부산중동과외": "부산중동과외는 학교를 임의로 추정하지 않고 귀가 후 세 전환 시각과 48시간 과제 복구법을 안내합니다.",
    "구미남통동과외": "구미남통동과외는 질문을 영향도에 따라 분류하고 깊이 학습일과 연결 학습일을 나누는 방법을 안내합니다.",
    "부산덕천동과외": "부산덕천동과외는 과제 마감을 세 가지 신호로 구분하고 영어·수학의 서로 다른 완료 기준을 안내합니다.",
    "부산전포동과외": "부산전포동과외는 학교별 일정을 구분하고 수행평가를 안내·초안·검토·제출로 관리하는 방법을 안내합니다.",
    "부산구포동과외": "부산구포동과외는 연결된 학교 일정을 평균 내지 않고 학교·과목·회복의 세 줄 계획법을 안내합니다.",
    "부산명륜동과외": "부산명륜동과외는 첫 시도·수업 피드백·독립 복원의 세 겹 노트와 과목별 기록법을 안내합니다.",
    "부산사하구과외": "부산사하구과외는 구 전체에서 실제 생활 동·재학 학교·우선 학습 과정으로 범위를 좁히는 법을 안내합니다.",
    "양산중부동과외": "양산중부동과외는 주중 회복 칸을 두고 시작 지연·이해 부족·시간 오판을 구분하는 계획법을 안내합니다.",
    "부산망미동과외": "부산망미동과외는 이동 중 회상과 책상 집중학습을 구분하고 질문 쪽지로 수업을 연결하는 법을 안내합니다.",
    "부산오륜동과외": "부산오륜동과외는 확인되지 않은 학교를 추정하지 않고 3일 생활 관찰로 학습 과정을 좁히는 법을 안내합니다.",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\u3000", " ").strip()


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def excerpt(value: str, limit: int = 115) -> str:
    text = strip_tags(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def region_meta_description(slug: str, body: str, limit: int = 80) -> str:
    """Build a complete, page-specific description from the first regional topic heading."""
    if slug in PRIORITY_REGION_META_DESCRIPTIONS:
        return PRIORITY_REGION_META_DESCRIPTIONS[slug]
    match = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    heading = html.unescape(strip_tags(match.group(1))) if match else ""
    theme = heading.split(",", 1)[1].strip() if "," in heading else heading.replace(slug, "").strip(" ,")
    if not theme:
        theme = "학교 일정과 가정학습을 연결하는 지역 학습 기준"

    prefix = f"{slug} 페이지는 "
    ending = " 관점에서 학년별 학습계획과 가정학습 기준을 안내합니다."
    description = f"{prefix}{theme}{ending}"
    if len(description) <= limit:
        return description

    available = max(12, limit - len(f"{prefix}{ending}"))
    shortened = theme[:available].rstrip()
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return f"{prefix}{shortened}{ending}"


def normalize_slug(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().replace("\u3000", ""))


def page_slug(region_slug: str | None, category: str) -> str:
    if not region_slug:
        return "전국과외" if category == "과외" else category
    return f"{region_slug}{category}"
