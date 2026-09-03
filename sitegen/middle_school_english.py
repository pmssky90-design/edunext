from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations
from pathlib import Path

from sitegen.utils import escape


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "middle_school_math_pages.json"


THEMES = (
    {
        "label": "문장 성분과 기본 어순",
        "problem": "단어 뜻은 알지만 주어·동사·목적어를 구분하지 못해 긴 문장의 중심이 흔들리는 상태",
        "evidence": "주어·핵심 동사·목적어·수식어를 서로 다른 칸에 나눈 문장 뼈대 표",
        "action": "수식어를 잠시 가리고 핵심절을 먼저 읽은 뒤 빠진 정보를 한 덩어리씩 다시 붙이는 연습",
        "output": "해석만 적는 대신 어느 성분을 잘못 잡았는지 설명할 수 있는 어순 기록",
    },
    {
        "label": "시제와 동사 형태",
        "problem": "시간 표현을 확인하지 않고 익숙한 동사 형태를 골라 서술형에서 반복해 틀리는 상태",
        "evidence": "시간 단서·주어의 수·동사 원형·선택한 시제를 함께 적은 동사 판단표",
        "action": "문장을 쓰기 전에 시간 단서와 주어를 표시하고 마지막에 부정문·의문문의 조동사를 역검산하는 연습",
        "output": "정답 형태와 함께 그 형태를 선택한 시간·수 일치 근거가 남는 교정 기록",
    },
    {
        "label": "품사와 문장 자리",
        "problem": "같은 어근의 명사·동사·형용사·부사를 뜻만 보고 바꾸어 문장 자리에 맞지 않는 상태",
        "evidence": "앞뒤 단서·필요한 품사·선택한 형태·문장 역할을 연결한 품사 변환표",
        "action": "빈칸 앞뒤의 구조로 필요한 품사를 먼저 정하고 접두사·접미사와 철자를 나중에 확인하는 연습",
        "output": "단어를 외웠는지가 아니라 문장 안에서 형태를 선택한 이유가 보이는 품사 기록",
    },
    {
        "label": "조동사와 의미 강도",
        "problem": "can·must·should 같은 표현을 한글 뜻 하나로 외워 문맥의 가능성·의무·조언 차이를 놓치는 상태",
        "evidence": "상황 문장·화자의 태도·조동사·바꿔 쓸 표현을 비교한 의미 강도표",
        "action": "조동사를 지운 문장에 화자의 의도를 먼저 적고 두 후보의 의미 강도를 대조하는 연습",
        "output": "번역 한 줄보다 표현을 바꿨을 때 달라지는 태도를 설명하는 문맥 기록",
    },
    {
        "label": "준동사 역할 구분",
        "problem": "to부정사와 동명사를 모양으로만 구분해 문장에서 명사·형용사·부사 역할을 연결하지 못하는 상태",
        "evidence": "준동사 형태·수식 대상·문장 역할·바꿔 쓸 절을 나란히 둔 역할표",
        "action": "준동사에 밑줄을 긋고 무엇을 설명하는지 화살표로 연결한 뒤 완전한 절로 바꾸어 검산하는 연습",
        "output": "용법 이름 암기보다 문장 안 연결 대상을 근거로 남긴 준동사 분석 기록",
    },
    {
        "label": "비교와 수량 표현",
        "problem": "비교급·최상급 형태는 기억하지만 비교 대상과 범위를 확인하지 않아 뜻이 어긋나는 상태",
        "evidence": "비교 대상·기준 집단·강조 표현·최종 문장을 한 줄로 이은 비교 조건표",
        "action": "형태를 쓰기 전에 무엇과 무엇을 어떤 범위에서 비교하는지 한국어와 영어로 각각 말하는 연습",
        "output": "철자만 고친 답안이 아니라 비교 범위가 맞는지 확인한 조건 기록",
    },
    {
        "label": "수동태와 행위 관계",
        "problem": "be동사와 과거분사가 보이면 수동태로 고르지만 행위자와 대상의 관계를 설명하지 못하는 상태",
        "evidence": "행동 주체·영향을 받는 대상·시제·능동문 변환을 묶은 태 전환표",
        "action": "누가 무엇을 했는지 먼저 적고 능동문과 수동문을 오가며 시제와 목적어 이동을 확인하는 연습",
        "output": "공식 적용보다 문장의 초점이 왜 바뀌었는지 말할 수 있는 태 판단 기록",
    },
    {
        "label": "관계 표현과 수식 범위",
        "problem": "관계대명사 앞의 명사만 보고 선택해 뒤 절의 빠진 성분과 수식 범위를 놓치는 상태",
        "evidence": "선행사·뒤 절의 빈자리·관계 표현·수식이 끝나는 지점을 표시한 연결표",
        "action": "두 문장으로 먼저 나누고 공통 명사를 찾은 뒤 뒤 절에서 빠진 성분을 기준으로 다시 합치는 연습",
        "output": "관계 표현의 종류와 함께 연결된 두 문장과 빈자리가 남는 구문 기록",
    },
    {
        "label": "교과서 본문 변형",
        "problem": "본문 순서를 통째로 외워 어순·빈칸·어법·영작처럼 질문 형식이 바뀌면 근거를 꺼내지 못하는 상태",
        "evidence": "핵심 문장·구문 근거·어휘 변형·내용 질문을 한 장에 나눈 본문 변형표",
        "action": "한 문장을 어순 배열·빈칸·어법·영작 네 형태로 바꾸고 같은 근거를 반복해서 찾는 연습",
        "output": "암기 여부보다 변형된 질문에서도 같은 개념을 재현한 적용 기록",
    },
    {
        "label": "서술형 조건 영작",
        "problem": "뜻이 비슷한 문장을 쓰고도 제시어·단어 수·시제·문장 형식 조건을 빠뜨리는 상태",
        "evidence": "문제 조건·첫 답안·누락된 조건·교정 이유를 네 칸으로 나눈 서술형 점검표",
        "action": "주어와 동사를 먼저 고정하고 제시 조건을 하나씩 대조한 뒤 소리 내어 읽으며 형태를 검산하는 연습",
        "output": "모범답안 암기보다 자신의 첫 문장에서 무엇을 왜 고쳤는지 보이는 영작 기록",
    },
    {
        "label": "문맥 어휘 회상",
        "problem": "단어 시험에서는 뜻을 맞히지만 본문에서 품사나 의미가 달라지면 해석이 멈추는 상태",
        "evidence": "표제어·문장 속 뜻·함께 쓰인 표현·다시 확인할 날짜를 연결한 문맥 어휘장",
        "action": "뜻을 가리고 예문을 먼저 읽은 뒤 문장 역할과 함께 쓰인 표현을 말하고 유사어 차이를 적는 연습",
        "output": "암기 개수보다 낯선 문장에서 뜻을 복원한 과정이 남는 어휘 회상 기록",
    },
    {
        "label": "문단 중심과 독해 근거",
        "problem": "모든 문장을 같은 비중으로 해석해 글의 주장·예시·전환 관계를 구분하지 못하는 상태",
        "evidence": "문단 핵심어·전환어·주장 문장·정답 근거를 연결한 독해 근거 지도",
        "action": "각 문단을 짧은 명사구로 줄이고 전환어 뒤의 내용을 확인한 다음 선택지와 근거 문장을 대조하는 연습",
        "output": "정답 번호보다 어느 문장에서 판단했는지 추적할 수 있는 독해 기록",
    },
    {
        "label": "듣기 선지 예측",
        "problem": "음원을 들은 뒤 선택지를 읽기 시작해 핵심 표현을 들었어도 비교 시간이 부족해지는 상태",
        "evidence": "선지 차이·예상 장면·실제로 들린 표현·놓친 신호를 순서대로 적은 듣기 점검표",
        "action": "재생 전에 선택지 차이를 표시하고 첫 청취에서는 상황을, 다시 들을 때는 숫자·이유·의도를 검증하는 연습",
        "output": "막연한 듣기 부족 대신 예측·청취·선택 중 약한 단계가 드러나는 기록",
    },
    {
        "label": "수행평가 발표와 쓰기",
        "problem": "마감 직전에 내용 구성과 영어 표현 교정을 동시에 처리해 요구 조건과 연습 시간을 놓치는 상태",
        "evidence": "평가 조건·자료 조사·한글 개요·영어 초안·말하기 연습·최종 교정을 날짜별로 나눈 준비표",
        "action": "평가 안내에서 필수 조건을 먼저 표시하고 개요와 문장 교정을 다른 날에 진행하며 마지막에 시간을 재는 연습",
        "output": "완성본뿐 아니라 어떤 조건을 언제 확인하고 수정했는지 남는 수행 과정 기록",
    },
)


METHODS = (
    {"label": "간격 복습", "start": "수업 뒤에는 핵심 문장과 판단 근거를 회상하고 간격을 둔 다음 조건을 바꾼 문항에 적용합니다", "record": "첫 기억과 후속 적용에서 막힌 위치를 서로 다른 표시로 남깁니다", "review": "충분한 간격 뒤 같은 순서를 자료 없이 재현할 수 있는지 확인합니다"},
    {"label": "학교자료 우선표", "start": "교과서·학교 학습지·평가 안내를 먼저 모으고 개인 교재는 빈틈을 채우는 데 사용합니다", "record": "자료마다 시험 범위 여부·완료 기준·다시 볼 날짜를 적습니다", "review": "시험 뒤 실제 판단 근거가 된 자료만 다음 계획에 남깁니다"},
    {"label": "오류 코드 장부", "start": "오답을 어휘·문법·구문·내용·조건 누락 가운데 하나로 먼저 분류합니다", "record": "오류 이름 옆에 다음 문제에서 먼저 확인할 신호를 한 문장으로 적습니다", "review": "같은 코드가 세 번 나오면 문제 수보다 판단 순서를 먼저 고칩니다"},
    {"label": "짧은 회상 루틴", "start": "귀가 뒤 짧은 시간을 정해 책을 덮고 핵심어·문장 구조·본문 흐름을 먼저 씁니다", "record": "기억난 내용과 확인 후 보완한 내용을 두 칸으로 나누어 원래 기억을 지우지 않습니다", "review": "주말에는 반복해서 빈칸이 된 항목만 다음 주 첫 복습으로 옮깁니다"},
    {"label": "두 문장 비교법", "start": "같은 문법이나 표현을 가진 두 문장을 나란히 두고 공통 구조와 다른 조건을 찾습니다", "record": "표현의 모양보다 문장 역할과 의미 차이를 비교표에 남깁니다", "review": "새 문장에서 비교 기준을 학생이 스스로 정하는지 확인합니다"},
    {"label": "빈 종이 재현", "start": "해설을 덮고 문제 조건·첫 판단·교정 근거·완성 문장을 빈 종이에 다시 씁니다", "record": "도움을 받은 줄과 혼자 이어 간 줄을 다른 기호로 남깁니다", "review": "하루 뒤 네 단계가 순서대로 유지될 때 완료로 처리합니다"},
    {"label": "질문 한 줄 기록", "start": "막힌 순간을 해설로 덮지 않고 아는 것·시도한 것·필요한 도움으로 나누어 적습니다", "record": "정답 요청 대신 확인이 필요한 단어나 문장 경계를 질문으로 바꿉니다", "review": "수업 끝에는 답보다 다음에 먼저 찾을 근거를 다시 씁니다"},
    {"label": "교정 색상 분리", "start": "첫 답안·학생 교정·설명 후 교정을 세 가지 색이나 기호로 구분합니다", "record": "정답만 덮어쓰지 않고 처음 판단이 바뀐 이유를 옆에 남깁니다", "review": "다음 날 첫 답안과 같은 오류가 반복되는지 대조합니다"},
    {"label": "소리 내어 검산", "start": "완성한 문장을 소리 내어 읽으며 주어·동사·멈추는 지점과 의미 흐름을 확인합니다", "record": "읽다가 멈춘 위치와 눈으로만 볼 때 놓친 형태를 표시합니다", "review": "말과 글의 구조가 같아질 때 짧은 변형 문장으로 넘어갑니다"},
    {"label": "주간 마감 역산", "start": "시험일과 제출일부터 거꾸로 세어 범위 확인·초안·교정·재현 날짜를 나눕니다", "record": "예상 시간과 실제 시간을 함께 적어 다음 분량을 조정합니다", "review": "밀린 항목은 모두 이월하지 않고 마감 영향과 학습 목적을 기준으로 다시 고릅니다"},
    {"label": "근거 말하기 점검", "start": "정답을 고른 뒤 본문이나 문장 안의 근거를 한 문장으로 설명합니다", "record": "근거가 없던 선택과 근거는 있었지만 해석이 틀린 선택을 따로 표시합니다", "review": "보호자는 답보다 판단 근거와 다음 확인 순서를 질문합니다"},
    {"label": "난도 교대 계획", "start": "집중 가능한 날에는 새 문법과 긴 독해를, 피로한 날에는 회상과 짧은 교정을 배치합니다", "record": "요일별 시작 시각·과제 난도·완료 단계를 함께 비교합니다", "review": "계획 실패를 의지로 해석하지 않고 시간대와 과제 크기를 바꿉니다"},
    {"label": "단계별 변형 적용", "start": "기본 문장을 이해한 뒤 형태를 바꾸고, 충분한 간격 뒤 낯선 문장에 같은 근거를 적용합니다", "record": "시도마다 달라진 조건과 유지된 문법 근거를 나란히 적습니다", "review": "간격을 둔 시도에서도 같은 곳에서 멈추면 선행 개념과 어휘로 돌아갑니다"},
)


SECTION_PURPOSES = (
    "검색 의도와 영어 학습 출발점",
    "학교 공시 자료와 확인 범위",
    "중1·중2·중3 학년별 경로",
    "어휘와 문법의 연결",
    "구문과 독해의 적용",
    "교과서 본문과 서술형 준비",
    "듣기평가와 수행평가 운영",
    "주간 일정과 복습 간격",
    "합성 사례로 보는 수정 과정",
    "과외 방식 비교 기준",
    "학부모 피드백과 누적 기록표",
    "공식 정보와 관련 페이지",
)


@dataclass(frozen=True)
class MiddleSchoolEnglishContext:
    slug: str
    math_slug: str
    city: str
    district: str
    town: str
    official_name: str
    display_name: str
    homepage: str
    parent_slug: str
    region_english_slug: str
    internal_links: tuple[str, ...]
    theme_index: int
    method_index: int
    row: dict[str, object]


def _exists(slug: str) -> bool:
    return bool(slug) and (ROOT / "output" / slug / "index.html").exists()


def _region_bases(row: dict[str, object]) -> list[str]:
    city = str(row.get("city") or "")
    district = str(row.get("district") or "")
    town = str(row.get("town") or "")
    town_base = town if town.startswith(city) else f"{city}{town}" if town else ""
    district_base = district if district.startswith(city) else f"{city}{district}" if city == "부산" and district else city
    return list(dict.fromkeys(item for item in (town_base, district_base, city) if item))


@lru_cache(maxsize=1)
def middle_school_english_contexts() -> dict[str, MiddleSchoolEnglishContext]:
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    contexts: dict[str, MiddleSchoolEnglishContext] = {}
    for index, row in enumerate(rows):
        math_slug = str(row["slug"])
        slug = math_slug.removesuffix("수학과외") + "영어과외"
        bases = _region_bases(row)
        parent_candidates = [f"{base}중등영어과외" for base in bases]
        region_candidates = [f"{base}영어과외" for base in bases]
        parent = next((item for item in parent_candidates if _exists(item)), f"{row['city']}중등영어과외")
        region_english = next((item for item in region_candidates if _exists(item)), f"{row['city']}영어과외")
        link_candidates = [
            math_slug,
            parent,
            region_english,
            f"{row['city']}중등과외",
            f"{row['city']}과외",
        ]
        internal = tuple(dict.fromkeys(item for item in link_candidates if _exists(item)))[:3]
        contexts[slug] = MiddleSchoolEnglishContext(
            slug=slug,
            math_slug=math_slug,
            city=str(row["city"]),
            district=str(row["district"]),
            town=str(row["town"]),
            official_name=str(row["official_name"]),
            display_name=str(row["display_name"]),
            homepage=str(row["homepage"]),
            parent_slug=parent,
            region_english_slug=region_english,
            internal_links=internal,
            theme_index=index % len(THEMES),
            method_index=(index // len(THEMES)) % len(METHODS),
            row=row,
        )
    return contexts


def is_middle_school_english_slug(slug: str) -> bool:
    return slug in middle_school_english_contexts()


def middle_school_english_focus(slug: str) -> str:
    context = middle_school_english_contexts()[slug]
    return f"{THEMES[context.theme_index]['label']}·{METHODS[context.method_index]['label']}"


def build_middle_school_english_meta(slug: str, source_body: str = "") -> tuple[str, str]:
    context = middle_school_english_contexts()[slug]
    focus = middle_school_english_focus(slug)
    title = f"{slug} | {focus} 학습 계획"
    description = (
        f"{context.official_name} 학생을 위한 중등 영어과외 안내입니다. {context.town} 생활권과 2025년 학교 공시 자료를 확인하고, "
        f"{focus} 중심으로 중1·중2·중3 교과서 본문·문법·서술형·듣기·수행평가 학습 순서를 정리했습니다."
    )
    return title, description


def _has_final(value: str) -> bool:
    for char in reversed(str(value).strip()):
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            return code % 28 != 0
    return False


def _object(value: str) -> str:
    return f"{value}{'을' if _has_final(value) else '를'}"


def _subject(value: str) -> str:
    return f"{value}{'이' if _has_final(value) else '가'}"


@lru_cache(maxsize=1)
def _variant_option_map() -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    slugs = sorted(middle_school_english_contexts())
    theme_sets = list(combinations(range(len(THEMES)), 3))
    method_sets = list(combinations(range(len(METHODS)), 3))
    theme_sets.sort(key=lambda values: hashlib.sha256(f"middle-english-theme:{values}".encode()).digest())
    method_sets.sort(key=lambda values: hashlib.sha256(f"middle-english-method:{values}".encode()).digest())
    orders = list(permutations(range(3)))
    result: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for index, slug in enumerate(slugs):
        digest = hashlib.sha256(f"middle-english-order:{slug}".encode("utf-8")).digest()
        themes = theme_sets[index]
        methods = method_sets[index]
        theme_order = orders[digest[0] % len(orders)]
        method_order = orders[digest[1] % len(orders)]
        result[slug] = (
            tuple(themes[position] for position in theme_order),
            tuple(methods[position] for position in method_order),
        )
    return result


def _variant(context: MiddleSchoolEnglishContext, section_index: int) -> tuple[dict[str, str], dict[str, str], str]:
    theme_options, method_options = _variant_option_map()[context.slug]
    theme = THEMES[theme_options[section_index % 3]]
    method = METHODS[method_options[(section_index + context.theme_index) % 3]]
    return theme, method, f"{theme['label']}·{method['label']}"


def _heading(context: MiddleSchoolEnglishContext, section_index: int, label: str) -> str:
    _, _, focus = _variant(context, section_index)
    return f"{context.slug}: {label} — {focus}"


def _table(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...], class_name: str = "") -> str:
    klass = f' class="{escape(class_name)}"' if class_name else ""
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table{klass}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _standard_section(context: MiddleSchoolEnglishContext, section_index: int, label: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="middle-school-english-section" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, label))}</h2>
<p>{slug}의 이번 확인 주제는 <strong>{escape(focus)}</strong>입니다. {school} 학생이라고 해서 시험 범위나 출제 방식을 임의로 단정하지 않습니다. 대신 {escape(_object(theme['problem']))} 관찰 가능한 출발점으로 두고, 학생이 받은 교과서·학습지·평가 안내에서 현재 범위와 실제로 막힌 문장을 먼저 구분합니다.</p>
<p>{school} 영어 학습에서는 {escape(_object(theme['evidence']))} 먼저 만듭니다. 이어서 {escape(method['start'])}. {slug} 계획은 공부시간의 총량보다 이 기록이 다음 행동을 바꾸는지 확인하며, 확인할 수 없는 점수 상승이나 학교별 출제 경향을 사실처럼 제시하지 않습니다.</p>
<p>{escape(_object(focus))} 실제 행동으로 바꿀 때는 {escape(theme['action'])}. {escape(method['record'])}. 이 과정은 {escape(theme['output'])}으로 이어지고, {school}의 일정이나 시험 범위가 바뀌면 문제 수보다 날짜와 자료의 우선순위를 먼저 조정하는 근거가 됩니다.</p>
<p>{slug}의 완료 기준은 한 번 맞힌 답이 아닙니다. {escape(method['review'])}. 설명하지 못한 문장이나 조건은 새 문제로 덮지 않고 다음 수업 질문으로 옮기며, {escape(focus)} 기록을 교과서 본문·문법·독해·서술형에서 각각 다시 확인합니다.</p>
</section>"""


def _profile_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    row = context.row
    theme, method, focus = _variant(context, section_index)
    table = _table(
        ("확인 항목", "2025년 공시 값", "영어 계획에서의 사용 범위"),
        (
            ("학교 구분", f"{row['establishment']} · {row['coeducation']} · {row['school_detail']}", "학교 식별과 공식 자료 확인에만 사용"),
            ("학급·학생", f"총 {row['total_classes']}학급 · {row['total_students']}명", "개별 성취도나 시험 난도를 추정하지 않음"),
            ("학년별 학생", f"중1 {row['grade1_students']}명 · 중2 {row['grade2_students']}명 · 중3 {row['grade3_students']}명", "학년별 학습 경로를 나누는 참고값"),
            ("교원", f"교원 {row['teachers']}명 · 교원 1인당 학생 {row['students_per_teacher']}명", "공시된 인원 정보 확인에만 사용"),
        ),
    )
    return f"""
<section class="middle-school-english-profile" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '학교 공시 자료와 확인 범위'))}</h2>
<p>{escape(context.official_name)}의 공시 주소는 {escape(str(row['address']))}이며, 이 페이지는 {escape(str(row['source_date']))} 기준 학교 통계를 사용했습니다. 공시 수치는 학교를 정확히 구분하고 학년 규모를 확인하기 위한 자료이며 영어 성취도, 반별 진도, 담당 교사의 평가 방식으로 해석하지 않습니다.</p>
<p>{escape(context.slug)}에서 실제 시험 범위와 수행평가 일정은 학생이 받은 공지, 교과서 진도, 학교 홈페이지의 최신 안내로 다시 확인합니다. 같은 학교 학생도 반·담당 교사·현재 단원·귀가 시각에 따라 필요한 순서가 다르므로 {escape(_object(theme['evidence']))} 첫 상담 자료로 사용합니다.</p>
<p>{escape(context.slug)}가 속한 {escape(context.town)} 생활권 정보도 대략적인 지역 탐색에만 사용합니다. 통학 거리나 배정을 단정하지 않고, {escape(method['start'])}. 이렇게 확인된 {escape(context.official_name)} 자료와 학생 기록이 만나는 지점에서만 <strong>{escape(focus)}</strong> 계획을 조정합니다.</p>
{table}
</section>"""


def _grade_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    table = _table(
        ("학년", f"{focus} 출발 행동", "주간 확인 증거", "피해야 할 판단"),
        (
            ("중1", f"{context.slug} 학생은 문장 성분과 기본 어순을 짧은 교과서 문장에서 다시 확인합니다.", theme["evidence"], "초등 영어 점수만으로 중학교 수준을 고정하지 않음"),
            ("중2", f"{context.official_name} 자료에서 문법 근거와 본문 내용을 분리하고 서술형 변형에 적용합니다.", method["record"], "시험 기간이라고 누적 어휘와 독해를 완전히 중단하지 않음"),
            ("중3", f"{context.slug} 기록에 고등 진입 전 부족한 어휘·구문·영작의 우선순위를 한 가지씩 남깁니다.", method["review"], "고등 선행을 이유로 현재 학교 범위를 건너뛰지 않음"),
        ),
    )
    return f"""
<section class="middle-school-english-grade" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '중1·중2·중3 학년별 경로'))}</h2>
<p>{escape(context.slug)}의 학년 계획은 같은 교재를 양만 달리 주는 방식이 아닙니다. {escape(context.official_name)}의 현재 학년과 실제 학교 자료를 확인한 뒤 <strong>{escape(focus)}</strong>을 공통 기준으로 삼되, 중1은 문장 구조 적응, 중2는 문법과 본문 변형, 중3은 내신 유지와 고등 연결에 서로 다른 비중을 둡니다.</p>
{table}
<p>{escape(context.official_name)}의 시험일과 수행평가 형식은 학기와 담당에 따라 달라질 수 있습니다. 이 표는 확정된 학교 일정이 아니라 공식 공지와 학생 안내를 확인한 뒤 수정하는 학년별 점검 틀이며, {escape(_subject(theme['problem']))} 보이면 학년보다 실제로 멈춘 단계부터 다시 확인합니다.</p>
</section>"""


def _schedule_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    table = _table(
        ("복습 구간", f"{focus} 행동", "남길 기록"),
        (
            ("수업 당일", method["start"], f"{context.slug} 첫 회상에서 비어 있던 핵심어와 문장을 표시"),
            ("다음 복습", theme["action"], f"{context.official_name} 자료를 보지 않고 재현한 부분과 도움받은 부분을 구분"),
            ("간격 후 재확인", method["review"], f"{context.slug} 다음 계획에 넣을 한 가지 행동을 완료량 대신 기록"),
        ),
    )
    return f"""
<section class="middle-school-english-schedule" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '주간 일정과 복습 간격'))}</h2>
<p>{escape(context.slug)} 주간표는 매일 같은 분량을 요구하지 않습니다. {escape(context.official_name)} 학생의 실제 귀가 시각과 제출 마감을 적은 뒤 <strong>{escape(focus)}</strong> 기준으로 집중일·유지일·회복일을 나눕니다. {escape(_subject(theme['problem']))} 반복되면 의지 부족으로 결론 내리기 전에 시작 시각과 과제 크기를 먼저 바꿉니다.</p>
{table}
<p>{escape(context.official_name)} 일정이 늦게 공지되거나 다른 과목 마감과 겹치면 순서를 즉시 조정합니다. 계획을 지우기보다 무엇을 줄이고 왜 옮겼는지 남겨야 {escape(_subject(focus))} 다음 주 분량을 결정하는 실제 자료가 됩니다.</p>
</section>"""


def _case_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    grade = ("중1", "중2", "중3")[(context.theme_index + context.method_index) % 3]
    table = _table(
        ("관찰 시점", f"{context.slug} 가상 학생의 행동", "수정 기준"),
        (
            ("처음", "정답을 확인한 뒤 자신의 첫 판단과 멈춘 문장을 지웠습니다.", theme["evidence"]),
            ("일주일", method["record"], theme["action"]),
            ("재점검", method["review"], theme["output"]),
        ),
    )
    return f"""
<section class="middle-school-english-case" data-case-model="composite" data-case-grade="{grade}" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '합성 사례로 보는 수정 과정'))}</h2>
<p><strong>아래 내용은 {escape(context.official_name)}의 실제 학생·성적·수업 결과가 아니라 여러 학습 장면을 합친 가상 사례입니다.</strong> {escape(context.slug)}의 {grade} 학생이 {escape(_object(theme['problem']))} 겪는다고 가정합니다. 처음에는 문제 수만 늘렸지만 원인이 보이지 않아 <strong>{escape(_object(focus))}</strong> 적용해 행동과 기록을 분리했습니다.</p>
{table}
<ol><li>{escape(context.official_name)}에서 받은 실제 자료와 사례가 다른 부분을 학생이 먼저 표시합니다.</li><li>{escape(context.slug)} 기록에는 점수 예상이 아니라 바꿀 학습 행동 하나를 적습니다.</li><li>{escape(_object(focus))} 일주일 적용한 뒤 변화가 없으면 학생 탓으로 돌리지 않고 과제 크기와 도움 시점을 바꿉니다.</li></ol>
<p>이 사례는 {escape(context.official_name)}의 출제 방식이나 특정 학생의 성과를 설명하지 않습니다. {escape(context.slug)}에서 보여 주는 것은 관찰 가능한 증거를 만들고 그 증거가 없을 때 계획을 수정하는 과정입니다.</p>
</section>"""


def _decision_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    theme, method, focus = _variant(context, section_index)
    table = _table(
        ("비교 질문", "확인할 답변", f"{context.slug} 경계 신호"),
        (
            (f"{_object(theme['problem'])} 어떻게 구분하나요?", f"{theme['evidence']}처럼 확인 가능한 증거가 있는지 봅니다.", "상담 전부터 점수 상승이나 학교별 경향을 단정함"),
            ("수업 뒤 혼자 할 행동은 무엇인가요?", f"{method['start']}처럼 재현할 순서가 있는지 봅니다.", "교재와 숙제량만 있고 완료 기준이 없음"),
            ("계획이 실패하면 무엇을 바꾸나요?", f"{method['review']}처럼 수정 시점과 기준이 있는지 봅니다.", f"{context.official_name} 학생이라는 이유로 같은 분량만 요구함"),
        ),
    )
    return f"""
<section class="middle-school-english-decision" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '과외 방식 비교 기준'))}</h2>
<p>{escape(_object(context.slug))} 비교할 때는 학교 이름을 안다는 말보다 <strong>{escape(_object(focus))}</strong> 어떻게 관찰하고 수정할지 물어야 합니다. {escape(context.official_name)}의 실제 자료를 제공했을 때 수업 전후에 무엇이 남는지, 설명 뒤 혼자 재현하는 간격을 어떻게 확인하는지 구체적으로 질문합니다.</p>
{table}
<p>{escape(context.slug)}에서 대면과 온라인 중 어느 방식이 맞는지도 미리 단정할 수 없습니다. {escape(context.official_name)} 자료를 이용한 같은 짧은 과제를 각각 수행해 준비 시간·질문 시점·필기 공유·독립 복습을 비교하고, {escape(focus)} 기록이 더 온전히 남는 방식을 선택합니다.</p>
</section>"""


def _tracker_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    _, _, focus = _variant(context, section_index)
    moments = (
        "학교 자료 확인", "도움 전 첫 시도", "핵심 근거 표시", "설명 직후 복원",
        "조건을 바꾼 적용", "학교 본문 대조", "오류 원인 분류", "간격 뒤 재현",
        "학생 질문 정리", "가정 확인 대화", "독립 수행 점검", "다음 계획 결정",
        "과제 목적 확인", "교과서 표현 대조", "어휘와 개념 회상", "근거 문장 선택",
        "힌트 사용 위치", "수정 전후 비교", "새 지문 적용", "학교 과제 연결",
        "수행평가 준비", "시험 범위 확인", "학습지 재구성", "오답 재설명",
        "귀가 후 첫 행동", "마감 전 자기점검", "보호자 질문 기록", "다음 수업 준비",
    )
    phases = ("관찰", "적용", "비교", "독립재현")
    rows: list[tuple[str, str, str, str]] = []
    for offset, moment in enumerate(moments):
        theme, method, daily_focus = _variant(context, section_index + offset + 1)
        phase = phases[offset // 7]
        row_variants = (
            (
                f"{context.slug}에서 {theme['label']}의 {phase} 행동을 도움 전에 시도하고 첫 흔적을 보존합니다.",
                f"{context.official_name} 자료와 {method['label']} 기록을 대조해 판단 근거와 수정 이유를 남깁니다.",
                f"{daily_focus} 가운데 다음 학습에 유지할 행동과 줄일 도움을 구분합니다.",
            ),
            (
                f"{context.official_name} 영어 자료에서 {phase}에 필요한 {theme['label']} 단서를 학생이 스스로 고릅니다.",
                f"{context.slug} 기록에는 {method['label']} 전후의 표현과 근거 문장을 서로 다른 칸에 둡니다.",
                f"다음에는 {daily_focus}를 새 문장에 적용하고 필요한 질문만 남깁니다.",
            ),
            (
                f"도움 없이 {theme['label']}를 시작한 위치를 {context.slug} 학습지에 먼저 표시합니다.",
                f"{method['label']} 과정에서 학생이 바꾼 표현과 {context.official_name} 원문 근거를 함께 대조합니다.",
                f"{daily_focus}가 유지되면 자료를 바꾸고, 흔들리면 과제 길이와 도움 시점을 줄입니다.",
            ),
            (
                f"{phase} 장면에서는 {context.official_name} 자료의 {theme['label']}를 학생 말로 다시 구성합니다.",
                f"첫 시도, 질문 위치, {method['label']} 뒤 달라진 문장을 {context.slug} 기록에 남깁니다.",
                f"후속 점검은 {daily_focus}의 독립 사용 여부에 따라 유지하거나 다시 나눕니다.",
            ),
        )
        start_text, evidence_text, decision_text = row_variants[
            hashlib.sha256(f"{context.slug}:middle-english-tracker:{offset}".encode("utf-8")).digest()[0] % len(row_variants)
        ]
        rows.append((
            moment,
            start_text,
            evidence_text,
            decision_text,
        ))
    table = _table(("점검 장면", "학생의 시작", "남길 증거", "다음 결정"), tuple(rows), "middle-school-english-evidence-tracker")
    return f"""
<section class="middle-school-english-tracker" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '학부모 피드백과 누적 기록표'))}</h2>
<p>{escape(context.slug)}의 학부모 피드백은 매일 점수나 외운 양을 확인하기보다 <strong>{escape(focus)}</strong>의 증거를 주 1회 함께 읽는 방식으로 구성합니다. 학생이 적은 판단 근거와 수정 행동을 먼저 듣고, 보호자는 완료되지 않은 이유가 시간·이해·시작 지연 중 어느 쪽인지 질문합니다.</p>
<ul><li>{escape(context.slug)} 기록에는 정확한 집 주소를 적지 않습니다.</li><li>{escape(context.official_name)} 이름과 학년은 자료 구분에 필요한 범위에서만 사용합니다.</li><li>{escape(focus)} 상담에는 최근 학교 자료와 반복 오류만 먼저 준비합니다.</li><li>피드백은 잘한 행동 하나와 바꿀 행동 하나로 끝냅니다.</li><li>학교 일정이 바뀌면 분량보다 마감 순서를 먼저 고칩니다.</li><li>기록의 보관 목적과 공유 범위를 확인한 뒤 전달합니다.</li></ul>
<p>아래 표는 관찰·적용·비교·독립재현을 구분하기 위한 누적 기록지입니다. 정해진 날짜를 채우는 방식이 아니라 현재 학교 일정에 맞는 점검 장면을 골라 학생의 첫 행동과 수정 근거를 남깁니다. {escape(context.official_name)} 시험 기간에는 학교 자료를 우선해 순서를 바꿉니다.</p>
{table}
<p>{escape(context.slug)}의 누적 표는 성과를 보장하는 프로그램이 아닙니다. 출발 시점과 간격을 둔 시점에 같은 짧은 과제를 수행해 시작 행동·근거 설명·혼자 교정한 범위를 비교하고, 변화가 없으면 압박보다 과제 크기와 도움 시점을 먼저 수정합니다.</p>
</section>"""


def _links_section(context: MiddleSchoolEnglishContext, section_index: int) -> str:
    _, _, focus = _variant(context, section_index)
    links = context.internal_links
    link_text = ", ".join(f'<a href="/{escape(slug)}/">{escape(slug)}</a>' for slug in links)
    place = " ".join(item for item in (context.city, context.district, context.town) if item)
    return f"""
<section class="middle-school-english-links" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '공식 정보와 관련 페이지'))}</h2>
<p>{escape(context.slug)}에서 학교 일정·교육과정·평가 안내처럼 바뀔 수 있는 내용은 <a class="source-link" href="{escape(context.homepage)}" target="_blank" rel="noopener noreferrer external">{escape(context.official_name)} 공식 홈페이지</a>를 직접 확인하십시오. 이 링크는 정보 확인용 외부 출처이며 EduNext가 학교를 대표하거나 제휴했다는 뜻이 아닙니다. {escape(place)} 표기는 지역 탐색 범위일 뿐 통학 시간이나 배정을 보장하지 않습니다.</p>
<p>같은 학교 수학 학습과 지역 중등 영어 탐색은 {link_text}에서 확인할 수 있습니다. 본문 링크는 공식 홈페이지와 세 가지 탐색 목적에만 제한해 모든 키워드를 링크로 만드는 과도한 연결을 피했습니다.</p>
<p>{escape(context.official_name)}의 최신 자료와 학생이 받은 안내가 다르면 학생 자료를 먼저 대조합니다. <strong>{escape(focus)}</strong>은 학교 정보를 추정하는 문구가 아니라 확인된 자료를 학습 행동으로 바꾸는 이 페이지의 고유한 점검 관점입니다.</p>
</section>"""


def _faq_section(context: MiddleSchoolEnglishContext) -> str:
    primary = middle_school_english_focus(context.slug)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    questions = (
        (f"{context.slug}에서는 영어 학습을 무엇부터 확인하나요?", f"{context.official_name}의 실제 교과서·학습지·평가 안내를 먼저 모은 뒤 {_object(theme['evidence'])} 만드십시오. {method['start']}. 처음부터 문제 수를 늘리기보다 학생이 멈춘 문장과 판단 근거를 남기고, 일주일 뒤 같은 순서를 혼자 재현하는지 확인해야 {context.slug}의 출발점이 구체적으로 보입니다. 공시 통계는 학교 식별에만 사용하고 개인 수준은 현재 답안으로 판단합니다."),
        (f"{context.slug}에서 학교 홈페이지는 왜 확인해야 하나요?", f"{context.official_name}의 시험일·행사·교육과정과 평가 안내는 시기에 따라 바뀔 수 있기 때문입니다. EduNext 본문은 확정된 일정을 대신하지 않으므로 공식 홈페이지와 학생이 받은 안내를 대조해야 합니다. {method['record']}. 이렇게 해야 {context.slug} 계획이 추정 정보가 아니라 현재 자료를 기준으로 움직이며, 반이나 담당에 따른 차이도 무리하게 일반화하지 않습니다."),
        (f"{context.slug}에서 내신 본문과 누적 영어를 함께 준비할 수 있나요?", f"역할을 나누면 함께 준비할 수 있습니다. 시험 전에는 {context.official_name}에서 실제로 사용하는 본문과 자료의 어휘·문법·서술형 조건을 우선하고, 누적 독해와 듣기는 짧게 유지합니다. 시험 뒤에는 {_object(theme['action'])} 적용해 학교 자료에서 확인한 개념이 낯선 문장에서도 재현되는지 점검합니다. {context.slug} 기록에는 맞힌 수보다 근거를 혼자 설명한 범위를 남깁니다."),
        (f"{_object(context.slug)} 비교할 때 무엇을 질문해야 하나요?", f"교재와 숙제량보다 {_object(theme['problem'])} 어떤 증거로 구분할지 물어보십시오. 수업 뒤 학생이 혼자 할 행동, 기록을 다시 보는 날짜, 계획이 실패했을 때 바꿀 기준까지 답에 포함되어야 합니다. {method['review']}. 학교 이름만 반복하거나 상담 전에 점수 상승을 단정한다면 {context.slug} 학생에게 맞는 방식인지 확인하기 어렵습니다."),
        (f"학부모는 {context.slug} 진행을 어떻게 확인하면 좋나요?", f"점수 예상이나 외운 양을 매일 묻기보다 주 1회 판단 근거, 반복 오류, 다음 행동을 확인하십시오. 정확한 주소나 불필요한 개인정보를 먼저 공유할 필요는 없습니다. {context.official_name}, 학년, 실제 귀가 시각, 최근 학교 자료와 {theme['output']}만으로 시작하고, {context.slug} 기록의 변화가 없으면 분량보다 학습 계획과 도움 시점을 먼저 고칩니다."),
    )
    items = "\n".join(f"<h3>{escape(question)}</h3>\n<p>{escape(answer)}</p>" for question, answer in questions)
    return f"""
<section class="middle-school-english-faq" data-faq-focus="{escape(primary)}">
<h2>{escape(context.slug)} 영어 학습 FAQ</h2>
{items}
</section>"""


def build_middle_school_english_body(slug: str, source_body: str = "") -> str:
    context = middle_school_english_contexts()[slug]
    focus = middle_school_english_focus(slug)
    intro = f"""
<section class="middle-school-english-guide" data-content-version="middle-school-english-individual-v1" data-middle-school-english-focus="{escape(focus)}" data-official-school="{escape(context.official_name)}">
<h2>{escape(context.slug)}: {escape(context.official_name)} 영어 학습의 고유 점검 주제</h2>
<p>{escape(context.slug)}는 <strong>{escape(_object(focus))}</strong> 중심으로 구성했습니다. 학교명을 검색한 사용자가 필요한 것은 확인되지 않은 출제 경향이나 성과 약속이 아니라, {escape(context.official_name)}의 최신 공식 자료와 학생이 가진 교과서·학습지·평가 안내를 구분하고 현재 학습 행동을 점검하는 순서입니다. 이 페이지는 학교와 제휴하거나 학교를 대표하지 않으며 특정 결과를 보장하지 않습니다.</p>
<p>{escape(context.official_name)} 학생의 영어 계획은 같은 학교 안에서도 학년·과목 담당·귀가 시각·현재 이해도에 따라 달라집니다. {escape(context.slug)}에서는 {escape(_object(focus))} 하나의 관찰 관점으로 두고 중1·중2·중3, 어휘·문법·구문·독해, 교과서 본문·서술형·듣기·수행평가를 서로 다른 역할로 나누어 설명합니다.</p>
"""
    sections: list[str] = []
    for index, label in enumerate(SECTION_PURPOSES):
        if index == 1:
            sections.append(_profile_section(context, index))
        elif index == 2:
            sections.append(_grade_section(context, index))
        elif index == 7:
            sections.append(_schedule_section(context, index))
        elif index == 8:
            sections.append(_case_section(context, index))
        elif index == 9:
            sections.append(_decision_section(context, index))
        elif index == 10:
            sections.append(_tracker_section(context, index))
        elif index == 11:
            sections.append(_links_section(context, index))
        else:
            sections.append(_standard_section(context, index, label))
    return intro + "\n".join(sections) + "\n" + _faq_section(context) + "\n</section>"


def individualize_middle_school_english_body(body: str, slug: str) -> str:
    if not is_middle_school_english_slug(slug):
        return body
    return build_middle_school_english_body(slug, body)
