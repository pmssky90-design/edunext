from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path

from sitegen.utils import escape


LOCAL_MIDDLE_MATH_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)중등수학과외$")
CONTENT_MARKER = "local-middle-math-content"
CONTENT_VERSION = "middle-math-individual-v7"
PREVIOUS_CONTENT_VERSIONS = (
    "middle-math-individual-v1",
    "middle-math-individual-v2",
    "middle-math-individual-v3",
    "middle-math-individual-v4",
    "middle-math-individual-v5",
    "middle-math-individual-v6",
)
SCHOOL_CONTEXT_MARKER = "middle-math-school-context"
SEARCH_INTENT_MARKER = "middle-math-search-intent"
STUDENT_CASE_MARKER = "middle-math-student-case"
FAQ_MARKER = "middle-math-faq"
CONTEXT_LINKS_MARKER = "middle-math-context-links"
LOCAL_CONTEXT_PATH = Path(__file__).resolve().parents[1] / "data" / "local_middle_school_context.json"


def _load_local_middle_math_context() -> dict[str, dict[str, object]]:
    if not LOCAL_CONTEXT_PATH.exists():
        return {}
    data = json.loads(LOCAL_CONTEXT_PATH.read_text(encoding="utf-8"))
    pages = data.get("pages", {}) if isinstance(data, dict) else {}
    if not isinstance(pages, dict):
        return {}
    contexts: dict[str, dict[str, object]] = {}
    for english_slug, context in pages.items():
        if not isinstance(english_slug, str) or not isinstance(context, dict):
            continue
        math_slug = english_slug.removesuffix("중등영어과외") + "중등수학과외"
        contexts[math_slug] = context
    return contexts


LOCAL_MIDDLE_MATH_CONTEXT = _load_local_middle_math_context()


MATH_PACKS: dict[str, dict[str, object]] = {
    "algebra": {
        "label": "식과 수의 구조",
        "signal": "기호를 보고 곧바로 계산을 시작하지만, 각 항과 조건의 역할을 말로 설명하지 못하는지",
        "first": "계산 전에 주어진 값·구할 값·적용할 성질을 세 줄로 분리해 적습니다.",
        "action": "한 줄을 바꿀 때 사용한 성질을 짧게 덧붙이고, 등호나 부등호 양쪽에서 무엇이 달라졌는지 확인합니다.",
        "transfer": "숫자와 항의 순서가 달라진 문제에서도 같은 원리를 찾아 첫 줄을 스스로 세우는지 봅니다.",
        "check": "계산 결과를 원래 식에 대입하거나 역연산으로 되돌려 조건을 만족하는지 확인합니다.",
        "risk": "공식 이름만 외운 채 모양이 비슷한 문제에 같은 절차를 적용하는 것",
    },
    "function": {
        "label": "관계와 그래프 해석",
        "signal": "식을 계산할 수는 있지만 두 양의 변화, 좌표, 그래프의 모양을 하나의 관계로 연결하지 못하는지",
        "first": "가로축과 세로축이 나타내는 양, 단위, 한 칸의 크기를 먼저 문장으로 적습니다.",
        "action": "표의 두 값을 짝지어 보고, 식에서 변한 값이 그래프의 위치와 기울기에 어떻게 나타나는지 표시합니다.",
        "transfer": "식·표·그래프·문장 중 표현 하나를 가린 뒤 나머지 자료만으로 빠진 표현을 복원하게 합니다.",
        "check": "구한 좌표를 식에 다시 넣고 그래프 위의 점인지, 문제 상황의 범위에 맞는지 함께 확인합니다.",
        "risk": "그래프의 생김새만 기억하고 축, 단위, 정의역을 읽지 않는 것",
    },
    "geometry": {
        "label": "도형 조건과 논리",
        "signal": "그림의 모양에 기대어 결론을 정하고, 주어진 조건과 증명에 필요한 조건을 구분하지 못하는지",
        "first": "문장에 제시된 길이·각·평행·수직 조건을 그림에 서로 다른 기호로 옮깁니다.",
        "action": "결론부터 거꾸로 필요한 성질을 찾고, 이미 주어진 조건과 새로 증명해야 할 내용을 나눕니다.",
        "transfer": "도형의 방향이나 크기를 바꾼 뒤에도 같은 성질을 근거로 설명할 수 있는지 확인합니다.",
        "check": "측정값이나 눈대중 대신 정의·정리·앞 단계에서 확인한 사실만으로 결론이 이어지는지 검토합니다.",
        "risk": "그림이 비슷하다는 이유만으로 합동·닮음·평행 같은 조건을 있다고 가정하는 것",
    },
    "data": {
        "label": "자료와 가능성 판단",
        "signal": "계산값은 구하지만 자료의 전체 크기, 비교 기준, 사건의 범위를 확인하지 않는지",
        "first": "전체 자료와 관심 있는 자료가 무엇인지 정하고, 표·그래프·경우를 빠뜨리지 않았는지 표시합니다.",
        "action": "계산한 수가 어떤 집단이나 사건을 나타내는지 한 문장으로 해석하고 비교 기준을 맞춥니다.",
        "transfer": "자료의 일부 값이나 전체 수를 바꿨을 때 결론이 유지되는지 반례를 만들어 확인합니다.",
        "check": "가능한 값의 범위와 단위를 살펴 계산 결과가 실제 자료에서 성립할 수 있는지 검토합니다.",
        "risk": "계산식만 맞으면 해석도 맞다고 여기거나 서로 다른 크기의 집단을 그대로 비교하는 것",
    },
    "routine": {
        "label": "풀이 습관과 학습 운영",
        "signal": "정답 수와 공부 시간은 기록하지만 처음 막힌 지점과 도움을 받은 순간이 남아 있지 않은지",
        "first": "시작 시각보다 첫 과제, 종료 기준, 다시 볼 날짜를 한 줄씩 정합니다.",
        "action": "풀이 중 멈춘 곳에 표시를 남기고 개념·조건·전략·계산 가운데 원인을 하나 선택합니다.",
        "transfer": "같은 날 반복하기보다 하루 이상 간격을 둔 뒤 도움 없이 첫 단계를 다시 시작하게 합니다.",
        "check": "맞힌 문제 수보다 스스로 시작한 문제, 설명한 근거, 예정일에 다시 푼 문제를 비교합니다.",
        "risk": "진도와 문제 수를 늘리면서도 무엇이 달라졌는지 확인하지 않는 것",
    },
}


SEARCH_INTENT_PACKS: dict[str, dict[str, str]] = {
    "algebra": {
        "material": "최근 학교 시험지의 식 계산 문항, 교과서 대표 예제, 학생이 중간 계산을 남긴 공책",
        "level": "계산 속도보다 기호와 항의 역할을 설명하고 같은 변형을 양쪽에 적용하는지",
        "grade1": "수와 문자, 식의 값, 일차방정식에서 기호의 뜻과 등식의 성질을 설명합니다.",
        "grade2": "다항식 계산과 연립방정식·부등식에서 항을 정리한 이유와 미지수의 뜻을 남깁니다.",
        "grade3": "인수분해와 이차방정식에서 식의 모양에 맞는 해법을 고르고 역연산으로 검산합니다.",
        "written": "식을 세운 근거, 변형에 사용한 성질, 답이 조건을 만족하는지의 세 문장이 보이는가",
        "finish": "숫자와 항의 순서를 바꾼 문제에서도 첫 변형을 설명하고 계산을 되돌려 확인할 수 있는가",
    },
    "function": {
        "material": "학교 시험지의 함수 문항, 교과서의 식·표·그래프 예제, 축과 단위를 표시한 학생 풀이",
        "level": "좌표를 구하는 데서 끝나지 않고 두 양의 변화와 그래프의 위치를 문장으로 연결하는지",
        "grade1": "좌표와 정비례·반비례에서 두 양을 짝지어 보고 표와 그래프의 의미를 읽습니다.",
        "grade2": "일차함수의 기울기·절편을 변화량과 연결하고 일차방정식의 해를 그래프에서 확인합니다.",
        "grade3": "이차함수의 축·꼭짓점·최대와 최소를 식의 계수 및 문제 상황의 범위와 함께 해석합니다.",
        "written": "축·단위·정의역을 먼저 밝히고 그래프에서 읽은 변화를 식과 문장으로 설명하는가",
        "finish": "식·표·그래프 중 하나를 가려도 나머지 표현으로 관계를 복원하고 범위에 맞게 해석할 수 있는가",
    },
    "geometry": {
        "material": "최근 도형 시험 문항, 교과서의 정의와 정리, 조건 기호와 보조선이 남은 학생 그림",
        "level": "눈에 보이는 모양이 아니라 주어진 조건과 앞 단계에서 확인한 성질로 결론을 설명하는지",
        "grade1": "기본 도형과 작도에서 점·선·각의 정의를 사용하고 측정과 논리적 결론을 구분합니다.",
        "grade2": "삼각형·사각형의 성질과 닮음에서 주어진 조건, 필요한 조건, 결론을 순서대로 연결합니다.",
        "grade3": "피타고라스 정리·삼각비·원의 성질에서 적용 조건을 확인하고 길이와 각의 범위를 검토합니다.",
        "written": "그림의 표시, 사용한 정의나 정리, 그 성질로 얻은 결론이 빠짐없이 이어지는가",
        "finish": "도형의 방향과 크기를 바꿔도 같은 조건을 찾아 증명 또는 계산의 첫 단계를 세울 수 있는가",
    },
    "data": {
        "material": "학교 시험지의 자료·확률 문항, 교과서 표와 그래프, 전체 경우를 나눈 학생 기록",
        "level": "계산값만 제시하지 않고 비교하는 집단, 전체 수, 사건의 범위와 결과의 의미를 설명하는지",
        "grade1": "도수분포와 그래프에서 계급·도수·상대도수의 기준을 맞추고 자료의 특징을 읽습니다.",
        "grade2": "경우의 수와 확률에서 전체 경우를 빠짐없이 나누고 덧셈·곱셈 선택의 이유를 말합니다.",
        "grade3": "대푯값과 산포도·상관관계에서 자료에 맞는 지표를 선택하고 해석의 한계를 확인합니다.",
        "written": "전체 자료와 선택한 기준, 계산 과정, 결과가 뜻하는 범위를 한 문단에서 설명하는가",
        "finish": "자료나 전체 경우의 수를 바꿨을 때 계산과 해석이 어떻게 달라지는지 반례로 확인할 수 있는가",
    },
    "routine": {
        "material": "최근 학교 시험지와 오답 공책, 교과서 진도표, 일주일의 시작·중단·재풀이 기록",
        "level": "공부시간과 문제 수보다 혼자 시작한 단계, 도움을 받은 순간, 다시 푼 결과가 남아 있는지",
        "grade1": "수학 용어와 기호를 자신의 말로 바꾸고 풀이를 생략하지 않는 공책 사용을 익힙니다.",
        "grade2": "단원 연결이 늘어나는 시기에 오답을 개념·조건·전략·계산으로 나누어 복습합니다.",
        "grade3": "내신 범위와 고등 선수개념을 분리하고 재풀이 간격과 시험 시간 배분까지 기록합니다.",
        "written": "정답 외에 첫 전략, 중단 위치, 수정 이유, 검산과 다음 복습 날짜가 남아 있는가",
        "finish": "정해진 날에 도움 없이 다시 시작하고 같은 오류가 줄었는지를 자신의 기록으로 설명할 수 있는가",
    },
}


STUDENT_CASE_PACKS: dict[str, dict[str, tuple[str, ...]]] = {
    "algebra": {
        "observation": (
            "계산은 끝내지만 등호를 넘긴 항의 부호가 왜 바뀌는지 설명하지 못합니다.",
            "익숙한 계수에서는 풀지만 문자나 항의 순서가 바뀌면 첫 식을 세우지 못합니다.",
            "정답은 맞아도 중간 식을 생략해 계산 오류가 생긴 줄을 스스로 찾기 어렵습니다.",
            "공식 이름은 말하지만 어떤 조건에서 그 공식을 선택했는지 근거가 남지 않습니다.",
        ),
        "evidence": (
            "시험지와 공책에서 같은 부호 오류가 반복되는 위치를 표시합니다.",
            "교과서 예제를 덮은 뒤 주어진 값·구할 값·적용할 성질을 나누어 말하게 합니다.",
            "정답을 가린 채 첫 변형과 마지막 검산만 다시 써 보게 합니다.",
            "숫자와 문자의 순서를 바꾼 짧은 문제로 같은 원리를 찾는지 확인합니다.",
        ),
        "action": (
            "한 줄을 바꿀 때마다 사용한 성질을 여백에 한 단어로 적게 합니다.",
            "계산 전에 항과 조건을 색이 아닌 기호로 구분하고 첫 줄을 말로 설명하게 합니다.",
            "완성된 풀이를 베끼지 않고 빈칸이 있는 중간 식을 스스로 복원하게 합니다.",
            "오답 한 문제를 개념 선택·식 세우기·계산·검산의 네 칸으로 나누어 기록합니다.",
        ),
        "transfer": (
            "계수와 항의 순서가 달라져도 같은 성질로 첫 줄을 세우는지 봅니다.",
            "문장제에서 미지수의 뜻을 먼저 정한 뒤 식과 답의 조건이 맞는지 확인합니다.",
            "풀이를 역연산으로 되돌려 원래 조건을 만족하는지 학생의 말로 설명하게 합니다.",
            "비슷해 보이지만 적용 성질이 다른 문제를 나란히 놓고 선택 이유를 비교합니다.",
        ),
    },
    "function": {
        "observation": (
            "좌표는 계산하지만 가로축과 세로축이 무엇을 뜻하는지 말하지 못합니다.",
            "기울기 공식을 적용해도 두 양이 함께 변하는 방향을 문장으로 연결하지 못합니다.",
            "그래프 모양만 기억해 축의 단위나 문제에서 허용한 범위를 놓칩니다.",
            "식·표·그래프가 같은 관계를 나타낸다는 점을 문제마다 새 내용처럼 받아들입니다.",
        ),
        "evidence": (
            "학교 문제의 축·단위·정의역을 가린 뒤 학생이 먼저 복원하도록 합니다.",
            "표의 두 값을 짝지은 기록과 그래프에 표시한 변화량을 함께 봅니다.",
            "식을 계산한 공책에서 좌표를 다시 대입해 확인한 흔적이 있는지 살핍니다.",
            "문장·식·표·그래프 가운데 어느 표현에서 연결이 끊기는지 따로 표시합니다.",
        ),
        "action": (
            "계산 전에 두 축의 뜻과 한 칸의 크기를 한 문장으로 적게 합니다.",
            "표에서 변한 양을 화살표로 표시한 뒤 식의 계수와 그래프의 변화로 옮기게 합니다.",
            "네 가지 표현 중 하나를 가리고 나머지 자료만으로 빠진 표현을 복원하게 합니다.",
            "구한 좌표 옆에 그 점이 문제 상황에서 무엇을 의미하는지 덧붙이게 합니다.",
        ),
        "transfer": (
            "수치와 축의 범위가 달라진 그래프에서도 같은 관계를 해석하는지 확인합니다.",
            "식만 주어진 문제를 표와 그래프로 바꾸고 변화 방향을 설명하게 합니다.",
            "그래프 위에 없는 점을 하나 제시해 식과 범위를 이용해 반박하게 합니다.",
            "기울기나 꼭짓점이 달라질 때 문제 상황의 결론도 함께 바뀌는지 말하게 합니다.",
        ),
    },
    "geometry": {
        "observation": (
            "그림이 비슷하다는 이유로 주어지지 않은 평행·합동·닮음 조건을 있다고 가정합니다.",
            "계산은 시작하지만 어떤 정의나 정리를 사용했는지 근거가 풀이에 남지 않습니다.",
            "도형의 방향이나 크기가 바뀌면 같은 조건을 가진 문제라는 점을 알아보지 못합니다.",
            "보조선을 그은 뒤 그 선이 필요한 이유와 새로 생긴 관계를 설명하지 못합니다.",
        ),
        "evidence": (
            "최근 도형 풀이에서 문제 문장의 조건과 학생이 그림에 추가한 표시를 구분합니다.",
            "측정하거나 눈대중으로 판단한 문장과 정의·정리로 설명한 문장을 따로 표시합니다.",
            "결론에서 거꾸로 필요한 성질을 적고 실제로 주어진 조건과 대조합니다.",
            "원래 그림을 회전하거나 크기를 바꿔도 같은 기호를 다시 표시하는지 확인합니다.",
        ),
        "action": (
            "길이·각·평행·수직 조건을 서로 다른 수학 기호로 옮긴 뒤 계산을 시작하게 합니다.",
            "결론에 필요한 성질과 이미 주어진 조건을 두 칸으로 나누어 연결하게 합니다.",
            "풀이 한 줄마다 사용한 정의나 정리의 이름을 짧게 덧붙이게 합니다.",
            "보조선을 그리기 전에 얻고 싶은 관계를 먼저 말한 뒤 선을 선택하게 합니다.",
        ),
        "transfer": (
            "도형을 회전하거나 문자 이름을 바꿔도 같은 근거로 첫 단계를 세우는지 봅니다.",
            "필요한 조건 하나를 뺀 반례를 제시해 결론이 성립하지 않는 이유를 설명하게 합니다.",
            "계산 결과가 길이와 각의 가능한 범위에 맞는지 마지막에 검토하게 합니다.",
            "비슷한 그림 두 개를 비교해 합동·닮음 판단에 실제로 사용한 조건을 고르게 합니다.",
        ),
    },
    "data": {
        "observation": (
            "계산값은 구하지만 비교하는 집단의 크기와 기준이 다른 점을 확인하지 않습니다.",
            "경우를 나누기 시작해도 빠진 경우와 중복된 경우를 스스로 점검하지 못합니다.",
            "평균이나 확률을 구한 뒤 그 수가 어떤 자료와 사건을 뜻하는지 설명하지 못합니다.",
            "그래프의 높이만 비교하고 계급·도수·단위·전체 자료 수를 함께 읽지 않습니다.",
        ),
        "evidence": (
            "시험지의 표와 그래프에서 전체 자료 수와 비교 기준을 먼저 표시하게 합니다.",
            "나열한 경우를 표나 나무그림으로 다시 옮겨 누락과 중복을 확인합니다.",
            "계산식 옆에 분자·분모 또는 대푯값이 뜻하는 집단을 문장으로 적게 합니다.",
            "결과를 가린 채 가능한 값의 범위와 단위를 먼저 예상하게 합니다.",
        ),
        "action": (
            "전체 자료와 관심 있는 자료를 두 칸으로 나눈 뒤 계산식을 세우게 합니다.",
            "경우를 나누는 기준을 먼저 정하고 각 칸이 겹치지 않는지 확인하게 합니다.",
            "계산한 수 뒤에 어떤 집단이나 사건을 설명하는 값인지 한 문장을 붙이게 합니다.",
            "서로 다른 크기의 집단은 상대도수나 같은 기준으로 바꾼 뒤 비교하게 합니다.",
        ),
        "transfer": (
            "자료의 일부 값이나 전체 수를 바꿨을 때 계산과 해석이 함께 바뀌는지 봅니다.",
            "빠뜨리기 쉬운 경우를 반례로 추가해 전체 경우의 수를 다시 검토하게 합니다.",
            "같은 자료에 서로 다른 대푯값을 적용하고 어떤 해석이 적절한지 설명하게 합니다.",
            "계산 결과가 0과 1 사이인지처럼 가능한 범위에 맞는지 스스로 확인하게 합니다.",
        ),
    },
    "routine": {
        "observation": (
            "공부시간과 문제 수는 기록하지만 처음 막힌 지점과 도움을 받은 순간은 남기지 않습니다.",
            "답을 고쳐 쓴 뒤 이해했다고 표시하지만 하루 뒤에는 같은 문제의 첫 단계를 시작하지 못합니다.",
            "시험이 가까워질수록 새 문제를 늘리면서 기존 오답의 원인을 다시 확인하지 않습니다.",
            "모르겠다는 말은 하지만 개념·조건·전략·계산 중 무엇이 필요한지 질문하지 못합니다.",
        ),
        "evidence": (
            "일주일 기록에서 시작 문제·중단 위치·힌트·재풀이 날짜가 있는지 확인합니다.",
            "오답 공책에서 답을 지운 뒤 풀이의 첫 줄만 다시 시작하게 합니다.",
            "시험 범위표와 실제 오답을 나란히 두고 반복 원인이 두 번 나온 항목을 찾습니다.",
            "도움을 요청하기 직전에 시도한 방법과 마지막으로 이해한 줄을 말하게 합니다.",
        ),
        "action": (
            "시작 시각 대신 첫 과제·종료 행동·다시 볼 날짜를 한 줄씩 적게 합니다.",
            "오답을 개념·조건·전략·계산 가운데 하나로 분류하고 이유를 짧게 남기게 합니다.",
            "새 분량을 추가하기 전에 같은 오류 한 문제를 답 없이 재시도하게 합니다.",
            "질문 전에 시도한 방법과 막힌 줄, 필요한 힌트를 한 문장으로 만들게 합니다.",
        ),
        "transfer": (
            "하루 이상 간격을 둔 뒤 도움 없이 같은 원리의 첫 단계를 다시 시작하는지 봅니다.",
            "새 단원에서도 중단 위치와 질문을 같은 형식으로 기록하는지 확인합니다.",
            "시험 직전에도 새 문제보다 표시해 둔 오답을 원인별로 먼저 꺼내는지 봅니다.",
            "학습 시간이 짧은 날에도 다음 시작 문제와 재풀이 날짜를 남기는지 확인합니다.",
        ),
    },
}


META_TITLE_FRAME = "{slug} | {focus}"

META_DESCRIPTION_FRAMES: dict[str, tuple[str, ...]] = {
    "algebra": (
        "{slug}에서 ‘{focus}’을 최근 학교 시험지와 풀이 기록으로 점검하는 방법입니다. 식의 첫 변형, 학년별 목표, 내신·서술형 준비, 합성 사례와 간격을 둔 재시도 기준을 정리했습니다.",
        "{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 기호와 항의 역할, 계산 근거, 검산을 나누어 확인하고 학교 자료·학년별 계획·오답 재시도·주제별 FAQ로 연결합니다.",
        "{slug} 페이지는 ‘{focus}’에서 막힌 위치를 찾는 기준을 다룹니다. 현재 풀이 진단부터 내신 범위, 가상 학생 사례, 서술형 근거와 다음 단원 이동 조건까지 확인할 수 있습니다.",
        "{slug} 중학생이 ‘{focus}’을 복습할 때 남길 기록을 정리했습니다. 학교 범위 확인, 첫 식과 수정 이유, 학년별 목표, 검산, 간격 뒤 재풀이와 관련 수학 경로를 제공합니다.",
    ),
    "function": (
        "{slug}에서 ‘{focus}’을 식·표·그래프와 학교 문제로 점검하는 방법입니다. 축과 단위, 변화량, 학년별 목표, 내신·서술형 준비와 간격을 둔 재시도 기준을 정리했습니다.",
        "{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 두 양의 관계와 그래프 해석을 나누어 확인하고 학교 자료·가상 사례·오답 검산·주제별 FAQ로 연결합니다.",
        "{slug} 페이지는 ‘{focus}’에서 표현 사이의 연결이 끊기는 위치를 찾습니다. 현재 풀이 진단, 학년별 함수 목표, 시험 준비, 합성 사례와 완료 기준을 확인할 수 있습니다.",
        "{slug} 중학생이 ‘{focus}’을 복습할 때 확인할 자료와 행동입니다. 학교 범위, 축·단위 표시, 식과 그래프 변환, 서술형 설명, 다음 날 재시도 순서를 정리했습니다.",
    ),
    "geometry": (
        "{slug}에서 ‘{focus}’을 도형 조건과 실제 학교 풀이로 점검하는 방법입니다. 그림 표시, 정의·정리의 근거, 학년별 목표, 내신·서술형과 재시도 기준을 정리했습니다.",
        "{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 눈에 보이는 모양과 주어진 조건을 구분하고 학교 자료·가상 사례·증명 기록·주제별 FAQ로 연결합니다.",
        "{slug} 페이지는 ‘{focus}’의 조건 누락과 논리 연결을 확인합니다. 현재 도형 풀이 진단부터 학년별 목표, 시험 준비, 합성 사례와 다른 그림 적용 기준까지 제공합니다.",
        "{slug} 중학생이 ‘{focus}’을 복습할 때 남길 근거를 정리했습니다. 학교 범위, 조건 표시, 사용한 정리, 검산, 방향을 바꾼 문제의 재시도와 관련 수학 경로를 확인하세요.",
    ),
    "data": (
        "{slug}에서 ‘{focus}’을 표·그래프·경우의 기록으로 점검하는 방법입니다. 전체 자료와 비교 기준, 학년별 목표, 내신·서술형 준비와 간격을 둔 재시도를 정리했습니다.",
        "{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 계산값과 해석을 구분하고 학교 자료·가상 사례·누락과 중복 점검·주제별 FAQ로 연결합니다.",
        "{slug} 페이지는 ‘{focus}’에서 자료 범위와 결과 해석이 어긋나는 지점을 찾습니다. 현재 진단, 학년별 목표, 시험 준비, 합성 사례와 완료 기준을 확인할 수 있습니다.",
        "{slug} 중학생이 ‘{focus}’을 복습할 때 확인할 자료와 행동입니다. 학교 범위, 전체 경우, 계산 근거, 결과의 의미, 조건을 바꾼 재시도와 관련 수학 경로를 정리했습니다.",
    ),
    "routine": (
        "{slug}에서 ‘{focus}’을 학교 일정과 실제 풀이 기록으로 점검하는 방법입니다. 시작·중단·도움·재시도 시점, 학년별 목표, 내신 준비와 합성 사례를 정리했습니다.",
        "{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 문제 수보다 첫 판단과 오답 원인을 확인하고 학교 자료·주간 계획·가상 사례·주제별 FAQ로 연결합니다.",
        "{slug} 페이지는 ‘{focus}’에 필요한 공부 행동과 완료 기준을 다룹니다. 현재 기록 진단부터 학년별 과제, 시험 준비, 합성 사례와 간격을 둔 재풀이를 확인할 수 있습니다.",
        "{slug} 중학생이 ‘{focus}’을 실행할 때 남길 기록을 정리했습니다. 학교 범위와 생활시간, 첫 풀이, 도움 뒤 변화, 다음 날 재시도와 관련 수학 학습 경로를 제공합니다.",
    ),
}


OPENING_FRAMES = (
    "{location}에서 ‘{focus}’을 점검할 때는 문제 수보다 첫 판단을 먼저 봅니다. 학생이 어디에서 멈췄고 어떤 근거로 다음 줄을 정했는지 남아 있어야 같은 오류가 우연인지 학습 공백인지 구분할 수 있습니다.",
    "‘{focus}’은 정답 한 개로 이해 여부를 판정하기 어려운 주제입니다. {location} 페이지에서는 처음 읽은 조건, 선택한 개념, 재시도 때 바뀐 행동을 차례로 비교해 현재 학습의 출발점을 찾습니다.",
    "{location} 중학생의 수학 계획을 세울 때 ‘{focus}’을 별도 암기 항목으로만 다루지 않습니다. 교과서 예제에서 확인한 원리가 낯선 문장과 다른 수치에도 이어지는지를 관찰해야 실제 이해 정도를 알 수 있습니다.",
    "같은 오답도 원인은 서로 다를 수 있습니다. {location}의 ‘{focus}’ 점검은 계산 결과를 고치는 데서 끝내지 않고 문제를 읽은 순간부터 검산까지 어느 단계에서 판단이 끊겼는지 찾는 데 초점을 둡니다.",
    "수학 학습의 변화는 풀이량보다 학생이 혼자 할 수 있는 행동에서 먼저 드러납니다. {location}에서는 ‘{focus}’을 기준으로 조건 표시, 개념 선택, 풀이 설명, 재확인의 네 행동을 나누어 살펴봅니다.",
    "{location} 페이지가 다루는 핵심은 ‘{focus}’이라는 주제를 얼마나 빨리 끝내는지가 아닙니다. 처음 시도와 하루 뒤 재시도 사이에서 필요한 힌트가 줄고 설명이 구체적으로 바뀌는지를 확인하는 과정입니다.",
)

OPENING_HEADINGS = (
    "정답보다 먼저 확인할 수학의 출발점",
    "한 번의 오답을 학습 정보로 바꾸는 방법",
    "풀이의 처음과 끝을 함께 보는 이유",
    "현재 이해를 드러내는 세 가지 흔적",
    "진도표 앞에 놓아야 할 관찰 기준",
    "설명 가능한 풀이를 만드는 첫 질문",
)

DIAGNOSIS_HEADINGS = (
    "{focus}에서 막힌 위치를 세 단계로 나누기",
    "{focus}의 오류를 결과가 아닌 과정에서 찾기",
    "첫 시도·도움 뒤 시도·재시도를 따로 기록하기",
    "{focus} 이해도를 확인하는 짧은 진단",
    "같은 오답이 반복되는 조건을 추적하기",
)

GRADE_HEADINGS = (
    "중1·중2·중3에서 관찰 기준을 다르게 두기",
    "학년이 올라갈수록 달라지는 {focus}의 역할",
    "현재 학년의 기초와 다음 단원을 함께 연결하기",
    "선행보다 먼저 확인할 학년별 수학 언어",
)

PRACTICE_HEADINGS = (
    "{focus}을 개념에서 낯선 문제로 옮기는 연습",
    "교과서 예제를 그대로 끝내지 않는 복원 활동",
    "힌트를 줄이며 혼자 시작하는 범위를 넓히기",
    "풀이를 설명·적용·검산으로 확장하기",
)

SCHEDULE_HEADINGS = (
    "{location} 생활 리듬에 맞춘 6일 점검 순서",
    "평일의 짧은 복원과 주말의 누적 확인",
    "시험 직전 몰아풀기를 막는 재풀이 간격",
    "분량 대신 종료 기준이 보이는 주간 계획",
)

CASE_HEADINGS = (
    "{focus} 학습 방식을 비교하는 가상 관찰 예시",
    "같은 문제를 두 번 풀 때 무엇을 비교할까",
    "도움을 줄였을 때 나타나는 행동 변화 기록",
    "점수를 예측하지 않는 학습 점검 사례",
)

REVIEW_HEADINGS = (
    "다음 주 과제를 정하는 기록 기준",
    "보호자와 학생이 함께 볼 수 있는 확인표",
    "정답률 밖에서 찾아야 할 변화의 증거",
    "유지·축소·변경을 결정하는 주간 검토",
)

SECTION_ORDERS = (
    ("diagnosis", "grade", "practice", "schedule", "case", "review"),
    ("diagnosis", "practice", "grade", "case", "schedule", "review"),
    ("grade", "diagnosis", "schedule", "practice", "case", "review"),
    ("diagnosis", "case", "practice", "grade", "schedule", "review"),
    ("practice", "diagnosis", "grade", "schedule", "case", "review"),
    ("diagnosis", "schedule", "grade", "case", "practice", "review"),
)

CATEGORY_ORDERS = (
    ("error", "diagnosis", "grade", "practice", "local", "case", "exam", "schedule", "review"),
    ("diagnosis", "error", "practice", "grade", "case", "local", "schedule", "exam", "review"),
    ("grade", "error", "diagnosis", "local", "practice", "exam", "case", "schedule", "review"),
    ("error", "case", "diagnosis", "practice", "grade", "schedule", "local", "exam", "review"),
    ("practice", "diagnosis", "error", "grade", "local", "case", "exam", "schedule", "review"),
    ("diagnosis", "local", "error", "schedule", "grade", "practice", "case", "exam", "review"),
    ("error", "grade", "case", "diagnosis", "exam", "practice", "local", "schedule", "review"),
    ("local", "diagnosis", "practice", "error", "grade", "schedule", "case", "exam", "review"),
    ("diagnosis", "practice", "case", "error", "local", "grade", "exam", "schedule", "review"),
    ("grade", "diagnosis", "practice", "case", "error", "schedule", "exam", "local", "review"),
    ("case", "error", "diagnosis", "grade", "practice", "local", "schedule", "exam", "review"),
    ("error", "schedule", "diagnosis", "local", "practice", "grade", "case", "exam", "review"),
)

HEADING_FRAMES = (
    "{heading} — {location}의 {focus} 점검",
    "{location}에서 다시 보는 {heading}: {focus}",
    "{heading}, {focus} 기록으로 확인하기",
    "{focus}을 기준으로 살펴보는 {heading}",
    "{location} 중학생에게 적용하는 {heading}",
    "{heading}: {location}의 첫 시도와 재시도",
    "{focus} 학습에서 필요한 {heading}",
    "{location}의 {focus} 관찰을 위한 {heading}",
)

PARAGRAPH_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "error": (
        "{location}의 ‘{focus}’ 기록에서는 틀린 답보다 처음 판단과 멈춘 줄을 함께 남겨 원인을 좁힙니다.",
        "‘{focus}’을 다시 볼 때에는 {location} 학생이 사용한 근거와 요청한 힌트를 분리해 적어야 같은 오류인지 확인할 수 있습니다.",
        "따라서 {location}에서는 ‘{focus}’의 첫 풀이를 지우지 않고 수정 전후에 달라진 행동을 비교합니다.",
        "이 오류는 {location}의 ‘{focus}’ 문제를 하루 뒤 다시 시작했을 때 같은 위치에서 나타나는지까지 살펴야 합니다.",
    ),
    "diagnosis": (
        "{location}의 ‘{focus}’ 진단은 혼자 설명 가능, 질문 뒤 가능, 개념 복원 필요의 세 단계로 나누어 기록합니다.",
        "‘{focus}’에서는 {location} 학생이 답을 본 뒤 이해했다고 말하는지보다 자료 없이 첫 단계를 복원하는지를 확인합니다.",
        "{location} 페이지의 다음 과제는 ‘{focus}’ 진단에서 가장 먼저 끊긴 행동 하나를 기준으로 정합니다.",
        "진단 직후 같은 문제를 반복하지 않고 {location}의 ‘{focus}’ 기록을 하루 뒤 재시도와 연결합니다.",
    ),
    "grade": (
        "{location}에서는 현재 학년 문제 속에서 ‘{focus}’에 필요한 이전 개념 한 가지만 찾아 짧게 복원합니다.",
        "‘{focus}’의 학년별 기준은 {location} 학생이 개념을 말하는 단계에서 낯선 조건에 적용하는 단계로 넓혀 갑니다.",
        "선행 여부보다 {location}의 ‘{focus}’ 풀이에서 중1·중2·중3 핵심 언어가 실제로 연결되는지를 먼저 봅니다.",
        "{location} 학생의 ‘{focus}’ 계획은 이전 학년 전체를 반복하지 않고 현재 풀이를 막는 공백만 선택합니다.",
    ),
    "practice": (
        "{location}에서 ‘{focus}’을 연습할 때에는 예제를 덮고 첫 줄을 복원한 뒤 조건이 달라진 문제로 옮깁니다.",
        "‘{focus}’의 적용 여부는 {location} 학생이 숫자나 그림이 바뀌어도 같은 원리를 선택하는지로 확인합니다.",
        "{location}의 ‘{focus}’ 과제는 정답 확인 뒤 선택 이유와 검산 방법을 한 문장씩 덧붙여 마무리합니다.",
        "힌트는 {location} 학생이 ‘{focus}’의 어느 단계까지 혼자 시작했는지 확인한 뒤 한 문장만 제공합니다.",
    ),
    "local": (
        "{location}의 ‘{focus}’ 복습은 고정된 공부시간보다 학교 수업 당일의 짧은 복원과 예정일의 재풀이를 우선합니다.",
        "‘{focus}’ 과제가 밀린 날에도 {location} 학생은 새 분량을 더하지 않고 다음 이해에 필요한 한 문제를 남깁니다.",
        "{location}에서는 ‘{focus}’의 시작 시각과 함께 종료 행동, 다시 볼 날짜까지 적어 생활 일정과 연결합니다.",
        "수행평가가 겹치는 주에는 {location}의 ‘{focus}’ 계획을 개념 확인과 오답 재시도로 나누어 부담을 조정합니다.",
    ),
    "case": (
        "이 사례는 {location}의 실제 성과를 뜻하지 않으며, ‘{focus}’의 처음과 재시도를 비교하는 가상 관찰 예시입니다.",
        "{location}에서 ‘{focus}’ 변화를 판단할 때에도 점수 향상을 단정하지 않고 필요한 도움과 설명의 차이를 기록합니다.",
        "가상의 기록은 {location} 학생 모두의 특성이 아니라 ‘{focus}’ 학습 과정을 비교하는 방법만 보여 줍니다.",
        "‘{focus}’ 사례에서 달라진 행동이 없다면 {location} 학생의 의지가 아니라 과제 크기와 힌트 간격을 먼저 조정합니다.",
    ),
    "exam": (
        "{location}의 시험 준비에서는 ‘{focus}’ 관련 교과서·학교 자료·오답을 먼저 묶고 새 문제는 마지막에 검토합니다.",
        "‘{focus}’의 시험 기록에는 {location} 학생이 문제별로 사용한 시간과 넘어간 기준도 함께 남깁니다.",
        "{location}에서는 ‘{focus}’의 정의 확인, 대표 적용, 서술 설명, 재풀이 날짜를 서로 다른 일정으로 나눕니다.",
        "시험 직전에는 {location}의 ‘{focus}’ 오답 가운데 같은 원인이 두 번 나온 문제부터 다시 시작합니다.",
    ),
    "schedule": (
        "{location}의 ‘{focus}’ 일정은 평일의 짧은 복원, 주말의 설명, 간격을 둔 재시도가 서로 이어지도록 만듭니다.",
        "‘{focus}’ 분량을 다 끝내지 못한 날에도 {location} 학생은 다음 시작 문제와 재풀이 날짜를 남겨 흐름을 보존합니다.",
        "{location}에서는 ‘{focus}’ 공부시간보다 시작할 행동과 멈출 기준이 일정표에 보이는지를 확인합니다.",
        "방학에도 {location}의 ‘{focus}’ 계획은 문제 수를 늘리기 전에 기존 오답의 재현 간격부터 유지합니다.",
    ),
    "review": (
        "{location}의 ‘{focus}’ 확인표는 정답 수, 풀이 근거, 힌트의 양, 재시도 결과를 같은 주에 함께 봅니다.",
        "보호자는 {location} 학생에게 ‘{focus}’ 답을 다시 설명하기보다 처음 무엇을 보고 시작했는지 묻습니다.",
        "‘{focus}’의 다음 주 계획은 {location} 기록에서 유지할 행동 하나와 바꿀 조건 하나만 선택합니다.",
        "{location}에서는 ‘{focus}’ 분량이 아니라 학생 혼자 설명할 수 있는 범위가 넓어졌는지를 검토합니다.",
    ),
}


def is_local_middle_math_slug(slug: str) -> bool:
    return bool(LOCAL_MIDDLE_MATH_PATTERN.fullmatch(slug))


def _plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _focus_from_body(body: str) -> str:
    faq_focus = re.search(r'data-faq-focus="([^"]+)"', body, flags=re.I)
    if faq_focus:
        return unescape(faq_focus.group(1)).strip()
    heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    text = _plain_text(heading.group(1)) if heading else "중등수학 풀이 과정"
    match = re.search(r",\s*(.+?)(?:을|를) 중심으로", text)
    if match:
        return match.group(1).strip()
    for faq_heading in re.findall(r"<h3\b[^>]*>(.*?)</h3>", body, flags=re.I | re.S):
        faq_text = _plain_text(faq_heading)
        faq_question = re.search(
            r"중등수학과외에서는\s*(.+?)(?:을|를)\s*어떻게 복습해야 하나요\?",
            faq_text,
        )
        if faq_question:
            return faq_question.group(1).strip()
    return "중등수학 풀이 과정"


def _kind_for_focus(focus: str) -> str:
    if any(word in focus for word in ("함수", "그래프", "기울기", "절편", "교점", "대응 관계", "최대·최소")):
        return "function"
    if any(
        word in focus
        for word in (
            "도형", "삼각형", "사각형", "다각형", "합동", "닮음", "작도", "평행선", "선분비",
            "피타고라스", "각 관계", "외심", "내심", "원주각", "중심각", "부채꼴", "삼각비",
            "전개도", "겉넓이", "부피", "보조선", "원의 현",
        )
    ):
        return "geometry"
    if any(word in focus for word in ("평균", "중앙값", "최빈값", "상관관계", "산포도", "도수분포", "히스토그램", "상대도수", "경우의 수", "확률")):
        return "data"
    if any(
        word in focus
        for word in (
            "내신", "공책", "검산", "질문", "단위", "설명", "오답", "서술형", "계산 실수", "조건 누락",
            "응용", "유형", "교과서", "시험", "수행평가", "공부 시작", "복습", "불안", "방학", "고등수학",
            "공식 암기",
        )
    ):
        return "routine"
    return "algebra"


def _index_for_slug(slug: str) -> int:
    return int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12], 16)


def _salted_index(slug: str, salt: str) -> int:
    value = f"{slug}|{salt}"
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def _pick(items: tuple[str, ...], index: int, offset: int = 0) -> str:
    return items[(index + offset) % len(items)]


def _has_final_consonant(value: str) -> bool:
    if not value:
        return False
    code = ord(value[-1])
    return 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0


def _fix_focus_particles(value: str, focus: str) -> str:
    has_final = _has_final_consonant(focus)
    obj = "을" if has_final else "를"
    topic = "은" if has_final else "는"
    conjunction = "과" if has_final else "와"
    naming = "이라는" if has_final else "라는"
    replacements = (
        (f"‘{focus}’이라는", f"‘{focus}’{naming}"),
        (f"‘{focus}’을", f"‘{focus}’{obj}"),
        (f"‘{focus}’은", f"‘{focus}’{topic}"),
        (f"‘{focus}’과", f"‘{focus}’{conjunction}"),
        (f"{focus}을", f"{focus}{obj}"),
        (f"{focus}은", f"{focus}{topic}"),
        (f"{focus}과", f"{focus}{conjunction}"),
    )
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def build_local_middle_math_meta(slug: str, body: str) -> tuple[str, str]:
    """Return complete, page-specific search metadata for a local middle-math page."""
    focus = _focus_from_body(body)
    kind = _kind_for_focus(focus)
    search_title = META_TITLE_FRAME.format(slug=slug, focus=focus)
    description = _pick(
        META_DESCRIPTION_FRAMES[kind],
        _salted_index(slug, "search-meta-description"),
    ).format(slug=slug, focus=focus)
    return (
        _fix_focus_particles(search_title, focus),
        _fix_focus_particles(description, focus),
    )


def _school_context_html(slug: str, focus: str, index: int) -> str:
    context = LOCAL_MIDDLE_MATH_CONTEXT.get(slug, {})
    location = slug.removesuffix("중등수학과외")
    town = str(context.get("town") or re.sub(r"^(부산|양산|구미)", "", location))
    schools = [item for item in context.get("schools", []) if isinstance(item, dict)]
    source_name = "제공받은 2025년 학교별 주요통계"
    heading_frames = (
        f"{location} 중학교 공식 자료를 {focus} 학습에 연결하기",
        f"{town} 주소의 중학교 자료와 {focus} 확인 순서",
        f"{location}에서 {focus}을 점검할 때 사용할 학교 자료",
        f"{focus} 복습 전에 확인할 {location} 중학교 공식 정보",
    )
    intro_frames = (
        f"{source_name}에서 학교급과 주소를 대조했습니다. 학교명은 {location} 학생의 재학·배정 가능성을 추정하는 목록이 아니라, 실제 학교 자료를 찾을 때 이름이 비슷한 다른 학교를 연결하지 않기 위한 확인 기준입니다.",
        f"{location}의 학교 정보는 {source_name}에 적힌 중학교 주소를 기준으로 확인했습니다. 거주지만으로 재학 학교나 통학 거리를 판단하지 않으며, {focus} 학습에는 학생이 실제로 받은 시험 범위와 교과서가 우선합니다.",
        f"{source_name}의 주소 표기와 {town}을 정확히 대조했습니다. 이 자료로 학교별 시험 난도나 출제 경향을 단정하지 않고, {location} 학생이 공식 공지와 자신의 수학 자료를 확인할 출발점으로만 사용합니다.",
        f"{location} 중학교 자료는 {source_name}의 학교명·주소·홈페이지 항목에서 확인했습니다. 목록에 학교가 있더라도 자동으로 배정 학교라고 보지 않으며, {focus} 기록은 실제 재학 학교 자료에서 다시 확인해야 합니다.",
    )
    intro = _fix_focus_particles(_pick(intro_frames, index, 1), focus)
    heading = _fix_focus_particles(_pick(heading_frames, index), focus)

    if schools:
        school_items: list[str] = []
        for school in schools[:4]:
            name = str(school.get("school_name") or "").strip()
            homepage = str(school.get("homepage") or "").strip()
            if homepage:
                school_items.append(
                    f'<li><a class="source-link" href="{escape(homepage)}" target="_blank" '
                    f'rel="noopener noreferrer external">{escape(name)} 공식 홈페이지 '
                    f'<span aria-hidden="true">↗</span></a></li>'
                )
            elif name:
                school_items.append(f"<li>{escape(name)} — 제공 자료에 개별 홈페이지 주소 없음</li>")
        all_names = ", ".join(str(item.get("school_name") or "").strip() for item in schools)
        remainder = len(schools) - min(4, len(schools))
        remainder_text = f" 화면에는 우선 4곳을 연결했으며 나머지 {remainder}곳도 제공 자료에서 확인됩니다." if remainder else ""
        school_summary_frames = (
            f"{town} 주소와 정확히 일치한 중학교는 {len(schools)}곳이며 {all_names}입니다.{remainder_text}",
            f"주소의 행정명에 {town}이 정확히 표시된 중학교 {len(schools)}곳은 {all_names}입니다.{remainder_text}",
            f"학교급이 중학교이고 주소가 {town}으로 일치한 항목은 {all_names}, 모두 {len(schools)}곳입니다.{remainder_text}",
        )
        school_summary = _pick(school_summary_frames, index, 2)
        school_block = (
            f"<p>{escape(school_summary)}</p><ul class=\"middle-math-school-links\">{''.join(school_items)}</ul>"
        )
    else:
        no_school_frames = (
            f"제공 자료에서는 주소가 {town}으로 정확히 일치하는 중학교 행을 확인하지 못했습니다. 이것이 {location} 생활권에 중학생이나 통학 학교가 없다는 뜻은 아니며, 다른 동·읍·면의 학교를 가까운 학교라고 추측해 넣지 않습니다.",
            f"{town} 표기와 정확히 맞는 중학교가 제공 통계에 없으므로 학교 이름을 임의로 나열하지 않습니다. {location} 학생의 실제 학교는 교과서 표지, 가정통신문, 시험 범위표, 재학 학교 홈페이지 순서로 직접 확인합니다.",
            f"제공된 학교별 주소에서 {town}과 일치하는 중학교 행은 찾지 못했습니다. 행정명과 통학권이 다를 수 있으므로 {location} 페이지에는 확인되지 않은 학교명이나 예상 이동시간을 추가하지 않습니다.",
        )
        school_block = f"<p>{escape(_pick(no_school_frames, index, 2))}</p>"

    usage_frames = (
        f"공식 홈페이지에서는 학사일정·공지·가정통신문을 확인하고, {focus}의 실제 시험 범위와 문제 내용은 학생이 받은 교과서·유인물·최근 시험지에서 확인합니다. 홈페이지에 없는 출제 범위나 난도를 학교의 특징처럼 만들지 않습니다.",
        f"{focus} 복습에는 학교 홈페이지의 일정 정보, 학생이 받은 범위표, 실제 오답을 서로 다른 자료로 사용합니다. {location} 학생은 공지에서 날짜를 확인하고 수학 내용은 자신의 학교 자료와 대조해야 합니다.",
        f"학교 링크는 {location}의 {focus} 수업을 추천하거나 성과를 보증하기 위한 것이 아닙니다. 시험 일정과 공식 공지를 확인한 뒤 학생의 실제 풀이 기록으로 개념·조건·계산 공백을 정하는 용도입니다.",
        f"{location}에서 {focus} 계획을 세울 때 공식 홈페이지는 일정의 출처로, 교과서와 시험지는 학습 내용의 출처로 구분합니다. 두 자료의 역할을 섞지 않아야 확인되지 않은 학교별 출제 경향을 사실처럼 쓰는 일을 막을 수 있습니다.",
    )
    usage = _fix_focus_particles(_pick(usage_frames, index, 3), focus)
    table_rows = (
        f"<tr><td>학교 공식 홈페이지</td><td>학사일정·공지·가정통신문</td><td>{escape(location)}의 시험·제출 날짜 확인</td></tr>"
        f"<tr><td>학생이 받은 학교 자료</td><td>교과서·범위표·유인물·최근 시험지</td><td>{escape(focus)} 관련 실제 문항 선택</td></tr>"
        f"<tr><td>학생 풀이 기록</td><td>첫 시도·힌트·재시도·검산</td><td>{escape(focus)} 다음 복습 결정</td></tr>"
    )
    return (
        f'<section class="{SCHOOL_CONTEXT_MARKER}" data-school-source="2025-school-statistics">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>{school_block}"
        "<table><thead><tr><th>확인 자료</th><th>자료에서 볼 내용</th><th>수학 계획에 쓰는 방법</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table><p>{escape(usage)}</p></section>"
    )


def _add_school_context(body: str, slug: str, focus: str) -> str:
    if SCHOOL_CONTEXT_MARKER in body:
        return body
    faq = re.search(
        r"<h2\b[^>]*>\s*중등수학 학습에 관해 자주 묻는 질문\s*</h2>",
        body,
        flags=re.I | re.S,
    )
    if not faq:
        return body
    school_context = _school_context_html(slug, focus, _index_for_slug(slug))
    return body[: faq.start()] + school_context + body[faq.start() :]


def _search_intent_html(slug: str, focus: str, index: int) -> str:
    location = slug.removesuffix("중등수학과외")
    kind = _kind_for_focus(focus)
    pack = SEARCH_INTENT_PACKS[kind]
    main_index = _salted_index(slug, "intent-main")
    intro_index = _salted_index(slug, "intent-intro")
    diagnosis_index = _salted_index(slug, "intent-diagnosis")
    grade_heading_index = _salted_index(slug, "intent-grade-heading")
    grade_closing_index = _salted_index(slug, "intent-grade-closing")
    exam_heading_index = _salted_index(slug, "intent-exam-heading")
    exam_cycle_index = _salted_index(slug, "intent-exam-cycle")
    decision_heading_index = _salted_index(slug, "intent-decision-heading")
    decision_text_index = _salted_index(slug, "intent-decision-text")
    order_index = _salted_index(slug, "intent-order")
    main_headings = (
        f"{location}중등수학과외를 찾을 때 {focus}부터 확인하는 순서",
        f"{location} 중학생의 현재 수준과 {focus} 학습 목표 정하기",
        f"{focus} 진단을 내신 계획으로 바꾸는 {location} 수학 기준",
        f"{location}중등수학과외 검색 전에 정리할 {focus} 학습 정보",
        f"{location}에서 {focus}과 학년별 수학 과제를 연결하는 방법",
    )
    intro_frames = (
        f"‘{location}중등수학과외’를 검색했다는 사실만으로 학생의 수준이나 필요한 수업 형태를 정할 수는 없습니다. {focus}과 관련해 최근 어떤 학교 자료에서 막혔는지, 혼자 가능한 단계가 어디까지인지, 시험일까지 무엇을 남겨야 하는지를 먼저 구분합니다.",
        f"{location}이라는 지역명은 학교 자료와 생활 일정을 확인하는 기준일 뿐 성취도를 설명하지 않습니다. {focus}의 현재 풀이, 학년별 선수개념, 내신 범위를 차례로 확인해야 검색 목적이 단순한 문제풀이에서 실제 학습 계획으로 구체화됩니다.",
        f"{location}에서 중등수학 도움을 찾는 이유는 선행, 내신, 오답 보완, 학습 습관처럼 서로 다를 수 있습니다. 이 페이지는 {focus}을 공통 출발점으로 두고 최근 자료와 재시도 결과를 이용해 필요한 과제의 크기를 정합니다.",
        f"지역명과 과목명만으로 교재나 진도를 먼저 고르면 현재 공백이 가려질 수 있습니다. {location} 학생의 {focus} 계획은 최근 시험지·교과서·풀이 기록을 확보한 뒤 학년 목표와 시험 준비 순서를 정하는 방식으로 세웁니다.",
    )
    intro = _pick(intro_frames, intro_index)

    diagnosis_headings = (
        f"{focus}의 시작 수준을 세 자료로 확인하기",
        f"{location} 학생의 현재 수학 상태를 말해 주는 자료",
        f"상담 전에 준비할 {focus}의 실제 풀이 기록",
        f"진도보다 먼저 볼 {location}의 {focus} 근거",
    )
    diagnosis_intro = (
        f"{location}의 {focus} 진단에는 {pack['material']}을 사용합니다. 자료마다 역할이 다르므로 한 문제의 정답률로 전체 수준을 판단하지 않고 아래 세 질문에 답할 수 있는지 봅니다."
    )
    diagnosis_rows = (
        f"<tr><td>현재 범위</td><td>{escape(location)} 학생이 실제로 배우는 단원과 시험 날짜는 무엇인가</td><td>학교 범위표와 교과서 진도 표시</td></tr>"
        f"<tr><td>{escape(focus)} 이해</td><td>{escape(pack['level'])}</td><td>답을 가리지 않은 첫 풀이와 설명</td></tr>"
        f"<tr><td>재시도</td><td>하루 이상 지난 뒤 ‘{escape(focus)}’ 풀이의 첫 단계를 다시 시작하는가</td><td>필요한 힌트와 수정 이유의 차이</td></tr>"
    )
    diagnosis = (
        f"<h3>{escape(_pick(diagnosis_headings, diagnosis_index))}</h3><p>{escape(diagnosis_intro)}</p>"
        "<table><thead><tr><th>확인 항목</th><th>구체적인 질문</th><th>준비할 근거</th></tr></thead>"
        f"<tbody>{diagnosis_rows}</tbody></table>"
    )

    grade_headings = (
        f"중1·중2·중3에서 달라지는 {focus}의 완료 기준",
        f"{location}의 학년별 수학 목표에 {focus} 배치하기",
        f"현재 학년과 다음 학년을 잇는 {focus} 확인표",
        f"선행 여부를 정하기 전 살펴볼 {focus}의 학년 단계",
    )
    grade_items = (
        f"<li><strong>중1:</strong> {escape(pack['grade1'])} {escape(location)}에서는 {escape(focus)}과 연결되는 기본 표현을 학생이 직접 설명하는지 봅니다.</li>"
        f"<li><strong>중2:</strong> {escape(pack['grade2'])} ‘{escape(focus)}’에서 익숙한 유형과 조건이 바뀐 유형을 분리해 기록합니다.</li>"
        f"<li><strong>중3:</strong> {escape(pack['grade3'])} {escape(location)}의 내신 준비와 고등 과정 예습을 같은 완료 기준으로 섞지 않습니다.</li>"
    )
    grade_closings = (
        f"학년이 높다는 이유만으로 어려운 문제를 먼저 배치하지 않습니다. {location} 학생이 {focus}을 설명하고 적용하고 다시 확인할 수 있는 단계까지 마친 뒤 다음 범위를 결정합니다.",
        f"{focus}의 이전 학년 공백이 확인되면 해당 단원 전체를 되돌리기보다 현재 {location} 학교 진도에 필요한 한 개념만 복원해 바로 적용합니다.",
        f"{location}의 학년별 계획에서는 진도표보다 {focus}의 도움 없는 첫 시도와 간격 뒤 재현을 완료 기준으로 사용합니다.",
    )
    grade = (
        f"<h3>{escape(_pick(grade_headings, grade_heading_index))}</h3><ul>{grade_items}</ul>"
        f"<p>{escape(_pick(grade_closings, grade_closing_index))}</p>"
    )

    exam_headings = (
        f"{focus}을 내신·서술형·시험 시간에 연결하는 4단계",
        f"{location} 학교 범위를 기준으로 나누는 시험 준비",
        f"시험일까지 {focus}을 다시 확인하는 간격",
        f"정의 확인에서 서술형 검토까지 이어지는 {location} 내신 순서",
    )
    exam_cycles = (
        (
            ("범위 확인", "공식 홈페이지의 일정과 학생이 받은 범위표를 대조하고 교과서 단원을 표시합니다."),
            ("개념 복원", "대표 예제를 덮은 뒤 정의와 첫 풀이를 자신의 말로 다시 시작합니다."),
            ("서술형 점검", f"답안에서 다음 기준을 확인합니다. {pack['written']}?"),
            ("시험 직전", "새 문제를 늘리지 않고 같은 원인이 반복된 오답과 시간 초과 문항만 다시 풉니다."),
        ),
        (
            ("첫 기록", "최근 시험지에서 맞고 틀림과 관계없이 설명이 끊긴 문항을 고릅니다."),
            ("학교 자료", "교과서 정의와 학교 유인물에서 선택한 풀이 근거를 다시 찾습니다."),
            ("변형 적용", "수치·표현·도형 방향 중 한 조건만 바꾼 문제로 판단을 옮깁니다."),
            ("마감 확인", f"다음 기준을 검토한 뒤 재풀이 날짜를 남깁니다. {pack['written']}?"),
        ),
        (
            ("시험 3주 전", "범위와 수행평가 일정을 확인하고 단원별 첫 오답을 분류합니다."),
            ("시험 2주 전", "대표 유형과 조건이 바뀐 문제를 짝지어 선택 이유를 비교합니다."),
            ("시험 1주 전", f"서술형에서 다음 기준을 확인합니다. {pack['written']}?"),
            ("시험 전날", "새로운 고난도 문제보다 이미 틀린 문항의 첫 단계와 검산만 복원합니다."),
        ),
    )
    exam_items = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(text)} {escape(location)}의 {escape(focus)} 기록에 날짜를 남깁니다.</li>"
        for label, text in exam_cycles[exam_cycle_index % len(exam_cycles)]
    )
    exam = f"<h3>{escape(_pick(exam_headings, exam_heading_index))}</h3><ol>{exam_items}</ol>"

    decision_headings = (
        f"{focus} 학습이 끝났다고 판단할 증거",
        f"{location}의 다음 수학 과제를 정하는 완료 기준",
        f"문제 수가 아닌 {focus}의 변화로 결정하기",
        f"유지·보완·확장을 나누는 {location} 수학 기록",
    )
    decision_frames = (
        f"{focus}의 완료 질문은 ‘{pack['finish']}’입니다. {location} 학생이 아직 설명은 가능하지만 적용에서 멈춘다면 개념을 처음부터 반복하지 않고 조건이 다른 문제 한 개를 다음 과제로 둡니다.",
        f"{location}에서 {focus} 과제를 유지할지는 ‘{pack['finish']}’라는 질문으로 판단합니다. 답을 확인하지 못한 경우 문제 수를 늘리기 전에 힌트의 위치와 재시도 간격을 바꿉니다.",
        f"정답률이 높아도 ‘{pack['finish']}’에 답할 근거가 없으면 {focus}을 완료로 처리하지 않습니다. {location}의 다음 주 계획에는 아직 혼자 하지 못한 행동 하나만 남깁니다.",
        f"{location} 학생이 {focus}에서 확인할 최종 질문은 ‘{pack['finish']}’입니다. 이 기록이 있으면 같은 유형의 반복을 줄이고 다음 단원에 필요한 연결 문제로 확장합니다.",
    )
    decision = (
        f"<h3>{escape(_pick(decision_headings, decision_heading_index))}</h3>"
        f"<p>{escape(_pick(decision_frames, decision_text_index))}</p>"
    )

    orders = (
        (diagnosis, grade, exam, decision),
        (diagnosis, exam, grade, decision),
        (grade, diagnosis, exam, decision),
        (exam, diagnosis, grade, decision),
    )
    body = "".join(orders[order_index % len(orders)])
    result = (
        f'<section class="{SEARCH_INTENT_MARKER}" data-intent-kind="{escape(kind)}">'
        f"<h2>{escape(_pick(main_headings, main_index))}</h2><p>{escape(intro)}</p>{body}</section>"
    )
    return _fix_focus_particles(result, focus)


def _add_search_intent(body: str, slug: str, focus: str) -> str:
    if SEARCH_INTENT_MARKER in body:
        return body
    insertion = re.search(
        rf'<section\s+class="{SCHOOL_CONTEXT_MARKER}"\b',
        body,
        flags=re.I,
    )
    if not insertion:
        insertion = re.search(
            r"<h2\b[^>]*>\s*중등수학 학습에 관해 자주 묻는 질문\s*</h2>",
            body,
            flags=re.I | re.S,
        )
    if not insertion:
        return body
    search_intent = _search_intent_html(slug, focus, _index_for_slug(slug))
    return body[: insertion.start()] + search_intent + body[insertion.start() :]


def _strip_heading_ids(html: str) -> str:
    return re.sub(r'(<h[23]\b[^>]*?)\s+id=["\'][^"\']+["\']', r"\1", html, flags=re.I)


def _existing_faq(body: str) -> str:
    marker = re.search(
        r"<h2\b[^>]*>\s*중등수학 학습에 관해 자주 묻는 질문\s*</h2>",
        body,
        flags=re.I | re.S,
    )
    if not marker:
        return ""
    return _strip_heading_ids(body[marker.start() :].strip())


def _diagnosis_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(DIAGNOSIS_HEADINGS, index, 1).format(focus=focus)
    rows = (
        ("처음 읽기", f"{focus} 문제에서 조건과 질문을 구분하는가", "표시 없이 계산을 시작한 순간까지 남깁니다."),
        ("풀이 진행", str(pack["signal"]), f"{pack['action']}"),
        ("간격 뒤 재시도", str(pack["transfer"]), f"{pack['check']}"),
    )
    table_rows = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(question)}</td><td>{escape(record)}</td></tr>"
        for stage, question, record in rows
    )
    variants = (
        f"{location}에서 {focus}을 진단할 때 정답률 하나로 시작 수준을 정하지 않습니다. {pack['signal']}를 먼저 확인하고, 힌트가 들어간 시점과 학생이 바꾼 풀이를 구분해 적습니다.",
        f"{focus}의 어려움은 개념을 모르는 경우와 개념을 문제에서 꺼내지 못하는 경우가 다릅니다. {location} 페이지에서는 첫 시도에 사용한 근거를 묻고 {pack['first']} 그 뒤 같은 원리를 다른 표현에서 다시 찾게 합니다.",
        f"진단 문제는 많이 필요하지 않습니다. {location} 학생이 {focus}과 관련한 대표 문제 한 개를 풀 때 {pack['signal']}를 관찰하고, 도움 없이 가능한 단계와 질문 뒤 가능한 단계를 따로 표시합니다.",
    )
    note = (
        f"표의 세 기록은 학생을 ‘잘함·못함’으로 나누기 위한 점수가 아닙니다. {location}에서 다음 과제를 고를 때 {focus}을 다시 설명할지, 적용 문제로 옮길지, 검산 절차만 보완할지를 정하는 근거입니다."
    )
    return (
        f"<h3>{escape(heading)}</h3>"
        f"<p>{escape(_pick(variants, index, 2))}</p>"
        "<table><thead><tr><th>관찰 단계</th><th>확인 질문</th><th>남길 기록</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table><p>{escape(note)}</p>"
    )


def _grade_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(GRADE_HEADINGS, index, 2).format(focus=focus)
    grade_sets = (
        (
            ("중1", "문자·식·좌표·기본 도형의 정의를 정확히 읽고, 계산 과정에 사용한 규칙을 짧게 말하는 단계입니다."),
            ("중2", "여러 개념이 한 문제에 함께 나오므로 조건을 분리하고 식·표·그래프·도형 사이를 오가는 연습이 필요합니다."),
            ("중3", "이차식과 함수, 증명, 통계처럼 선택할 전략이 늘어납니다. 풀이의 이유와 다른 방법의 가능성까지 확인해야 고등수학의 기초가 됩니다."),
        ),
        (
            ("중1", "답을 빨리 내기보다 수학 용어와 기호의 뜻을 자신의 문장으로 바꾸는 습관을 먼저 만듭니다."),
            ("중2", "익숙한 계산과 새로운 활용을 구분하고, 문제의 조건을 식이나 그림으로 옮기는 첫 단계를 안정시킵니다."),
            ("중3", "공식 선택의 근거와 검산 방법을 함께 남겨 복합 문제에서도 풀이 방향을 스스로 조정하도록 합니다."),
        ),
        (
            ("중1", "교과서 예제의 각 줄이 왜 필요한지 확인해 중등수학의 표현 방식에 익숙해지는 시기입니다."),
            ("중2", "단원 사이 연결이 많아지는 만큼 이전 개념의 공백과 현재 문제의 낯섦을 구별해야 합니다."),
            ("중3", "선행 진도보다 중등 핵심 개념을 설명·적용·재확인할 수 있는지 먼저 살펴야 합니다."),
        ),
    )
    grades = grade_sets[index % len(grade_sets)]
    items = "".join(
        f"<li><strong>{grade}:</strong> {escape(text)} {escape(focus)}도 이 기준에 맞춰 확인합니다.</li>"
        for grade, text in grades
    )
    closing = (
        f"{location}의 실제 학년 계획에서는 앞선 학년 내용을 모두 다시 시작하지 않습니다. {focus} 풀이에서 드러난 한 가지 공백만 짧게 복원하고, 현재 학교 진도 문제에서 같은 원리를 바로 사용하게 해야 복습이 현재 학습과 분리되지 않습니다."
    )
    return f"<h3>{escape(heading)}</h3><ul>{items}</ul><p>{escape(closing)}</p>"


def _practice_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(PRACTICE_HEADINGS, index, 3).format(focus=focus)
    lead_variants = (
        f"{focus}을 배운 날에는 예제 풀이를 덮은 뒤 첫 줄만 다시 세워 봅니다. {pack['first']} 이어서 {pack['action']}",
        f"{location}에서 사용할 연습은 ‘보고 따라 풀기’와 ‘기억해 다시 시작하기’를 분리합니다. 먼저 {pack['first']} 예제와 숫자나 방향이 다른 문제에서는 {pack['transfer']}",
        f"문제 난도를 한꺼번에 높이지 않고 도움의 양을 줄입니다. {focus}의 정의를 볼 수 있는 1단계, 핵심 질문만 받는 2단계, 자료 없이 시작하는 3단계를 거치며 {pack['check']}",
        f"{focus} 복습은 풀이를 예쁘게 다시 쓰는 활동이 아닙니다. 처음 선택한 방법 옆에 선택 이유를 남기고, 막힌 줄에서는 {pack['action']} 마지막에는 {pack['check']}",
    )
    tasks = (
        f"교과서 예제에서 {focus}과 직접 연결되는 조건에 밑줄을 긋고 나머지 설명을 가린 채 풀이의 출발점을 말합니다.",
        f"같은 개념의 문제를 표현만 바꾸어 풀고, 두 문제에서 변하지 않은 원리와 달라진 조건을 각각 한 줄로 적습니다.",
        f"풀이가 끝나면 {pack['check']} 틀렸다면 답을 지우기 전에 처음 판단이 달라져야 하는 지점을 표시합니다.",
        f"하루 뒤에는 완성된 풀이를 보지 않고 {focus}의 첫 단계만 복원합니다. 시작할 수 없다면 필요한 힌트를 한 문장으로 제한합니다.",
    )
    rotate = index % len(tasks)
    ordered = tasks[rotate:] + tasks[:rotate]
    items = "".join(f"<li>{escape(task)}</li>" for task in ordered)
    warning = (
        f"이 과정에서 피할 방식은 {pack['risk']}입니다. {location} 페이지의 목표는 풀이 형식을 통일하는 것이 아니라 학생이 {focus}에 필요한 근거를 골라 혼자 시작할 범위를 넓히는 것입니다."
    )
    return f"<h3>{escape(heading)}</h3><p>{escape(_pick(lead_variants, index, 1))}</p><ol>{items}</ol><p>{escape(warning)}</p>"


def _schedule_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(SCHEDULE_HEADINGS, index, 1).format(location=location)
    day_sets = (
        (
            ("1일차", "학교 자료에서 대표 문제 한 개를 골라 조건 표시와 첫 풀이를 그대로 남깁니다."),
            ("2일차", "정의나 성질을 보지 않고 한 문장으로 복원한 뒤 예제의 빈 줄을 채웁니다."),
            ("3일차", "표현이나 수치가 다른 문제에 같은 원리를 적용하고 선택 이유를 적습니다."),
            ("4일차", "전날 틀린 문제를 답 없이 다시 시작해 필요한 힌트의 양을 비교합니다."),
            ("5일차", "서술형 한 문항에서 조건·개념·계산·결론이 모두 보이는지 확인합니다."),
            ("6일차", "첫날 기록과 마지막 기록을 나란히 놓고 다음 주에 유지할 행동 하나를 정합니다."),
        ),
        (
            ("수업 당일", "배운 정의와 예제를 15분 안에 복원하고 이해가 끊긴 줄에 표시합니다."),
            ("다음 날", "표시한 한 줄만 교과서에서 확인한 뒤 풀이를 처음부터 다시 씁니다."),
            ("평일 중간", "같은 개념의 다른 유형을 골라 조건과 첫 전략을 비교합니다."),
            ("평일 마지막", "오답 원인을 한 가지로 분류하고 검산 방법을 덧붙입니다."),
            ("주말 전반", "학교 자료의 서술형이나 수행평가형 문항으로 설명을 확장합니다."),
            ("주말 마감", "재풀이 날짜와 다음 시작 문제를 적어 다음 주 계획으로 넘깁니다."),
        ),
        (
            ("관찰", "완성된 풀이를 고치지 말고 처음 멈춘 위치와 학생의 질문을 기록합니다."),
            ("복원", "필요한 개념을 짧게 확인한 뒤 자료를 덮고 자신의 말로 다시 설명합니다."),
            ("적용", "조건이 하나 달라진 문제에서 같은 원리가 유지되는지 확인합니다."),
            ("간격", "하루 이상 지난 뒤 도움 없이 첫 줄을 세우고 이전 기록과 비교합니다."),
            ("설명", "풀이 순서를 상대에게 설명하며 생략한 근거나 단위를 찾아 보완합니다."),
            ("결정", "다음 주에는 개념, 적용, 검산 중 하나만 우선 과제로 선택합니다."),
        ),
    )
    days = day_sets[index % len(day_sets)]
    items = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(text)} {escape(focus)} 기록과 연결합니다.</li>"
        for label, text in days
    )
    intro = (
        f"{location}에서도 귀가 시각, 학교 과제, 수행평가 일정은 학생마다 다릅니다. 따라서 매일 같은 분량을 강제하지 않고 {focus}을 확인할 최소 행동과 종료 기준을 먼저 정합니다. 시간이 짧은 날에는 새 문제보다 수업 당일의 첫 판단을 복원합니다."
    )
    closing = (
        f"시험 기간에는 이 순서를 새 교재로 바꾸지 않습니다. 이미 표시한 {focus} 문제를 범위별로 묶고, 설명 없이 맞힌 문제와 같은 오류가 두 번 나온 문제를 먼저 다시 봅니다. 일정이 밀리면 문제 수를 줄이되 재풀이 날짜는 남깁니다."
    )
    return f"<h3>{escape(heading)}</h3><p>{escape(intro)}</p><ol>{items}</ol><p>{escape(closing)}</p>"


def _case_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(CASE_HEADINGS, index, 2).format(focus=focus)
    case_variants = (
        (
            f"가상의 중2 학생이 {focus} 문제를 풀 때 답은 맞혔지만 풀이 이유를 묻자 첫 줄부터 다시 시작하지 못했다고 가정해 봅니다.",
            f"첫 주에는 {pack['first']} 둘째 시도에서는 {pack['action']} 정답률을 비교하기보다 힌트 전에 시작한 단계와 설명이 멈춘 위치를 기록합니다.",
            f"일주일 뒤 같은 문제를 외워 풀지 않도록 표현을 바꿔 제시합니다. {pack['transfer']} 변화가 없다면 공부 의지로 판단하지 않고 과제 크기나 힌트 방식을 하나만 조정합니다.",
        ),
        (
            f"다음은 {location}의 실제 학생 성과가 아니라 기록 방법을 설명하기 위한 가상 상황입니다. 중3 학생이 시험 전 {focus} 문제만 반복했지만 조건이 바뀌면 방법을 고르지 못했다고 가정합니다.",
            f"연습량을 더하기 전에 처음 풀이를 보존하고 {pack['signal']}를 확인합니다. 이어 {pack['first']} 재시도에서는 도움을 한 단계 줄여 학생이 스스로 연결한 부분을 표시합니다.",
            f"검토할 때는 점수 상승을 예상하지 않습니다. {pack['check']} 이 행동이 안정되면 다음 유형으로 옮기고, 다시 끊기면 필요한 개념 한 항목만 복원합니다.",
        ),
        (
            f"가상의 중1 학생이 {focus} 설명을 들을 때는 이해했다고 했지만 다음 날 같은 원리를 꺼내지 못했다고 해 봅니다. 이는 기억 부족인지 표현 전환의 어려움인지 아직 구분되지 않은 상태입니다.",
            f"{location} 페이지의 관찰자는 답을 알려주기 전에 학생이 찾는 자료와 질문을 적습니다. {pack['action']} 이후 자료를 덮고 같은 첫 단계를 다시 말하게 합니다.",
            f"두 번째 기록에서 필요한 도움이 줄었는지, 풀이 근거가 구체화됐는지 확인합니다. {pack['transfer']} 결과가 같아도 과정이 달라졌다면 그 행동을 다음 주 과제에 남깁니다.",
        ),
        (
            f"{focus}에서 계산 실수가 반복되는 가상 학생을 생각해 볼 수 있습니다. 매번 답만 고치면 개념 선택, 조건 해석, 계산 중 어느 지점이 원인인지 알기 어렵습니다.",
            f"첫 시도에는 멈춘 위치를 그대로 두고 {pack['signal']}를 관찰합니다. 그 뒤 {pack['first']} 한 번에 모든 풀이 습관을 바꾸지 않고 확인 행동 하나만 정합니다.",
            f"다음 시도에서는 {pack['check']} 학생이 스스로 오류를 찾은 순간과 요청한 힌트를 기록하면 {location}의 다음 학습 계획을 구체적으로 조정할 수 있습니다.",
        ),
    )
    paragraphs = case_variants[index % len(case_variants)]
    return f"<h3>{escape(heading)}</h3>" + "".join(f"<p>{escape(p)}</p>" for p in paragraphs)


def _student_case_html(slug: str, focus: str) -> str:
    location = slug.removesuffix("중등수학과외")
    kind = _kind_for_focus(focus)
    math_pack = MATH_PACKS[kind]
    intent_pack = SEARCH_INTENT_PACKS[kind]
    case_pack = STUDENT_CASE_PACKS[kind]
    grade_index = _salted_index(slug, "case-grade") % 3
    grade = ("중1", "중2", "중3")[grade_index]
    grade_goal = str(intent_pack[("grade1", "grade2", "grade3")[grade_index]]).rstrip(".")
    observation = _pick(case_pack["observation"], _salted_index(slug, "case-observation"))
    evidence = _pick(case_pack["evidence"], _salted_index(slug, "case-evidence"))
    action = _pick(case_pack["action"], _salted_index(slug, "case-action"))
    transfer = _pick(case_pack["transfer"], _salted_index(slug, "case-transfer"))

    heading_frames = (
        f"{location} {grade} 학생의 {focus} 상담 기록을 만드는 합성 사례",
        f"{focus}의 첫 시도와 재시도를 비교하는 {location} {grade} 사례",
        f"{location}에서 {focus} 과제를 정하는 {grade} 상담 예시",
        f"정답률 대신 {focus} 행동 변화를 보는 {location} {grade} 수학 사례",
        f"{focus}에서 막힌 위치를 찾는 {location} {grade} 합성 기록",
        f"{location} {grade}의 {focus} 계획을 조정하는 가상 상담 흐름",
    )
    disclaimer_frames = (
        f"아래 내용은 {location}의 실제 학생, 학교 성과, 상담 후기를 옮긴 것이 아닙니다. 개인정보가 없는 합성 사례로 {focus}의 관찰 자료를 수업 계획으로 바꾸는 과정을 설명합니다.",
        f"이 사례는 {location} 학생의 공통 성향이나 성적 변화를 주장하지 않습니다. 서로 다른 학습 기록을 조합한 가상 상황이며 {focus} 상담에서 확인할 질문과 결정 기준만 보여 줍니다.",
        f"{location}이라는 지역명으로 학생의 수준을 추정할 수는 없습니다. 다음 {grade} 사례는 실제 인물을 가리키지 않으며 {focus}의 첫 시도, 도움 뒤 시도, 간격 뒤 재시도를 비교하기 위한 예시입니다.",
        f"다음 기록은 {location}의 특정 학생이나 학교를 묘사하지 않는 합성 예시입니다. {focus} 학습에서 점수를 예측하지 않고 관찰한 행동으로 다음 과제를 정하는 방법에 초점을 둡니다.",
    )
    situation_frames = (
        f"가상의 {grade} 학생은 {location}의 {focus} 점검에서 다음 행동을 보였습니다. {observation} 상담자는 곧바로 연습량을 늘리지 않고 {evidence} 이 기록만으로 개념 부족을 단정하지 않고 문제 해석, 개념 선택, 계산, 검산 중 어디에서 흐름이 끊기는지 나눕니다.",
        f"{location}의 첫 상담에서 가상의 {grade} 학생에게 나타난 {focus} 장면은 다음과 같습니다. {observation} 이를 확인하기 위해 {evidence} 정답 개수보다 학생이 혼자 시작한 단계와 요청한 힌트의 크기를 기준선으로 남깁니다.",
        f"{location}에서 {focus}을 공부하는 가상의 {grade} 학생에게 다음 행동이 보였다고 가정합니다. {observation} 이때 상담 기록에는 ‘노력이 부족하다’는 평가 대신 {evidence} 그 결과를 이용해 한 주 동안 바꿀 행동 하나만 선택합니다.",
        f"가상의 {grade} 학생은 {location}의 {focus} 풀이에서 다음 행동을 보였습니다. {observation} 원인을 한 번에 정하기 전에 {evidence} 같은 지점이 다른 문제와 재시도에서도 반복되는지를 확인합니다.",
    )
    parent_questions = (
        f"보호자는 ‘왜 또 틀렸니?’보다 ‘{focus} 문제에서 처음 무엇을 보고 시작했니?’라고 묻습니다.",
        f"상담에서는 ‘몇 문제를 더 풀까?’보다 ‘{focus}의 어느 단계까지 도움 없이 설명할 수 있나?’를 먼저 묻습니다.",
        f"가정에서는 ‘오늘 몇 점이었니?’보다 ‘{focus} 풀이에서 힌트 없이 다시 한 행동은 무엇이니?’를 확인합니다.",
        f"다음 계획을 정할 때에는 ‘진도를 얼마나 나갔나?’보다 ‘{focus}의 같은 오류가 어떤 조건에서 다시 나타났나?’를 묻습니다.",
    )
    local_closings = (
        f"{location}이라는 위치는 학교 일정과 이동 시간을 확인하는 기준일 뿐 학습 성향을 설명하지 않습니다. 실제 계획에서는 재학 학교의 시험 범위와 학생의 귀가 시각을 확인해 위 재시도 간격만 조정합니다.",
        f"{location} 학생이라는 이유로 특정 교재나 진도를 권하지 않습니다. 학교 자료의 날짜와 학생이 남긴 {focus} 기록을 대조하고, 시간이 부족한 날에도 첫 단계 복원과 다음 재풀이 날짜는 남깁니다.",
        f"이 합성 사례를 {location}의 실제 계획에 적용할 때에는 학교별 난도나 출제 경향을 추측하지 않습니다. 학생이 받은 범위표·시험지·공책에서 {focus} 문항을 골라 같은 관찰 순서만 사용합니다.",
        f"{location}의 생활 일정은 학생마다 다르므로 수업 횟수나 문제 수를 사례와 똑같이 맞추지 않습니다. {focus}에서 혼자 가능한 행동과 시험일까지 남은 날짜를 기준으로 과제 크기를 다시 정합니다.",
    )
    decision_frames = (
        f"이 {focus} 사례의 학년 목표는 ‘{grade_goal}’입니다. {action} 그런 다음 {transfer} 점수가 오를 것이라고 단정하지 않고 필요한 힌트가 줄고 설명의 근거가 늘었는지를 다음 결정에 사용합니다.",
        f"{focus} 점검의 {grade} 단계에서는 ‘{grade_goal}’을 목표로 둡니다. 첫 변화로는 {action} 이후 {transfer} 결과가 같더라도 혼자 시작한 범위가 넓어졌는지와 같은 오류가 반복됐는지를 따로 기록합니다.",
        f"{focus}의 첫 주 과제는 {action} {grade}의 확인 목표인 ‘{grade_goal}’과 연결한 뒤 {transfer} 한 번의 성공을 일반화하지 않고 간격을 둔 재시도에서 같은 행동이 남는지 봅니다.",
        f"{focus} 상담 후 바로 새 단원으로 넘어가지 않고 {action} 이어서 {transfer} 이 순서는 {grade} 목표인 ‘{grade_goal}’을 실제 풀이에서 확인하기 위한 것이며 성과를 미리 약속하는 기준이 아닙니다.",
    )
    branch_sets = (
        (
            "혼자 근거까지 설명하면 숫자·표현·조건을 바꾼 문제로 옮깁니다.",
            "짧은 질문 뒤 가능하면 힌트를 한 단계 줄이고 같은 지점부터 다시 시작합니다.",
            "첫 줄을 시작하지 못하면 현재 단원 전체가 아니라 바로 필요한 이전 개념 하나만 복원합니다.",
        ),
        (
            "풀이와 검산을 스스로 연결하면 다음 유형에서 첫 판단만 기록하게 합니다.",
            "답은 맞지만 설명이 끊기면 완성 풀이 대신 선택 이유를 묻는 질문 하나만 제공합니다.",
            "같은 오류가 다시 나오면 문제 수를 늘리지 않고 과제 난도·분량·재시도 간격 중 하나만 바꿉니다.",
        ),
        (
            "다음 날에도 첫 단계를 복원하면 학교 범위 안의 낯선 문항으로 적용 범위를 넓힙니다.",
            "자료를 보고만 가능하면 자료를 가리는 순서를 정해 도움의 양을 줄입니다.",
            "질문 뒤에도 시작이 어렵다면 오답 이름보다 막힌 수학 용어와 조건부터 다시 확인합니다.",
        ),
        (
            "사용한 개념과 조건을 모두 말하면 풀이 시간을 재기 전에 표현이 다른 문제를 제시합니다.",
            "계산은 가능하지만 근거가 없으면 풀이 한 줄과 이유 한 문장을 짝지어 다시 씁니다.",
            "재시도에서 변화가 없으면 학생의 의지로 평가하지 않고 첫 과제의 크기를 더 작게 나눕니다.",
        ),
    )
    branches = branch_sets[_salted_index(slug, "case-branches") % len(branch_sets)]

    def clean(value: str) -> str:
        return _fix_focus_particles(value, focus)

    heading = clean(_pick(heading_frames, _salted_index(slug, "case-heading")))
    disclaimer = clean(_pick(disclaimer_frames, _salted_index(slug, "case-disclaimer")))
    situation = clean(_pick(situation_frames, _salted_index(slug, "case-situation")))
    decision = clean(_pick(decision_frames, _salted_index(slug, "case-decision")))
    parent_question = clean(_pick(parent_questions, _salted_index(slug, "case-question")))
    local_closing = clean(_pick(local_closings, _salted_index(slug, "case-local")))
    phase_rows = (
        ("첫 확인", observation, "첫 풀이를 지우지 않고 멈춘 줄과 사용한 근거를 남김"),
        ("한 가지 조정", action, "도움을 받은 시점과 학생이 이어서 한 행동을 구분"),
        ("간격 뒤 재시도", transfer, str(math_pack["check"])),
    )
    rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(clean(observed))}</td><td>{escape(clean(record))}</td></tr>"
        for label, observed, record in phase_rows
    )
    branch_items = "".join(f"<li>{escape(clean(item))}</li>" for item in branches)
    return (
        f'<section class="middle-math-block middle-math-case {STUDENT_CASE_MARKER}" '
        f'data-case-model="composite" data-case-grade="{escape(grade)}" data-case-kind="{escape(kind)}">'
        f"<h3>{escape(heading)}</h3><p>{escape(disclaimer)}</p><p>{escape(situation)}</p>"
        "<table><thead><tr><th>관찰 시점</th><th>학생 행동과 과제</th><th>남길 기록</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><p>{escape(decision)}</p><ol>{branch_items}</ol>"
        f"<p>{escape(parent_question)} {escape(local_closing)}</p></section>"
    )


def _replace_student_case(body: str, slug: str, focus: str) -> str:
    if STUDENT_CASE_MARKER in body:
        return body
    case_pattern = re.compile(
        r'<section\b(?=[^>]*class="[^"]*\bmiddle-math-case\b[^"]*")[^>]*>.*?</section>',
        flags=re.I | re.S,
    )
    student_case = _student_case_html(slug, focus)
    if case_pattern.search(body):
        return case_pattern.sub(student_case, body, count=1)
    for marker in (SEARCH_INTENT_MARKER, SCHOOL_CONTEXT_MARKER):
        match = re.search(rf'<section\b[^>]*class="[^"]*\b{re.escape(marker)}\b[^"]*"', body, flags=re.I)
        if match:
            return body[: match.start()] + student_case + body[match.start() :]
    faq = re.search(
        r"<h2\b[^>]*>\s*중등수학 학습에 관해 자주 묻는 질문\s*</h2>",
        body,
        flags=re.I | re.S,
    )
    return body[: faq.start()] + student_case + body[faq.start() :] if faq else body + student_case


def _middle_math_context_links_html(slug: str, focus: str) -> str:
    location = slug.removesuffix("중등수학과외")
    context = LOCAL_MIDDLE_MATH_CONTEXT.get(slug, {})
    parent_english = str(context.get("parent_slug") or "").strip()
    if parent_english.endswith("중등영어과외"):
        parent_math = parent_english.removesuffix("중등영어과외") + "중등수학과외"
    else:
        parent_math = str(context.get("city") or location[:2]) + "중등수학과외"
    parent_location = parent_math.removesuffix("중등수학과외")
    local_math = f"{location}수학과외"
    parent_labels = (
        f"{parent_location} 중등수학 학습 범위",
        f"{parent_location} 중학생 수학 안내",
        f"{parent_location} 중등수학과외 기준",
        f"{parent_location} 지역의 중등수학 흐름",
    )
    local_labels = (
        f"{location} 수학과외 전체 안내",
        f"{location} 수학 학습 페이지",
        f"{location} 수학과외 기준",
        f"{location} 지역 수학 학습 안내",
    )
    parent_link = (
        f'<a href="/{escape(parent_math)}/" data-link-role="broader-middle-math">'
        f'{escape(_pick(parent_labels, _salted_index(slug, "context-parent-label")))}</a>'
    )
    local_link = (
        f'<a href="/{escape(local_math)}/" data-link-role="local-all-math">'
        f'{escape(_pick(local_labels, _salted_index(slug, "context-local-label")))}</a>'
    )
    frames = (
        f"{focus}의 현재 학년 기준을 더 넓은 지역 단위와 비교하려면 {parent_link}에서 공통 단원과 학년별 연결을 확인할 수 있습니다. 과목 전체의 진단·오답·시험 준비 흐름은 {local_link}에서 이어서 살펴보되, 이 페이지에서 확인한 첫 풀이와 재시도 기록을 우선 기준으로 사용합니다.",
        f"이 페이지의 {focus} 기록만으로 다른 단원까지 일반화하지 않습니다. 상위 생활권의 중등 과정은 {parent_link}에서 비교하고, 초·중·고 수학 학습의 큰 흐름은 {local_link}에서 확인한 뒤 학생의 실제 학교 범위에 필요한 내용만 선택합니다.",
        f"{location}의 {focus} 계획을 인접 범위와 함께 검토할 때에는 {parent_link}를 이용해 중등수학의 공통 기준을 먼저 맞춥니다. 이후 {local_link}에서 과목 전체의 연결을 확인하되, 같은 링크를 반복해서 따라가기보다 현재 오답과 직접 관련된 페이지 두 곳만 참고합니다.",
        f"현재 {focus}이 한 단원 문제인지 학년 전체의 공백인지 구분하려면 {parent_link}의 중등 기준과 대조할 수 있습니다. 더 넓은 과목별 설명이 필요할 때만 {local_link}를 확인하고, 새 페이지를 보는 대신 기존 재시도 기록이 충분하면 현재 계획을 유지합니다.",
        f"{focus} 복습을 현재 페이지에서 마친 뒤에는 {parent_link}에서 다음 학년과 연결되는 기준을 확인할 수 있습니다. 단원보다 넓은 수학 학습 순서가 필요한 경우에는 {local_link}를 보며, 실제 시험 범위와 무관한 링크까지 한꺼번에 확장하지 않습니다.",
        f"{location} 학생의 {focus} 기록을 해석할 때 지역 페이지를 많이 여는 것보다 비교 목적을 분명히 하는 편이 좋습니다. {parent_link}는 상위 지역의 중등수학 범위를 볼 때, {local_link}는 수학 과목 전체의 학습 순서를 볼 때 한 번씩 사용합니다.",
    )
    paragraph = _fix_focus_particles(_pick(frames, _salted_index(slug, "context-frame")), focus)
    return (
        f'<aside class="{CONTEXT_LINKS_MARKER}" data-link-count="2" '
        f'aria-label="{escape(location)} 중등수학 관련 페이지">'
        f"<p>{paragraph}</p></aside>"
    )


def _add_middle_math_context_links(body: str, slug: str, focus: str) -> str:
    if CONTEXT_LINKS_MARKER in body:
        return body
    faq_heading = re.search(
        r"<h2\b[^>]*>(?:(?!</h2>).)*(?:FAQ|자주\s*묻는\s*질문)(?:(?!</h2>).)*</h2>",
        body,
        flags=re.I | re.S,
    )
    if not faq_heading:
        return body
    contextual = _middle_math_context_links_html(slug, focus)
    return body[: faq_heading.start()] + contextual + body[faq_heading.start() :]


def _middle_math_faq_html(slug: str, focus: str) -> str:
    location = slug.removesuffix("중등수학과외")
    kind = _kind_for_focus(focus)
    math_pack = MATH_PACKS[kind]
    intent_pack = SEARCH_INTENT_PACKS[kind]
    case_pack = STUDENT_CASE_PACKS[kind]
    grade_index = _salted_index(slug, "case-grade") % 3
    grade = ("중1", "중2", "중3")[grade_index]
    grade_goal = str(intent_pack[("grade1", "grade2", "grade3")[grade_index]]).rstrip(".")
    observation = _pick(case_pack["observation"], _salted_index(slug, "faq-observation"))
    evidence = _pick(case_pack["evidence"], _salted_index(slug, "faq-evidence"))
    action = _pick(case_pack["action"], _salted_index(slug, "faq-action"))
    transfer = _pick(case_pack["transfer"], _salted_index(slug, "faq-transfer"))

    heading_frames = (
        f"{location}중등수학과외와 {focus}에 관해 자주 묻는 질문",
        f"{location} {grade} 학생의 {focus} 학습 FAQ",
        f"{focus} 진단부터 내신 복습까지 묻는 {location} FAQ",
        f"{location}에서 {focus} 계획을 세울 때 자주 묻는 질문",
        f"학교 자료와 {focus} 재시도에 관한 {location} 중등수학 FAQ",
        f"{location} 중학생의 {focus} 과제 결정 FAQ",
    )
    question_2_frames = (
        f"{location} {grade} 학생은 {focus}에서 무엇을 먼저 확인해야 하나요?",
        f"{focus} 학습 목표는 {location} {grade}에서 어떻게 정하나요?",
        f"{location} {grade}의 {focus} 복습과 다음 학년 준비를 어떻게 연결하나요?",
        f"{location} {grade} 학생이 {focus} 선행보다 먼저 확인할 기준은 무엇인가요?",
    )
    question_3_frames = (
        f"{location} 학교 시험을 앞두고 {focus}은 어떤 순서로 준비해야 하나요?",
        f"{location} 내신 범위에서 {focus} 서술형은 어떻게 점검하나요?",
        f"시험까지 시간이 짧을 때 {location}의 {focus} 과제를 어떻게 줄이나요?",
        f"{location} 학생의 시험지와 교과서를 {focus} 복습에 어떻게 사용하나요?",
    )
    question_4_frames = (
        f"보호자는 {location} 학생의 {focus} 오답에 어떤 질문을 하면 좋나요?",
        f"{location}의 {focus} 상담 전에 어떤 풀이 기록을 준비해야 하나요?",
        f"{focus} 문제에서 계속 도움을 요청하는 {location} 학생은 어떻게 관찰하나요?",
        f"{location} 학생이 {focus}을 이해했다고 말할 때 무엇으로 확인하나요?",
    )
    question_5_frames = (
        f"{location}에서 {focus} 복습을 마쳤다고 판단하는 기준은 무엇인가요?",
        f"{focus}의 다음 유형으로 넘어가도 되는지 {location}에서는 어떻게 확인하나요?",
        f"{location} 학생의 {focus} 재시도 결과가 같으면 무엇을 바꿔야 하나요?",
        f"{focus} 문제를 맞혔는데도 {location}에서 다시 확인해야 하는 이유는 무엇인가요?",
    )
    answer_1_frames = (
        f"먼저 {intent_pack['material']}을 나란히 놓고 {math_pack['signal']}를 확인합니다. {location} 학생의 첫 풀이를 지우지 않은 채 {math_pack['first']} 하루 이상 뒤에는 답과 해설을 가리고 같은 원리의 첫 단계를 다시 시작해 설명과 검산이 이어지는지 봅니다.",
        f"{location}의 {focus} 복습은 새 문제집 선택보다 실제 풀이 확보에서 시작합니다. {evidence} 이어서 {math_pack['first']} 같은 날의 정답과 간격 뒤 재시도를 분리해 필요한 힌트가 줄었는지 기록합니다.",
        f"정답률 하나로 {location} 학생의 {focus} 이해를 정하지 않습니다. {math_pack['signal']}를 먼저 살피고 {evidence} 그다음 {math_pack['action']} 이 순서가 유지되는지를 다음 날 다른 표현의 문제에서 다시 확인합니다.",
        f"{location}에서는 {focus}과 관련된 학교 범위표, 교과서 예제, 학생 공책의 역할을 나눕니다. 범위와 날짜는 학교 자료에서 확인하고 {evidence} 이후 {math_pack['first']} 풀이 근거와 재시도 결과로 다음 과제를 정합니다.",
    )
    answer_2_frames = (
        f"{grade} 목표는 ‘{grade_goal}’입니다. {location} 학생에게 이 내용을 전부 외우게 하기보다 {action} 이어 {transfer} 혼자 가능한 단계와 짧은 질문 뒤 가능한 단계를 나누면 선행이 현재 학년의 공백을 가리는 일을 줄일 수 있습니다.",
        f"{location}의 {grade} 계획은 진도표보다 ‘{grade_goal}’을 실제 {focus} 풀이에서 확인하는 데서 시작합니다. {observation} 같은 장면이 보이면 {action} 한 번에 여러 습관을 바꾸지 않고 일주일 뒤 같은 행동이 유지되는지 봅니다.",
        f"{focus}의 {grade} 기준은 ‘{grade_goal}’입니다. {location} 학생이 이 기준을 말로 설명한 뒤 {transfer} 결과가 안정되면 다음 학년 내용으로 짧게 연결하고, 다시 끊기면 필요한 이전 개념 한 항목만 복원합니다.",
        f"학년이 같아도 {location} 학생마다 시작점은 다릅니다. ‘{grade_goal}’을 공통 확인 항목으로 두되 {evidence} 그 결과에 따라 {action} 다음 단원보다 현재 풀이를 막는 한 행동을 먼저 조정합니다.",
    )
    answer_3_frames = (
        f"학교별 난도나 출제 경향을 추측하지 않고 실제 범위표와 최근 시험지에서 {focus} 문항을 찾습니다. {location} 학생은 개념 정의, 대표 적용, 조건이 바뀐 문제, 서술형, 오답 재시도를 날짜별로 나눕니다. 서술형은 ‘{intent_pack['written']}?’에 답할 근거가 남았는지 확인합니다.",
        f"{location}의 시험 준비는 교과서 정의와 학교 자료 확인부터 시작합니다. {focus} 오답을 개념·조건·전략·계산으로 나누고 같은 원인이 두 번 나온 문제를 먼저 재시도합니다. 마지막에는 ‘{intent_pack['written']}?’를 기준으로 풀이 문장을 검토하며 새 고난도 문제는 뒤로 미룹니다.",
        f"시간이 부족해도 {location}의 {focus} 계획에서 재시도 날짜를 없애지 않습니다. 새 문제 수를 줄이고 실제 시험 범위 안에서 첫 오답, 대표 유형, 서술형 한 문제를 남깁니다. 완료 여부는 ‘{intent_pack['finish']}?’를 학생이 자신의 풀이로 설명하는지에 따라 판단합니다.",
        f"학교 홈페이지는 일정 확인에, 학생이 받은 시험지·유인물·교과서는 {focus} 내용 확인에 사용합니다. {location} 학생은 {math_pack['check']} 이어 ‘{intent_pack['written']}?’를 서술형 점검 질문으로 삼아 답뿐 아니라 근거와 검산까지 남깁니다.",
    )
    answer_4_frames = (
        f"‘왜 또 틀렸니?’라고 묻기보다 ‘처음 무엇을 보고 시작했니?’, ‘어느 줄에서 도움이 필요했니?’를 묻습니다. {location}의 {focus} 기록에는 {evidence} 보호자는 답을 대신 설명하지 않고 다음 재시도에서 학생이 혼자 시작할 행동 하나를 정하도록 돕습니다.",
        f"상담 전에는 {intent_pack['material']} 가운데 실제로 사용한 자료와 첫 풀이를 준비합니다. {location} 학생에게 {observation} 같은 모습이 보여도 성향으로 단정하지 않습니다. {evidence} 같은 장면이 다른 문제에서도 반복되는지를 확인한 뒤 과제 크기를 정합니다.",
        f"도움 요청 횟수만 세지 말고 요청 직전까지 학생이 한 행동을 기록합니다. {location}의 {focus} 과제에서는 {action} 그 뒤 질문의 길이를 줄였을 때 학생이 이어서 한 단계와 다시 멈춘 위치를 구분해 다음 상담 자료로 사용합니다.",
        f"이해했다는 말은 출발점으로만 봅니다. {location} 학생에게 {evidence} 이어 {transfer} 정답이 같더라도 근거를 혼자 말했는지, 필요한 힌트가 줄었는지, 검산까지 이어졌는지를 각각 기록합니다.",
    )
    answer_5_frames = (
        f"완료 기준은 ‘{intent_pack['finish']}?’입니다. {location} 학생이 한 번 맞힌 것만으로 {focus}을 끝내지 않고 {transfer} {math_pack['risk']}을 피하려면 간격 뒤 재시도에서도 같은 근거와 검산이 남아야 합니다.",
        f"{location}에서 {focus}의 다음 유형으로 이동하려면 학생이 첫 판단을 설명하고 {math_pack['check']} 이어 {transfer} 이 세 행동이 도움 없이 이어지는지 확인합니다. 하나가 끊기면 전체 단원을 반복하지 않고 그 단계의 과제만 더 작게 나눕니다.",
        f"재시도 결과가 같다면 학생의 의지나 {location}의 환경을 원인으로 단정하지 않습니다. {focus} 과제의 난도·분량·힌트 간격 중 하나만 바꾸고 {action} 다음 기록에서 혼자 가능한 범위가 달라졌는지를 비교합니다.",
        f"정답은 우연히 맞을 수 있고 설명 없이 익숙한 절차만 반복했을 수도 있습니다. {location}의 {focus} 완료 기준은 ‘{intent_pack['finish']}?’이며 {math_pack['risk']}이 남아 있지 않은지 다른 표현의 문제와 검산으로 확인합니다.",
    )
    closing_frames = (
        f"이 FAQ는 {location} 학생 전체의 수준이나 성과를 말하지 않습니다. {focus} 계획은 실제 학교 범위, 첫 풀이, 도움 뒤 행동, 간격 뒤 재시도를 확인한 다음 개인별로 조정해야 합니다.",
        f"{location}이라는 지역명은 일정과 생활권을 확인하기 위한 기준입니다. {focus}의 난도와 분량은 학생의 실제 자료에서 정하고, 학교별 출제 경향이나 성적 변화를 확인 없이 가정하지 않습니다.",
        f"질문에 대한 답은 {location}의 평균적인 학생상을 제시하는 내용이 아닙니다. {focus}에서 혼자 가능한 단계와 필요한 힌트가 다르면 같은 학년이라도 과제 순서와 재시도 간격을 다르게 정합니다.",
        f"{location} 중등수학 계획을 비교할 때에는 문제 수보다 {focus}의 첫 판단, 근거 설명, 검산, 재시도 기록을 함께 보세요. 이 네 자료가 있어야 다음 과제를 유지할지 줄일지 바꿀지 결정할 수 있습니다.",
    )

    def clean(value: str) -> str:
        return _fix_focus_particles(value, focus)

    pairs = (
        (
            clean(f"{location}중등수학과외에서는 {focus}을 어떻게 복습해야 하나요?"),
            clean(_pick(answer_1_frames, _salted_index(slug, "faq-answer-1"))),
        ),
        (
            clean(_pick(question_2_frames, _salted_index(slug, "faq-question-2"))),
            clean(_pick(answer_2_frames, _salted_index(slug, "faq-answer-2"))),
        ),
        (
            clean(_pick(question_3_frames, _salted_index(slug, "faq-question-3"))),
            clean(_pick(answer_3_frames, _salted_index(slug, "faq-answer-3"))),
        ),
        (
            clean(_pick(question_4_frames, _salted_index(slug, "faq-question-4"))),
            clean(_pick(answer_4_frames, _salted_index(slug, "faq-answer-4"))),
        ),
        (
            clean(_pick(question_5_frames, _salted_index(slug, "faq-question-5"))),
            clean(_pick(answer_5_frames, _salted_index(slug, "faq-answer-5"))),
        ),
    )
    items = "".join(
        f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in pairs
    )
    heading = clean(_pick(heading_frames, _salted_index(slug, "faq-heading")))
    closing = clean(_pick(closing_frames, _salted_index(slug, "faq-closing")))
    return (
        f'<h2 class="{FAQ_MARKER}" data-faq-focus="{escape(focus)}">{escape(heading)}</h2>'
        f"{items}<p>{escape(closing)}</p>"
    )


def _replace_middle_math_faq(body: str, slug: str, focus: str) -> str:
    if FAQ_MARKER in body:
        return body
    faq_heading = re.search(
        r"<h2\b[^>]*>(?:(?!</h2>).)*(?:FAQ|자주\s*묻는\s*질문)(?:(?!</h2>).)*</h2>",
        body,
        flags=re.I | re.S,
    )
    if not faq_heading:
        return body
    outer_end = body.rfind("</section>")
    if outer_end <= faq_heading.start():
        return body
    return body[: faq_heading.start()] + _middle_math_faq_html(slug, focus) + body[outer_end:]


def _review_section(location: str, focus: str, pack: dict[str, object], index: int) -> str:
    heading = _pick(REVIEW_HEADINGS, index, 1)
    checklist_sets = (
        (
            "문제를 읽은 뒤 질문과 조건을 구분해 표시했는가",
            "풀이의 첫 줄에 사용한 개념이나 성질을 말할 수 있는가",
            "힌트를 받은 시점과 힌트 뒤에 바꾼 행동이 남아 있는가",
            "맞힌 문제도 다른 방법이나 검산으로 조건을 다시 확인했는가",
            "하루 이상 지난 뒤 답 없이 첫 단계를 다시 시작했는가",
            "다음 복습 날짜와 시작할 문제를 구체적으로 정했는가",
        ),
        (
            "학습 시간을 늘리기 전에 반복되는 오류 한 가지를 정했는가",
            "교과서 정의와 예제의 근거를 자신의 문장으로 바꿨는가",
            "비슷해 보이는 문제에서 달라진 조건을 찾아 표시했는가",
            "오답을 개념·조건·전략·계산 중 하나로 분류했는가",
            "설명 없이 맞힌 문제를 이해한 문제로 바로 처리하지 않았는가",
            "이번 주 기록으로 다음 주 과제 하나를 줄이거나 바꿨는가",
        ),
        (
            "현재 학년의 학교 진도와 복습할 공백을 연결했는가",
            "분량이 아니라 오늘 끝낼 수 있는 행동을 정했는가",
            "풀이 과정에서 생략한 단위와 근거를 다시 확인했는가",
            "도움 없이 가능한 단계와 질문 뒤 가능한 단계를 나눴는가",
            "첫 시도와 재시도의 설명이 어떻게 달라졌는지 비교했는가",
            "새 교재를 추가하기 전에 기존 오답의 재풀이를 마쳤는가",
        ),
    )
    checks = checklist_sets[index % len(checklist_sets)]
    items = "".join(f"<li>{escape(item)} — {escape(focus)} 기록에서 확인</li>" for item in checks)
    before = (
        f"{location}의 주간 검토에서는 문제집 페이지 수만 합산하지 않습니다. {focus}에 대해 혼자 시작한 범위, 사용한 힌트, 설명이 끊긴 위치, 간격 뒤 재현 여부를 나란히 놓습니다."
    )
    after = (
        f"보호자는 정답을 다시 가르치기보다 ‘처음 무엇을 보고 시작했는지’, ‘다음에는 어떤 확인을 혼자 할지’를 묻는 편이 좋습니다. {pack['risk']}을 피하고, 기록이 달라지지 않으면 학생을 평가하기 전에 과제 난도·분량·확인 간격 중 하나만 바꿉니다."
    )
    return f"<h3>{escape(heading)}</h3><p>{escape(before)}</p><ul>{items}</ul><p>{escape(after)}</p>"


def _category_for_heading(heading: str) -> str:
    if "실수의 원인" in heading or "오류" in heading:
        return "error"
    if "중1" in heading or "학년" in heading:
        return "grade"
    if "생활권" in heading or "공부시간" in heading:
        return "local"
    if "개념 이해" in heading or "문제 적용" in heading or "옮기는 방법" in heading:
        return "practice"
    if "학생 사례" in heading or "공부 방식을 바꾼" in heading:
        return "case"
    if "진단" in heading:
        return "diagnosis"
    if "내신" in heading or "수행평가" in heading or "시험 시간" in heading:
        return "exam"
    if "평일" in heading or "주말" in heading or "방학" in heading:
        return "schedule"
    if "체크리스트" in heading or "학부모" in heading:
        return "review"
    return "practice"


def _rewrite_source_block(
    block: str,
    *,
    category: str,
    location: str,
    focus: str,
    index: int,
    block_index: int,
) -> str:
    heading_match = re.search(r"<h3\b[^>]*>(.*?)</h3>", block, flags=re.I | re.S)
    original_heading = _plain_text(heading_match.group(1)) if heading_match else focus
    if focus in original_heading and location in original_heading:
        compact_frames = (
            "{heading} — 첫 시도와 재시도",
            "{heading}: 풀이 기록 점검",
            "{heading}, 근거를 남기는 방법",
            "{heading} — 다음 과제를 정하는 기준",
        )
        heading = _pick(compact_frames, index, block_index).format(heading=original_heading)
    elif focus in original_heading:
        focus_frames = (
            "{heading} — {location}의 풀이 기록",
            "{location}에서 다시 보는 {heading}",
            "{heading}: 첫 시도와 재시도",
            "{heading}, 근거를 남기는 {location} 방식",
        )
        heading = _pick(focus_frames, index, block_index).format(
            heading=original_heading,
            location=location,
        )
    elif location in original_heading:
        location_frames = (
            "{heading} — {focus} 점검",
            "{heading}: {focus} 복습 연결",
            "{focus} 기록으로 확인하는 {heading}",
            "{heading} — 첫 판단을 남기는 방법",
        )
        heading = _pick(location_frames, index, block_index).format(
            heading=original_heading,
            focus=focus,
        )
    else:
        heading_frame = _pick(HEADING_FRAMES, index, block_index)
        heading = heading_frame.format(heading=original_heading, location=location, focus=focus)
    heading = _fix_focus_particles(heading, focus)
    block = re.sub(
        r"<h3\b[^>]*>.*?</h3>",
        f"<h3>{escape(heading)}</h3>",
        block,
        count=1,
        flags=re.I | re.S,
    )
    paragraph_index = 0
    expansions = PARAGRAPH_EXPANSIONS[category]

    def expand_paragraph(match: re.Match[str]) -> str:
        nonlocal paragraph_index
        attrs, inner = match.group(1) or "", match.group(2)
        expansion = _pick(expansions, index + block_index, paragraph_index)
        paragraph_index += 1
        return f"<p{attrs}>{inner.rstrip()} {escape(expansion.format(location=location, focus=focus))}</p>"

    block = re.sub(r"<p(\s[^>]*)?>(.*?)</p>", expand_paragraph, block, flags=re.I | re.S)
    item_index = 0

    def individualize_item(match: re.Match[str]) -> str:
        nonlocal item_index
        inner = match.group(1).rstrip()
        endings = (
            f" — {location}의 {focus} 첫 시도에서 확인",
            f" — {focus} 재시도 기록으로 {location}에서 비교",
            f" — {location} 학생의 {focus} 설명에서 점검",
            f" — {focus} 복습 날짜와 함께 {location} 계획에 표시",
        )
        ending = endings[(index + item_index + block_index) % len(endings)]
        item_index += 1
        return f"<li>{inner}{escape(ending)}</li>"

    block = re.sub(r"<li\b[^>]*>(.*?)</li>", individualize_item, block, flags=re.I | re.S)
    return (
        f'<section class="middle-math-block middle-math-{escape(category)}" '
        f'data-block-order="{block_index + 1}">{block.strip()}</section>'
    )


def _build_from_source_body(body: str, slug: str, focus: str) -> str:
    faq_match = re.search(
        r"<h2\b[^>]*>\s*중등수학 학습에 관해 자주 묻는 질문\s*</h2>",
        body,
        flags=re.I | re.S,
    )
    if not faq_match:
        return ""
    core = body[: faq_match.start()]
    faq = _strip_heading_ids(body[faq_match.start() :].strip())
    headings = list(re.finditer(r"<h([23])\b[^>]*>(.*?)</h\1>", core, flags=re.I | re.S))
    if len(headings) < 3 or headings[0].group(1) != "2":
        return ""

    location = slug.removesuffix("중등수학과외")
    index = _index_for_slug(slug)
    original_intro = _plain_text(core[headings[0].end() : headings[1].start()])
    main_heading_variants = (
        f"{location}중등수학과외, {focus} 풀이의 첫 판단부터 재시도까지",
        f"{focus}을 기록으로 확인하는 {location} 중등수학 학습",
        f"{location}중등수학과외에서 살펴보는 {focus} 학습 과정",
        f"{location} 중학생의 {focus} 풀이를 단계별로 점검하기",
        f"{location}중등수학과외, {focus} 오류와 적용을 연결하는 방법",
    )
    intro_additions = (
        f"{location}의 이 안내는 {focus}에 관한 정답률을 예측하지 않고, 처음 읽은 조건과 사용한 근거, 도움 뒤 달라진 행동을 비교하는 데 목적이 있습니다.",
        f"이 페이지에서는 {location} 학생 모두를 하나의 유형으로 가정하지 않으며, {focus} 문제에서 실제로 남은 풀이와 재시도 기록을 기준으로 다음 학습을 정합니다.",
        f"{location}에서 {focus}을 확인할 때에는 특정 교재의 진도보다 학교 자료에 남은 첫 시도, 설명, 검산의 순서를 관찰합니다.",
        f"학습 결과를 미리 단정하지 않고 {location}의 {focus} 기록에서 혼자 가능한 단계와 질문 뒤 가능한 단계를 나누어 살펴봅니다.",
        f"{focus}은 한 번 맞힌 답으로 이해를 확정하기 어렵기 때문에 {location} 페이지는 간격을 둔 재시도와 학생의 설명을 함께 봅니다.",
    )
    opening_headings = (
        f"{focus}을 {location} 학습의 관찰 기준으로 삼는 이유",
        f"{location}에서 {focus}의 풀이 흔적을 먼저 보는 까닭",
        f"문제 수보다 {focus}의 첫 판단을 확인하는 {location} 기준",
        f"{location} 학생의 {focus} 이해를 결과만으로 정하지 않기",
        f"{focus}의 설명과 재시도를 연결하는 {location} 관찰법",
    )

    blocks_by_category: dict[str, str] = {}
    extra_blocks: list[tuple[str, str]] = []
    for position, heading_match in enumerate(headings[1:], start=1):
        end = headings[position + 1].start() if position + 1 < len(headings) else len(core)
        block = core[heading_match.start() : end]
        heading_text = _plain_text(heading_match.group(2))
        category = _category_for_heading(heading_text)
        if category in blocks_by_category:
            extra_blocks.append((category, block))
        else:
            blocks_by_category[category] = block

    ordered_categories = CATEGORY_ORDERS[index % len(CATEGORY_ORDERS)]
    ordered_blocks: list[tuple[str, str]] = [
        (category, blocks_by_category[category])
        for category in ordered_categories
        if category in blocks_by_category
    ]
    ordered_blocks.extend(extra_blocks)
    individualized_blocks = "".join(
        _rewrite_source_block(
            block,
            category=category,
            location=location,
            focus=focus,
            index=index,
            block_index=block_index,
        )
        for block_index, (category, block) in enumerate(ordered_blocks)
    )
    intro = f"{original_intro} {_pick(intro_additions, index, 2)}"
    opening = _pick(OPENING_FRAMES, index, 3).format(location=location, focus=focus)
    result = (
        f'<section class="{CONTENT_MARKER}" data-content-version="{CONTENT_VERSION}" '
        f'data-math-focus="{escape(_kind_for_focus(focus))}">'
        f"<h2>{escape(_pick(main_heading_variants, index))}</h2><p>{escape(intro)}</p>"
        f"<h3>{escape(_pick(opening_headings, index, 1))}</h3><p>{escape(opening)}</p>"
        f"{individualized_blocks}{faq}</section>"
    )
    return _fix_focus_particles(result, focus)


def build_local_middle_math_body(slug: str, focus: str, existing_faq: str = "") -> str:
    location = slug.removesuffix("중등수학과외")
    focus = focus.strip()
    kind = _kind_for_focus(focus)
    pack = MATH_PACKS[kind]
    index = _index_for_slug(slug)
    opening_heading = _pick(OPENING_HEADINGS, index)
    opening = _pick(OPENING_FRAMES, index, 1).format(location=location, focus=focus)
    main_heading_variants = (
        f"{location}중등수학과외, {focus}으로 살펴보는 풀이 과정",
        f"{location}중등수학과외, {focus}을 기록으로 점검하는 방법",
        f"{location}중등수학과외에서 확인하는 {focus} 학습 기준",
        f"{focus}부터 다시 세우는 {location} 중등수학 학습",
    )
    main_heading = main_heading_variants[index % len(main_heading_variants)]
    intro = (
        f"이 페이지는 {location} 학생이 모두 같은 어려움을 겪는다고 가정하거나 특정 수업의 결과를 약속하지 않습니다. "
        f"‘{focus}’이라는 고유한 점검 주제를 이용해 실제 시험지와 학교 자료에서 무엇을 관찰하고, 어떤 순서로 복습을 조정할지 설명하는 교육 정보입니다."
    )
    sections = {
        "diagnosis": _diagnosis_section(location, focus, pack, index),
        "grade": _grade_section(location, focus, pack, index),
        "practice": _practice_section(location, focus, pack, index),
        "schedule": _schedule_section(location, focus, pack, index),
        "case": _case_section(location, focus, pack, index),
        "review": _review_section(location, focus, pack, index),
    }
    order = SECTION_ORDERS[index % len(SECTION_ORDERS)]
    core = "".join(sections[name] for name in order)
    faq = existing_faq.strip()
    if not faq:
        faq = (
            "<h2>중등수학 학습에 관해 자주 묻는 질문</h2>"
            f"<h3>{escape(location)}에서 {escape(focus)}은 어떻게 복습하나요?</h3>"
            f"<p>{escape(str(pack['first']))} 하루 이상 지난 뒤에는 답을 보지 않고 첫 단계를 다시 시작해 설명이 이어지는지 확인합니다.</p>"
        )
    return (
        f'<section class="{CONTENT_MARKER}" data-content-version="{CONTENT_VERSION}" '
        f'data-math-focus="{escape(kind)}">'
        f"<h2>{escape(main_heading)}</h2><p>{escape(intro)}</p>"
        f"<h3>{escape(opening_heading)}</h3><p>{escape(opening)}</p>"
        f"{core}{faq}</section>"
    )


def individualize_local_middle_math_body(body: str, slug: str) -> str:
    """Replace the shared core of the 69 local middle-math pages and retain their FAQ block."""
    if not is_local_middle_math_slug(slug):
        return body
    if f'data-content-version="{CONTENT_VERSION}"' in body:
        # Older generated copies kept a full stop inside a quoted grade goal,
        # producing combinations such as ``합니다.’을``.  Keep the wording and
        # remove only that misplaced punctuation when an already-current page
        # passes through the renderer again.
        return (
            body.replace(".’을", "’을")
            .replace(".’과", "’과")
            .replace(".’입니다", "’입니다")
        )
    for previous_version in PREVIOUS_CONTENT_VERSIONS:
        if f'data-content-version="{previous_version}"' not in body:
            continue
        focus = _focus_from_body(body)
        upgraded = _add_school_context(body, slug, focus)
        upgraded = _add_search_intent(upgraded, slug, focus)
        upgraded = _replace_student_case(upgraded, slug, focus)
        upgraded = _add_middle_math_context_links(upgraded, slug, focus)
        upgraded = _replace_middle_math_faq(upgraded, slug, focus)
        upgraded = upgraded.replace(
            f"{escape(focus)}의 다음 복습 결정",
            f"{escape(focus)} 다음 복습 결정",
        )
        return upgraded.replace(
            f'data-content-version="{previous_version}"',
            f'data-content-version="{CONTENT_VERSION}"',
            1,
        )
    focus = _focus_from_body(body)
    source_based = _build_from_source_body(body, slug, focus)
    individualized = source_based or build_local_middle_math_body(slug, focus, _existing_faq(body))
    individualized = _add_school_context(individualized, slug, focus)
    individualized = _add_search_intent(individualized, slug, focus)
    individualized = _replace_student_case(individualized, slug, focus)
    individualized = _add_middle_math_context_links(individualized, slug, focus)
    individualized = _replace_middle_math_faq(individualized, slug, focus)
    for previous_version in PREVIOUS_CONTENT_VERSIONS:
        individualized = individualized.replace(
            f'data-content-version="{previous_version}"',
            f'data-content-version="{CONTENT_VERSION}"',
            1,
        )
    return individualized
