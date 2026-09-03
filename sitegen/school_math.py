from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations
from pathlib import Path

from sitegen.utils import escape


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PATH = ROOT / "data" / "school_official_homepages.json"
REGION_MAP_PATH = ROOT / "data" / "school_region_map.json"


@dataclass(frozen=True)
class SchoolMathContext:
    slug: str
    general_slug: str
    english_slug: str
    city: str
    district: str
    town: str
    official_name: str
    display_name: str
    homepage: str
    region_math_slug: str
    theme_index: int
    method_index: int


THEMES = (
    {
        "label": "조건 번역과 첫 식",
        "problem": "문제의 문장을 읽고도 주어진 값과 구할 값을 분리하지 못해 풀이 첫 줄이 늦어지는 상태",
        "evidence": "주어진 조건, 구할 값, 사용할 정의, 첫 식을 네 칸에 적은 조건 번역표",
        "action": "숫자를 대입하기 전에 조건을 기호와 짧은 문장으로 각각 한 번 표현하고 두 표현이 같은 뜻인지 확인하는 연습",
        "output": "정답 여부와 별개로 어떤 조건에서 첫 식을 선택했는지 설명하는 풀이 시작 기록",
    },
    {
        "label": "개념 정의와 반례",
        "problem": "공식의 모양은 기억하지만 적용 조건과 적용할 수 없는 경우를 구분하지 못하는 상태",
        "evidence": "개념 정의, 성립 조건, 맞는 예, 틀린 반례를 한 줄씩 연결한 개념 경계표",
        "action": "정의를 자신의 말로 설명한 뒤 조건 하나를 바꾸어 반례를 만들고 공식이 더 이상 성립하지 않는 이유를 적는 연습",
        "output": "공식을 외운 횟수보다 개념의 사용 범위를 스스로 설명할 수 있는 정의 복원 기록",
    },
    {
        "label": "풀이 첫 줄 선택",
        "problem": "해설을 보면 이해하지만 혼자 풀 때 어떤 개념으로 시작할지 결정하지 못하는 상태",
        "evidence": "문제의 핵심 조건, 후보 개념 두 개, 선택한 첫 줄, 선택하지 않은 이유를 남긴 시작 판단표",
        "action": "완전한 풀이를 쓰기 전에 서로 다른 첫 줄 두 개를 제안하고 더 적은 가정으로 이어지는 쪽을 선택하는 연습",
        "output": "도움을 받기 전과 후의 첫 줄이 어떻게 달라졌는지 비교할 수 있는 시작 전략 기록",
    },
    {
        "label": "식 변형의 근거",
        "problem": "식을 빠르게 정리하려다 등식의 성질이나 부호 변화의 근거를 놓쳐 중간 계산이 끊기는 상태",
        "evidence": "변형 전 식, 사용한 성질, 변형 후 식, 역으로 확인한 결과를 나란히 둔 식 변형표",
        "action": "한 줄에 한 번의 변형만 쓰고 각 줄 옆에 이항·인수분해·치환처럼 사용한 근거를 짧게 표시하는 연습",
        "output": "계산 실수라는 한 단어 대신 오류가 처음 발생한 변형 줄을 찾을 수 있는 과정 기록",
    },
    {
        "label": "그래프·표·식 전환",
        "problem": "식으로는 풀 수 있지만 그래프나 표로 표현이 바뀌면 같은 관계를 알아보지 못하는 상태",
        "evidence": "식의 계수와 조건이 그래프의 위치·기울기·교점 또는 표의 변화에 어떻게 대응하는지 적은 표현 전환표",
        "action": "한 문제를 식, 간단한 표, 스케치 세 방식으로 나타낸 뒤 각 표현에서 바로 보이는 정보와 숨은 정보를 구분하는 연습",
        "output": "표현이 바뀌어도 같은 개념을 찾아낸 근거가 남는 다중 표현 기록",
    },
    {
        "label": "계산 오류의 최초 지점",
        "problem": "마지막 답만 고쳐 쓰고 처음 틀린 계산 줄과 그 뒤에 따라온 오류를 구분하지 못하는 상태",
        "evidence": "마지막으로 맞았던 줄, 최초 오류, 오류 유형, 다시 확인할 날짜를 표시한 계산 추적표",
        "action": "해설을 보기 전에 끝에서 거꾸로 대입하거나 검산해 모순이 처음 나타나는 줄을 찾는 연습",
        "output": "부호·분배·약분·대입 가운데 반복되는 계산 습관을 확인할 수 있는 오류 경로 기록",
    },
    {
        "label": "함수 변화와 대응",
        "problem": "함수식을 개별 공식으로 외워 입력 변화와 출력 변화의 관계를 문제 조건에 연결하지 못하는 상태",
        "evidence": "정의역의 선택, 대응 규칙, 변화량, 그래프에서 확인한 위치를 연결한 함수 대응표",
        "action": "특정 값 하나의 계산 뒤에 값을 조금 바꾸었을 때 결과가 어떻게 달라지는지 말하고 그래프로 다시 확인하는 연습",
        "output": "함수 문제에서 무엇이 변하고 무엇이 고정되는지를 분리한 변화 관찰 기록",
    },
    {
        "label": "수열 규칙과 재현",
        "problem": "앞의 몇 항을 계산하고도 항 사이 관계와 일반항·점화식의 역할을 구분하지 못하는 상태",
        "evidence": "처음 항, 이웃한 항의 관계, 일반화한 식, 다른 항으로 검증한 결과를 적은 규칙 재현표",
        "action": "항을 세 개 이상 직접 만든 뒤 말로 설명한 규칙을 식으로 바꾸고 충분히 뒤의 항에서도 맞는지 확인하는 연습",
        "output": "공식 대입이 아니라 규칙을 발견하고 검증한 순서를 보여 주는 수열 추론 기록",
    },
    {
        "label": "경우 분류와 누락 점검",
        "problem": "확률과 경우의 수에서 기준 없이 나열해 중복과 누락을 동시에 발견하지 못하는 상태",
        "evidence": "분류 기준, 각 경우의 범위, 겹치는 조건, 전체 개수를 확인한 경우 분류표",
        "action": "무엇을 먼저 고정할지 정한 뒤 표나 나무그림으로 경우를 나누고 다른 분류 기준으로 총수를 다시 확인하는 연습",
        "output": "답의 개수보다 빠진 경우와 중복된 경우를 설명할 수 있는 분류 검증 기록",
    },
    {
        "label": "도형 조건과 보조선",
        "problem": "그림의 모양에 의존해 실제로 주어진 조건과 추정한 관계를 구분하지 못하는 상태",
        "evidence": "주어진 길이·각·평행 관계, 사용할 정리, 추가한 보조선의 목적을 구분한 도형 조건표",
        "action": "그림을 비율이 다르게 다시 그린 뒤에도 유지되는 조건만 표시하고 보조선마다 얻으려는 관계를 한 문장으로 적는 연습",
        "output": "시각적 추측과 논리적으로 확인한 사실을 분리할 수 있는 도형 근거 기록",
    },
    {
        "label": "변화율과 누적량",
        "problem": "미분과 적분 공식을 적용하면서 순간 변화·구간 변화·누적의 의미를 문장과 그래프로 연결하지 못하는 상태",
        "evidence": "문제의 단위, 변화하는 양, 기준 구간, 그래프의 기울기나 넓이를 연결한 변화량 해석표",
        "action": "식을 계산하기 전 결과의 부호와 대략적인 크기를 예상하고 계산 뒤 그래프와 단위로 타당성을 확인하는 연습",
        "output": "계산 결과가 문제 상황에서 무엇을 뜻하는지 설명하는 변화율 검증 기록",
    },
    {
        "label": "자료 해석과 대표값",
        "problem": "평균이나 분산을 계산하고도 자료의 분포와 이상값이 결론에 미치는 영향을 설명하지 못하는 상태",
        "evidence": "자료의 범위, 중심, 퍼짐, 이상값, 선택한 대표값의 이유를 함께 적은 자료 판단표",
        "action": "같은 자료를 표와 그래프로 확인하고 값 하나를 바꾸었을 때 평균·중앙값·산포가 어떻게 달라지는지 비교하는 연습",
        "output": "계산한 통계량과 해석 문장을 서로 대조할 수 있는 자료 설명 기록",
    },
    {
        "label": "서술형 논리 연결",
        "problem": "답은 맞지만 중간 근거가 생략되어 다른 사람이 풀이의 논리를 따라가기 어려운 상태",
        "evidence": "가정, 사용한 정의나 정리, 계산 결과, 결론을 순서대로 표시한 서술형 논리표",
        "action": "각 식 사이에 왜 다음 줄로 갈 수 있는지 짧은 연결 문장을 넣고 불필요한 계산은 별도로 분리하는 연습",
        "output": "채점자가 확인할 근거와 학생이 생략한 판단을 구분하는 서술형 교정 기록",
    },
    {
        "label": "실전 시간과 보류 판단",
        "problem": "어려운 한 문제에 시간을 모두 사용해 해결 가능한 뒤 문항의 검토 기회를 잃는 상태",
        "evidence": "유형별 실제 시간, 보류 시점, 다시 돌아온 순서, 최종 판단을 적은 실전 운영표",
        "action": "정해 둔 시간 안에 첫 식이나 핵심 조건이 보이지 않으면 표시하고 넘어간 뒤 확보한 문제부터 검토하는 연습",
        "output": "점수만이 아니라 보류와 재진입 결정의 적절성을 확인할 수 있는 시간 선택 기록",
    },
)


METHODS = (
    {"label": "3일 풀이 복원", "start": "첫날에는 풀이를 보며 오류 위치를 표시하고, 둘째 날에는 첫 줄만 남겨 다시 풀며, 셋째 날에는 조건을 바꾼 문제에 같은 판단을 적용합니다", "record": "세 번의 풀이에서 도움을 받은 줄과 혼자 이어 간 줄을 다른 기호로 남깁니다", "review": "셋째 날에도 같은 위치에서 멈추면 문제 수보다 선행 개념과 첫 판단을 다시 확인합니다"},
    {"label": "빈 풀이 재현", "start": "정답을 확인한 뒤 풀이를 덮고 빈 종이에 조건, 첫 식, 핵심 변형, 검산 순서만 다시 씁니다", "record": "기억으로 재현한 내용과 원문을 보고 보완한 내용을 지우지 않고 두 색으로 구분합니다", "review": "하루 뒤 핵심 네 단계가 순서대로 재현될 때 해당 문제를 완료로 처리합니다"},
    {"label": "오류 코드 장부", "start": "오답을 개념·조건·전략·계산·시간의 다섯 코드 가운데 하나로 먼저 분류합니다", "record": "코드 옆에는 틀린 이유보다 다음에 가장 먼저 확인할 신호를 한 문장으로 적습니다", "review": "같은 코드가 세 번 나오면 새 유형을 추가하지 않고 판단 순서를 짧게 다시 연습합니다"},
    {"label": "학교자료 우선표", "start": "교과서와 학교 학습지, 평가 안내를 먼저 모으고 개인 문제집은 빈틈을 확인하는 순서로 배치합니다", "record": "자료마다 현재 시험 범위인지, 완료 기준이 무엇인지, 다시 볼 날짜가 언제인지 표시합니다", "review": "시험 뒤에는 많이 푼 자료보다 실제 판단 근거가 된 자료를 남겨 다음 계획에 반영합니다"},
    {"label": "24·72시간 확인", "start": "수업 뒤 하루 안에는 핵심 개념과 첫 식을 회상하고 사흘 안에는 조건을 바꾼 문제로 적용합니다", "record": "첫날의 기억, 사흘 뒤 적용, 일주일 뒤 재현을 한 줄씩 이어 적습니다", "review": "잊은 항목은 처음부터 반복하지 않고 설명이 끊긴 단계로 돌아가 복습 간격을 다시 정합니다"},
    {"label": "두 풀이 비교", "start": "같은 문제를 식 중심 풀이와 그래프·도형 중심 풀이로 나누어 공통 조건과 다른 선택을 찾습니다", "record": "풀이 길이보다 각 방식에서 먼저 보인 조건과 검산이 쉬웠던 지점을 비교표에 남깁니다", "review": "새 문제에서 두 방식 가운데 하나를 스스로 선택하고 그 이유를 말할 수 있는지 확인합니다"},
    {"label": "다음 한 줄 설명", "start": "각 계산 줄을 쓰기 전에 다음에 할 행동과 사용할 근거를 먼저 소리 내어 설명합니다", "record": "설명이 막힌 줄, 계산만 가능했던 줄, 근거까지 설명한 줄을 서로 다른 표시로 구분합니다", "review": "답을 맞혀도 다음 한 줄의 이유를 설명하지 못하면 완료 대신 재확인 항목으로 남깁니다"},
    {"label": "시간 상한 기록", "start": "유형별 목표 시간을 정하고 시간이 지나면 현재까지 확인한 조건과 막힌 위치를 표시한 뒤 보류합니다", "record": "전체 시간뿐 아니라 읽기·첫 식·계산·검토에 사용한 시간을 짧게 나누어 적습니다", "review": "느린 원인이 개념인지 계산인지 판단한 뒤에만 다음 주 목표 시간을 조정합니다"},
    {"label": "역방향 검산", "start": "답에서 출발해 원래 조건에 대입하거나 결론에서 가정으로 거꾸로 확인합니다", "record": "정방향 풀이와 역방향 확인이 처음 어긋난 줄을 표시해 오류 범위를 좁힙니다", "review": "검산에서 발견한 오류가 다음 문제의 첫 확인 행동으로 이어지는지 주말에 점검합니다"},
    {"label": "질문 한 줄 기록", "start": "풀이가 멈춘 순간의 질문을 해설로 덮지 않고 현재 알고 있는 것과 필요한 도움으로 나누어 적습니다", "record": "질문 옆에 혼자 시도한 방법과 선생님에게 확인할 한 가지 조건을 구분해 남깁니다", "review": "수업 끝에는 답을 얻었는지보다 다음에는 어떤 근거를 먼저 찾을지 다시 씁니다"},
    {"label": "난도 교대 계획", "start": "집중 가능한 날에는 새 개념과 복합 문제를, 피로한 날에는 정의 회상과 짧은 오답 복원을 배치합니다", "record": "요일별 시작 시각과 집중 시간을 과제 난도, 완료한 판단 단계와 함께 비교합니다", "review": "계획 실패를 의지로 해석하지 않고 시간대와 과제 크기의 조합을 바꿉니다"},
)


SECTION_PURPOSES = (
    "검색 의도와 학교 자료의 경계",
    "현재 풀이를 진단하는 증거",
    "고1·고2·고3 학년별 경로",
    "개념과 계산의 연결",
    "함수·도형·자료 표현 전환",
    "내신과 서술형 준비",
    "모의고사와 실전 운영",
    "주간 일정과 복습 간격",
    "합성 사례로 보는 수정 과정",
    "과외 방식 비교 기준",
    "학부모 피드백과 기록",
    "공식 정보와 관련 페이지",
)


def _load_json(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}")
    return [row for row in data if isinstance(row, dict)]


def _clean_html(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _first_sentence(value: str) -> str:
    match = re.match(r"(.+?[.!?])(?:\s|$)", value.strip())
    return match.group(1) if match else value.strip()


def _has_final_consonant(value: str) -> tuple[bool, bool]:
    for char in reversed(str(value).strip()):
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            final_index = code % 28
            return final_index != 0, final_index == 8
    return False, False


def _object(value: str) -> str:
    has_final, _ = _has_final_consonant(value)
    return f"{value}{'을' if has_final else '를'}"


def _subject(value: str) -> str:
    has_final, _ = _has_final_consonant(value)
    return f"{value}{'이' if has_final else '가'}"


def _topic(value: str) -> str:
    has_final, _ = _has_final_consonant(value)
    return f"{value}{'은' if has_final else '는'}"


def _direction(value: str) -> str:
    has_final, is_rieul = _has_final_consonant(value)
    return f"{value}{'으로' if has_final and not is_rieul else '로'}"


@lru_cache(maxsize=1)
def school_math_contexts() -> dict[str, SchoolMathContext]:
    official_rows = _load_json(OFFICIAL_PATH)
    region_rows = {str(row.get("keyword") or ""): row for row in _load_json(REGION_MAP_PATH)}
    ordered = sorted(official_rows, key=lambda row: str(row.get("page") or ""))
    contexts: dict[str, SchoolMathContext] = {}
    for index, row in enumerate(ordered):
        general_slug = str(row.get("page") or "")
        if not general_slug.endswith("과외"):
            continue
        base = general_slug.removesuffix("과외")
        slug = f"{base}수학과외"
        region = region_rows.get(slug, {})
        city = str(row.get("city") or region.get("city") or "")
        town = str(region.get("town") or "")
        candidate = f"{city}{town}수학과외" if town else f"{city}수학과외"
        region_math_slug = candidate if (ROOT / "output" / candidate / "index.html").exists() else f"{city}수학과외"
        display = str(region.get("school_display_name") or base.removeprefix(city))
        contexts[slug] = SchoolMathContext(
            slug=slug,
            general_slug=general_slug,
            english_slug=f"{base}영어과외",
            city=city,
            district=str(region.get("district") or ""),
            town=town,
            official_name=str(row.get("official_school_name") or region.get("official_school_name") or display),
            display_name=display,
            homepage=str(row.get("homepage") or ""),
            region_math_slug=region_math_slug,
            theme_index=index // len(METHODS),
            method_index=index % len(METHODS),
        )
    return contexts


def is_school_math_slug(slug: str) -> bool:
    return slug in school_math_contexts()


def _source_details(source_body: str, context: SchoolMathContext) -> dict[str, str]:
    headings = [_clean_html(item) for item in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", source_body, flags=re.I | re.S)]
    paragraphs = [_clean_html(item) for item in re.findall(r"<p[^>]*>(.*?)</p>", source_body, flags=re.I | re.S)]
    focus = "수학 조건 해석"
    first_heading = headings[0] if headings else ""
    match = re.search(r"학생을 위한 (.+?) 수학 학습", first_heading)
    if match:
        focus = match.group(1).strip()
    basic = _first_sentence(next((item for item in paragraphs if context.official_name in item and "에 위치한" in item), ""))
    stats = _first_sentence(next((item for item in paragraphs if "2025년 4월 1일 교육통계" in item), ""))
    grades = _first_sentence(next((item for item in paragraphs if "학년별 학생 수" in item), ""))
    if not basic:
        place = " ".join(item for item in (context.city, context.district, context.town) if item)
        basic = f"{context.official_name}의 학교 유형과 위치는 공식 홈페이지와 교육통계에서 확인해야 하며, {place} 표기는 지역 탐색을 위한 범위입니다."
    if not stats:
        stats = "학생 수와 학급 수는 기준일에 따라 달라질 수 있으므로 최신 교육통계와 학교 안내를 함께 확인합니다."
    if not grades:
        grades = "학년별 규모만으로 수학 수준을 판단하지 않고 학생이 가진 교과서·학습지와 현재 풀이를 직접 확인합니다."
    return {"source_focus": focus, "basic": basic, "stats": stats, "grades": grades}


def school_math_focus(slug: str, source_body: str = "") -> str:
    context = school_math_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    source_focus = _source_details(source_body, context)["source_focus"]
    return f"{source_focus}·{theme['label']}·{method['label']}"


def build_school_math_meta(slug: str, source_body: str = "") -> tuple[str, str]:
    context = school_math_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    source_focus = _source_details(source_body, context)["source_focus"]
    title = f"{slug} | {source_focus}·{method['label']} 점검"
    description = (
        f"{slug}는 {context.official_name}의 공식 자료를 확인하며 {source_focus} 진단, "
        f"{theme['label']}, {method['label']} 순서로 고1·고2·고3 수학 내신과 오답 복원 과정을 정리합니다."
    )
    return title, description


@lru_cache(maxsize=1)
def _variant_option_map() -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    slugs = sorted(school_math_contexts())
    theme_sets = list(combinations(range(len(THEMES)), 3))
    method_sets = list(combinations(range(len(METHODS)), 3))
    theme_sets.sort(key=lambda values: hashlib.sha256(f"school-math-theme:{values}".encode()).digest())
    method_sets.sort(key=lambda values: hashlib.sha256(f"school-math-method:{values}".encode()).digest())
    orders = list(permutations(range(3)))
    result: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for index, slug in enumerate(slugs):
        digest = hashlib.sha256(f"school-math-order:{slug}".encode("utf-8")).digest()
        theme_order = orders[digest[0] % len(orders)]
        method_order = orders[digest[1] % len(orders)]
        themes = theme_sets[index]
        methods = method_sets[index]
        result[slug] = (
            tuple(themes[position] for position in theme_order),
            tuple(methods[position] for position in method_order),
        )
    return result


def _variant(context: SchoolMathContext, section_index: int) -> tuple[dict[str, str], dict[str, str], str]:
    theme_options, method_options = _variant_option_map()[context.slug]
    theme = THEMES[theme_options[section_index % len(theme_options)]]
    method = METHODS[method_options[(section_index + context.theme_index) % len(method_options)]]
    return theme, method, f"{theme['label']}·{method['label']}"


def _section_heading(context: SchoolMathContext, section_index: int, label: str) -> str:
    _, _, focus = _variant(context, section_index)
    return f"{context.slug}: {label} — {focus}"


def _standard_section(context: SchoolMathContext, section_index: int, label: str, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-math-section school-math-section-{section_index + 1}" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, label))}</h2>
<p>{slug}의 이번 점검은 <strong>{escape(focus)}</strong>입니다. {school} 학생이라는 이유만으로 시험 난도나 출제 유형을 추정하지 않고, 학생이 실제로 받은 교과서·학습지·평가 안내에서 현재 범위를 먼저 구분합니다. {_topic(source_focus)} 이 과정을 설명하기 위한 진단 예시이며 학교의 고정된 교육과정이나 출제 특성을 뜻하지 않습니다.</p>
<p>{school} 수학 학습에서는 {escape(_object(theme['evidence']))} 먼저 만듭니다. {escape(method['start'])}. {slug} 계획은 문제 수보다 학생이 어느 조건에서 멈추고 어떤 근거로 다음 줄을 선택했는지 확인하며, 확인할 수 없는 성적 향상이나 학교별 우열을 제시하지 않습니다.</p>
<p>{escape(_object(focus))} 실제 행동으로 옮길 때는 {escape(_object(theme['action']))} 사용합니다. {escape(method['record'])}. 이렇게 남긴 자료는 {escape(theme['output'])}으로 이어지고, {school}의 일정이나 범위가 바뀌면 분량보다 날짜와 우선순위를 먼저 조정하는 근거가 됩니다.</p>
<p>{slug}의 완료 기준은 한 번 맞힌 답이 아닙니다. {escape(method['review'])}. 학생이 설명하지 못한 줄은 새 문제로 덮지 않고 다음 질문으로 옮기며, {escape(focus)} 점검 자료가 쌓이면 내신·수행평가·모의고사에서 같은 오류가 반복되는지도 구분할 수 있습니다.</p>
</section>"""


def _grade_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-math-grade" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '고1·고2·고3 학년별 경로'))}</h2>
<p>{slug}의 학년 계획은 같은 교재의 양만 늘리는 방식이 아닙니다. {school}의 현재 학년과 실제 학교 자료를 확인한 뒤 <strong>{escape(focus)}</strong>을 공통 기준으로 사용하되, 고1은 개념 언어와 첫 식, 고2는 여러 표현과 선택과목의 연결, 고3은 실전 선택과 취약 단원 유지에 서로 다른 비중을 둡니다.</p>
<table>
<thead><tr><th>학년</th><th>{escape(source_focus)} 출발 행동</th><th>주간 확인 증거</th><th>피해야 할 판단</th></tr></thead>
<tbody>
<tr><td>고1</td><td>{slug} 학생은 정의와 조건을 말한 뒤 교과서 예제의 첫 줄을 자료 없이 다시 씁니다.</td><td>{escape(theme['evidence'])}</td><td>중학교 점수만으로 고등 수학의 현재 수준을 고정하지 않습니다.</td></tr>
<tr><td>고2</td><td>{school} 자료에서 식·그래프·표 가운데 바뀐 표현을 찾고 같은 개념의 적용 차이를 설명합니다.</td><td>{escape(method['record'])}</td><td>내신 기간이라는 이유로 누적 오답과 선택과목 기초를 완전히 멈추지 않습니다.</td></tr>
<tr><td>고3</td><td>{slug} 실전 기록에 문항별 시간, 보류 시점, 다시 돌아온 근거를 함께 남깁니다.</td><td>{escape(method['review'])}</td><td>어려운 한 문항의 해결을 전체 시간 운영보다 앞세우지 않습니다.</td></tr>
</tbody>
</table>
<p>{school}의 시험일, 선택과목, 수행평가 형식은 학기와 담당에 따라 달라질 수 있습니다. 따라서 {slug}의 표는 확정된 학교 정보가 아니라 공식 공지와 학생 안내를 확인한 뒤 수정하는 학년별 점검 틀로 사용합니다. {_object(source_focus)} 다룰 때도 현재 진도와 선행 여부를 먼저 확인합니다.</p>
</section>"""


def _schedule_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-math-schedule" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '주간 일정과 복습 간격'))}</h2>
<p>{slug} 주간표는 매일 같은 문제 수를 요구하지 않습니다. {school} 학생의 실제 귀가 시각과 제출 마감을 적은 뒤 <strong>{escape(_object(focus))}</strong> 기준으로 집중일·유지일·회복일을 나눕니다. {escape(_subject(theme['problem']))} 반복되는 날에는 의지 부족으로 결론 내리기 전에 시작 시각, 선행 개념, 과제 크기의 조합을 먼저 바꿉니다.</p>
<table>
<thead><tr><th>구간</th><th>{escape(source_focus)} 행동</th><th>{escape(focus)} 기록</th></tr></thead>
<tbody>
<tr><td>수업 당일</td><td>{escape(method['start'])}.</td><td>{slug} 첫 풀이에서 비어 있던 조건과 도움받은 줄을 지우지 않습니다.</td></tr>
<tr><td>24시간 안</td><td>{escape(theme['action'])}.</td><td>{school} 자료를 보지 않고 재현한 범위와 확인 뒤 보완한 범위를 구분합니다.</td></tr>
<tr><td>72시간 안</td><td>{escape(method['review'])}.</td><td>{slug} 다음 계획에 넣을 한 가지 판단 행동을 완료 문제 수 대신 적습니다.</td></tr>
</tbody>
</table>
<p>{school} 일정이 늦게 공지되거나 다른 과목의 마감과 겹치면 {slug} 표의 순서를 바꿉니다. 계획을 지우고 새로 쓰기보다 무엇을 줄였고 왜 옮겼는지 남겨야 {escape(_subject(focus))} 구호가 아니라 다음 주 분량을 결정하는 자료가 됩니다. {escape(source_focus)} 예시는 실제 시험 범위와 다르면 현재 학교 자료로 교체합니다.</p>
</section>"""


def _case_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    grade = ("고1", "고2", "고3")[(context.theme_index + context.method_index) % 3]
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-math-case" data-case-model="composite" data-case-grade="{grade}" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '합성 사례로 보는 수정 과정'))}</h2>
<p><strong>아래 내용은 {school}의 실제 학생·성적·수업 결과가 아니라 여러 학습 장면을 합쳐 만든 가상 사례입니다.</strong> {slug}의 {grade} 학생이 {escape(_object(theme['problem']))} 겪는다고 가정합니다. 처음에는 {escape(source_focus)} 문제의 답만 고쳤지만 실패 원인이 보이지 않았고, 이후 <strong>{escape(_object(focus))}</strong> 적용해 조건·판단·계산·검산을 분리했습니다.</p>
<table>
<thead><tr><th>관찰 시점</th><th>{slug} 가상 학생의 행동</th><th>수정 기준</th></tr></thead>
<tbody>
<tr><td>처음</td><td>정답을 본 뒤 자신의 첫 판단과 마지막으로 맞았던 계산 줄을 지웠습니다.</td><td>{escape(theme['evidence'])}</td></tr>
<tr><td>일주일</td><td>{escape(method['record'])}.</td><td>{escape(theme['action'])}</td></tr>
<tr><td>재점검</td><td>{escape(method['review'])}.</td><td>{escape(theme['output'])}</td></tr>
</tbody>
</table>
<ol>
<li>{school}에서 받은 실제 자료와 이 가상 사례가 다른 부분을 학생이 먼저 표시합니다.</li>
<li>{slug} 기록에는 점수 예상이 아니라 조건·첫 식·변형·검산 가운데 바꿀 한 단계를 적습니다.</li>
<li>{escape(_object(focus))} 일주일 적용해도 변화가 없으면 학생 탓으로 돌리지 않고 진단 가설과 과제 크기를 바꿉니다.</li>
</ol>
<p>이 사례는 {school}의 출제 방식이나 특정 학생의 성과를 설명하지 않습니다. {slug}에서 보여 주려는 것은 {escape(_object(source_focus))} 소재로 관찰 가능한 증거를 만들고, 그 증거가 없을 때 {escape(_direction(focus))} 계획을 수정하는 과정입니다.</p>
</section>"""


def _decision_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-math-decision" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '과외 방식 비교 기준'))}</h2>
<p>{slug} 과외를 비교할 때는 학교 이름을 안다는 말보다 <strong>{escape(_object(focus))}</strong> 어떻게 관찰하고 수정할지 답을 들어야 합니다. {school}의 실제 자료를 학생이 제공했을 때 수업 전후에 어떤 풀이가 남는지, 설명을 들은 뒤 {escape(source_focus)} 판단을 혼자 재현하는 간격을 어떻게 확인하는지 질문합니다.</p>
<table>
<thead><tr><th>비교 질문</th><th>확인할 답변</th><th>{slug} 경계 신호</th></tr></thead>
<tbody>
<tr><td>{escape(_topic(theme['problem']))} 어떻게 구분하나요?</td><td>{escape(theme['evidence'])}처럼 학생 풀이에서 확인 가능한 증거가 제시되는지 봅니다.</td><td>상담 전부터 점수 상승이나 학교별 출제 경향을 단정하는 답변입니다.</td></tr>
<tr><td>수업 뒤 혼자 할 행동은 무엇인가요?</td><td>{escape(method['start'])}처럼 학생이 재현할 순서가 있는지 봅니다.</td><td>교재 이름과 숙제량만 있고 완료 기준이 없는 답변입니다.</td></tr>
<tr><td>계획이 실패하면 무엇을 바꾸나요?</td><td>{escape(method['review'])}처럼 수정 시점과 판단 기준이 있는지 봅니다.</td><td>{school} 학생이라는 이유만으로 같은 분량을 계속 요구하는 답변입니다.</td></tr>
</tbody>
</table>
<p>대면과 온라인 가운데 어느 방식이 맞는지도 {slug}에서 미리 단정할 수 없습니다. 같은 짧은 {escape(source_focus)} 과제를 각각 한 번 수행해 준비 시간, 질문 시점, 필기 공유, 수업 후 독립 복원을 비교하십시오. {escape(focus)} 기록이 온전히 남고 학생이 스스로 다음 줄을 찾을 수 있는 방식을 선택하는 편이 안전합니다.</p>
</section>"""


def _feedback_tracker_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    _, _, focus = _variant(context, section_index)
    phases = ("조건관찰", "풀이적용", "표현비교", "독립복원")
    rows: list[str] = []
    for day in range(1, 29):
        theme, method, daily_focus = _variant(context, section_index + day)
        phase = phases[(day - 1) // 7]
        rows.append(
            "<tr>"
            f"<td>{escape(context.slug)}·{day}일</td>"
            f"<td>{escape(source_focus.replace(' ', '·'))} {escape(theme['label'].replace(' ', '·'))} {phase}·시작</td>"
            f"<td>{escape(context.official_name)} {escape(method['label'].replace(' ', '·'))} 근거·기록</td>"
            f"<td>{escape(focus.replace(' ', '·'))} {escape(daily_focus.replace(' ', '·'))} {phase}·확인</td>"
            "</tr>"
        )
    return f"""
<section class="school-math-feedback-tracker" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '학부모 피드백과 28일 풀이 기록표'))}</h2>
<p>{escape(context.slug)}의 학부모 피드백은 매일 정답 수나 진도만 확인하기보다 <strong>{escape(focus)}</strong>의 증거를 주 1회 함께 읽는 방식으로 진행합니다. {escape(context.official_name)} 학생이 직접 적은 조건과 수정 행동을 먼저 듣고, 보호자는 완료되지 않은 이유를 개념·전략·계산·시간 가운데 어느 쪽인지 질문합니다.</p>
<ul>
<li>{escape(context.slug)} 기록에는 정확한 집 주소나 불필요한 개인정보를 적지 않습니다.</li>
<li>{escape(context.official_name)} 이름과 학년은 학교 자료를 구분하는 데 필요한 범위에서만 사용합니다.</li>
<li>{escape(source_focus)} 상담에는 최근 학교 자료와 반복되는 풀이 오류만 먼저 준비합니다.</li>
<li>{escape(context.slug)} 피드백은 유지할 판단 하나와 바꿀 행동 하나로 끝냅니다.</li>
<li>{escape(context.official_name)} 일정이 바뀌면 문제 수보다 마감과 복습 순서를 먼저 고칩니다.</li>
<li>{escape(focus)} 기록은 보관 목적과 공유 범위를 확인한 뒤 전달합니다.</li>
</ul>
<p>아래 표는 {escape(context.slug)}에서 4주 동안 조건관찰·풀이적용·표현비교·독립복원을 구분하기 위한 짧은 기록지입니다. 하루에 긴 공부 일지를 쓰는 대신 해당되는 행동 한 줄만 남깁니다. {escape(context.official_name)}의 실제 시험 기간에는 학교 자료를 우선하고 표의 날짜와 순서를 바꾸어 사용합니다.</p>
<table class="school-math-28day-tracker">
<thead><tr><th>날짜</th><th>오늘의 시작</th><th>남길 증거</th><th>주간 확인</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p>{escape(context.slug)}의 28일 표는 학습 성과를 보장하는 프로그램이 아닙니다. 첫째 주와 넷째 주에 같은 짧은 {escape(source_focus)} 과제를 수행해 첫 식, 근거 설명, 혼자 검산한 범위를 비교하는 도구입니다. {escape(focus)} 변화가 보이지 않으면 학생을 압박하기보다 과제 크기와 도움 시점을 먼저 수정합니다.</p>
</section>"""


def _links_section(context: SchoolMathContext, section_index: int, source_focus: str) -> str:
    _, _, focus = _variant(context, section_index)
    place = " ".join(item for item in (context.city, context.district, context.town) if item) or context.city
    return f"""
<section class="school-math-links" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '공식 정보와 관련 페이지'))}</h2>
<p>{escape(context.slug)}에서 학교 일정·교육과정·평가 안내처럼 바뀔 수 있는 내용은 <a class="source-link" href="{escape(context.homepage)}" target="_blank" rel="noopener noreferrer external">{escape(context.official_name)} 공식 홈페이지</a>를 직접 확인하십시오. 홈페이지는 학교 정보 확인용 외부 출처이며 EduNext가 해당 학교를 대표하거나 학교와 제휴했다는 뜻이 아닙니다. {escape(place)} 표기는 지역 매핑을 위한 범위일 뿐 통학 시간이나 배정을 보장하지 않습니다.</p>
<p>{escape(context.slug)}와 같은 학교의 전체 학습 범위는 <a href="/{escape(context.general_slug)}/">{escape(context.general_slug)}</a>, 영어 과목 비교는 <a href="/{escape(context.english_slug)}/">{escape(context.english_slug)}</a>에서 확인할 수 있습니다. 학교 한 곳을 넘어 생활권 수학 정보를 보려면 <a href="/{escape(context.region_math_slug)}/">{escape(context.region_math_slug)}</a>로 이동하십시오. 본문 링크는 이 세 탐색 목적과 공식 홈페이지에만 제한해 키워드 나열을 피했습니다.</p>
<p>{escape(context.official_name)}의 최신 자료와 학생이 실제로 받은 안내가 다르면 현재 학생 자료를 먼저 확인합니다. {_topic(source_focus)} 학교 정보를 추정하는 문구가 아니라, 확인된 자료를 바탕으로 {escape(_object(focus))} 적용하는 이번 페이지의 고유한 점검 소재입니다.</p>
</section>"""


def _faq_section(context: SchoolMathContext, source_body: str) -> str:
    details = _source_details(source_body, context)
    source_focus = details["source_focus"]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    primary = f"{source_focus}·{theme['label']}·{method['label']}"
    questions = (
        (
            f"{context.slug}에서 {_object(primary)} 가장 먼저 어떻게 확인하나요?",
            f"{context.official_name}의 실제 교과서·학습지·평가 안내를 먼저 모은 뒤 {_object(theme['evidence'])} 만드십시오. {method['start']}. 처음부터 문제 수를 늘리기보다 학생이 멈춘 조건과 마지막으로 확신한 줄을 남기고, 일주일 뒤 같은 판단을 혼자 재현하는지 확인해야 {context.slug}의 출발점이 구체적으로 보입니다.",
        ),
        (
            f"{context.slug}의 {primary} 기준에서 학교 홈페이지는 왜 확인하나요?",
            f"{context.official_name}의 시험일·행사·교육과정과 평가 안내는 시기에 따라 바뀔 수 있기 때문입니다. EduNext 본문은 확정된 학교 일정을 대신하지 않으므로 공식 홈페이지와 학생이 받은 안내를 대조해야 합니다. 확인 뒤에는 {method['record']}. 이렇게 해야 {context.slug} 계획이 추정 정보가 아니라 현재 자료를 기준으로 움직입니다.",
        ),
        (
            f"{context.slug}에서 내신과 모의고사를 {_direction(primary)} 함께 준비할 수 있나요?",
            f"역할을 나누면 함께 유지할 수 있습니다. 시험 전에는 {context.official_name}에서 실제로 사용하는 교과서와 학교 자료의 개념·대표 유형·서술형을 우선하고, 짧은 실전 문제는 판단 감각을 유지하는 정도로 둡니다. 시험 뒤에는 {theme['action']}을 적용해 {source_focus}에서 확인한 판단이 낯선 조건에서도 재현되는지 점검합니다.",
        ),
        (
            f"{context.slug}의 {primary} 과외를 비교할 때 무엇을 질문해야 하나요?",
            f"교재와 숙제량보다 {_object(theme['problem'])} 어떤 풀이 증거로 구분할지 물어보십시오. 수업 뒤 학생이 혼자 할 행동, 기록을 다시 보는 날짜, 계획이 실패했을 때 바꿀 기준까지 답에 포함되어야 합니다. {method['review']}. 이 과정이 설명되지 않으면 {context.slug} 학생에게 맞는 방식인지 판단하기 어렵습니다.",
        ),
        (
            f"학부모는 {context.slug}의 {primary} 진행을 어떻게 확인하면 좋나요?",
            f"점수 예상이나 푼 문제 수를 매일 묻기보다 주 1회 첫 식, 반복 오류, 검산 행동을 확인하십시오. 정확한 주소나 불필요한 개인정보를 먼저 공유할 필요는 없습니다. {context.official_name}, 학년, 실제 귀가 시각, 최근 학교 자료와 {theme['output']}만으로 시작하고, {context.slug} 기록의 변화가 없으면 분량보다 진단 가설을 고칩니다.",
        ),
    )
    items = "\n".join(f"<h3>{escape(question)}</h3>\n<p>{escape(answer)}</p>" for question, answer in questions)
    return f"""
<section class="school-math-faq-section" data-faq-focus="{escape(primary)}">
<h2 class="school-math-faq">{escape(context.slug)} {escape(primary)} FAQ</h2>
{items}
</section>"""


def build_school_math_body(slug: str, source_body: str = "") -> str:
    context = school_math_contexts()[slug]
    details = _source_details(source_body, context)
    source_focus = details["source_focus"]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    primary = f"{source_focus}·{theme['label']}·{method['label']}"
    intro = f"""
<section class="school-math-guide" data-content-version="school-math-individual-v1" data-school-math-focus="{escape(primary)}" data-official-school="{escape(context.official_name)}">
<h2>{escape(context.slug)}: {escape(context.official_name)} 수학 학습의 고유 점검 주제</h2>
<p>{escape(context.slug)}는 <strong>{escape(_object(primary))}</strong> 중심으로 구성했습니다. 학교명을 검색한 사용자가 실제로 필요한 것은 확인되지 않은 출제 경향이나 성과 약속이 아니라, {escape(context.official_name)}의 최신 공식 자료와 학생이 가진 수업 자료를 구분하고 현재 풀이 행동을 점검하는 순서입니다. 이 페이지는 학교와 제휴하거나 학교를 대표하지 않으며 특정 학생의 결과를 보장하지 않습니다.</p>
<p>{escape(details['basic'])} {escape(details['stats'])} {escape(details['grades'])} 이 교육통계는 학교 규모를 이해하는 참고자료일 뿐 수학 성취나 학교의 우수성을 판단하는 근거로 사용하지 않습니다.</p>
<p>{escape(context.official_name)} 학생의 수학 계획은 같은 학교 안에서도 학년·선택과목·귀가 시각·현재 이해도에 따라 달라집니다. {escape(context.slug)}에서는 {_object(source_focus)} 하나의 진단 예시로 두고 개념·조건·전략·계산·검산, 내신·수행평가·모의고사를 서로 다른 역할로 나누어 설명합니다.</p>
"""
    sections: list[str] = []
    for index, label in enumerate(SECTION_PURPOSES):
        if index == 2:
            sections.append(_grade_section(context, index, source_focus))
        elif index == 7:
            sections.append(_schedule_section(context, index, source_focus))
        elif index == 8:
            sections.append(_case_section(context, index, source_focus))
        elif index == 9:
            sections.append(_decision_section(context, index, source_focus))
        elif index == 10:
            sections.append(_feedback_tracker_section(context, index, source_focus))
        elif index == 11:
            sections.append(_links_section(context, index, source_focus))
        else:
            sections.append(_standard_section(context, index, label, source_focus))
    return intro + "\n".join(sections) + "\n" + _faq_section(context, source_body) + "\n</section>"


def individualize_school_math_body(body: str, slug: str) -> str:
    if not is_school_math_slug(slug):
        return body
    return build_school_math_body(slug, body)
