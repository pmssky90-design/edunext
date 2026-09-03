from __future__ import annotations

import json
import hashlib
from itertools import combinations, permutations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sitegen.utils import escape


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PATH = ROOT / "data" / "school_official_homepages.json"
REGION_MAP_PATH = ROOT / "data" / "school_region_map.json"


@dataclass(frozen=True)
class SchoolEnglishContext:
    slug: str
    general_slug: str
    math_slug: str
    city: str
    district: str
    town: str
    official_name: str
    display_name: str
    homepage: str
    region_english_slug: str
    theme_index: int
    method_index: int


THEMES = (
    {
        "label": "장문 구조와 시간 배분",
        "problem": "긴 지문을 처음부터 같은 속도로 읽어 후반 문항의 판단 시간이 부족해지는 상태",
        "evidence": "문단별 핵심어, 답의 근거 문장, 문항별 실제 소요 시간을 한 장에 함께 남기는 기록",
        "action": "첫 문단에서 글의 방향을 예상하고 전환어 뒤의 주장과 예시를 구분한 다음 마지막에 근거를 다시 대조하는 연습",
        "output": "읽기 속도보다 먼저 어느 문단에서 판단이 멈췄는지 설명할 수 있는 독해 기록",
    },
    {
        "label": "서술형 문장 재구성",
        "problem": "본문 뜻은 이해하지만 조건에 맞게 어순과 형태를 바꾸는 서술형에서 점수를 잃는 상태",
        "evidence": "원문, 변형 조건, 첫 답안, 교정 이유를 네 칸으로 나누어 비교하는 문장 변형표",
        "action": "주어와 동사를 먼저 고정하고 시제·수·태를 확인한 뒤 수식어를 붙이며 조건 누락을 마지막에 점검하는 연습",
        "output": "정답 문장을 외우는 대신 자신의 첫 문장에서 바뀐 근거를 말할 수 있는 교정 기록",
    },
    {
        "label": "어휘의 문맥 회상",
        "problem": "단어 시험에서는 뜻을 맞히지만 지문 안에서 품사와 의미가 바뀌면 해석이 끊기는 상태",
        "evidence": "표제어, 문장 속 뜻, 함께 쓰인 표현, 다시 확인할 날짜를 연결한 문맥 어휘장",
        "action": "뜻을 가리고 예문을 먼저 읽은 뒤 품사와 문장 역할을 설명하고 비슷한 표현과의 차이를 한 줄로 적는 연습",
        "output": "암기 개수보다 낯선 문장에서 의미를 복원한 과정이 남는 어휘 회상 기록",
    },
    {
        "label": "구문 경계와 핵심절",
        "problem": "문장이 길어질수록 수식어를 주절로 오해하고 해석의 중심을 놓치는 상태",
        "evidence": "주절, 종속절, 수식 범위, 생략 요소를 색이나 괄호로 구분한 구문 분석지",
        "action": "접속사와 관계 표현을 표시하고 핵심 동사를 찾은 뒤 수식 부분을 걷어 내며 문장의 뼈대를 먼저 말하는 연습",
        "output": "해석문만 적지 않고 어느 경계에서 문장 구조를 잘못 잡았는지 보이는 분석 기록",
    },
    {
        "label": "빈칸과 논리 연결",
        "problem": "낯선 어휘에 시선이 머물러 빈칸 앞뒤의 주장 관계와 반복되는 핵심 개념을 놓치는 상태",
        "evidence": "전환어, 반복어, 주장, 예시, 반대 관계를 표시한 뒤 선택지 판단 근거를 적는 논리 지도",
        "action": "빈칸에 들어갈 말을 바로 고르지 않고 문단의 역할을 요약한 뒤 선택지마다 맞지 않는 이유를 지우는 연습",
        "output": "감으로 고른 답과 지문 근거로 남긴 답을 분리해 볼 수 있는 선택지 판단 기록",
    },
    {
        "label": "순서 배열과 문장 삽입",
        "problem": "연결 표현 하나만 보고 문장 순서를 정해 지시어와 정보의 흐름을 함께 확인하지 못하는 상태",
        "evidence": "대명사가 가리키는 대상, 새 정보와 이미 나온 정보, 문단 기능을 연결한 배열 근거표",
        "action": "각 문장의 첫 정보와 끝 정보를 짧게 적고 연결 가능한 쌍을 만든 다음 전체 흐름에서 다시 검증하는 연습",
        "output": "정답 번호보다 문장 사이 연결 근거를 두 가지 이상 제시하는 배열 설명 기록",
    },
    {
        "label": "듣기 선지 예측",
        "problem": "음원을 들은 뒤 선택지를 처음 읽어 핵심 표현을 들었어도 비교 시간이 부족해지는 상태",
        "evidence": "선지 차이, 예상 장면, 실제 들린 표현, 놓친 신호를 순서대로 적는 듣기 점검표",
        "action": "재생 전에 선택지의 차이를 표시하고 첫 청취에서는 상황을, 두 번째 확인에서는 숫자·이유·의도를 검증하는 연습",
        "output": "막연한 듣기 부족이 아니라 예측·청취·선택 가운데 어느 단계가 약한지 드러나는 기록",
    },
    {
        "label": "어법 판단의 설명",
        "problem": "익숙해 보이는 표현을 감각으로 골라 문장 성분과 수식 관계를 설명하지 못하는 상태",
        "evidence": "판단 대상, 적용 규칙, 문장 안 근거, 틀린 선택지가 성립하려면 필요한 조건을 적는 어법 노트",
        "action": "밑줄 주변만 보지 않고 핵심절을 찾은 뒤 태·수·시제·준동사·관계 표현의 적용 순서를 고정하는 연습",
        "output": "맞고 틀림을 넘어 해당 규칙이 이 문장에서 작동하는 이유를 말하는 판단 기록",
    },
    {
        "label": "요약문과 핵심어 압축",
        "problem": "세부 문장은 해석하지만 글 전체를 두 개의 핵심어와 한 문장으로 줄이지 못하는 상태",
        "evidence": "문단별 요지, 반복 개념, 필자의 결론, 버린 세부 내용을 비교하는 요약 초안",
        "action": "각 문단을 짧은 명사구로 바꾸고 공통 개념을 묶은 뒤 원문의 주장 강도와 반대되지 않는지 확인하는 연습",
        "output": "원문을 길게 옮기지 않고 포함한 정보와 제외한 정보를 설명하는 요약 기록",
    },
    {
        "label": "내신 본문 변형 대응",
        "problem": "교과서 본문을 순서대로 외워 문장 위치나 표현이 바뀌면 적용하지 못하는 상태",
        "evidence": "학교에서 실제로 사용한 본문과 자료를 기준으로 핵심 구문·어휘·내용 질문을 분리한 점검지",
        "action": "한 문장을 어순 배열, 빈칸, 어법, 영작 형태로 바꾸고 같은 근거를 다른 형식에서 다시 찾는 연습",
        "output": "암기 여부가 아니라 변형된 질문에서도 동일한 개념을 꺼낼 수 있는 적용 기록",
    },
    {
        "label": "모의고사 오답 원인",
        "problem": "틀린 문항을 정답 해설로 덮어 어휘·구문·논리·시간 중 실제 원인을 구분하지 못하는 상태",
        "evidence": "첫 판단, 근거로 본 문장, 바꾼 이유, 다음에 먼저 확인할 신호를 남기는 오답 분류표",
        "action": "정답을 지운 채 다시 풀고 같은 선택을 하면 해석보다 판단 기준을, 다른 선택을 하면 첫 읽기의 누락을 점검하는 연습",
        "output": "오답 수보다 반복되는 실패 원인과 다음 시도의 행동이 보이는 재풀이 기록",
    },
    {
        "label": "수행평가 발표와 쓰기",
        "problem": "마감 직전에 초안을 만들어 내용 구성과 영어 표현의 교정을 동시에 처리하는 상태",
        "evidence": "요구 조건, 자료 조사, 한글 개요, 영어 초안, 소리 내어 읽기, 최종 교정을 날짜별로 나눈 준비표",
        "action": "평가 안내에서 필수 조건을 먼저 표시하고 개요와 문장 교정을 다른 날에 진행하며 출처와 표현을 마지막에 확인하는 연습",
        "output": "완성본만 남기지 않고 어떤 조건을 언제 확인했는지 추적할 수 있는 수행 과정 기록",
    },
    {
        "label": "고3 실전 선택 전략",
        "problem": "어려운 한 문항에 시간을 모두 써 풀 수 있는 뒤 문항까지 놓치는 상태",
        "evidence": "유형별 목표 시간, 보류 신호, 돌아올 순서, 검토 결과를 함께 적는 실전 운영표",
        "action": "정해 둔 시간 안에 근거가 두 개 이상 보이지 않으면 표시하고 넘어간 뒤 쉬운 문항을 확보하고 다시 돌아오는 연습",
        "output": "점수만 보지 않고 보류와 재검토 결정이 적절했는지 판단하는 실전 선택 기록",
    },
)


METHODS = (
    {"label": "3일 근거표", "start": "월요일에 기준 문장을 고르고 수요일에 근거 없이 다시 설명하며 금요일에 다른 지문에 적용합니다", "record": "날짜마다 처음 막힌 위치와 도움을 받은 문장을 서로 다른 색으로 남깁니다", "review": "세 번째 날에는 맞은 수보다 같은 판단을 혼자 반복할 수 있는지 확인합니다"},
    {"label": "15분 회상 루틴", "start": "귀가 뒤 15분 동안 책을 보지 않고 수업의 핵심어와 문장 구조를 먼저 적습니다", "record": "기억난 내용과 확인 후 보완한 내용을 두 칸으로 나누어 원래 기억을 지우지 않습니다", "review": "주말에는 빈칸이 반복된 영역만 골라 다음 주 첫 복습 순서를 정합니다"},
    {"label": "오류 코드 기록", "start": "오답을 어휘·구문·논리·시간·조건 누락의 다섯 코드 가운데 하나로 분류합니다", "record": "코드 옆에는 틀린 이유가 아니라 다음에 먼저 볼 신호를 한 문장으로 적습니다", "review": "같은 코드가 세 번 나오면 문제 수를 늘리기 전에 판단 순서를 다시 연습합니다"},
    {"label": "학교자료 우선표", "start": "교과서와 학교 학습지, 평가 안내를 먼저 모으고 개인 교재는 빈틈 확인용으로 배치합니다", "record": "자료마다 시험 범위 여부와 완료 기준, 다시 볼 날짜를 표시합니다", "review": "시험 뒤에는 많이 본 자료가 아니라 실제로 근거가 된 자료를 남깁니다"},
    {"label": "주간 마감 역산", "start": "시험일과 제출일부터 거꾸로 세어 초안·교정·재풀이 날짜를 따로 잡습니다", "record": "예상 시간과 실제 시간을 함께 적어 다음 계획의 분량을 조정합니다", "review": "밀린 과제는 모두 이월하지 않고 마감 영향과 학습 목적을 기준으로 다시 선택합니다"},
    {"label": "설명 후 재풀이", "start": "답을 보기 전에 자신의 첫 판단을 말하고 설명을 들은 뒤 같은 유형을 한 번 더 풉니다", "record": "처음 설명과 두 번째 설명에서 달라진 단어를 표시해 이해 변화를 확인합니다", "review": "하루 뒤 자료 없이 같은 절차를 재현할 수 있을 때 해당 항목을 완료로 처리합니다"},
    {"label": "두 지문 비교법", "start": "같은 주제나 구문이 있는 두 지문을 나란히 두고 공통점과 다른 판단 지점을 찾습니다", "record": "표현의 모양보다 문장 역할과 글 안의 기능을 비교표에 남깁니다", "review": "새 지문에서 비교 기준을 스스로 고를 수 있는지 짧게 확인합니다"},
    {"label": "질문 한 줄 장부", "start": "공부를 멈춘 순간의 질문을 해설로 덮지 않고 한 줄 그대로 기록합니다", "record": "질문 옆에 혼자 시도한 방법과 필요한 도움의 종류를 구분해 적습니다", "review": "수업 끝에는 질문이 해결됐는지보다 다음에는 어떤 근거를 먼저 찾을지 다시 씁니다"},
    {"label": "난도 교대 계획", "start": "집중 가능한 날에는 새 개념과 긴 독해를, 피로한 날에는 회상과 짧은 교정을 배치합니다", "record": "요일별 귀가 시각과 시작 지연 시간을 과제 난도와 함께 비교합니다", "review": "계획 실패를 의지로 해석하지 않고 시간대와 과제 크기의 조합을 바꿉니다"},
    {"label": "근거 말하기 점검", "start": "정답을 고른 뒤 지문이나 문장 안의 근거를 소리 내어 한 문장으로 설명합니다", "record": "근거가 없었던 선택과 근거는 있었지만 해석이 틀린 선택을 따로 표시합니다", "review": "보호자는 답을 묻기보다 판단 근거와 다음 확인 순서를 질문합니다"},
    {"label": "24·72시간 복습", "start": "수업 뒤 하루 안에는 핵심을 회상하고 사흘 안에는 조건을 바꾼 문제에 적용합니다", "record": "첫날의 기억, 사흘 뒤의 적용, 일주일 뒤의 재현을 한 줄씩 이어 적습니다", "review": "잊은 항목은 처음부터 반복하지 않고 끊긴 단계로 돌아가 복습 간격을 다시 잡습니다"},
)


SECTION_PURPOSES = (
    "검색 의도와 출발점",
    "학교 자료 확인 범위",
    "고1·고2·고3 학년별 경로",
    "어휘와 문법의 연결",
    "구문과 독해의 적용",
    "내신과 서술형 준비",
    "모의고사와 수능 운영",
    "주간 일정과 복습 간격",
    "합성 사례로 보는 수정 과정",
    "과외 방식 비교 기준",
    "학부모 피드백과 개인정보",
    "공식 정보와 관련 페이지",
)


def _has_final_consonant(value: str) -> tuple[bool, bool]:
    """Return whether the last Hangul syllable has batchim and whether it is rieul."""
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


def _load_json(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}")
    return [row for row in data if isinstance(row, dict)]


@lru_cache(maxsize=1)
def school_english_contexts() -> dict[str, SchoolEnglishContext]:
    official_rows = _load_json(OFFICIAL_PATH)
    region_rows = {str(row.get("keyword") or ""): row for row in _load_json(REGION_MAP_PATH)}
    ordered = sorted(official_rows, key=lambda row: str(row.get("page") or ""))
    contexts: dict[str, SchoolEnglishContext] = {}
    for index, row in enumerate(ordered):
        general_slug = str(row.get("page") or "")
        if not general_slug.endswith("과외"):
            continue
        base = general_slug.removesuffix("과외")
        slug = f"{base}영어과외"
        region = region_rows.get(slug, {})
        city = str(row.get("city") or region.get("city") or "")
        mapped = [item for item in str(region.get("mapped_region_pages") or "").split("|") if item]
        town_candidates = [
            item
            for item in mapped
            if item.endswith("영어과외") and item not in {f"{city}영어과외", f"{city}고등영어과외"}
        ]
        region_english_slug = town_candidates[0] if town_candidates else f"{city}고등영어과외"
        display = str(region.get("school_display_name") or base.removeprefix(city))
        contexts[slug] = SchoolEnglishContext(
            slug=slug,
            general_slug=general_slug,
            math_slug=f"{base}수학과외",
            city=city,
            district=str(region.get("district") or ""),
            town=str(region.get("town") or ""),
            official_name=str(row.get("official_school_name") or region.get("official_school_name") or display),
            display_name=display,
            homepage=str(row.get("homepage") or ""),
            region_english_slug=region_english_slug,
            theme_index=index // len(METHODS),
            method_index=index % len(METHODS),
        )
    return contexts


def is_school_english_slug(slug: str) -> bool:
    return slug in school_english_contexts()


def school_english_focus(slug: str) -> str:
    context = school_english_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    return f"{theme['label']}·{method['label']}"


def build_school_english_meta(slug: str, body: str = "") -> tuple[str, str]:
    context = school_english_contexts()[slug]
    focus = school_english_focus(slug)
    title = f"{slug} | {focus} 점검"
    description = (
        f"{slug}는 {context.official_name}의 실제 학교 자료를 확인하며 {_object(focus)} 중심으로 "
        "고1·고2·고3 영어 내신, 서술형, 수행평가와 모의고사 학습 순서를 구체적으로 정리합니다."
    )
    return title, description


@lru_cache(maxsize=1)
def _variant_option_map() -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    slugs = sorted(school_english_contexts())
    theme_sets = list(combinations(range(len(THEMES)), 3))
    method_sets = list(combinations(range(len(METHODS)), 3))
    theme_sets.sort(key=lambda values: hashlib.sha256(f"school-theme:{values}".encode()).digest())
    method_sets.sort(key=lambda values: hashlib.sha256(f"school-method:{values}".encode()).digest())
    orders = list(permutations(range(3)))
    result: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for index, slug in enumerate(slugs):
        digest = hashlib.sha256(f"school-variant-order:{slug}".encode("utf-8")).digest()
        theme_order = orders[digest[0] % len(orders)]
        method_order = orders[digest[1] % len(orders)]
        themes = theme_sets[index]
        methods = method_sets[index]
        result[slug] = (
            tuple(themes[position] for position in theme_order),
            tuple(methods[position] for position in method_order),
        )
    return result


def _variant(context: SchoolEnglishContext, section_index: int) -> tuple[dict[str, str], dict[str, str], str]:
    theme_options, method_options = _variant_option_map()[context.slug]
    theme_index = theme_options[section_index % len(theme_options)]
    method_index = method_options[(section_index + context.theme_index) % len(method_options)]
    theme = THEMES[theme_index]
    method = METHODS[method_index]
    return theme, method, f"{theme['label']}·{method['label']}"


def _section_heading(context: SchoolEnglishContext, section_index: int, label: str) -> str:
    _, _, focus = _variant(context, section_index)
    return f"{context.slug}: {label} — {focus}"


def _standard_section(context: SchoolEnglishContext, section_index: int, label: str) -> str:
    theme, method, focus = _variant(context, section_index)
    school = escape(context.official_name)
    slug = escape(context.slug)
    return f"""
<section class="school-english-section school-english-section-{section_index + 1}" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, label))}</h2>
<p>{slug}의 이번 확인 주제는 <strong>{escape(focus)}</strong>입니다. {school} 학생이라고 해서 실제 시험 범위나 자료 구성을 임의로 단정하지 않습니다. 대신 {escape(_object(theme['problem']))} 관찰 가능한 출발점으로 두고, 학교에서 받은 교과서·학습지·평가 안내 가운데 어떤 자료가 현재 범위에 해당하는지 학생이 직접 구분하도록 합니다.</p>
<p>{school} 영어 학습에서는 {escape(_object(theme['evidence']))} 먼저 만듭니다. 이어서 {escape(method['start'])}. {slug} 계획은 공부시간의 총량보다 이 기록이 다음 학습 행동을 바꾸는지를 확인하며, 확인할 수 없는 성적 향상이나 학교별 출제 성향을 사실처럼 제시하지 않습니다.</p>
<p>{escape(_object(focus))} 실제 행동으로 바꿀 때는 {escape(_object(theme['action']))} 사용합니다. {escape(method['record'])}. 이렇게 남긴 자료는 {escape(theme['output'])}으로 이어지고, {school}의 공식 일정이 바뀌면 분량보다 날짜와 우선순위를 먼저 조정하는 근거가 됩니다.</p>
<p>{slug}의 완료 기준은 한 번 맞힌 정답이 아닙니다. {escape(method['review'])}. 학생이 설명하지 못한 지점은 새 문제로 덮지 않고 다음 수업의 질문으로 옮기며, {escape(focus)} 기록이 누적되면 내신과 모의고사 준비의 역할도 분리해 볼 수 있습니다.</p>
</section>"""


def _grade_section(context: SchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-english-grade" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '고1·고2·고3 학년별 경로'))}</h2>
<p>{slug}의 학년 계획은 같은 교재를 양만 달리 주는 방식이 아닙니다. {school}의 현재 학년과 실제 학교 자료를 확인한 뒤 <strong>{escape(focus)}</strong>을 공통 기준으로 삼되, 고1은 적응과 문장 구조, 고2는 내신과 모의고사의 병행, 고3은 실전 선택과 취약 영역 유지에 서로 다른 비중을 둡니다.</p>
<table>
<thead><tr><th>학년</th><th>{escape(focus)} 출발 행동</th><th>주간 확인 증거</th><th>피해야 할 판단</th></tr></thead>
<tbody>
<tr><td>고1</td><td>{slug} 학생은 교과서 한 문장의 핵심절을 말하고 당일에 다시 씁니다.</td><td>{escape(theme['evidence'])}</td><td>중학교 때의 점수만으로 고등 영어 수준을 고정하지 않습니다.</td></tr>
<tr><td>고2</td><td>{school} 자료와 모의고사 지문에서 같은 개념을 찾아 적용 차이를 설명합니다.</td><td>{escape(method['record'])}</td><td>내신 기간이라는 이유로 누적 독해를 완전히 멈추지 않습니다.</td></tr>
<tr><td>고3</td><td>{slug} 실전표에 유형별 시간과 보류한 이유를 함께 남깁니다.</td><td>{escape(method['review'])}</td><td>어려운 한 문항의 해결을 전체 시간 운영보다 앞세우지 않습니다.</td></tr>
</tbody>
</table>
<p>{school}의 구체적인 시험일이나 수행평가 형식은 학기와 과목 담당에 따라 달라질 수 있습니다. 따라서 {slug}에서는 표를 확정된 학교 정보로 읽지 않고, 공식 공지와 학생이 실제로 받은 안내를 확인한 뒤 수정하는 학년별 점검 틀로 사용합니다.</p>
</section>"""


def _schedule_section(context: SchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-english-schedule" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '주간 일정과 복습 간격'))}</h2>
<p>{slug} 주간표는 매일 같은 분량을 요구하지 않습니다. {school} 학생의 실제 귀가 시각과 제출 마감을 적은 뒤 <strong>{escape(_object(focus))}</strong> 기준으로 집중일·유지일·회복일을 나눕니다. {escape(_subject(theme['problem']))} 반복되는 날에는 의지 부족으로 결론 내리기 전에 시작 시각과 과제 크기의 조합을 먼저 바꿉니다.</p>
<table>
<thead><tr><th>구간</th><th>{escape(focus)} 행동</th><th>남길 기록</th></tr></thead>
<tbody>
<tr><td>수업 당일</td><td>{escape(method['start'])}.</td><td>{slug} 첫 회상에서 비어 있던 핵심어를 지우지 않고 표시합니다.</td></tr>
<tr><td>24시간 안</td><td>{escape(theme['action'])}.</td><td>{school} 자료를 보지 않고 재현한 부분과 도움받은 부분을 구분합니다.</td></tr>
<tr><td>72시간 안</td><td>{escape(method['review'])}.</td><td>{slug} 다음 계획에 넣을 한 가지 행동을 완료량 대신 적습니다.</td></tr>
</tbody>
</table>
<p>{school} 일정이 늦게 공지되거나 다른 과목의 마감과 겹치면 {slug} 표의 순서를 즉시 바꿉니다. 계획을 지우고 새로 쓰기보다 무엇을 줄였고 왜 옮겼는지 남겨야 {escape(_subject(focus))} 단순한 구호가 아니라 다음 주 분량을 결정하는 자료가 됩니다.</p>
</section>"""


def _case_section(context: SchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    grade = ("고1", "고2", "고3")[(context.theme_index + context.method_index) % 3]
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-english-case" data-case-model="composite" data-case-grade="{grade}" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '합성 사례로 보는 수정 과정'))}</h2>
<p><strong>아래 내용은 {school}의 실제 학생·성적·수업 결과가 아니라 여러 학습 장면을 합쳐 만든 가상 사례입니다.</strong> {slug}의 {grade} 학생이 {escape(_object(theme['problem']))} 겪는다고 가정합니다. 처음에는 문제 수만 늘렸지만 실패 원인이 보이지 않았고, 이후 <strong>{escape(_object(focus))}</strong> 적용해 행동과 기록을 분리했습니다.</p>
<table>
<thead><tr><th>관찰 시점</th><th>{slug} 가상 학생의 행동</th><th>수정 기준</th></tr></thead>
<tbody>
<tr><td>처음</td><td>정답을 확인한 뒤 자신의 첫 판단과 멈춘 위치를 지웠습니다.</td><td>{escape(theme['evidence'])}</td></tr>
<tr><td>일주일</td><td>{escape(method['record'])}.</td><td>{escape(theme['action'])}</td></tr>
<tr><td>재점검</td><td>{escape(method['review'])}.</td><td>{escape(theme['output'])}</td></tr>
</tbody>
</table>
<ol>
<li>{school}에서 받은 실제 자료와 이 가상 사례가 다른 부분을 학생이 먼저 표시합니다.</li>
<li>{slug} 기록에는 점수 예상이 아니라 시작·판단·교정 가운데 바꿀 한 단계를 적습니다.</li>
<li>{escape(_object(focus))} 일주일 적용한 뒤 변화가 없으면 학생 탓으로 돌리지 않고 가설과 과제 크기를 바꿉니다.</li>
</ol>
<p>이 사례는 {school}의 출제 방식이나 특정 학생의 성과를 설명하지 않습니다. {slug}에서 보여 주려는 것은 {escape(_object(focus))} 통해 관찰 가능한 증거를 만들고, 그 증거가 없을 때는 계획을 수정하는 과정입니다.</p>
</section>"""


def _decision_section(context: SchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-english-decision" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '과외 방식 비교 기준'))}</h2>
<p>{slug} 과외를 비교할 때는 학교 이름을 안다는 말보다 <strong>{escape(_object(focus))}</strong> 어떻게 관찰하고 수정할지 답을 들어야 합니다. {school}의 실제 자료를 학생이 제공했을 때 수업 전후에 무엇이 남는지, 설명을 들은 뒤 혼자 재현하는 간격을 어떻게 확인하는지 구체적으로 질문합니다.</p>
<table>
<thead><tr><th>비교 질문</th><th>확인할 답변</th><th>{slug} 경계 신호</th></tr></thead>
<tbody>
<tr><td>{escape(_topic(theme['problem']))} 어떻게 구분하나요?</td><td>{escape(theme['evidence'])}처럼 확인 가능한 증거가 제시되는지 봅니다.</td><td>상담 전부터 점수 상승이나 학교별 경향을 단정하는 답변입니다.</td></tr>
<tr><td>수업 뒤 혼자 할 행동은 무엇인가요?</td><td>{escape(method['start'])}처럼 학생이 재현할 순서가 있는지 봅니다.</td><td>교재 이름과 숙제량만 있고 완료 기준이 없는 답변입니다.</td></tr>
<tr><td>계획이 실패하면 무엇을 바꾸나요?</td><td>{escape(method['review'])}처럼 수정 시점과 기준이 있는지 봅니다.</td><td>{school} 학생이라는 이유만으로 같은 분량을 계속 요구하는 답변입니다.</td></tr>
</tbody>
</table>
<p>대면과 온라인 가운데 어느 방식이 맞는지도 {slug}에서 미리 단정할 수 없습니다. 같은 짧은 과제를 각각 한 번 수행해 준비 시간, 질문 시점, 필기 공유, 수업 후 독립 복습을 비교하십시오. {escape(focus)} 기록이 더 온전히 남고 학생이 스스로 다음 행동을 찾을 수 있는 방식을 선택하는 편이 안전합니다.</p>
</section>"""


def _feedback_tracker_section(context: SchoolEnglishContext, section_index: int) -> str:
    _, _, focus = _variant(context, section_index)
    focus_compact = focus.replace(" ", "·")
    phases = ("관찰", "적용", "비교", "독립재현")
    rows: list[str] = []
    for day in range(1, 29):
        theme, method, daily_focus = _variant(context, section_index + day)
        theme_compact = theme["label"].replace(" ", "·")
        method_compact = method["label"].replace(" ", "·")
        phase = phases[(day - 1) // 7]
        rows.append(
            "<tr>"
            f"<td>{escape(context.slug)}·{day}일</td>"
            f"<td>{escape(context.slug)} {escape(theme_compact)} {phase}·시작</td>"
            f"<td>{escape(context.official_name)} {escape(method_compact)} 근거·기록</td>"
            f"<td>{escape(focus_compact)} {escape(daily_focus.replace(' ', '·'))} {phase}·확인</td>"
            "</tr>"
        )
    return f"""
<section class="school-english-feedback-tracker" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '학부모 피드백과 28일 기록표'))}</h2>
<p>{escape(context.slug)}의 학부모 피드백은 매일 점수나 외운 양을 확인하는 방식보다 <strong>{escape(focus)}</strong>의 증거를 주 1회 함께 읽는 방식이 적절합니다. {escape(context.official_name)} 학생이 직접 적은 판단 근거와 수정 행동을 먼저 듣고, 보호자는 완료되지 않은 이유를 시간·이해·시작 지연 가운데 어느 쪽인지 질문합니다.</p>
<ul>
<li>{escape(context.slug)} 기록에는 정확한 집 주소를 적지 않습니다.</li>
<li>{escape(context.official_name)} 이름과 학년은 자료 구분에 필요한 범위에서만 사용합니다.</li>
<li>{escape(focus)} 상담에는 최근 학교 자료와 반복 오류만 먼저 준비합니다.</li>
<li>{escape(context.slug)} 피드백은 잘한 행동 하나와 바꿀 행동 하나로 끝냅니다.</li>
<li>{escape(context.official_name)} 일정이 바뀌면 분량보다 마감 순서를 먼저 고칩니다.</li>
<li>{escape(focus)} 기록은 보관 목적과 공유 범위를 확인한 뒤 전달합니다.</li>
</ul>
<p>아래 표는 {escape(context.slug)}에서 4주 동안 관찰·적용·비교·독립재현을 구분하기 위한 짧은 기록지입니다. 각 칸은 긴 공부 일지를 요구하지 않으며, 하루에 해당되는 행동 한 줄만 남깁니다. {escape(context.official_name)}의 실제 시험 기간에는 학교 자료를 우선하고 표의 날짜와 순서를 바꾸어 사용합니다.</p>
<table class="school-english-28day-tracker">
<thead><tr><th>날짜</th><th>오늘의 시작</th><th>남길 증거</th><th>주간 확인</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p>{escape(context.slug)}의 28일 표는 학습 성과를 보장하는 프로그램이 아닙니다. 첫째 주와 넷째 주에 같은 짧은 과제를 수행해 시작 시간, 근거 설명, 혼자 교정한 범위를 비교하는 도구입니다. {escape(focus)}의 변화가 보이지 않으면 학생을 압박하기보다 과제의 크기와 도움의 시점을 먼저 수정합니다.</p>
</section>"""


def _links_section(context: SchoolEnglishContext, section_index: int) -> str:
    _, _, focus = _variant(context, section_index)
    place = " ".join(item for item in (context.city, context.district, context.town) if item) or context.city
    return f"""
<section class="school-english-links" data-section-focus="{escape(focus)}">
<h2>{escape(_section_heading(context, section_index, '공식 정보와 관련 페이지'))}</h2>
<p>{escape(context.slug)}에서 학교 일정·교육과정·평가 안내처럼 바뀔 수 있는 내용은 <a class="source-link" href="{escape(context.homepage)}" target="_blank" rel="noopener noreferrer external">{escape(context.official_name)} 공식 홈페이지</a>를 직접 확인하십시오. 홈페이지는 학교 정보 확인용 외부 출처이며, EduNext가 해당 학교를 대표하거나 학교와 제휴했다는 뜻이 아닙니다. {escape(place)} 표기는 지역 매핑을 위한 범위일 뿐 통학 시간이나 배정을 보장하지 않습니다.</p>
<p>{escape(context.slug)}와 같은 학교의 전체 학습 범위는 <a href="/{escape(context.general_slug)}/">{escape(context.general_slug)}</a>, 수학 과목 비교는 <a href="/{escape(context.math_slug)}/">{escape(context.math_slug)}</a>에서 확인할 수 있습니다. 학교 한 곳을 넘어 생활권 영어 정보를 보려면 <a href="/{escape(context.region_english_slug)}/">{escape(context.region_english_slug)}</a>로 이동하십시오. 본문 링크는 이 세 탐색 목적과 공식 홈페이지에만 제한해 키워드 나열을 피했습니다.</p>
<p>{escape(context.official_name)}의 최신 자료와 학생이 실제로 받은 안내가 다르면 학생 자료를 우선 확인합니다. {escape(_topic(focus))} 학교 정보를 추정하는 문구가 아니라, 확인된 자료를 바탕으로 학습 행동을 나누는 이번 페이지의 고유한 점검 관점입니다.</p>
</section>"""


def _faq_section(context: SchoolEnglishContext) -> str:
    primary = school_english_focus(context.slug)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    questions = (
        (
            f"{context.slug}에서 {_object(primary)} 가장 먼저 어떻게 확인하나요?",
            f"{context.official_name}의 실제 교과서·학습지·평가 안내를 먼저 모은 뒤 {_object(theme['evidence'])} 만드십시오. {method['start']}. 처음부터 문제 수를 늘리기보다 학생이 멈춘 위치와 판단 근거를 남기고, 일주일 뒤 같은 순서를 혼자 재현하는지 확인해야 {context.slug}의 출발점이 구체적으로 보입니다.",
        ),
        (
            f"{context.slug}의 {primary} 계획에서 학교 홈페이지는 왜 확인하나요?",
            f"{context.official_name}의 시험일·행사·교육과정과 평가 안내는 시기에 따라 바뀔 수 있기 때문입니다. EduNext 본문은 확정된 학교 일정을 대신하지 않으므로 공식 홈페이지와 학생이 받은 안내를 대조해야 합니다. 확인 뒤에는 {method['record']}. 이렇게 해야 {context.slug} 계획이 추정 정보가 아니라 현재 자료를 기준으로 움직입니다.",
        ),
        (
            f"{context.slug}에서 내신과 모의고사를 {_direction(primary)} 함께 준비할 수 있나요?",
            f"역할을 나누면 함께 유지할 수 있습니다. 시험 전에는 {context.official_name}에서 실제로 사용하는 본문과 자료의 어휘·구문·서술형을 우선하고, 짧은 모의고사 독해는 판단 감각을 유지하는 정도로 둡니다. 시험 뒤에는 {theme['action']}을 적용해 학교 자료에서 확인한 개념이 낯선 지문에서도 재현되는지 점검합니다.",
        ),
        (
            f"{context.slug}의 {primary} 과외를 비교할 때 무엇을 질문해야 하나요?",
            f"교재와 숙제량보다 {_object(theme['problem'])} 어떤 증거로 구분할지 물어보십시오. 수업 뒤 학생이 혼자 할 행동, 기록을 다시 보는 날짜, 계획이 실패했을 때 바꿀 기준까지 답에 포함되어야 합니다. {method['review']}. 이 과정이 설명되지 않으면 {context.slug} 학생에게 맞는 방식인지 판단하기 어렵습니다.",
        ),
        (
            f"학부모는 {context.slug}의 {primary} 진행을 어떻게 확인하면 좋나요?",
            f"점수 예상이나 외운 양을 매일 묻기보다 주 1회 판단 근거, 반복 오류, 다음 행동을 확인하십시오. 정확한 주소나 불필요한 개인정보를 먼저 공유할 필요는 없습니다. {context.official_name}, 학년, 실제 귀가 시각, 최근 학교 자료와 {theme['output']}만으로 시작하고, {context.slug} 기록의 변화가 없으면 분량보다 계획 가설을 고칩니다.",
        ),
    )
    items = "\n".join(
        f"<h3>{escape(question)}</h3>\n<p>{escape(answer)}</p>" for question, answer in questions
    )
    return f"""
<section class="school-english-faq-section" data-faq-focus="{escape(primary)}">
<h2 class="school-english-faq">{escape(context.slug)} {escape(primary)} FAQ</h2>
{items}
</section>"""


def build_school_english_body(slug: str) -> str:
    context = school_english_contexts()[slug]
    focus = school_english_focus(slug)
    intro = f"""
<section class="school-english-guide" data-content-version="school-english-individual-v1" data-school-english-focus="{escape(focus)}" data-official-school="{escape(context.official_name)}">
<h2>{escape(context.slug)}: {escape(context.official_name)} 영어 학습의 고유 점검 주제</h2>
<p>{escape(context.slug)}는 <strong>{escape(_object(focus))}</strong> 중심으로 구성했습니다. 학교명을 검색한 사용자가 실제로 필요한 것은 확인되지 않은 출제 경향이나 성과 약속이 아니라, {escape(context.official_name)}의 최신 공식 자료와 학생이 가진 수업 자료를 구분하고 현재 학습 행동을 점검하는 순서입니다. 이 페이지는 학교와 제휴하거나 학교를 대표하지 않으며, 특정 학생의 결과를 보장하지 않습니다.</p>
<p>{escape(context.official_name)} 학생의 영어 계획은 같은 학교 안에서도 학년·과목 담당·귀가 시각·현재 이해도에 따라 달라집니다. {escape(context.slug)}에서는 {escape(_object(focus))} 하나의 관찰 관점으로 두고 고1·고2·고3, 어휘·문법·구문·독해, 내신·수행평가·모의고사를 서로 다른 역할로 나누어 설명합니다.</p>
"""
    sections: list[str] = []
    for index, label in enumerate(SECTION_PURPOSES):
        if index == 2:
            sections.append(_grade_section(context, index))
        elif index == 7:
            sections.append(_schedule_section(context, index))
        elif index == 8:
            sections.append(_case_section(context, index))
        elif index == 9:
            sections.append(_decision_section(context, index))
        elif index == 10:
            sections.append(_feedback_tracker_section(context, index))
        elif index == 11:
            sections.append(_links_section(context, index))
        else:
            sections.append(_standard_section(context, index, label))
    return intro + "\n".join(sections) + "\n" + _faq_section(context) + "\n</section>"


def individualize_school_english_body(body: str, slug: str) -> str:
    if not is_school_english_slug(slug):
        return body
    return build_school_english_body(slug)
