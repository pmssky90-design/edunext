from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path

from sitegen.utils import escape


LOCAL_MIDDLE_GENERAL_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등과외$")
CONTENT_VERSION = "middle-general-individual-v1"
CONTEXT_PATH = Path(__file__).resolve().parents[1] / "data" / "local_middle_school_context.json"
LEGACY_PATH = Path(__file__).resolve().parents[1] / "data" / "local_middle_general_legacy_unique.json"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _stable_index(slug: str, salt: str = "") -> int:
    return int(hashlib.sha256(f"{slug}|{salt}".encode("utf-8")).hexdigest()[:12], 16)


def _pick(values: tuple[str, ...], slug: str, salt: str) -> str:
    return values[_stable_index(slug, salt) % len(values)]


def _has_final_consonant(value: str) -> bool:
    for char in reversed(value.strip()):
        if "가" <= char <= "힣":
            return (ord(char) - ord("가")) % 28 != 0
    return False


def _object_form(value: str) -> str:
    return value + ("을" if _has_final_consonant(value) else "를")


def _topic_form(value: str) -> str:
    return value + ("은" if _has_final_consonant(value) else "는")


def _with_form(value: str) -> str:
    return value + ("과" if _has_final_consonant(value) else "와")


def is_local_middle_general_slug(slug: str) -> bool:
    return bool(LOCAL_MIDDLE_GENERAL_PATTERN.fullmatch(slug))


def _load_context() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    if not CONTEXT_PATH.exists():
        return {}, {}
    data = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    raw_pages = data.get("pages", {}) if isinstance(data, dict) else {}
    pages: dict[str, dict[str, object]] = {}
    if isinstance(raw_pages, dict):
        for english_slug, context in raw_pages.items():
            if isinstance(english_slug, str) and isinstance(context, dict):
                slug = english_slug.removesuffix("중등영어과외") + "중등과외"
                pages[slug] = context
    source = data.get("source", {}) if isinstance(data, dict) else {}
    return pages, source if isinstance(source, dict) else {}


MIDDLE_CONTEXT, MIDDLE_SOURCE = _load_context()
LOCAL_SLUGS = tuple(sorted(MIDDLE_CONTEXT))


def _load_legacy() -> dict[str, list[str]]:
    if not LEGACY_PATH.exists():
        return {}
    data = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
    pages = data.get("pages", {}) if isinstance(data, dict) else {}
    if not isinstance(pages, dict):
        return {}
    return {
        str(slug): [str(value) for value in values if isinstance(value, str)]
        for slug, values in pages.items()
        if isinstance(values, list)
    }


LEGACY_UNIQUE = _load_legacy()


STUDY_PACKS: tuple[dict[str, object], ...] = (
    {
        "label": "학교 일정과 평가 운영",
        "focuses": (
            "교과서 복습과 수행평가 마감을 한 주에 배치하기",
            "학교 시험 범위를 원본 자료부터 나누기",
            "수행평가와 지필평가 준비를 충돌 없이 운영하기",
            "과목별 마감일을 실제 행동 순서로 바꾸기",
            "시험 3주 전부터 복습 밀도를 단계적으로 높이기",
            "학교 유인물과 교과서의 역할을 구분하기",
            "평가 뒤 오답을 다음 단원 출발점으로 옮기기",
            "평일 복습과 주말 누적 점검의 역할을 나누기",
        ),
        "evidence": "학교 알림과 과목별 유인물, 교과서 표시, 제출 전 산출물, 평가 뒤 수정 기록의 날짜가 서로 이어지는지",
        "risk": "시험이 가까워진 뒤 새 자료를 늘리거나 모든 과목에 같은 문제 수를 배정하는 방식",
        "grade1": "중1은 시간표와 준비물, 과목별 공책의 위치를 먼저 익히고 하루 복습을 끝내는 기준을 한 문장으로 정합니다.",
        "grade2": "중2는 단원 누적과 수행평가가 겹치므로 마감·복습·재시도를 다른 칸에 두고 우선순위를 다시 고릅니다.",
        "grade3": "중3은 내신과 진학 준비를 같은 계획표에 무리하게 합치지 않고 현재 학교 평가와 다음 단계 준비를 주간 단위로 분리합니다.",
        "korean": "국어는 작품명보다 학교에서 다룬 질문과 근거 문장을 묶고, 서술형 답안을 조건·근거·결론 순서로 고칩니다.",
        "math": "수학은 시험 범위의 대표 예제와 첫 풀이를 연결하고 계산·조건·개념 오류의 재확인 날짜를 따로 둡니다.",
        "english": "영어는 본문·어휘·문법·서술형을 서로 다른 자료로 흩뜨리지 않고 교과서 문장에 다시 연결합니다.",
        "science": "과학은 실험과 자료 해석의 변인·단위·결론을 학교 활동지에서 다시 찾아 설명합니다.",
        "social": "사회는 연표·지도·도표와 핵심 개념을 한 쌍으로 묶어 암기와 자료 해석을 함께 확인합니다.",
        "assessment": "범위표를 받은 날에는 자료를 모으고, 2주 전에는 설명이 막힌 단원을 찾으며, 마지막 주에는 새 문제보다 학교 원본과 오답을 재확인합니다.",
        "case": "여러 마감이 한 주에 몰리자 쉬운 문제집부터 반복하고 학교 산출물을 늦게 시작한 상황",
        "transition": "고등학교에서 평가 범위가 넓어져도 원본 수집·주간 분할·오답 재현의 순서를 혼자 유지하는 준비로 연결합니다.",
    },
    {
        "label": "읽기와 서술형 표현",
        "focuses": (
            "긴 지시문을 과제 조건으로 분해하기",
            "교과 지문에서 주장과 근거를 구분하기",
            "서술형 답을 핵심어와 근거로 확장하기",
            "여러 문단의 관계를 표로 재구성하기",
            "낯선 어휘를 문맥과 교과 개념으로 연결하기",
            "읽은 내용을 자료 없이 다시 설명하기",
            "답의 범위를 질문 문장에서 먼저 정하기",
            "초안과 수정본 사이의 판단 변화를 기록하기",
        ),
        "evidence": "첫 읽기에서 표시한 질문·조건·근거와 말로 설명한 내용, 초안에서 고친 문장의 이유가 같은 판단을 보여 주는지",
        "risk": "지문을 여러 번 읽었지만 질문의 범위와 답을 뒷받침하는 문장을 구분하지 않는 방식",
        "grade1": "중1은 긴 교과서 문장을 핵심어와 예시로 나누고 질문이 요구하는 답의 범위를 먼저 표시합니다.",
        "grade2": "중2는 여러 문단의 관계와 자료의 역할을 비교하고 한 문단의 답에 근거 두 가지를 연결합니다.",
        "grade3": "중3은 제한된 시간 안에 질문·근거·결론을 선택하고 초안에서 빠진 조건을 스스로 고칩니다.",
        "korean": "국어는 문단 기능과 표현 효과를 구분하고 답의 근거가 되는 원문을 서술형 문장과 나란히 둡니다.",
        "math": "수학은 문장제의 조건과 구할 값을 자기 말로 바꾼 뒤 식을 세운 이유를 짧은 문장으로 남깁니다.",
        "english": "영어는 중심 문장과 세부 정보를 나누고 선택지의 범위가 본문 근거와 같은지 확인합니다.",
        "science": "과학은 관찰 사실·개념·결론을 다른 문장으로 써서 근거보다 큰 표현을 사용하지 않도록 합니다.",
        "social": "사회는 자료의 시기와 공간, 작성 목적을 읽고 교과 개념을 근거로 비교 문장을 완성합니다.",
        "assessment": "서술형은 정답 예시를 외우기보다 질문의 동사, 필요한 핵심어, 사용할 근거, 마지막 결론을 네 칸으로 점검합니다.",
        "case": "읽은 양은 많지만 서술형에서 질문과 무관한 내용을 길게 쓰고 근거를 빠뜨린 상황",
        "transition": "고등 교과의 긴 글과 논술형 문항을 만나기 전에 질문의 범위 안에서 근거를 선택하고 수정 이유를 말하는 습관으로 이어 갑니다.",
    },
    {
        "label": "개념과 자료 해석",
        "focuses": (
            "수학 풀이의 첫 판단과 검산을 연결하기",
            "과학 자료의 단위와 변인을 먼저 읽기",
            "그래프와 식을 같은 관계로 설명하기",
            "개념 오류와 계산 실수를 다른 방식으로 고치기",
            "도형 조건을 그림의 모양과 분리하기",
            "사회 자료의 비교 기준을 정확히 맞추기",
            "표와 그래프에서 말할 수 있는 범위를 구분하기",
            "공식을 적용한 이유를 교과 개념으로 복원하기",
        ),
        "evidence": "답을 가린 상태에서 조건·단위·관계를 말하고 표현이 달라진 문제에도 같은 개념을 선택하는지",
        "risk": "공식 이름과 계산 순서만 외운 뒤 표·그래프·문장의 조건이 바뀌어도 같은 절차를 반복하는 방식",
        "grade1": "중1은 수와 문자, 기본 도형, 자료 표현에서 기호와 단위가 뜻하는 내용을 말로 바꿉니다.",
        "grade2": "중2는 식·그래프·도형 조건을 연결하고 한 단계의 판단이 다음 단계에 필요한 이유를 표시합니다.",
        "grade3": "중3은 여러 개념이 함께 쓰인 문제에서 첫 선택과 검산 방법을 분리해 기록하고 간격을 두고 다시 풉니다.",
        "korean": "국어는 설명 글의 정의·예시·비교 구조를 표시해 수학과 과학의 조건 읽기에 활용합니다.",
        "math": "수학은 식·표·그래프·도형을 오가며 각 표현이 같은 관계를 나타내는 근거를 설명합니다.",
        "english": "영어는 수량·비교·원인 표현이 자료 해석 문장에서 어떤 관계를 만드는지 확인합니다.",
        "science": "과학은 변인, 측정 단위, 예상, 결과, 결론을 분리하고 자료가 뒷받침하는 범위까지만 말합니다.",
        "social": "사회는 서로 다른 규모와 시기의 자료를 그대로 비교하지 않고 전체 수와 기준 시점을 먼저 맞춥니다.",
        "assessment": "평가 뒤에는 맞고 틀림보다 첫 판단, 사용한 개념, 놓친 조건, 검산 여부를 기록해 다음 문제의 시작 행동을 정합니다.",
        "case": "계산은 빠르지만 문제의 단위와 자료 범위를 놓쳐 비슷한 유형에서 같은 실수를 반복한 상황",
        "transition": "고등 과정의 추상적인 기호와 복합 자료를 만나기 전에 표현이 바뀌어도 개념의 관계를 복원하는 힘을 확인합니다.",
    },
    {
        "label": "영어와 교과 문해력",
        "focuses": (
            "영어 문장 구조를 뜻과 함께 설명하기",
            "어휘 암기를 교과서 문장 회상으로 바꾸기",
            "듣기 선택지와 실제 근거를 구분하기",
            "독해에서 중심 문장과 세부 정보를 나누기",
            "영작 초안의 어순과 의미를 함께 고치기",
            "국어 읽기 전략을 영어 지문에 옮기기",
            "문법 개념을 새로운 예문으로 검증하기",
            "영어 수행평가의 내용과 전달을 단계별로 준비하기",
        ),
        "evidence": "외운 답이 아니라 문장 속 단서와 구조를 가리키고, 어휘·문법·독해·듣기의 오류 원인을 서로 다르게 설명하는지",
        "risk": "단어 수와 문제 수만 늘리면서 문장 뜻을 복원하거나 틀린 선택지의 이유를 설명하지 않는 방식",
        "grade1": "중1은 교과서의 짧은 문장을 소리·뜻·어순으로 나누고 배운 표현을 다른 장면에 바꾸어 씁니다.",
        "grade2": "중2는 문법과 독해를 분리하지 않고 구조가 글의 의미와 선택지 판단에 미치는 영향을 확인합니다.",
        "grade3": "중3은 긴 글의 단락 기능과 근거 문장을 제한 시간 안에 선택하고 고등 영어에 필요한 회상 간격을 만듭니다.",
        "korean": "국어는 질문의 범위와 근거 문장을 찾는 방법을 영어 독해에 옮기고 두 언어의 표현 차이를 설명합니다.",
        "math": "수학은 수량·시간·비교를 나타내는 영어 문장을 실제 관계와 연결해 의미를 확인합니다.",
        "english": "영어는 첫 회상, 교과서 확인, 새 문장 적용, 간격 재현의 네 단계로 어휘와 구조를 함께 복습합니다.",
        "science": "과학은 영어로 된 간단한 자료 제목과 단위를 읽을 때 아는 낱말만 이어 붙이지 않고 관계를 봅니다.",
        "social": "사회는 안내문과 도표의 목적·대상·핵심 정보를 구분해 실용문 독해와 연결합니다.",
        "assessment": "영어 평가는 본문 회상, 문법 판단, 낯선 글의 근거, 듣기 메모, 서술형 산출물을 서로 다른 완료 기준으로 점검합니다.",
        "case": "단어 시험은 통과하지만 교과서 문장을 가리면 뜻과 어순을 설명하지 못해 독해가 늦어진 상황",
        "transition": "고등 영어의 어휘량을 먼저 늘리기보다 문장을 읽고 구조를 설명하며 간격을 두고 다시 회상하는 복습으로 연결합니다.",
    },
    {
        "label": "자기주도 실행과 시간 관리",
        "focuses": (
            "귀가 뒤 공부 시작 신호를 학생이 직접 정하기",
            "과제를 작은 완료 행동으로 분해하기",
            "예상 시간과 실제 시간을 비교해 계획 고치기",
            "도움이 필요한 지점을 구체적인 질문으로 바꾸기",
            "밀린 과제를 주말에 몰지 않는 재배치 기준 만들기",
            "스마트폰 종료와 첫 학습 행동 사이를 줄이기",
            "공부가 끊긴 뒤 다음 시작점을 기록하기",
            "부모의 지시를 학생의 선택과 설명으로 바꾸기",
        ),
        "evidence": "보호자의 반복 지시 없이 자료·순서·종료 기준을 말하고 계획이 어긋난 이유와 다음 행동을 스스로 고르는지",
        "risk": "공부시간을 길게 잡은 뒤 시작하지 못한 이유와 남은 과제를 옮길 기준을 기록하지 않는 방식",
        "grade1": "중1은 과목이 늘어난 환경에서 준비물·마감·첫 복습을 한곳에 모으고 가장 짧은 행동부터 시작합니다.",
        "grade2": "중2는 과목별 예상 시간과 실제 시간을 비교해 어려운 과제와 단순 반복을 다른 시간대에 배치합니다.",
        "grade3": "중3은 내신·수행평가·진학 준비 가운데 이번 주에 반드시 끝낼 항목과 미룰 항목을 근거와 함께 고릅니다.",
        "korean": "국어는 읽기·문제 적용·서술형 수정의 종료 기준을 나누어 긴 과제를 다시 시작하기 쉽게 만듭니다.",
        "math": "수학은 문제 수 대신 예제 설명·기본 적용·오류 재시도의 세 단위로 과제를 배치합니다.",
        "english": "영어는 어휘 회상·문장 읽기·듣기·쓰기 가운데 피로가 있어도 유지할 최소 행동을 정합니다.",
        "science": "과학은 실험 자료 읽기와 개념 복습을 다른 날로 흩뜨리지 않고 한 기록 안에서 연결합니다.",
        "social": "사회는 암기할 개념과 해석할 자료를 나누고 짧은 복습과 주말 누적 점검의 역할을 구분합니다.",
        "assessment": "계획표에는 시작 시각보다 사용할 자료, 첫 행동, 종료 기준, 다시 볼 날짜를 적고 실제 기록과 매주 비교합니다.",
        "case": "해야 할 일이 많아 보이면 책상 정리와 쉬운 과제만 반복하다 중요한 복습을 늦게 시작한 상황",
        "transition": "고등학교에서 스스로 관리할 시간이 늘어날 때 마감·우선순위·도움 요청·재배치를 학생 언어로 설명하는 준비가 됩니다.",
    },
    {
        "label": "수행평가와 탐구 과정",
        "focuses": (
            "수행평가 조건표를 실제 제작 순서로 바꾸기",
            "발표 내용을 근거와 시간에 맞게 구조화하기",
            "탐구 질문과 자료 출처를 함께 기록하기",
            "모둠 활동에서 개인의 학습 흔적 남기기",
            "초안·피드백·수정본의 변화를 설명하기",
            "실험 결과를 예상과 구분해 보고서로 쓰기",
            "여러 자료를 비교해 결론의 범위를 정하기",
            "완성품보다 준비 과정의 누락을 먼저 찾기",
        ),
        "evidence": "조건표의 각 항목이 초안·자료·발표·수정본에 반영되고 학생이 선택한 자료와 고친 이유를 설명하는지",
        "risk": "제출 직전에 결과물의 모양만 다듬고 자료 출처, 역할, 근거, 수정 과정을 남기지 않는 방식",
        "grade1": "중1은 조건표의 동사를 읽고 준비물·기한·분량·발표 역할을 체크 항목으로 바꿉니다.",
        "grade2": "중2는 여러 자료의 출처와 공통점·차이를 확인하고 자신의 결론이 자료 범위를 넘지 않는지 봅니다.",
        "grade3": "중3은 내신 일정과 수행평가 제작 시간을 분리하고 피드백 뒤 바꾼 내용과 이유를 최종본에 남깁니다.",
        "korean": "국어는 발표와 보고서의 주장·근거·예시를 구조화하고 인용한 자료와 자신의 판단을 구분합니다.",
        "math": "수학은 조사한 값을 표와 그래프로 바꾸며 축·단위·전체 수가 정확한지 확인합니다.",
        "english": "영어는 발표문을 의미 단위로 나누고 발음·내용·시간을 한 번에 고치지 않고 차례로 점검합니다.",
        "science": "과학은 예상·변인·관찰 결과·해석을 다른 칸에 기록하고 결과에 맞추어 예상을 바꾸지 않습니다.",
        "social": "사회는 자료의 작성 시기와 목적, 출처를 확인해 서로 다른 관점을 근거와 함께 비교합니다.",
        "assessment": "제출일까지 역산해 조건 확인, 자료 선택, 첫 산출물, 피드백, 수정, 최종 점검의 여섯 마감으로 나눕니다.",
        "case": "완성품은 제출했지만 조건 하나와 자료 출처를 빠뜨리고 자신의 선택을 설명하지 못한 상황",
        "transition": "고등학교의 탐구·발표·보고서에서도 결과만 제출하지 않고 자료 선택과 수정 과정을 증거로 남기는 준비가 됩니다.",
    },
    {
        "label": "오답과 간격 복습",
        "focuses": (
            "틀린 이유를 개념·조건·전략·실행으로 나누기",
            "오답을 같은 날 반복하지 않고 간격을 두고 복원하기",
            "맞힌 문제의 불확실한 판단까지 표시하기",
            "시험 뒤 단원 연결표로 다음 복습 정하기",
            "힌트가 있던 답과 독립적으로 재현한 답을 구분하기",
            "실수의 첫 위치를 찾아 한 행동만 바꾸기",
            "오답 노트를 베끼기보다 질문을 다시 만들기",
            "재시험보다 설명과 변형 적용으로 이해 확인하기",
        ),
        "evidence": "처음 틀린 위치와 도움의 종류, 수정 근거, 간격을 둔 재현 결과가 한 기록에서 비교되는지",
        "risk": "정답 풀이를 깨끗하게 옮겨 적은 뒤 같은 날 바로 풀어 익숙함을 이해로 판단하는 방식",
        "grade1": "중1은 틀린 답을 지우기 전에 처음 막힌 문장과 사용한 도움을 표시하고 짧은 재시도 날짜를 정합니다.",
        "grade2": "중2는 누적 단원의 오류를 개념·조건·전략·실행으로 나누어 다음 단원과 연결되는 항목을 먼저 봅니다.",
        "grade3": "중3은 맞힌 문제도 근거가 불확실했다면 표시하고 제한 시간 뒤 독립적으로 첫 판단을 복원합니다.",
        "korean": "국어는 틀린 선택지의 범위와 원문 근거를 비교하고 서술형에서 빠진 조건을 질문 문장으로 되돌립니다.",
        "math": "수학은 풀이 첫 줄과 오류가 생긴 줄을 나누고 다른 숫자에서도 같은 원리를 사용할 수 있는지 봅니다.",
        "english": "영어는 오답을 어휘·구조·내용·근거·시간으로 나누어 서로 다른 복습 행동을 선택합니다.",
        "science": "과학은 개념을 모른 경우와 자료의 단위·변인을 놓친 경우를 구분해 재확인 자료를 다르게 고릅니다.",
        "social": "사회는 개념 암기 오류와 지도·연표·도표 해석 오류를 나누어 근거 자료를 다시 읽습니다.",
        "assessment": "평가 직후 분류하고 이틀 뒤 도움 없이 복원하며 일주일 뒤 표현이 바뀐 문제에 적용해 세 결과를 비교합니다.",
        "case": "오답 노트는 많이 만들었지만 정답을 베껴 쓴 뒤 같은 개념에서 다시 멈춘 상황",
        "transition": "고등 과정의 누적 학습에서 오답의 양보다 다시 설명하고 변형 문제에 적용한 간격 기록을 사용하는 준비가 됩니다.",
    },
    {
        "label": "학습 감정과 생활 리듬",
        "focuses": (
            "평가 불안을 준비 행동과 분리해 기록하기",
            "학습 피로와 이해 부족을 같은 문제로 묶지 않기",
            "친구 관계로 흔들린 날의 최소 학습 유지하기",
            "어려운 과제에서 도움을 구체적으로 요청하기",
            "실수를 숨기지 않고 재시도 날짜 남기기",
            "수면과 귀가 시각에 맞춰 과목 순서 조정하기",
            "잘하는 과목의 시작 전략을 취약 과목에 옮기기",
            "점수 대화를 과정 질문으로 전환하기",
        ),
        "evidence": "어려웠던 감정과 실제로 멈춘 학습 행동, 사용한 도움, 다시 시작한 조건을 서로 다른 문장으로 말하는지",
        "risk": "피곤함·불안·개념 공백·시작 지연을 모두 의지 문제로 해석하고 공부시간부터 늘리는 방식",
        "grade1": "중1은 새로운 학교생활의 피로와 과제 이해를 분리하고 귀가 뒤 회복과 첫 복습의 순서를 관찰합니다.",
        "grade2": "중2는 과목 난도가 높아질 때 자신감 표현보다 막힌 개념과 도움을 요청한 문장을 구체적으로 남깁니다.",
        "grade3": "중3은 평가 결과와 진학 부담을 한꺼번에 다루지 않고 이번 주에 바꿀 행동 하나와 유지할 생활 기준을 고릅니다.",
        "korean": "국어는 이해되지 않은 문장을 질문으로 바꾸고 자신이 해석한 부분과 원문 근거를 나누어 말합니다.",
        "math": "수학은 틀린 풀이를 지우기 전에 맞는 줄과 달라진 줄을 찾아 도움을 요청할 지점을 좁힙니다.",
        "english": "영어는 들리지 않음·뜻을 모름·말하기 부담을 구분하고 각각 다른 짧은 재시도를 선택합니다.",
        "science": "과학은 결과를 외우기 전에 예상과 달라진 장면을 말해 실수를 탐구 질문으로 바꿉니다.",
        "social": "사회는 많은 내용을 외우려는 부담을 개념·자료·시간 순서로 나누어 최소 복습을 정합니다.",
        "assessment": "시험 점수를 묻기 전에 준비한 자료, 혼자 시작한 행동, 도움을 받은 지점, 다음 재시도 날짜를 차례로 확인합니다.",
        "case": "시험 결과가 낮은 날 공부를 완전히 미루거나 부모의 질문에 답하지 않아 다음 계획도 세우지 못한 상황",
        "transition": "고등학교의 성적 변동이 커져도 결과와 감정을 분리하고 도움 요청과 재시도 행동을 유지하는 준비가 됩니다.",
    },
    {
        "label": "고등 전환과 누적 공백",
        "focuses": (
            "현재 학년의 공백과 고등 선행을 구분하기",
            "중학교 교과 기록을 고등 학습 계획으로 옮기기",
            "과목별 독립 복습 능력을 전환 기준으로 삼기",
            "누적 개념을 설명한 뒤 다음 난도로 이동하기",
            "고등 시간표 전에 우선순위 언어 익히기",
            "교재가 달라도 유지할 학습 절차 만들기",
            "중3 내신과 다음 단계 준비의 비중 조정하기",
            "긴 평가 범위를 주간 단위로 스스로 나누기",
        ),
        "evidence": "현재 교과서의 핵심 개념을 자료 없이 설명하고 과목에 따라 읽기·풀이·암기·재시도 절차를 다르게 선택하는지",
        "risk": "현재 학년의 설명 공백을 확인하지 않고 고등 교재의 진도와 문제 수부터 늘리는 방식",
        "grade1": "중1은 과목별 자료 정리와 하루 복습을 끝내는 경험을 쌓아 학년이 올라가도 유지할 기본 절차를 만듭니다.",
        "grade2": "중2는 누적 개념과 새 단원의 연결을 설명하고 취약 과목의 재시도 간격을 스스로 정합니다.",
        "grade3": "중3은 현재 내신·누적 공백·고등 준비를 세 칸에 두고 독립적으로 유지한 행동이 확인될 때 다음 난도를 넓힙니다.",
        "korean": "국어는 긴 지문에서 질문과 근거를 선택하고 교과별 서술형에 필요한 설명 구조를 유지합니다.",
        "math": "수학은 중학교의 식·함수·도형·자료 개념을 식과 문장으로 복원해 고등 선수 개념의 빈칸을 찾습니다.",
        "english": "영어는 단어 암기와 문장 이해, 듣기와 쓰기의 목적을 나누고 자료 없이 회상하는 간격을 만듭니다.",
        "science": "과학은 개념과 실험 자료를 연결해 현상을 설명하고 새로운 단원의 원리를 이전 기록과 비교합니다.",
        "social": "사회는 시기·공간·자료를 함께 읽고 여러 단원의 공통 개념을 근거로 비교합니다.",
        "assessment": "전환 준비는 선행 진도보다 자료 선택, 마감 확인, 질문 작성, 간격 복습을 혼자 수행한 기록으로 판단합니다.",
        "case": "고등 문제집은 시작했지만 현재 교과서의 누적 개념을 설명하지 못해 두 계획이 함께 밀린 상황",
        "transition": "고등학교 입학 전에는 앞선 진도보다 현재 학습을 혼자 시작·설명·수정·재현하는 절차가 남는지 확인합니다.",
    },
)


LENSES: tuple[dict[str, str], ...] = (
    {"label": "원본 대조", "question": "학생의 기억보다 교과서·공책·학교 자료에 남은 첫 흔적을 먼저 비교합니다.", "record": "도움 전 원본과 도움 뒤 수정본을 나란히 두고 달라진 한 줄에 날짜를 적습니다.", "parent": "부모는 결과를 평가하지 않고 두 기록에서 학생이 직접 바꾼 부분을 질문합니다."},
    {"label": "시간 간격", "question": "같은 날의 익숙함과 며칠 뒤의 독립 재현을 다른 결과로 봅니다.", "record": "첫 수행, 이틀 뒤 회상, 일주일 뒤 변형 적용을 같은 기준표에 남깁니다.", "parent": "부모는 오늘의 정답보다 다시 볼 날짜와 다음 시작점을 학생이 정했는지 확인합니다."},
    {"label": "도움의 양", "question": "힌트의 종류와 횟수를 남겨 혼자 한 범위와 도움받은 범위를 구분합니다.", "record": "질문, 예시, 선택지, 정답 확인 중 어떤 도움 뒤에 행동이 이어졌는지 표시합니다.", "parent": "부모는 답을 설명하기 전에 학생이 필요한 도움을 한 문장으로 요청하게 합니다."},
    {"label": "표현 전환", "question": "말·글·표·식 가운데 표현을 바꾸어도 같은 개념을 유지하는지 살핍니다.", "record": "처음 사용한 표현과 바꾼 표현, 바꾸면서 빠진 조건을 세 칸에 적습니다.", "parent": "부모는 맞았는지보다 같은 내용을 다른 방식으로 설명할 수 있는지 묻습니다."},
    {"label": "첫 판단", "question": "정답을 보기 전에 고른 첫 자료와 첫 행동이 문제의 요구와 맞는지 봅니다.", "record": "처음 선택, 멈춘 위치, 수정 근거, 다음 선택을 지우지 않고 순서대로 남깁니다.", "parent": "부모는 왜 틀렸는지 추궁하기보다 처음 무엇을 보고 시작했는지 듣습니다."},
    {"label": "완료 기준", "question": "시간과 분량 대신 학생이 설명·수정·제출까지 마쳤다고 판단할 행동을 정합니다.", "record": "시작 전 완료 기준과 실제 종료 상태를 비교하고 남은 행동은 다음 계획으로 옮깁니다.", "parent": "부모는 오래 앉았는지보다 학생이 정한 종료 기준을 스스로 확인했는지 봅니다."},
    {"label": "전이 확인", "question": "익숙한 예제에서 성공한 방법을 조건이 달라진 과제에도 선택하는지 확인합니다.", "record": "원래 문제와 바뀐 문제의 공통 조건, 달라진 조건, 새로 고른 전략을 기록합니다.", "parent": "부모는 비슷한 문제를 더 주기 전에 무엇이 달라졌는지 학생에게 설명하게 합니다."},
    {"label": "재시작 가능성", "question": "계획이 끊긴 뒤 실패로 끝내지 않고 남은 자료와 다음 행동을 다시 정하는지 봅니다.", "record": "중단 이유, 남은 일, 다시 시작할 시각, 첫 행동을 짧은 문장으로 남깁니다.", "parent": "부모는 밀린 양을 한꺼번에 요구하지 않고 학생이 고른 재시작 행동을 확인합니다."},
)


# Each page receives a different section-to-theme order. Across these 69 rows,
# no pair uses the same theme in more than three of nine section positions.
PACK_ORDERS: tuple[tuple[int, ...], ...] = (
    (4, 3, 8, 6, 0, 1, 7, 5, 2), (0, 2, 8, 4, 3, 5, 1, 7, 6),
    (7, 8, 2, 4, 6, 5, 3, 0, 1), (8, 0, 4, 6, 1, 7, 3, 2, 5),
    (3, 4, 2, 0, 5, 8, 6, 7, 1), (6, 4, 1, 8, 0, 3, 7, 2, 5),
    (7, 6, 5, 0, 4, 1, 3, 8, 2), (5, 2, 7, 3, 8, 6, 4, 0, 1),
    (1, 7, 4, 0, 6, 2, 8, 3, 5), (3, 6, 7, 1, 8, 0, 2, 4, 5),
    (0, 4, 6, 2, 1, 5, 7, 3, 8), (8, 2, 1, 5, 7, 3, 4, 6, 0),
    (7, 1, 5, 8, 2, 0, 6, 3, 4), (1, 0, 7, 3, 5, 4, 6, 2, 8),
    (2, 1, 0, 6, 3, 4, 5, 8, 7), (1, 0, 6, 5, 4, 3, 8, 7, 2),
    (1, 5, 8, 7, 0, 6, 4, 2, 3), (4, 0, 5, 8, 3, 6, 2, 1, 7),
    (3, 0, 1, 2, 8, 6, 7, 5, 4), (2, 0, 6, 4, 5, 7, 1, 8, 3),
    (5, 1, 8, 2, 4, 3, 7, 0, 6), (6, 7, 3, 5, 1, 0, 4, 2, 8),
    (1, 6, 3, 2, 7, 4, 0, 8, 5), (4, 5, 6, 0, 3, 2, 7, 8, 1),
    (3, 2, 4, 1, 0, 5, 8, 6, 7), (6, 3, 5, 8, 1, 4, 0, 7, 2),
    (7, 0, 3, 8, 4, 2, 1, 6, 5), (2, 8, 0, 5, 6, 3, 7, 1, 4),
    (2, 7, 8, 3, 0, 5, 6, 4, 1), (8, 4, 3, 1, 7, 5, 2, 0, 6),
    (3, 2, 6, 7, 4, 0, 1, 5, 8), (4, 1, 7, 5, 3, 8, 0, 2, 6),
    (0, 2, 3, 5, 6, 7, 8, 4, 1), (2, 6, 8, 0, 1, 3, 4, 7, 5),
    (3, 5, 0, 2, 6, 8, 1, 4, 7), (8, 3, 0, 7, 4, 5, 6, 1, 2),
    (5, 4, 2, 7, 8, 1, 0, 3, 6), (4, 1, 3, 7, 8, 2, 6, 5, 0),
    (0, 8, 6, 7, 2, 4, 3, 1, 5), (6, 8, 2, 0, 1, 7, 5, 3, 4),
    (6, 5, 4, 7, 3, 1, 8, 0, 2), (6, 2, 8, 0, 5, 4, 7, 1, 3),
    (5, 6, 0, 1, 4, 7, 8, 2, 3), (8, 5, 3, 6, 2, 4, 1, 7, 0),
    (3, 7, 5, 4, 2, 6, 0, 8, 1), (5, 3, 1, 0, 7, 6, 8, 4, 2),
    (7, 8, 0, 1, 3, 2, 4, 5, 6), (2, 5, 6, 1, 0, 8, 3, 7, 4),
    (0, 3, 7, 8, 5, 1, 2, 6, 4), (6, 3, 0, 4, 7, 8, 5, 2, 1),
    (5, 4, 8, 3, 2, 0, 1, 6, 7), (2, 8, 4, 0, 7, 1, 6, 5, 3),
    (5, 2, 3, 6, 4, 8, 0, 1, 7), (1, 8, 7, 6, 4, 5, 2, 3, 0),
    (0, 7, 1, 3, 8, 4, 5, 6, 2), (4, 3, 5, 0, 6, 7, 1, 2, 8),
    (1, 8, 4, 2, 5, 0, 3, 7, 6), (8, 6, 1, 7, 5, 2, 0, 4, 3),
    (4, 6, 7, 8, 2, 5, 1, 0, 3), (8, 3, 4, 5, 0, 6, 2, 7, 1),
    (0, 1, 5, 4, 7, 2, 3, 6, 8), (1, 5, 2, 8, 3, 7, 6, 4, 0),
    (7, 4, 1, 3, 6, 8, 2, 5, 0), (8, 0, 7, 4, 6, 1, 5, 3, 2),
    (4, 6, 2, 3, 7, 0, 5, 1, 8), (3, 8, 1, 6, 5, 7, 4, 0, 2),
    (6, 4, 5, 2, 8, 7, 3, 1, 0), (1, 3, 6, 0, 8, 4, 2, 5, 7),
    (7, 1, 3, 2, 0, 6, 5, 4, 8),
)


def _assignment(slug: str) -> tuple[dict[str, object], str, dict[str, str], int]:
    try:
        index = LOCAL_SLUGS.index(slug)
    except ValueError:
        index = _stable_index(slug, "assignment") % 69
    pack = STUDY_PACKS[(index // 8) % len(STUDY_PACKS)]
    focuses = pack["focuses"]
    assert isinstance(focuses, tuple)
    focus = str(focuses[index % len(focuses)])
    return pack, focus, LENSES[index % len(LENSES)], index


def _place(slug: str) -> tuple[str, str, str]:
    location = slug.removesuffix("중등과외")
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    return location, city, location.removeprefix(city)


def build_local_middle_general_meta(slug: str, body: str = "") -> tuple[str, str]:
    if not is_local_middle_general_slug(slug):
        return slug, _clean(body)[:155]
    pack, focus, lens, _ = _assignment(slug)
    title = f"{slug} | {focus}·중1~3 학습 점검"
    description = (
        f"{slug}에서 {_object_form(focus)} 중심으로 중1·중2·중3 학습, 국어·수학·영어·과학·사회, "
        f"학교 평가 자료와 {lens['label']} 기록, 수행평가·오답·고등 전환을 단계별로 점검하는 안내입니다."
    )
    return title[:60], description[:160]


def _school_section(slug: str, location: str, focus: str, school_pack: dict[str, object], lens: dict[str, str]) -> str:
    context = MIDDLE_CONTEXT.get(slug, {})
    schools = context.get("schools", []) if isinstance(context, dict) else []
    schools = [item for item in schools if isinstance(item, dict)][:4] if isinstance(schools, list) else []
    source_name = str(MIDDLE_SOURCE.get("workbook") or "2025년 학교별 주요통계 자료")
    if schools:
        items = "".join(
            f'<li><a class="source-link" href="{escape(str(item.get("homepage") or ""))}" target="_blank" rel="noopener noreferrer external">{escape(str(item.get("school_name") or "중학교"))} 공식 홈페이지</a></li>'
            for item in schools
            if item.get("homepage") and item.get("school_name")
        )
        names = ", ".join(str(item.get("school_name")) for item in schools if item.get("school_name"))
        detail = (
            f"자료에서 {location} 페이지와 직접 연결된 학교는 {names}입니다. 이 연결은 학교 선택이나 배정, 재학 여부, 수업 효과를 뜻하지 않습니다. "
            f"시험일·수행평가·방학 일정은 학생이 실제로 재학 중인 학교의 최신 공지와 대조해야 합니다."
        )
    else:
        items = ""
        detail = (
            f"현재 자료에는 {location} 페이지와 직접 연결해 제시할 중학교 공식 홈페이지가 없습니다. 인접 학교를 임의로 추정하지 않으며, "
            f"학생이 재학 중인 학교명과 공식 홈페이지를 직접 확인한 뒤 학사일정만 {focus} 계획에 사용합니다."
        )
    return (
        f'<section class="middle-general-school-context" data-school-count="{len(schools)}" data-school-source="2025-school-statistics">'
        f'<h2>{escape(location)} 학교 자료를 {escape(focus)} 계획에 사용하는 범위</h2>'
        f'<p>{escape(source_name)}의 중학교 항목을 학교명과 공식 홈페이지 확인에만 사용했습니다. 지역명만으로 학생의 학교, 수준, 통학권을 단정하지 않습니다. {escape(detail)} {escape(str(school_pack["assessment"]))} {escape(lens["question"])}</p>'
        + (f'<ul>{items}</ul>' if items else "")
        + "</section>"
    )


def _context_links(location: str, city: str, focus: str) -> str:
    links = (
        (f"/{city}중등과외/", f"{city} 전체 중등 학습 흐름"),
        (f"/{location}중등영어과외/", f"{location} 중등영어 점검"),
        (f"/{location}중등수학과외/", f"{location} 중등수학 점검"),
    )
    items = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for href, label in links)
    return (
        '<aside class="middle-general-context-links" data-link-count="3">'
        f'<h2>{escape(focus)} 확인 뒤 이어 볼 세 페이지</h2>'
        f'<p>{escape(location)}의 전체 중등 계획을 과목별로 좁힐 때만 아래 링크를 사용합니다. 같은 문장에서 여러 키워드를 반복해 연결하지 않습니다.</p>'
        f'<ul>{items}</ul></aside>'
    )


def _legacy_unique_section(slug: str, location: str, focus: str) -> str:
    paragraphs = LEGACY_UNIQUE.get(slug, [])
    if not paragraphs:
        return ""
    content = "".join(f"<p>{escape(value)}</p>" for value in paragraphs)
    return (
        f'<section class="middle-general-local-notes" data-local-note-count="{len(paragraphs)}">'
        f'<h2>{escape(location)} 중학생의 기존 지역 학습 장면과 {escape(focus)} 연결</h2>'
        f'<p>{escape(location)} 페이지에서 기존에 다루던 학습 장면 가운데 다른 지역에 반복 적용되지 않은 내용을 남겼습니다. 아래 내용은 지역 학생 전체의 특성이나 결과를 단정하는 사례가 아니며, 실제 학교 자료와 생활 기록을 확인할 때 사용할 질문의 배경입니다.</p>'
        + content
        + "</section>"
    )


def _faq(
    slug: str,
    location: str,
    focus: str,
    packs: tuple[dict[str, object], ...],
    lenses: tuple[dict[str, str], ...],
) -> str:
    first, second, third, fourth, fifth = packs[:5]
    pairs = (
        (
            f"{location}중등과외에서 {_object_form(focus)} 가장 먼저 어떻게 확인하나요?",
            f"{location} 학생의 교과서·공책·학교 유인물 가운데 최근 자료 하나를 고르고 {first['evidence']}를 확인합니다. {first['assessment']} {lenses[0]['question']} 처음부터 공부시간과 문제 수를 늘리지 말고 일주일 동안 한 행동만 바꾸어 도움 전후 기록을 비교해야 현재 문제와 조정할 행동이 섞이지 않습니다.",
        ),
        (
            f"{location} 중1·중2·중3은 {focus} 계획을 똑같이 적용해도 되나요?",
            f"같은 {focus} 주제라도 학년별 책임을 다르게 봅니다. {second['grade1']} {second['grade2']} {second['grade3']} {lenses[1]['question']} {location} 학생의 학년명만으로 난도를 정하지 않고 현재 교과서에서 자료 없이 설명 가능한 범위와 도움의 양을 먼저 확인합니다.",
        ),
        (
            f"{location}중등과외와 학교 숙제는 {focus} 과정에서 어떻게 나누나요?",
            f"학교 숙제는 당일 수업과 평가 요구를 보여 주는 원본으로 사용합니다. {third['korean']} {third['math']} {location} 학생은 학교 자료에서 막힌 첫 위치를 다음 질문으로 옮기고, {lenses[2]['record']} 별도 학습은 설명·변형 적용·간격 재현을 확인하는 보완 활동으로 두며 두 활동의 목적이 겹치면 분량보다 역할을 먼저 줄입니다.",
        ),
        (
            f"{location} 학부모는 {focus} 점검 때 어떤 말을 줄여야 하나요?",
            f"{location}의 {focus} 대화에서 ‘왜 아직 안 했니’나 ‘몇 문제 했니’처럼 결과와 속도만 묻는 말은 {fourth['risk']}을 강화할 수 있습니다. {fourth['case']} 이런 장면을 피하려면 사용할 자료, 첫 행동, 멈춘 지점, 다음 재시도 시각을 학생이 설명하게 합니다. {lenses[3]['parent']} 정확한 주소나 성적 전체를 공유하지 않아도 최근 학교 자료와 일주일 행동 기록으로 먼저 비교할 수 있습니다.",
        ),
        (
            f"{location} 중학생의 {_object_form(focus)} 고등학교 준비와 언제 연결하나요?",
            f"현재 교과서의 핵심 내용을 자료 없이 설명하고 과목에 맞는 복습 방법을 학생이 고를 수 있을 때 다음 난도를 조금씩 넓힙니다. {fifth['english']} {fifth['transition']} {lenses[4]['question']} {location}에서는 특정 학교의 진도나 평가 방식을 지역명만으로 추정하지 않고 실제 학교 공지와 학생 기록을 대조하며, 선행량이 아니라 독립적으로 다시 시작하고 수정한 행동을 전환 기준으로 사용합니다.",
        ),
    )
    content = "".join(f'<h3>{escape(q)}</h3><p>{escape(a)}</p>' for q, a in pairs)
    return f'<section class="middle-general-faq" data-faq-focus="{escape(focus)}"><h2>{escape(location)} {escape(focus)} 중등 학습 FAQ</h2>{content}</section>'


def _focus_deep_dive(
    location: str,
    focus: str,
    material: str,
    evidence: str,
    risk: str,
    compare_days: str,
    lens: dict[str, str],
) -> str:
    rows = (
        (
            "첫 자료 고르기",
            f"{location} 학생은 {focus} 점검을 시작할 때 새 문제집보다 {material} 가운데 최근 자료 하나를 고릅니다. 이 자료에서 날짜·과목·학교 요구를 먼저 읽고, {focus}에 필요한 첫 행동을 학생 말로 한 문장에 적습니다. 자료가 여러 개라면 가장 급한 것이 아니라 현재 판단과 수정 흔적을 함께 볼 수 있는 것을 우선합니다.",
        ),
        (
            "현재 행동 촬영하기",
            f"{location}의 {focus} 기록은 잘한 결과만 모으지 않습니다. 도움을 주기 전 학생이 펼친 페이지, 표시한 조건, 처음 쓴 문장이나 식, 멈춘 위치를 순서대로 남깁니다. {evidence}가 보이지 않으면 능력을 추정하지 않고 자료 선택이나 질문 이해부터 다시 확인합니다. 이 기준이 있어야 다음 변화가 실제 행동 변화인지 비교할 수 있습니다.",
        ),
        (
            "완료 문장 정하기",
            f"{focus}의 완료 기준을 ‘열심히 하기’나 ‘많이 풀기’로 두면 {location} 학생이 언제 끝내고 무엇을 다시 봐야 하는지 판단하기 어렵습니다. 대신 설명하기, 근거 표시하기, 조건에 맞춰 수정하기, 답을 가리고 복원하기 중 이번 주에 필요한 행동 하나를 고릅니다. 학생이 시작 전에 그 문장을 읽고 종료 뒤 스스로 확인하도록 합니다.",
        ),
        (
            "도움 전후 나누기",
            f"{location} {focus} 과정에서는 질문·예시·선택지·정답 확인을 모두 같은 도움으로 기록하지 않습니다. 어떤 도움 뒤에 학생이 다시 읽었는지, 풀이 첫 줄을 바꾸었는지, 초안을 수정했는지를 구분합니다. {lens['record']} 이렇게 남긴 차이는 도움을 많이 받았다는 평가가 아니라 다음 회차에 줄여 볼 지원을 정하는 근거입니다.",
        ),
        (
            "다른 표현에 옮기기",
            f"{location} 학생이 {focus} 내용을 익숙한 자료에서만 반복하면 기억과 이해를 구분하기 어렵습니다. 같은 개념을 말·글·표·식·그림 가운데 다른 표현으로 바꾸고, 바꾸는 동안 빠진 조건을 표시합니다. 표현을 바꾼 뒤에도 처음 정한 근거와 결론이 이어지는지 확인하며, 막히면 원본의 어느 줄로 돌아갔는지를 기록합니다.",
        ),
        (
            "간격 뒤 복원하기",
            f"{focus} 결과는 수업 직후의 정답만으로 판단하지 않습니다. {location} 학생은 첫 기록을 덮고 {compare_days} 뒤 같은 개념을 다시 시작해 사용할 자료와 첫 행동을 스스로 고릅니다. 답이 맞아도 근거를 설명하지 못하면 재확인 항목으로 남기고, 틀렸어도 오류 위치와 수정 이유를 독립적으로 찾았다면 그 행동을 다음 계획에 유지합니다.",
        ),
        (
            "학교 일정에 배치하기",
            f"{location}의 실제 학교 공지에서 평가·제출·행사 날짜를 확인한 뒤 {focus} 행동을 주간 계획에 배치합니다. 특정 학교의 일정을 지역명으로 추정하지 않고 학생이 가져온 최신 원본을 사용합니다. 마감이 겹치면 모든 분량을 유지하지 말고 학교 요구, 누적 공백, 재시도 날짜를 비교해 이번 주에 끝낼 항목과 다음 주로 옮길 항목을 나눕니다.",
        ),
        (
            "과목별 차이 설명하기",
            f"{location} {focus} 계획에서 국어·영어의 근거 읽기, 수학의 첫 판단과 검산, 과학·사회의 자료 해석을 같은 방식으로 세지 않습니다. 학생은 과목마다 사용할 원본과 완료 행동이 왜 다른지 설명합니다. 한 과목에서 효과적으로 사용한 시작 전략을 다른 과목에 옮길 때에는 공통점과 달라지는 조건을 먼저 말하게 합니다.",
        ),
        (
            "가정 질문 줄이기",
            f"{location} 가정에서 {focus} 변화를 확인할 때 부모는 점수·시간·문제 수를 한꺼번에 묻지 않습니다. {lens['parent']} 학생이 고른 자료, 혼자 시작한 부분, 받은 도움, 다음 재시도 가운데 하루에는 한 항목만 묻습니다. 설명이 막히면 부모가 계획을 대신 쓰지 않고 학생이 참고할 원본과 다음 질문을 선택하도록 기다립니다.",
        ),
        (
            "다음 주 결정 남기기",
            f"한 주의 {location} {focus} 기록은 성공과 실패를 판정하는 표가 아닙니다. 유지할 행동 하나, 줄일 도움 하나, 다시 확인할 날짜 하나를 학생이 직접 적으면 다음 주 출발점이 됩니다. {risk}은 피하고 처음 정한 기준과 실제 종료 상태를 비교합니다. 기록이 일치하지 않으면 분량을 늘리기 전에 자료와 완료 문장을 더 구체적으로 고칩니다.",
        ),
    )
    cards = "".join(
        f'<h3>{escape(location)} {escape(focus)} {escape(name)}</h3><p>{escape(text)}</p>'
        for name, text in rows
    )
    return (
        '<section class="middle-general-focus-workshop" data-workshop-steps="10">'
        f'<h2>{escape(location)} {escape(focus)} 10단계 실전 기록</h2>'
        f'<p>{escape(location)} 학생에게 맞는 {escape(focus)} 방법은 지역명이나 학년만으로 정할 수 없습니다. 아래 열 단계는 {escape(_object_form(material))} 출발점으로 삼아 같은 학생의 도움 전후와 간격 뒤 행동을 비교하는 기록 순서입니다. 모든 단계를 한날에 끝내지 않고 학교 일정에 맞춰 한두 단계씩 적용합니다.</p>'
        + cards
        + f'<p>{escape(location)} {escape(focus)} 기록이 두 주 이상 이어졌다면 많이 한 항목보다 도움 없이 유지된 행동을 먼저 남깁니다. 변화가 없을 때도 학생의 의지로 단정하지 않고 자료 난도, 질문 범위, 생활시간, 지원 방식 가운데 무엇을 한 가지 조정할지 정합니다.</p></section>'
    )


def build_local_middle_general_body(slug: str) -> str:
    pack, focus, lens, index = _assignment(slug)
    def section_packs(multiplier: int, offset: int) -> tuple[dict[str, object], ...]:
        order = PACK_ORDERS[(index * multiplier + offset) % len(PACK_ORDERS)]
        return tuple(STUDY_PACKS[value] for value in order)

    search_packs = section_packs(2, 1)
    grade_packs = section_packs(4, 2)
    subject_packs = section_packs(5, 3)
    assessment_packs = section_packs(7, 4)
    school_packs = section_packs(8, 5)
    case_packs = section_packs(10, 6)
    protocol_packs = section_packs(11, 7)
    experiment_packs = section_packs(13, 8)
    parent_packs = section_packs(16, 9)
    transition_packs = section_packs(17, 10)
    faq_packs = section_packs(19, 11)
    faq_order = PACK_ORDERS[(index * 20 + 12) % len(PACK_ORDERS)]
    faq_lenses = tuple(LENSES[value] for value in faq_order if value < len(LENSES))
    experiment_order = PACK_ORDERS[(index * 22 + 13) % len(PACK_ORDERS)]
    experiment_lenses = tuple(LENSES[value] for value in experiment_order if value < len(LENSES))
    location, city, town = _place(slug)
    label = str(pack["label"])
    evidence = str(pack["evidence"])
    risk = str(pack["risk"])
    material = _pick(
        (
            "최근 교과서와 공책, 학교 유인물, 수정 흔적이 남은 평가 원본",
            "과목별 교과서 표시, 수행평가 조건표, 학생의 첫 풀이와 재시도 기록",
            "학교 알림 일정, 최근 답안, 학생이 직접 쓴 계획표와 도움 뒤 수정본",
            "일주일 과제표, 교과 활동지, 답을 가린 회상 기록과 다시 볼 날짜",
            "최근 시험 범위표, 과목별 공책, 산출물 초안과 오류 분류 메모",
            "평일 시작 기록, 학교 원본 자료, 첫 설명과 간격을 둔 재현 결과",
            "교과서 대표 내용, 학생의 첫 판단, 부모 도움 전후의 다른 색 기록",
            "학교 과제와 평가 자료, 예상 시간표, 실제 종료 상태와 다음 시작 메모",
        ),
        slug,
        "material",
    )
    grade = ("중1", "중2", "중3")[index % 3]
    compare_days = ("이틀", "사흘", "나흘", "일주일")[index % 4]
    opening = (
        f'<section class="middle-general-opening" data-content-version="{CONTENT_VERSION}" data-middle-general-focus="{escape(focus)}">'
        f'<h2>{escape(location)}중등과외, {escape(_object_form(focus))} 학교 자료에서 시작하는 방법</h2>'
        f'<p>{escape(location)}이라는 지역명만으로 중학생의 성취도나 학교 진도를 단정할 수는 없습니다. 이 페이지는 {escape(_object_form(focus))} 고유 점검 주제로 삼아 {escape(material)}에서 시작 행동·설명·수정·재현을 비교합니다. {escape(label)} 관점과 {escape(lens["label"])} 기준을 함께 사용하되 한 주에 바꿀 행동은 하나만 정합니다.</p></section>'
    )
    local_notes = _legacy_unique_section(slug, location, focus)
    search = (
        '<section class="middle-general-search-intent" data-search-rows="3">'
        f'<h2>{escape(location)} {escape(focus)} 검색을 실제 상담 질문으로 바꾸기</h2>'
        f'<p>{escape(location)}에서 {escape(_object_form(focus))} 찾을 때 광고 문구보다 {escape(str(search_packs[8]["evidence"]))}를 먼저 확인합니다. {escape(lens["question"])} 아래 자료와 판단 기준은 수업 효과를 보장하는 지표가 아니라 현재 행동을 구분하는 교육용 점검 도구입니다.</p>'
        '<table><thead><tr><th>비교 자료</th><th>준비할 원본</th><th>판단 질문</th></tr></thead><tbody>'
        f'<tr><td>학교 요구</td><td>{escape(material)}</td><td>{escape(str(search_packs[0]["assessment"]))}</td></tr>'
        f'<tr><td>첫 수행</td><td>도움 전 풀이·읽기·초안</td><td>{escape(str(search_packs[1]["evidence"]))}</td></tr>'
        f'<tr><td>간격 재현</td><td>{compare_days} 뒤 답을 가린 같은 개념</td><td>{escape(str(search_packs[2]["transition"]))}</td></tr>'
        '</tbody></table><ol>'
        f'<li>{escape(location)}의 최근 학교 원본에서 {escape(str(search_packs[3]["grade1"]))}</li>'
        f'<li>{escape(focus)} 첫 기록에는 {escape(str(search_packs[4]["risk"]))}을 피할 수 있도록 멈춘 위치와 도움을 남깁니다.</li>'
        f'<li>{escape(str(search_packs[5]["grade2"]))} {compare_days} 뒤 같은 기준으로 다시 확인합니다.</li>'
        f'<li>{escape(str(search_packs[6]["grade3"]))} 유지할 행동 하나와 줄일 도움 하나를 선택합니다.</li>'
        '</ol></section>'
    )
    grade_rows = (
        ("중1", str(grade_packs[0]["grade1"]), str(grade_packs[0]["risk"])),
        ("중2", str(grade_packs[1]["grade2"]), str(grade_packs[1]["risk"])),
        ("중3", str(grade_packs[2]["grade3"]), str(grade_packs[2]["risk"])),
    )
    grades = (
        '<section class="middle-general-grade" data-grade-groups="3">'
        f'<h2>{escape(location)} {escape(focus)} 계획을 중1·중2·중3으로 나누기</h2>'
        f'<p>{escape(_topic_form(focus))} 세 학년에 같은 분량으로 적용하지 않습니다. {escape(location)} 학생이 현재 교과서에서 혼자 설명할 수 있는 범위와 학교 일정, 도움의 양을 확인한 뒤 학년별 책임을 조금씩 넓힙니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {name}의 {escape(focus)} 시작점</h3><p>{escape(text)} {escape(lens["question"])} {escape(location)} {name}의 {escape(focus)} 기준으로 설명합니다.</p><p>{escape(location)} {name}은 {escape(row_risk)}을 피하고 사용할 자료와 종료 기준을 먼저 말한 뒤 {compare_days} 뒤 같은 개념을 다시 복원합니다.</p>'
            for name, text, row_risk in grade_rows
        )
        + "</section>"
    )
    subject_rows = tuple(
        (name, key, subject_packs[position])
        for position, (name, key) in enumerate((("국어", "korean"), ("수학", "math"), ("영어", "english"), ("과학", "science"), ("사회", "social")), start=1)
    )
    subjects = (
        '<section class="middle-general-subjects" data-subject-count="5">'
        f'<h2>{escape(location)} 다섯 과목에서 {escape(_object_form(focus))} 다르게 확인하기</h2>'
        f'<p>{escape(_topic_form(label))} 모든 과목에 같은 노트 형식과 문제 수를 적용하는 뜻이 아닙니다. {escape(location)} 학생의 읽기·풀이·회상·자료 해석·산출물에 맞춰 완료 행동과 재확인 방법을 구분합니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {name}의 {escape(focus)} 기록</h3><p>{escape(str(row_pack[key]))} {escape(lens["record"])} {escape(location)} 학생은 정답 수보다 과목에 맞는 첫 행동을 스스로 선택했는지 설명합니다.</p>'
            for name, key, row_pack in subject_rows
        )
        + "</section>"
    )
    assessment_steps = (
        ("평가 3주 전", "학교 범위와 제출물을 한곳에 모으고 아직 설명하지 못하는 단원을 표시합니다."),
        ("평가 2주 전", "과목별 핵심 개념과 학교 원본을 연결하고 서술형·자료 해석·풀이의 빈칸을 찾습니다."),
        ("평가 1주 전", "새 자료를 줄이고 오류 분류와 간격 재현 결과에서 남은 항목만 좁혀 확인합니다."),
        ("평가 이후", "점수와 오답을 다음 단원에 필요한 개념·조건·전략·실행 기록으로 옮깁니다."),
    )
    assessment = (
        '<section class="middle-general-assessment" data-assessment-stages="4">'
        f'<h2>{escape(location)} 학교 평가와 {escape(_object_form(focus))} 연결하는 네 시점</h2>'
        f'<p>{escape(str(assessment_packs[8]["assessment"]))} {escape(location)}에서는 학교별 시험일과 수행평가를 추정하지 않고 실제 공지를 기준으로 날짜를 바꿉니다.</p>'
        '<table><thead><tr><th>시점</th><th>학교 원본</th><th>학생 행동</th></tr></thead><tbody>'
        f'<tr><td>시작</td><td>범위표·조건표·교과서</td><td>{escape(focus)}의 완료 기준을 한 문장으로 정하기</td></tr>'
        f'<tr><td>중간</td><td>첫 답안·초안·오답</td><td>{escape(str(assessment_packs[7]["evidence"]))}</td></tr>'
        f'<tr><td>마무리</td><td>답을 가린 재현 자료</td><td>{escape(lens["record"])}</td></tr>'
        '</tbody></table>'
        + "".join(
            f'<h3>{escape(location)} {name}의 {escape(focus)} 점검</h3><p>{escape(text)} {escape(str(assessment_packs[position]["evidence"]))}를 {escape(location)}의 {escape(focus)} {escape(lens["label"])} 기록에서 대조합니다.</p>'
            for position, (name, text) in enumerate(assessment_steps)
        )
        + "</section>"
    )
    school = _school_section(slug, location, focus, school_packs[0], lens)
    case = (
        f'<section class="middle-general-student-case" data-case-model="composite" data-case-grade="{grade}">'
        f'<h2>{escape(location)} {grade}의 {escape(focus)} 합성 사례</h2>'
        f'<p>다음은 특정 학생의 실제 상담 후기가 아니라 여러 학습 장면을 섞어 만든 교육용 합성 사례입니다. {escape(location)} {grade} 학생이 {escape(str(case_packs[0]["case"]))}에서 출발했다고 가정하고, {escape(focus)} 행동 하나만 바꾼 과정을 보여 줍니다.</p>'
        '<table><thead><tr><th>관찰 시점</th><th>남긴 증거</th><th>다음 행동</th></tr></thead><tbody>'
        f'<tr><td>첫 주</td><td>{escape(str(case_packs[3]["evidence"]))}</td><td>{escape(lens["question"])}</td></tr>'
        f'<tr><td>도움 뒤</td><td>{escape(str(case_packs[4]["korean"]))}</td><td>{escape(str(case_packs[5]["assessment"]))}</td></tr>'
        f'<tr><td>{compare_days} 뒤</td><td>{escape(str(case_packs[6]["math"]))}</td><td>{escape(str(case_packs[7]["transition"]))}</td></tr>'
        f'</tbody></table><ol><li>{escape(str(case_packs[1]["grade1"]))}</li><li>{escape(str(case_packs[2]["grade2"]))}</li><li>{escape(str(case_packs[8]["grade3"]))}</li></ol>'
        f'<p>이 사례는 점수 상승이나 수업 효과를 보장하지 않습니다. {escape(str(case_packs[0]["transition"]))} {escape(str(case_packs[8]["risk"]))}을 피하며 {escape(location)} 학생의 실제 변화는 학교 자료, 생활시간, 독립 수행 기록을 같은 기준으로 비교해 판단해야 합니다.</p></section>'
    )
    protocol_rows = (
        ("원본 모으기", "교과서·공책·학교 유인물·평가 자료의 날짜와 과목을 맞춥니다."),
        ("첫 행동 정하기", "학생이 자료를 보고 가장 먼저 할 읽기·풀이·회상·작성 행동을 말합니다."),
        ("도움 표시하기", "질문·예시·선택지·정답 확인 가운데 실제로 사용한 도움을 구분합니다."),
        ("수정 이유 쓰기", "바뀐 답만 적지 않고 조건·개념·전략 가운데 판단을 바꾼 이유를 남깁니다."),
        ("간격 재현하기", "답과 힌트를 가린 뒤 같은 개념을 다른 표현에서 다시 시작합니다."),
        ("다음 계획 고르기", "유지할 행동, 줄일 도움, 다시 볼 날짜를 학생이 한 문장씩 정합니다."),
    )
    protocol = (
        '<section class="middle-general-protocol" data-protocol-cards="6">'
        f'<h2>{escape(location)} {escape(_object_form(focus))} 실행하는 여섯 단계</h2>'
        f'<p>{escape(label)} 계획은 한 번에 완성하지 않습니다. {escape(location)} 학생은 {escape(lens["label"])} 관점으로 시작·설명·수정·재현을 한 단계씩 남겨 도움을 줄여도 유지되는 행동을 찾습니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {number}단계: {escape(name)}</h3><p>{escape(str(protocol_packs[number - 1][("grade1", "grade2", "grade3", "korean", "math", "english")[number - 1]]))} {escape(str(protocol_packs[number - 1]["assessment"]))} {escape(_with_form(focus))} 관련해서는 {escape(str(protocol_packs[number - 1]["evidence"]))}를 확인하고, 기록이 없으면 결과를 추정하지 않습니다.</p>'
            for number, (name, text) in enumerate(protocol_rows, start=1)
        )
        + "</section>"
    )
    experiment_rows = (
        ("1회차", "자료 선택", "학생이 최근 학교 원본 하나와 가장 먼저 고칠 행동 하나를 선택합니다."),
        ("2회차", "표현 바꾸기", "같은 개념을 말·글·표·식 가운데 다른 표현으로 바꾸어 빠진 조건을 찾습니다."),
        ("3회차", "도움 줄이기", "지난번 사용한 힌트를 하나 가리고 멈춘 위치에서 구체적인 질문을 만듭니다."),
        ("4회차", "간격 비교", "첫 기록과 독립 재현을 나란히 두고 유지할 행동과 줄일 도움을 정합니다."),
    )
    experiment = (
        '<section class="middle-general-local-experiment" data-experiment-sessions="4">'
        f'<h2>{escape(location)}에서 해 볼 {escape(focus)} 4회 점검</h2>'
        f'<p>아래 활동은 수업 성과를 약속하는 프로그램이 아니라 {escape(location)} 학생의 현재 과정을 짧게 비교하는 교육용 점검입니다. {escape(str(experiment_packs[0]["risk"]))}을 피하고 매회 같은 자료와 판단 기준을 사용합니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {session} {escape(name)}</h3><p>{escape(str(experiment_packs[position]["case"]))} {escape(str(experiment_packs[position]["assessment"]))} {escape(experiment_lenses[position]["record"])} {escape(focus)}의 변화는 정답 수가 아니라 도움 없이 다시 시작하고 설명한 범위로 봅니다.</p>'
            for position, (session, name, text) in enumerate(experiment_rows, start=2)
        )
        + "</section>"
    )
    parent_rows = (
        ("결과 대신 과정 묻기", lens["parent"]),
        ("도움의 경계 정하기", "학생이 혼자 읽고 표시할 시간을 먼저 주고, 질문이 구체화된 뒤 필요한 한 단계만 지원합니다."),
        ("주간 기록 함께 닫기", "완료하지 못한 일을 비난하지 않고 남은 이유와 다음 시작점을 학생이 계획표에 직접 옮기게 합니다."),
    )
    parent = (
        '<section class="middle-general-parent" data-parent-checks="3">'
        f'<h2>{escape(location)} 학부모가 {escape(_object_form(focus))} 과도하게 통제하지 않는 법</h2>'
        f'<p>{escape(location)} 가정에서는 공부량보다 학생의 선택과 설명이 남는 질문을 사용합니다. {escape(_topic_form(focus))} 부모가 계획을 대신 완성할수록 확인하기 어려우므로 도움을 주기 전과 뒤의 행동을 분리합니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {escape(name)}</h3><p>{escape(text)} {escape(location)}의 {escape(focus)} 과정에서는 {escape(str(parent_packs[position]["evidence"]))}를 한 주에 한 번 확인하고 다음 주에 줄일 질문 하나를 정합니다.</p>'
            for position, (name, text) in enumerate(parent_rows, start=5)
        )
        + "</section>"
    )
    transition_rows = (
        ("현재 학년 설명력", f"{transition_packs[6]['grade3']} 교과서의 핵심 내용을 자료 없이 설명하고 막힌 개념을 질문으로 바꿀 수 있는지 봅니다."),
        ("과목별 학습 방법", f"{transition_packs[7]['assessment']} 읽기·풀이·암기·자료 해석·산출물에 맞는 첫 행동과 종료 기준을 학생이 다르게 고릅니다."),
        ("고등 전환 준비", str(transition_packs[8]["transition"])),
    )
    transition = (
        '<section class="middle-general-transition" data-transition-checks="3">'
        f'<h2>{escape(location)} {escape(_object_form(focus))} 고등 학습으로 옮기는 기준</h2>'
        f'<p>선행 교재를 시작한 사실만으로 전환 준비가 끝났다고 판단하지 않습니다. {escape(location)} 학생이 현재 자료에서 독립적으로 시작·설명·수정·재현한 증거가 남을 때 다음 난도와 분량을 조금씩 넓힙니다.</p>'
        + "".join(
            f'<h3>{escape(location)} {escape(name)}</h3><p>{escape(text)} {escape(lens["question"])} {escape(focus)} 기록이 다른 교재에서도 유지되는지 확인합니다.</p>'
            for name, text in transition_rows
        )
        + "</section>"
    )
    links = _context_links(location, city, focus)
    faq = _faq(slug, location, focus, faq_packs, faq_lenses)
    closing = (
        '<section class="middle-general-closing">'
        f'<h2>{escape(location)} 학생이 {escape(_object_form(focus))} 혼자 이어 갈 때까지</h2>'
        f'<p>이 페이지의 학교 정보와 {escape(focus)} 계획은 상담 결과나 성취를 보장하지 않습니다. {escape(str(transition_packs[5]["transition"]))} {escape(location)} 학생의 실제 교과서·공책·학교 공지·생활시간을 함께 확인하고 한 번에 하나의 행동만 바꾸어 같은 기준으로 다시 관찰하는 교육용 안내입니다.</p></section>'
    )
    return opening + local_notes + search + grades + subjects + assessment + school + case + protocol + experiment + parent + transition + links + faq + closing


def individualize_local_middle_general_body(body: str, slug: str) -> str:
    if not is_local_middle_general_slug(slug):
        return body
    return build_local_middle_general_body(slug)
