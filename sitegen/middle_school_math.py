from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sitegen.utils import escape


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "middle_school_math_pages.json"


THEMES = (
    ("정수·유리수 부호", "부호를 계산 규칙으로만 외워 식의 의미가 바뀔 때 판단이 흔들리는 상태", "수직선 위치·연산 근거·검산값을 함께 적은 부호 판단표", "답보다 부호가 처음 달라진 줄을 찾아 말로 설명합니다"),
    ("문자식 조건 번역", "문장을 읽고도 수량 관계를 문자와 식으로 바꾸는 첫 단계가 늦어지는 상태", "주어진 값·구할 값·관계 문장·첫 식을 나눈 조건 번역표", "숫자를 넣기 전에 같은 관계를 말과 식으로 한 번씩 표현합니다"),
    ("일차방정식 역연산", "이항을 기호 이동으로 기억해 등식의 성질과 검산이 연결되지 않는 상태", "변형 전 식·양변에 한 연산·변형 후 식·대입 결과를 잇는 등식 기록", "한 줄에 한 연산만 쓰고 구한 값을 원래 식에 대입합니다"),
    ("좌표와 일차함수", "표·식·그래프가 같은 관계라는 사실을 문제 조건에 맞춰 전환하지 못하는 상태", "x 변화·y 변화·기울기·절편·그래프 위치를 연결한 표현 전환표", "한 관계를 표와 식과 스케치 세 방식으로 바꿔 봅니다"),
    ("기본도형의 근거", "그림의 모양에 기대어 주어진 조건과 추측한 관계를 구분하지 못하는 상태", "주어진 조건·사용할 성질·보조선 목적·결론을 구분한 도형 근거표", "그림을 다르게 다시 그려도 유지되는 조건만 표시합니다"),
    ("자료 해석과 대표값", "평균을 계산하고도 분포와 이상값이 결론에 미치는 영향을 설명하지 못하는 상태", "범위·중심·퍼짐·이상값·대표값 선택 이유를 묶은 자료 판단표", "값 하나를 바꾸며 평균과 중앙값의 변화를 비교합니다"),
    ("연립방정식 모델링", "두 조건을 각각 식으로 만들지만 두 식이 함께 만족해야 한다는 뜻을 놓치는 상태", "미지수 정의·두 조건·연립식·해의 상황 검산을 잇는 모델링표", "해를 구한 뒤 두 원문 조건에 각각 다시 대입합니다"),
    ("일차부등식 범위", "부등호 방향과 해의 범위를 수직선·문장과 연결하지 못하는 상태", "경계값·부등호·수직선·상황 문장을 맞춘 범위 확인표", "음수를 곱하거나 나눌 때 방향 변화의 이유를 설명합니다"),
    ("삼각형 닮음", "닮음 조건을 찾고도 대응 순서와 길이 비를 일관되게 쓰지 못하는 상태", "대응점·닮음 조건·대응변·비례식을 나란히 둔 닮음 대응표", "도형 이름의 순서를 먼저 맞춘 뒤 비례식을 세웁니다"),
    ("확률 경우 분류", "기준 없이 경우를 나열해 중복과 누락을 동시에 발견하지 못하는 상태", "분류 기준·각 경우·겹침 여부·전체 개수를 확인한 경우 분류표", "표나 나무그림으로 나누고 다른 기준으로 총수를 검산합니다"),
    ("피타고라스 활용", "공식을 기억해도 어느 삼각형에 적용할지와 구한 길이의 타당성을 놓치는 상태", "직각 표시·빗변 선택·제곱 관계·길이 검산을 묶은 적용표", "계산 전에 가장 긴 변과 예상 길이 범위를 먼저 정합니다"),
    ("다항식 인수분해", "전개와 인수분해를 별개 공식으로 외워 서로 역과정이라는 점을 활용하지 못하는 상태", "공통인수·곱 구조·인수분해식·재전개 결과를 적은 구조 확인표", "완성한 식은 반드시 다시 전개해 원래 식과 비교합니다"),
    ("이차함수 변화", "계수 변화와 그래프의 꼭짓점·축·개형을 따로 기억해 조건 해석이 늦어지는 상태", "식의 계수·꼭짓점·축·그래프 이동을 연결한 함수 변화표", "값을 조금 바꾸었을 때 그래프가 어떻게 이동하는지 먼저 예상합니다"),
    ("원과 각의 추론", "원주각·중심각 관계를 도형마다 새 공식처럼 적용해 근거가 끊기는 상태", "호·중심각·원주각·같은 호를 보는 각을 잇는 원 조건표", "어떤 호를 보고 있는지 색으로 표시한 뒤 각 관계를 씁니다"),
)


METHODS = (
    ("24·72시간 복원", "수업 뒤 하루 안에 핵심 개념과 첫 식을 회상하고 사흘 안에 조건을 바꾼 문제에 적용합니다", "첫날 회상·사흘 뒤 적용·일주일 뒤 재현을 한 줄씩 이어 적습니다", "설명이 끊긴 단계만 다시 학습해 복습 간격을 조정합니다"),
    ("오류 코드 장부", "오답을 개념·조건·전략·계산·검산 가운데 하나로 먼저 분류합니다", "오류 이름보다 다음 문제에서 먼저 볼 신호를 기록합니다", "같은 코드가 세 번 나오면 새 문제보다 판단 순서를 다시 연습합니다"),
    ("빈 풀이 재현", "해설을 덮고 조건·첫 식·핵심 변형·검산 순서를 빈 종이에 다시 씁니다", "기억한 내용과 보고 보완한 내용을 두 색으로 남깁니다", "하루 뒤 네 단계가 순서대로 재현될 때 완료로 봅니다"),
    ("두 풀이 비교", "식 중심 풀이와 그림·표 중심 풀이를 나누어 공통 조건과 다른 선택을 찾습니다", "각 방식에서 먼저 보인 조건과 검산이 쉬운 지점을 비교합니다", "새 문제에서 한 방식을 스스로 선택하고 이유를 설명합니다"),
    ("다음 한 줄 설명", "계산하기 전에 다음 행동과 사용할 근거를 먼저 짧게 말합니다", "설명이 막힌 줄과 근거까지 설명한 줄을 다른 표시로 구분합니다", "답이 맞아도 다음 줄의 이유를 말하지 못하면 재확인합니다"),
    ("시간 상한 기록", "유형별 목표 시간이 지나면 확인한 조건과 막힌 위치를 표시하고 보류합니다", "읽기·첫 식·계산·검토 시간을 나누어 기록합니다", "느린 원인이 개념인지 계산인지 확인한 뒤에만 목표 시간을 바꿉니다"),
    ("역방향 검산", "답에서 출발해 원래 조건에 대입하거나 결론에서 가정으로 거꾸로 확인합니다", "정방향 풀이와 역방향 확인이 처음 어긋난 줄을 표시합니다", "검산에서 찾은 오류를 다음 문제의 첫 확인 행동으로 연결합니다"),
    ("질문 한 줄 기록", "막힌 순간을 해설로 덮지 않고 아는 것과 필요한 도움으로 나누어 적습니다", "혼자 시도한 방법과 선생님에게 확인할 조건 하나를 구분합니다", "수업 끝에는 답보다 다음에 먼저 찾을 근거를 다시 씁니다"),
    ("난도 교대 계획", "집중 가능한 날에는 새 개념을, 피로한 날에는 정의 회상과 짧은 오답을 배치합니다", "요일별 집중 시간과 과제 난도와 완료 단계를 함께 적습니다", "계획 실패를 의지로 해석하지 않고 시간대와 과제 크기를 바꿉니다"),
    ("3일 풀이 복원", "첫날 오류 위치를 표시하고 둘째 날 첫 줄부터 다시 풀며 셋째 날 변형 문제에 적용합니다", "도움을 받은 줄과 혼자 이어 간 줄을 다른 기호로 남깁니다", "셋째 날 같은 곳에서 멈추면 선행 개념으로 돌아갑니다"),
    ("교과자료 우선표", "교과서·학교 학습지·평가 안내를 먼저 놓고 문제집은 빈틈을 채우는 데 씁니다", "자료마다 시험 범위·완료 기준·다시 볼 날짜를 표시합니다", "시험 뒤 실제 판단 근거가 된 자료만 다음 계획에 남깁니다"),
    ("정의·예·반례", "개념 정의를 자신의 말로 쓰고 맞는 예와 틀린 반례를 하나씩 만듭니다", "성립 조건과 조건이 깨지는 지점을 나란히 적습니다", "새 문제에서 적용 가능 여부를 근거와 함께 판단합니다"),
    ("단원 연결 지도", "현재 문제에 필요한 이전 단원 개념과 다음 단원에서의 쓰임을 한 장에 잇습니다", "선행 개념·현재 판단·후속 활용을 화살표로 연결합니다", "막힌 곳이 현재 계산인지 선행 개념인지 주말에 구분합니다"),
    ("서술형 문장 보완", "식 사이에 왜 다음 줄로 갈 수 있는지 짧은 근거 문장을 넣습니다", "가정·정의·계산·결론을 서로 다른 기호로 표시합니다", "채점자가 따라갈 수 없는 생략 한 곳을 찾아 보완합니다"),
    ("미니 시험 재배열", "오답을 단원 순서가 아니라 오류 유형과 해결 시간 순으로 다시 배열합니다", "문항별 시작 판단·보류 시점·검산 결과를 기록합니다", "같은 시간 안에 판단 순서가 안정됐는지 비교합니다"),
    ("주간 자기설명", "주말에 이번 주 대표 문제 한 개를 풀이 없이 말로 설명합니다", "설명이 멈춘 문장과 그때 참고한 자료를 함께 남깁니다", "다음 주 첫 학습에서 멈춘 개념만 짧게 복원합니다"),
)


ACTION_LIBRARY = (
    ("정의 회상", "교과서 핵심 용어를 보지 않고 설명", "정의·맞는 예·반례 세 칸", "세 칸을 순서대로 재현", "반례가 막히면 성립 조건으로 복귀"),
    ("조건 색인", "문제 문장에서 수치와 관계를 분리", "주어진 값·구할 값·제약 표시", "누락 없이 첫 식과 연결", "첫 식이 늦으면 관계 문장만 다시 작성"),
    ("부호 추적", "음수와 괄호가 바뀌는 줄을 관찰", "변형 전후 부호 대조", "최초 변화의 근거를 설명", "계산량보다 한 줄 한 연산으로 축소"),
    ("식 역검산", "구한 값을 원래 식에 대입", "정방향과 역방향의 첫 불일치", "두 방향이 같은 조건에서 만남", "불일치 줄의 연산 성질을 재확인"),
    ("표현 전환", "한 관계를 말·표·식·그림으로 변환", "표현별 바로 보이는 정보", "두 표현 이상에서 같은 결론", "한 표현만 가능하면 연결 예제로 복귀"),
    ("그래프 예측", "계수를 바꾸기 전 이동 방향을 예상", "예상 위치와 실제 스케치", "오차 이유를 계수와 연결", "값 대입 전에 기준 그래프부터 복원"),
    ("도형 재구성", "모양이 다른 그림에서 조건을 찾기", "주어진 사실과 추론 사실 구분", "보조선 목적을 한 문장으로 설명", "시각적 추측은 조건표에서 제외"),
    ("대응 순서", "닮음 도형의 대응점을 먼저 배열", "도형 이름과 대응변 순서", "비례식의 항이 모두 대응", "길이 계산 전에 순서를 다시 점검"),
    ("자료 비교", "평균과 중앙값의 역할을 나누기", "중심·퍼짐·이상값 변화", "대표값 선택 이유를 설명", "계산만 맞으면 해석 문장을 보완"),
    ("경우 분류", "무엇을 먼저 고정할지 결정", "나무그림·표의 분류 기준", "중복과 누락을 다른 기준으로 검산", "전체 수가 다르면 분류 경계 재설정"),
    ("첫 줄 후보", "풀이 시작식을 두 개 제안", "선택한 식과 버린 식의 이유", "더 적은 가정의 시작을 선택", "둘 다 막히면 개념 정의로 복귀"),
    ("서술형 연결", "식 사이의 생략된 근거를 채우기", "가정·정의·계산·결론 표식", "다른 사람이 중단 없이 읽음", "한 문장에 근거 하나만 남기기"),
    ("시간 구간", "읽기·첫 식·계산·검토 시간을 분리", "문항별 네 구간 실제 시간", "보류와 재진입 시점 준수", "한 구간만 길면 해당 행동을 축소 연습"),
    ("오류 코드", "최초 오류를 다섯 유형으로 분류", "개념·조건·전략·계산·시간 코드", "다음 확인 신호까지 기록", "결과 오류와 최초 원인을 다시 분리"),
    ("빈 종이 복원", "해설을 덮고 핵심 네 단계를 재현", "조건·첫 식·변형·검산", "하루 뒤에도 순서가 유지", "멈춘 단계만 참고 후 다시 덮기"),
    ("변형 문제", "수치나 조건 하나를 바꾸어 적용", "원문과 달라진 조건 표시", "같은 개념의 적용 범위를 설명", "공식 모양만 찾으면 반례를 추가"),
    ("학교자료 대조", "교과서와 학습지의 공통 조건 찾기", "자료별 범위·완료 기준·날짜", "학교 범위와 보조 문제를 구분", "새 교재보다 미완 학교자료 우선"),
    ("질문 정제", "막힌 말을 구체적인 질문으로 바꾸기", "아는 것·시도한 것·필요한 도움", "조건 하나로 질문을 표현", "정답 요청이면 막힌 줄부터 다시 표시"),
    ("설명 녹음", "대표 문제를 풀이 없이 말로 설명", "멈춘 문장과 참고한 개념", "다음 날 같은 순서로 재설명", "말과 식이 다르면 대응표를 작성"),
    ("짝 문제 비교", "겉모양이 비슷한 두 문제의 차이 찾기", "공통 조건과 달라진 조건", "서로 다른 첫 줄의 이유를 설명", "답만 다르면 조건 번역을 재실행"),
    ("난도 사다리", "같은 개념을 기본·변형·복합으로 배열", "단계별 도움의 양", "한 단계씩 근거를 유지", "두 단계 연속 정체면 기본 정의 복귀"),
    ("주말 미니시험", "이번 주 오답을 시간 안에 재배열", "시작 판단·보류·검산 시각", "같은 시간에 판단 순서 안정", "정답률보다 멈춘 위치를 다음 목표로"),
    ("피드백 요약", "수업 끝에 배운 판단을 세 문장으로 정리", "할 수 있음·도움 필요·다음 질문", "학생 표현으로 세 문장을 완성", "선생님 문장을 베꼈다면 다음 날 재작성"),
    ("4주 조정", "유지·변경·중단 행동을 하나씩 선택", "도움 없이 수행한 단계 수", "다음 달 목표 한 가지 합의", "과제 부담이 크면 범위보다 크기부터 축소"),
)


@dataclass(frozen=True)
class MiddleSchoolMathContext:
    slug: str
    city: str
    district: str
    town: str
    official_name: str
    display_name: str
    homepage: str
    parent_slug: str
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
    if city == "부산" and district:
        district_base = district if district.startswith(city) else f"{city}{district}"
    else:
        district_base = city
    return list(dict.fromkeys(item for item in (town_base, district_base, city) if item))


@lru_cache(maxsize=1)
def middle_school_math_contexts() -> dict[str, MiddleSchoolMathContext]:
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    contexts: dict[str, MiddleSchoolMathContext] = {}
    for index, row in enumerate(rows):
        slug = str(row["slug"])
        bases = _region_bases(row)
        middle_candidates = [f"{base}중등수학과외" for base in bases]
        general_candidates = [f"{base}과외" for base in bases]
        broader = [f"{row['city']}중등과외", f"{row['city']}수학과외", "중등수학과외"]
        internal = tuple(dict.fromkeys(item for item in (*middle_candidates, *general_candidates, *broader) if _exists(item)))
        parent = next((item for item in middle_candidates if _exists(item)), "")
        if not parent:
            parent = next((item for item in internal if item.endswith("중등수학과외")), f"{row['city']}중등수학과외")
        contexts[slug] = MiddleSchoolMathContext(
            slug=slug,
            city=str(row["city"]),
            district=str(row["district"]),
            town=str(row["town"]),
            official_name=str(row["official_name"]),
            display_name=str(row["display_name"]),
            homepage=str(row["homepage"]),
            parent_slug=parent,
            internal_links=internal[:4],
            theme_index=index // len(METHODS),
            method_index=index % len(METHODS),
            row=row,
        )
    return contexts


def is_middle_school_math_slug(slug: str) -> bool:
    return slug in middle_school_math_contexts()


def middle_school_math_focus(slug: str) -> str:
    context = middle_school_math_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    return f"{theme[0]}·{method[0]}"


def build_middle_school_math_meta(slug: str, source_body: str = "") -> tuple[str, str]:
    context = middle_school_math_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    title = f"{slug} | {theme[0]}·{method[0]} 학습 계획"
    description = (
        f"{context.official_name} 학생을 위한 중등 수학과외 안내입니다. "
        f"2025년 학교 공시 자료와 {context.town} 생활권을 확인하고, {theme[0]} 진단부터 "
        f"내신 서술형·오답 복원·주간 기록까지 {method[0]} 방식으로 정리했습니다."
    )
    return title, description


def _num(context: MiddleSchoolMathContext, key: str) -> str:
    value = context.row.get(key, 0)
    return f"{value:,}" if isinstance(value, int) else str(value)


def _table(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _section(section_id: str, title: str, paragraphs: tuple[str, ...], table: str = "") -> str:
    return f'<section class="middle-school-math-section" id="{escape(section_id)}"><h2>{escape(title)}</h2>{"".join(f"<p>{item}</p>" for item in paragraphs)}{table}</section>'


def _school_profile(context: MiddleSchoolMathContext) -> str:
    row = context.row
    table = _table(
        ("확인 항목", "공시 값", "학습 계획에서의 쓰임"),
        (
            ("학교 구분", f"{row['establishment']} · {row['coeducation']} · {row['school_detail']}", "학교 유형 확인에만 사용"),
            ("학급·학생", f"총 {context.row['total_classes']}학급 · {context.row['total_students']}명", "수업 규모의 참고값"),
            ("학년별 학생", f"1학년 {row['grade1_students']}명 · 2학년 {row['grade2_students']}명 · 3학년 {row['grade3_students']}명", "학년별 경로를 나누는 기준"),
            ("교원", f"교원 {row['teachers']}명 · 교원 1인당 학생 {row['students_per_teacher']}명", "공시된 인원 정보 확인"),
        ),
    )
    paragraphs = (
        f"{escape(context.official_name)}의 공시 주소는 {escape(str(row['address']))}이며, 이 페이지는 {escape(str(row['source_date']))} 기준 학교 통계를 사용했습니다. 공시 수치는 학교를 정확히 식별하고 학년 규모를 이해하기 위한 출발점입니다.",
        f"{escape(context.slug)}에서 학급 수나 학생 수를 성취도·수업 난도·교사의 질로 해석하지 않습니다. 실제 시험 범위와 수행평가 일정은 학생이 받은 공지, 교과서 진도, 학교 홈페이지의 최신 안내로 다시 확인해야 합니다.",
        f"{escape(context.display_name)} 학생이라도 반·담당 교사·현재 단원·귀가 시각에 따라 필요한 과외 계획은 달라집니다. 따라서 공통 통계 다음에는 최근 시험지 두 장과 풀이 흔적, 일주일 학습 기록을 먼저 놓습니다.",
    )
    return _section("school-facts", f"{context.slug} 학교 정보와 자료 사용 범위", paragraphs, table)


def _diagnosis(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    table = _table(
        ("진단 순간", "남길 증거", "다음 행동"),
        (
            ("문제를 읽은 직후", "주어진 조건과 구할 값을 분리한 한 줄", f"{theme[0]} 관련 첫 판단 표시"),
            ("풀이가 멈춘 지점", theme[2], theme[3]),
            ("정답을 확인한 뒤", f"{method[0]} 재현 기록", method[2]),
            ("일주일 뒤", "도움 없이 설명한 단계 수", method[3]),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 수학 진단의 첫 주제는 <strong>{escape(theme[0])}</strong>입니다. 현재 관찰할 문제는 {escape(theme[1])}인지 여부이며, 맞힌 문항도 풀이 근거가 비어 있다면 진단 대상에 포함합니다.",
        f"진단은 문제 수를 늘리는 일이 아니라 행동의 위치를 찾는 일입니다. {escape(context.slug)}에서는 {escape(theme[2])}를 남겨 개념·조건·전략·계산·검산 중 어디에서 처음 흐름이 끊겼는지 확인합니다.",
        f"과외 첫 상담에서는 점수 한 개보다 최근 시험지, 교과서 표시, 학교 학습지, 오답을 고친 흔적을 같은 순서로 봅니다. 이 네 자료가 없으면 {escape(theme[3])}부터 짧게 시도해 출발점을 다시 잡습니다.",
    )
    return _section("diagnosis", f"{context.display_name} {theme[0]} 출발 진단", paragraphs, table)


def _grade_path(context: MiddleSchoolMathContext, theme: tuple[str, ...]) -> str:
    table = _table(
        ("학년", "핵심 연결", "완료 기준"),
        (
            ("중1", "수와 연산·문자식에서 정의와 부호를 말로 확인", f"{theme[0]} 판단을 예 한 개로 설명"),
            ("중2", "식·함수·도형에서 조건을 두 표현으로 전환", "표·식·그림 가운데 두 방식으로 재현"),
            ("중3", "인수분해·이차함수·원에서 근거와 검산 연결", "서술형 풀이의 생략 한 곳을 스스로 보완"),
        ),
    )
    paragraphs = (
        f"{escape(context.official_name)} 1학년은 초등 계산의 속도만 이어가기보다 문자와 음수의 의미를 언어로 바꾸는 과정이 필요합니다. {escape(theme[0])}도 공식 암기보다 조건을 표시하고 첫 식을 선택하는 연습으로 시작합니다.",
        f"2학년은 계산과 함수·도형이 동시에 넓어지므로 단원을 따로 끝냈다는 표시만으로는 부족합니다. 같은 관계를 표·식·그래프로 바꾸고, 한 표현에서 놓친 조건을 다른 표현에서 찾는 기록을 남깁니다.",
        f"3학년은 고등 수학 선행보다 현재 교과의 인수분해·이차함수·도형 근거를 빈 종이에 재현할 수 있는지 먼저 봅니다. {escape(context.slug)}의 학년 구분은 진도를 서두르는 기준이 아니라 누적된 빈틈을 찾는 순서입니다.",
    )
    return _section("grade-path", f"{context.display_name} 중1·중2·중3 수학 경로", paragraphs, table)


def _concept_and_expression(context: MiddleSchoolMathContext, theme: tuple[str, ...]) -> str:
    table = _table(
        ("풀이 층", "학생 질문", "기록 예시"),
        (
            ("개념", "이 정의가 성립하려면 무엇이 필요한가?", "정의·조건·반례 한 줄"),
            ("번역", "문장의 어느 말이 이 식이 되었는가?", "조건 문장과 대응 식"),
            ("변형", "이 줄에서 사용한 성질은 무엇인가?", "한 줄 한 변형과 근거"),
            ("검산", "결과가 원래 조건을 모두 만족하는가?", theme[2]),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 학생의 식 학습에서는 계산 속도와 개념 설명을 분리해 기록합니다. 빠르게 맞혔어도 적용 조건을 설명하지 못하면 개념 칸을, 느렸지만 근거가 정확하면 시간 칸을 다음 목표로 둡니다.",
        f"{escape(theme[0])} 문제는 풀이 첫 줄을 고르는 장면을 관찰하기 좋습니다. 선생님이 시작식을 알려 주기 전에 학생이 후보를 두 개 적고, 덜 적절한 선택을 지운 이유까지 남겨야 도움 의존도를 확인할 수 있습니다.",
        f"문제집 진도는 학교 교과서와 학습지 범위를 확인한 뒤 보조 자료로 배치합니다. {escape(context.slug)} 계획의 완료 기준은 몇 쪽을 풀었는지가 아니라 조건 해석과 변형 근거와 검산이 한 풀이 안에서 이어지는지입니다.",
    )
    return _section("concept-expression", f"{context.display_name} 개념·문자식·방정식 연결", paragraphs, table)


def _geometry_data(context: MiddleSchoolMathContext, method: tuple[str, ...]) -> str:
    table = _table(
        ("표현", "먼저 확인할 것", "검산 방법"),
        (
            ("도형", "주어진 길이·각·평행과 추정 분리", "그림 비율을 바꿔 다시 그리기"),
            ("함수", "무엇이 변하고 무엇이 고정되는지 표시", "표의 값과 그래프 위치 대조"),
            ("자료", "범위·대표값·이상값의 역할 구분", "값 하나를 바꿔 결론 변화 확인"),
            ("확률", "분류 기준과 전체 경우의 수 확인", f"{method[0]} 방식으로 누락 재점검"),
        ),
    )
    paragraphs = (
        f"{escape(context.official_name)} 내신에서 도형·함수·자료 문항을 준비할 때는 그림이나 표를 보는 즉시 공식을 고르지 않습니다. 문제에 실제로 적힌 조건, 표현에서 읽은 정보, 추가로 추론한 내용을 세 칸으로 나눕니다.",
        f"{escape(method[0])}은 표현 전환에도 적용할 수 있습니다. {escape(method[1])} 이 과정에서 식만 남기지 말고 표·스케치·상황 문장 중 적어도 하나를 함께 저장합니다.",
        f"오답을 다시 풀 때 원래 그림을 그대로 따라 그리면 모양을 외운 것인지 조건을 이해한 것인지 구분하기 어렵습니다. {escape(context.slug)} 복습에서는 점과 변의 위치를 바꾸어도 같은 근거를 찾는지 확인합니다.",
    )
    return _section("geometry-data", f"{context.display_name} 함수·도형·자료 표현 전환", paragraphs, table)


def _exam_plan(context: MiddleSchoolMathContext, theme: tuple[str, ...]) -> str:
    table = _table(
        ("기간", "학교자료", "개인 학습", "확인 결과"),
        (
            ("범위 발표 전", "교과서 진도·수업 필기", "정의 회상과 대표 예제", "설명 중 끊긴 개념"),
            ("시험 3~4주 전", "학습지·수행평가 안내", "단원별 첫 풀이", "조건·전략 오류 코드"),
            ("시험 1~2주 전", "이전 시험지·서술형 기준", "시간 제한 미니 시험", "보류와 재진입 순서"),
            ("시험 직후", "채점 결과·교사 피드백", "최초 오류 복원", f"다음 {theme[0]} 행동"),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 내신 준비는 확인되지 않은 출제 경향을 단정하는 대신 학생이 실제로 받은 자료를 기준으로 시작합니다. 시험 범위, 반별 안내, 수행평가 일정은 매 학기 달라질 수 있어 최신 학교 공지가 우선입니다.",
        f"객관식은 답을 찾는 속도만 보지 않고 오답 선택지가 왜 틀렸는지 한 문장으로 남깁니다. 서술형은 가정·사용한 성질·계산·결론 사이에 빠진 근거가 없는지 다른 사람이 읽는 순서로 점검합니다.",
        f"시험 직전의 새 문제 수를 늘리면 익숙함과 재현 가능성을 혼동하기 쉽습니다. {escape(context.slug)}에서는 {escape(theme[2])}를 시험 7일 전 다시 확인해, 혼자 복원하지 못한 단계만 짧게 반복합니다.",
    )
    return _section("school-exam", f"{context.display_name} 내신·서술형 준비 순서", paragraphs, table)


def _error_method(context: MiddleSchoolMathContext, method: tuple[str, ...]) -> str:
    table = _table(
        ("오류 코드", "관찰 질문", "수정 행동"),
        (
            ("C 개념", "정의와 성립 조건을 설명할 수 있는가?", "예와 반례를 하나씩 만들기"),
            ("R 조건", "문장의 조건을 빠짐없이 표시했는가?", "말·식·그림으로 두 번 번역"),
            ("S 전략", "첫 줄을 왜 선택했는가?", "후보 두 개와 선택 이유 기록"),
            ("A 계산", "최초로 값이 달라진 줄은 어디인가?", "한 줄 한 변형 뒤 역검산"),
            ("T 시간", "보류 시점을 지켰는가?", "읽기·첫 식·계산 시간을 분리"),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 오답장은 문제를 다시 베끼는 공책이 아니라 다음 행동을 예약하는 기록이어야 합니다. {escape(method[1])} 한 문제에 오류 코드를 여러 개 붙이기보다 최초 원인 하나와 뒤따른 결과를 나눕니다.",
        f"{escape(method[2])} 기록은 선생님이 대신 완성하지 않고 학생이 이해한 범위와 도움을 받은 범위를 그대로 보이게 합니다. 지운 흔적을 모두 없애면 같은 실수가 반복되는 지점을 비교할 수 없습니다.",
        f"{escape(method[3])} {escape(context.slug)} 과외를 비교할 때도 오답 수보다 이 기록을 학생이 혼자 다시 사용할 수 있도록 설명하는지 확인합니다.",
    )
    return _section("error-method", f"{context.display_name} {method[0]} 오답 복원법", paragraphs, table)


def _weekly(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    digest = int(hashlib.sha256(context.slug.encode("utf-8")).hexdigest()[:4], 16)
    first, second = ("화", "목") if digest % 3 == 0 else (("월", "금") if digest % 3 == 1 else ("수", "토"))
    table = _table(
        ("시점", "학습 행동", "남길 기록"),
        (
            (f"{first}요일", f"{theme[0]} 개념·대표 문제", "정의와 첫 판단 한 줄"),
            (f"{second}요일", "학교자료 적용·서술형 보완", theme[2]),
            ("수업 후 24시간", method[1], method[2]),
            ("주말 20분", "대표 오답 한 문제 빈 풀이", method[3]),
        ),
    )
    paragraphs = (
        f"{escape(context.town)} 생활권의 실제 귀가 시각은 학생마다 다르므로 이 표는 고정 시간표가 아니라 순서 예시입니다. {escape(context.display_name)} 학생은 학원·동아리·가족 일정이 없는 두 날을 먼저 정하고, 피곤한 날에는 새 단원보다 짧은 복원을 배치합니다.",
        f"한 번의 긴 학습보다 수업 뒤 24시간과 72시간의 짧은 재현이 무엇을 잊었는지 보여 줍니다. {escape(context.slug)} 주간 계획에는 시작 시각, 실제 집중 분량, 도움 없이 끝낸 단계만 기록합니다.",
        f"과제를 못 끝낸 날은 양을 그대로 다음 날로 밀지 않습니다. 읽기·첫 식·계산·검산 중 멈춘 단계를 표시하고, 다음 회차 시작 과제를 15~25분 안에 끝나는 크기로 줄여 다시 연결합니다.",
    )
    return _section("weekly-plan", f"{context.display_name} {method[0]} 주간 운영표", paragraphs, table)


def _action_cycle(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    digest = int(hashlib.sha256(f"cycle:{context.slug}".encode("utf-8")).hexdigest()[:12], 16)
    chosen = random.Random(digest).sample(ACTION_LIBRARY, 12)

    blocks: list[str] = []
    for session, action in enumerate(chosen, start=1):
        label, start, evidence, done, adjust = action
        blocks.append(
            f'<section class="middle-school-math-action" id="action-{session}">'
            f'<h3>{escape(context.display_name)} {session}회차: {escape(label)}와 {escape(theme[0])}</h3>'
            f'<p>{escape(context.display_name)} {session}회차의 출발 행동은 {escape(start)}입니다. '
            f'{escape(context.town)} 과제에서는 {escape(theme[0])} 문항을 골라 {escape(evidence)}을 남깁니다. '
            f'{escape(method[0])} 절차로 {escape(done)}할 때 이 회차를 완료로 표시합니다.</p>'
            f'<p>{escape(context.official_name)} 점검에서 완료 기준에 닿지 않으면 정답 수를 늘리지 않습니다. '
            f'{escape(context.slug)}의 조정 행동은 {escape(adjust)}이며, 다음 회차에는 {escape(theme[2])}와 '
            f'{escape(method[2])}을 함께 대조합니다. 이 순서는 성적 약속이 아니라 도움 없이 재현하는 범위를 찾기 위한 계획입니다.</p>'
            '</section>'
        )
    intro = (
        f'<section class="middle-school-math-cycle" id="twelve-session-cycle">'
        f'<h2>{escape(context.display_name)} 학교자료 기반 12회 실행 순서</h2>'
        f'<p>{escape(context.official_name)}의 실제 시험 범위와 일정은 최신 공지를 확인한 뒤 아래 회차에 넣습니다. '
        f'{escape(context.display_name)} 계획은 {escape(theme[0])}과 {escape(method[0])}을 축으로 삼되, '
        f'각 회차를 고정 진도가 아니라 관찰·기록·조정의 단위로 사용합니다.</p>'
    )
    return intro + "".join(blocks) + "</section>"


def _scenario(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    table = _table(
        ("가상 시점", "관찰된 행동", "조정 예시"),
        (
            ("1주차", theme[1], theme[2]),
            ("2주차", "해설 직후에는 풀지만 빈 종이에서 첫 줄이 멈춤", method[1]),
            ("3주차", "틀린 위치를 계산 실수라고만 표시", "최초 오류 코드와 다음 확인 신호 기록"),
            ("4주차", "도움 없이 설명한 단계가 일부 늘어남", "유지할 행동과 새 목표를 분리"),
        ),
    )
    paragraphs = (
        f"<strong class=\"scenario-notice\">아래 내용은 실제 {escape(context.official_name)} 학생의 상담 후기나 성적 결과가 아니라 학습 조정 방법을 설명하기 위해 만든 가상 시나리오입니다.</strong> 가상의 학생은 {escape(theme[0])} 문항에서 답을 확인한 뒤에도 풀이 첫 줄을 혼자 재현하지 못한다고 가정합니다.",
        f"첫 주에는 새 문제를 늘리지 않고 {escape(theme[2])}를 남깁니다. 둘째 주에는 {escape(method[1])} 셋째 주에는 도움을 받은 부분을 숨기지 않고 다른 기호로 표시합니다.",
        f"넷째 주의 판단 기준은 점수 상승이 아니라 첫 줄 선택, 근거 설명, 검산 중 혼자 수행한 단계가 늘었는지입니다. 변화가 없으면 학생의 노력 부족으로 결론 내리지 않고 과제 크기·설명 방식·선행 개념을 각각 다시 확인합니다.",
    )
    return _section("scenario", f"가상 학습 시나리오: {context.display_name} {theme[0]} 조정", paragraphs, table)


def _tutor_choice(context: MiddleSchoolMathContext, theme: tuple[str, ...]) -> str:
    table = _table(
        ("비교 질문", "구체적인 답의 기준", "주의할 신호"),
        (
            ("첫 4주에 무엇을 진단하나요?", f"시험지와 {theme[2]}를 함께 확인", "점수만 보고 진도부터 확정"),
            ("학교자료와 문제집을 어떻게 나누나요?", "교과서·학습지 우선순위를 설명", "모든 학생에게 같은 교재만 제시"),
            ("수업 밖 과제는 어떻게 조정하나요?", "귀가 시각과 재현 가능 분량을 반영", "못 끝낸 양을 계속 누적"),
            ("피드백은 무엇을 남기나요?", "오류 원인·학생 설명·다음 행동을 구분", "정답률만 전달"),
        ),
    )
    paragraphs = (
        f"{escape(context.slug)} 과외 후보에게는 모두 같은 최근 시험지 두 장과 일주일 시간표를 보여 주고 답을 비교해야 합니다. 서로 다른 자료를 주면 수업 방식 차이인지 자료 차이인지 판단하기 어렵습니다.",
        f"첫 상담에서는 {escape(theme[0])}을 예로 들어 학생이 막힌 장면을 어떻게 관찰하고, 선생님의 설명 뒤 학생 혼자 재현하는 시간을 어떻게 확보하는지 묻습니다. 특정 학교의 출제 경향을 근거 없이 단정하는 답은 피합니다.",
        f"수업료·이동·온라인 가능 여부와 함께 취소·보강·자료비·보호자 피드백 주기를 서면으로 확인합니다. 선택 뒤에는 4주 점검일을 미리 정하고 유지·변경·중단 조건을 학생과 함께 기록합니다.",
    )
    return _section("tutor-choice", f"{context.display_name} 수학과외 비교 질문", paragraphs, table)


def _feedback(context: MiddleSchoolMathContext, method: tuple[str, ...]) -> str:
    table = _table(
        ("주차", "학생 기록", "보호자 확인", "다음 결정"),
        (
            ("1주", "시작 가능한 과제 크기", "귀가·수면 흐름", "시간대 조정"),
            ("2주", "오류 코드와 질문 한 줄", "완료 여부보다 막힌 단계", "설명 방식 조정"),
            ("3주", "24·72시간 재현", "도움 요청 시점", "복습 간격 조정"),
            ("4주", "혼자 설명한 단계", "부담·지속 가능성", "유지·변경·중단"),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 보호자 피드백은 매일 감시하는 표가 아니라 학생과 선생님이 합의한 기준을 4주 단위로 확인하는 장치입니다. 정답률, 공부 시간, 문제 수를 한꺼번에 목표로 두지 않고 이번 달 행동 하나를 고릅니다.",
        f"{escape(method[2])} 이 기록에서 학생이 도움을 요청한 시점은 실패가 아니라 혼자 해결 가능한 범위를 알려 주는 자료입니다. 보호자는 정답을 다시 검사하기보다 다음 수업에서 묻고 싶은 질문이 남았는지 확인합니다.",
        f"4주 뒤에도 같은 위치에서 멈추면 횟수를 곧바로 늘리기 전에 과제 난도, 선행 개념, 수업 언어, 생활 시간대를 나눠 검토합니다. {escape(context.slug)} 페이지는 이 의사결정을 돕는 정보이며 개인 상담이나 성과 보장을 대신하지 않습니다.",
    )
    return _section("feedback", f"{context.display_name} 4주 학부모 피드백", paragraphs, table)


def _links(context: MiddleSchoolMathContext) -> str:
    internal = context.internal_links[:3]
    links = [f'<li><a class="source-link" href="{escape(context.homepage)}" rel="nofollow noopener noreferrer" target="_blank">{escape(context.official_name)} 공식 홈페이지</a></li>']
    links.extend(f'<li><a href="/{escape(slug)}/">{escape(slug)}</a></li>' for slug in internal)
    list_html = '<ul class="reference-link-list">' + "".join(links) + "</ul>"
    paragraphs = (
        f"{escape(context.official_name)}의 학사 일정, 시험·수행평가 안내, 학교 연락처는 공식 홈페이지의 최신 공지를 우선 확인하세요. 이 페이지에 표시한 통계 기준일은 {escape(str(context.row['source_date']))}이므로 이후 변동은 학교와 교육통계 원문에서 다시 확인해야 합니다.",
        f"{escape(context.town)} 또는 더 넓은 {escape(context.city)} 학습 정보를 비교할 때는 아래 내부 페이지를 사용합니다. 링크는 같은 문장을 반복하기 위한 키워드 나열이 아니라 학교 페이지에서 지역·학년·과목 페이지로 이동하는 경로만 제공합니다.",
        f"{escape(context.slug)}와 연결된 내부 페이지가 여러 개여도 모두 읽을 필요는 없습니다. 현재 질문이 학교별 수학 계획인지, 생활권 과외 비교인지, 중등 수학 전체 흐름인지에 따라 한 경로를 선택하면 됩니다.",
    )
    return _section("official-links", f"{context.display_name} 공식 정보와 지역 연결", paragraphs, list_html)


def _next_cycle(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    table = _table(
        ("점검 결과", "다음 4주 행동", "줄이거나 멈출 것"),
        (
            ("개념 설명이 끊김", "정의·예·반례를 짧게 재현", "새 유형 추가"),
            ("첫 식 선택이 늦음", f"{theme[0]} 조건 번역 연습", "해설 첫 줄 바로 보기"),
            ("계산 오류가 반복", "최초 오류 줄과 역검산 기록", "정답만 다시 쓰기"),
            ("혼자 재현 가능", f"{method[0]} 간격을 조금 늘려 확인", "이미 가능한 유형의 과도한 반복"),
        ),
    )
    paragraphs = (
        f"{escape(context.display_name)} 학습 계획은 시험이 끝날 때마다 전부 새로 만드는 것이 아니라 유지할 행동, 수정할 행동, 중단할 행동을 구분해 이어 갑니다. 학생이 혼자 설명할 수 있는 부분까지 계속 반복하면 필요한 빈틈에 쓸 시간이 줄어듭니다.",
        f"다음 4주의 핵심 질문은 {escape(theme[0])} 문항을 더 많이 풀었는지가 아니라 처음 보는 조건에서도 {escape(theme[3])}를 수행하는지입니다. 필요한 도움의 양과 위치가 줄었는지도 함께 봅니다.",
        f"{escape(context.slug)} 점검일에는 학생·보호자·선생님이 같은 기록을 보고 한 가지 결정을 남깁니다. 목표가 달성되면 난도를 조금 높이고, 일부만 가능하면 간격을 유지하며, 부담이 누적되면 과제 크기부터 줄입니다.",
    )
    return _section("next-cycle", f"{context.display_name} 다음 4주 조정 기준", paragraphs, table)


def _faq(context: MiddleSchoolMathContext, theme: tuple[str, ...], method: tuple[str, ...]) -> str:
    items = (
        (f"{context.display_name} 수학과외 첫 상담에는 무엇을 준비하나요?", f"최근 시험지 두 장, 교과서 진도 표시, 학교 학습지, 일주일 시간표를 준비하세요. {theme[0]}에서 혼자 시작하지 못한 문제 한 개를 함께 가져가면 설명 전후의 차이를 확인하기 쉽습니다."),
        (f"{context.display_name} 중1은 선행보다 무엇을 먼저 봐야 하나요?", "정수·유리수와 문자식의 정의를 말로 설명하고, 문장을 식으로 바꾸며, 계산 결과를 원래 조건에 대입하는 세 행동을 먼저 확인하세요. 선행 범위보다 현재 풀이의 끊긴 위치가 우선입니다."),
        (f"{context.display_name} 중2 수학 오답은 어떻게 다시 보나요?", f"함수·도형·확률 오답을 한 묶음으로 처리하지 말고 개념·조건·전략·계산·시간 코드로 나누세요. {method[0]} 방식으로 하루와 사흘 뒤 혼자 재현되는지도 확인합니다."),
        (f"{context.display_name} 중3은 고등 수학을 바로 시작해야 하나요?", "고등 선행 시작 시점은 학생별로 다릅니다. 중3 인수분해·이차함수·도형의 근거를 빈 종이에 재현하고 서술형 생략을 스스로 보완할 수 있는지 확인한 뒤 범위를 결정하세요."),
        (f"{context.slug} 페이지의 학교 통계는 성적을 뜻하나요?", f"아닙니다. {context.row['source_date']} 기준 학급·학생·교원 수는 학교 식별과 규모 확인을 위한 참고값일 뿐 성취도, 시험 난도, 교육 품질을 나타내지 않습니다. 최신 일정과 공지는 학교 공식 홈페이지에서 확인하세요."),
    )
    body = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in items)
    return f'<section class="middle-school-math-faq"><h2>{escape(context.display_name)} 중등수학과외 FAQ</h2>{body}</section>'


def _contextualize_shared_paragraphs(
    body: str,
    context: MiddleSchoolMathContext,
    theme: tuple[str, ...],
    method: tuple[str, ...],
) -> str:
    """Keep shared teaching principles anchored to the page's school and focus.

    Some principles legitimately apply to every middle-school learner.  This
    adds a short, useful application note only where a paragraph otherwise has
    no school-specific evidence or label, preventing generic paragraphs from
    becoming identical copy across the collection.
    """
    notes = (
        f"{context.display_name} 적용 시에는 {context.town} 일정과 {theme[0]} 풀이 흔적에 맞춰 이 기준을 조정합니다.",
        f"{context.official_name} 계획에서는 {method[0]} 기록으로 이 행동이 실제로 재현되는지 대조합니다.",
        f"{context.slug} 상담에서는 같은 원칙을 최근 학교 자료와 학생의 귀가 시각에 맞춰 구체화합니다.",
        f"{context.display_name}의 다음 점검에서는 {theme[2]}와 {method[2]}을 나란히 놓고 변화를 확인합니다.",
        f"{context.town}에서 수업을 정할 때도 {context.display_name} 학생의 현재 과제량을 먼저 반영합니다.",
        f"{context.official_name} 학생에게는 {theme[0]} 진단 뒤 {method[3]}",
    )
    index = 0

    def add_note(match: re.Match[str]) -> str:
        nonlocal index
        opening, inner, closing = match.groups()
        plain = re.sub(r"<[^>]+>", " ", inner)
        if context.display_name in plain or context.official_name in plain or context.slug in plain:
            return match.group(0)
        note = notes[index % len(notes)]
        index += 1
        return f"{opening}{inner} {escape(note)}{closing}"

    return re.sub(r"(<p\b[^>]*>)(.*?)(</p>)", add_note, body, flags=re.I | re.S)


def build_middle_school_math_body(slug: str, source_body: str = "") -> str:
    context = middle_school_math_contexts()[slug]
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    intro = (
        f'<section class="middle-school-math-guide" data-content-version="middle-school-math-individual-v1" data-school="{escape(context.official_name)}" data-focus="{escape(theme[0])}·{escape(method[0])}">'
        f'<h2>{escape(context.slug)}: {escape(context.official_name)} 중등 수학 학습 설계</h2>'
        f'<p>{escape(context.slug)}는 <strong>{escape(theme[0])}</strong> 진단과 <strong>{escape(method[0])}</strong> 복습을 중심으로 구성한 학교별 정보 페이지입니다. 학교명을 검색한 학생과 보호자가 확인 가능한 학교 자료, 현재 풀이 증거, 과외 비교 질문을 한 흐름으로 볼 수 있게 했습니다.</p>'
        f'<p>{escape(context.official_name)}의 {escape(context.town)} 소재와 학년별 학생 수는 공식 통계에서 확인했지만, 시험 난도나 특정 교사의 출제 방식은 추정하지 않습니다. 실제 계획은 학생이 받은 최신 시험 범위·학습지·수행평가 안내로 조정해야 합니다.</p>'
        f'<p>현재 점수만으로 진도를 정하지 않고 최근 풀이에서 {escape(theme[1])}인지 먼저 관찰합니다. 이후 {escape(theme[2])}와 {escape(method[2])}을 남겨 설명을 들은 직후와 스스로 다시 푼 뒤의 차이를 비교합니다.</p>'
    )
    sections = (
        _school_profile(context),
        _diagnosis(context, theme, method),
        _grade_path(context, theme),
        _concept_and_expression(context, theme),
        _geometry_data(context, method),
        _exam_plan(context, theme),
        _error_method(context, method),
        _weekly(context, theme, method),
        _action_cycle(context, theme, method),
        _scenario(context, theme, method),
        _tutor_choice(context, theme),
        _feedback(context, method),
        _links(context),
        _next_cycle(context, theme, method),
        _faq(context, theme, method),
    )
    body = intro + "".join(sections) + "</section>"
    return _contextualize_shared_paragraphs(body, context, theme, method)


def individualize_middle_school_math_body(body: str, slug: str) -> str:
    if not is_middle_school_math_slug(slug):
        return body
    return build_middle_school_math_body(slug, body)
