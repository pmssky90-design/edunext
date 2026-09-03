from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations
from pathlib import Path

from sitegen.school_math import school_math_contexts
from sitegen.utils import escape


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SchoolGeneralContext:
    slug: str
    math_slug: str
    english_slug: str
    city: str
    district: str
    town: str
    official_name: str
    display_name: str
    homepage: str
    region_slug: str
    theme_index: int
    method_index: int


THEMES = (
    {
        "label": "귀가 후 첫 과제",
        "problem": "학교에서 돌아온 뒤 해야 할 일을 고르지 못해 쉬운 과제만 반복하거나 시작이 계속 늦어지는 상태",
        "evidence": "귀가 시각, 제출 마감, 예상 집중 시간, 가장 먼저 끝낼 한 가지를 적은 시작표",
        "action": "집에 온 뒤 20분 안에 학교 자료를 펼치고 오늘 반드시 남길 결과 한 줄을 정하는 연습",
        "output": "공부 시간보다 실제 시작 시각과 첫 과제가 완료된 시점을 비교한 주간 기록",
    },
    {
        "label": "제출일 역산",
        "problem": "수행평가와 과제의 최종 제출일만 기억해 조사·초안·수정이 마지막 날에 몰리는 상태",
        "evidence": "제출일에서 거꾸로 조사, 초안, 확인, 수정 날짜를 나눈 마감 역산표",
        "action": "마감 전날을 완료일로 잡고 필요한 자료와 질문을 단계별로 한 칸씩 앞당기는 연습",
        "output": "늦어진 단계와 다음 과제에서 먼저 시작해야 할 행동을 확인하는 제출 과정 기록",
    },
    {
        "label": "과목 우선순위",
        "problem": "좋아하는 과목이나 급한 숙제에만 시간을 써서 누적 공백과 시험 범위를 함께 관리하지 못하는 상태",
        "evidence": "마감 긴급도, 현재 이해도, 다시 확인할 날짜를 과목별로 나눈 우선순위표",
        "action": "오늘 반드시 끝낼 과목과 짧게 유지할 과목을 구분하고 미룬 이유를 다음 날 계획에 남기는 연습",
        "output": "주간 과목 배분이 감정이 아니라 마감과 학습 증거에 따라 바뀐 기록",
    },
    {
        "label": "수업 당일 복원",
        "problem": "수업 내용을 이해했다고 느끼지만 교재를 덮으면 핵심 개념과 과제의 목적을 설명하지 못하는 상태",
        "evidence": "오늘 배운 개념, 기억으로 설명한 문장, 막힌 지점, 다시 볼 자료를 적은 당일 복원표",
        "action": "학교 자료를 보기 전에 핵심 내용을 세 문장으로 회상하고 원문을 확인해 빠진 부분만 보완하는 연습",
        "output": "수업 직후의 이해와 하루 뒤 독립 재현 사이의 차이를 보여 주는 복원 기록",
    },
    {
        "label": "오답 원인 분리",
        "problem": "틀린 문제를 모두 실수라고 적어 개념·조건·전략·계산·시간 가운데 실제 원인을 구분하지 못하는 상태",
        "evidence": "최초 오류 위치, 원인 코드, 다시 시도할 날짜, 다음에 볼 신호를 연결한 오답 분류표",
        "action": "정답을 옮겨 적기 전에 마지막으로 맞았던 판단과 처음 어긋난 줄을 표시하는 연습",
        "output": "과목이 달라도 반복되는 오류 습관과 과목별 고유 오류를 나누어 본 기록",
    },
    {
        "label": "질문 한 줄 준비",
        "problem": "모르는 부분이 있어도 무엇을 질문할지 정리하지 못해 해설을 그대로 받아 적는 상태",
        "evidence": "알고 있는 것, 시도한 것, 막힌 지점, 확인할 질문을 네 칸으로 나눈 질문표",
        "action": "도움을 요청하기 전에 막힌 순간을 한 문장으로 쓰고 필요한 설명 범위를 한 단계로 좁히는 연습",
        "output": "답을 들은 횟수보다 다음에는 혼자 확인할 수 있는 판단이 늘어난 질문 기록",
    },
    {
        "label": "모의고사 복기",
        "problem": "점수와 등급만 확인하고 시간 배분, 보류 판단, 선택지 근거가 어디서 흔들렸는지 남기지 않는 상태",
        "evidence": "문항별 시간, 확신 정도, 보류 시점, 다시 풀 때 바꾼 행동을 적은 실전 복기표",
        "action": "시험 직후 기억이 남아 있을 때 어려웠던 문항의 판단 순서를 먼저 적고 해설과 비교하는 연습",
        "output": "다음 실전에서 유지할 선택과 바꿀 선택이 구분된 모의고사 운영 기록",
    },
    {
        "label": "과제 크기 조절",
        "problem": "계획이 밀릴 때 학습량을 무조건 늘려 피로와 미완료가 함께 누적되는 상태",
        "evidence": "예상 시간, 실제 시간, 완료 기준, 줄이거나 나눈 단위를 적은 과제 크기표",
        "action": "한 번에 끝내지 못한 과제를 개념 확인·첫 문제·검토처럼 다시 시작 가능한 단위로 나누는 연습",
        "output": "의지 평가 대신 어떤 크기의 과제에서 시작과 완료가 가능했는지 보여 주는 기록",
    },
    {
        "label": "교과 간 전환",
        "problem": "한 과목을 오래 공부한 뒤 다른 과목으로 옮길 때 준비 시간이 길어지고 이전 과목의 미완료가 남는 상태",
        "evidence": "과목별 종료 신호, 다음 과목의 시작 자료, 전환에 걸린 시간을 표시한 과목 전환표",
        "action": "현재 과목에서 다음에 할 일을 한 줄 남긴 뒤 책상 위 자료를 바꾸고 새 과목의 첫 행동을 바로 시작하는 연습",
        "output": "하루 총시간뿐 아니라 과목 사이의 빈 시간과 재시작 부담을 줄인 전환 기록",
    },
    {
        "label": "시험 범위 지도",
        "problem": "범위표를 받아도 교과서·학습지·문제집의 어느 부분과 연결되는지 한눈에 보지 못하는 상태",
        "evidence": "시험 범위, 학교 자료, 완료한 증거, 다시 볼 날짜를 한 줄로 연결한 범위 지도",
        "action": "학교가 안내한 범위를 자료별 페이지와 활동으로 바꾸고 빈칸이 남은 자료부터 확인하는 연습",
        "output": "많이 푼 교재가 아니라 실제 범위를 빠짐없이 확인했는지 보여 주는 시험 준비 기록",
    },
    {
        "label": "집중 시간대 배치",
        "problem": "피로가 큰 시간에도 어려운 과제를 고집해 시작 지연과 계산·독해 오류가 늘어나는 상태",
        "evidence": "요일별 귀가 시각, 집중이 유지된 시간, 과제 난도, 완료 여부를 나란히 둔 시간대표",
        "action": "집중 가능한 시간에는 새로운 판단을, 피로한 시간에는 짧은 복원과 정리를 배치하는 연습",
        "output": "계획 실패를 의지 대신 시간대와 과제 난도의 조합으로 설명한 생활 기록",
    },
    {
        "label": "주간 누적 공백",
        "problem": "당일 숙제는 끝내지만 이전 단원의 취약 개념과 장기 과제가 계속 뒤로 밀리는 상태",
        "evidence": "이번 주 마감, 지난주 미완료, 누적 개념, 다음 확인일을 분리한 주간 공백표",
        "action": "매주 같은 요일에 미완료 항목을 새 계획으로 옮기기 전에 유지·축소·중단 가운데 하나로 결정하는 연습",
        "output": "미룬 항목이 사라지지 않고 다음 주 행동과 연결되는 누적 관리 기록",
    },
    {
        "label": "설명 가능한 완료",
        "problem": "문제나 과제를 끝냈지만 핵심 판단과 결과를 자신의 말로 설명하지 못하는 상태",
        "evidence": "완료한 결과, 사용한 근거, 막혔던 지점, 다시 설명할 날짜를 적은 완료 확인표",
        "action": "답이나 제출물을 덮고 무엇을 왜 했는지 짧게 설명한 뒤 빠진 근거만 다시 확인하는 연습",
        "output": "체크 표시보다 학생이 독립적으로 재현할 수 있는 범위가 남는 완료 기록",
    },
    {
        "label": "회복과 수면 경계",
        "problem": "시험 기간에 수면을 줄여 공부 시간을 늘리지만 다음 날 독해와 계산의 정확도가 함께 떨어지는 상태",
        "evidence": "취침 시각, 실제 집중 시간, 반복 오류, 다음 날 첫 과제를 비교한 회복 점검표",
        "action": "끝나지 않은 과제를 모두 밤에 밀어 넣지 않고 반드시 할 한 단위와 다음 날로 옮길 단위를 구분하는 연습",
        "output": "공부 시간 증가가 실제 재현과 정확도로 이어졌는지 확인하는 생활 리듬 기록",
    },
)


METHODS = (
    {"label": "간격 재확인", "start": "수업 뒤에는 기억으로 핵심을 복원하고 간격을 둔 다음 자료 없이 같은 판단을 다시 적용합니다", "record": "처음 기억한 내용과 확인 뒤 보완한 내용을 지우지 않고 두 칸으로 나누어 남깁니다", "review": "간격을 둔 뒤에도 설명이 끊기면 분량을 늘리지 않고 끊긴 개념과 질문으로 돌아갑니다"},
    {"label": "마감 역산 보드", "start": "학교 공지와 학생 안내에서 날짜를 확인한 뒤 제출일 전날을 완료일로 두고 단계를 거꾸로 배치합니다", "record": "조사·초안·질문·수정 가운데 늦어진 단계와 필요한 자료를 함께 표시합니다", "review": "계획이 밀리면 마지막 날의 시간을 늘리지 않고 아직 시작하지 않은 단계를 더 작은 단위로 나눕니다"},
    {"label": "세 칸 우선표", "start": "오늘 끝낼 일, 짧게 유지할 일, 다음 날짜로 옮길 일을 서로 다른 칸에 배치합니다", "record": "과목명 옆에 마감, 현재 이해, 완료 증거를 적어 선택 이유를 남깁니다", "review": "주말에는 미룬 횟수보다 같은 이유로 반복해 밀린 과목과 시간대를 확인합니다"},
    {"label": "빈 종이 복원", "start": "학교 자료를 닫고 오늘 배운 핵심과 다음 과제를 빈 종이에 기억나는 순서대로 씁니다", "record": "기억으로 쓴 문장과 자료를 다시 보고 추가한 문장을 다른 표시로 구분합니다", "review": "하루 뒤 핵심 판단을 자료 없이 설명할 수 있을 때 해당 단위를 완료로 처리합니다"},
    {"label": "오류 코드 장부", "start": "미완료와 오답을 개념·조건·전략·계산·시간의 다섯 코드 가운데 하나로 먼저 분류합니다", "record": "코드 옆에는 변명보다 다음에 가장 먼저 확인할 신호를 한 문장으로 적습니다", "review": "같은 코드가 세 번 반복되면 새 과제를 추가하지 않고 시작 행동과 도움 시점을 바꿉니다"},
    {"label": "질문 전 자기점검", "start": "도움을 요청하기 전 알고 있는 것, 시도한 것, 막힌 곳을 한 줄씩 씁니다", "record": "받은 설명 전체가 아니라 혼자 다시 해야 할 다음 행동만 질문 아래에 남깁니다", "review": "다음 확인에서 같은 질문을 답이 아닌 판단 순서로 설명할 수 있는지 확인합니다"},
    {"label": "집중·회복 교대", "start": "집중 가능한 날과 새로운 판단 과제를 두고 피로한 날에는 짧은 복원과 자료 정리를 배치합니다", "record": "요일별 시작 시각과 실제 집중 시간을 과제 난도와 함께 비교합니다", "review": "계획 실패를 의지로 해석하지 않고 시간대와 과제 크기의 조합을 바꿉니다"},
    {"label": "주간 증거 회의", "start": "일주일에 한 번 완료량 대신 가장 잘 설명한 결과와 반복해서 막힌 결과를 각각 하나 고릅니다", "record": "유지할 행동, 바꿀 행동, 다음 확인일을 학생이 먼저 적고 보호자가 질문을 덧붙입니다", "review": "점수 예상보다 학생이 혼자 재현한 범위가 넓어졌는지 같은 자료로 비교합니다"},
    {"label": "과목 전환 메모", "start": "한 과목을 끝낼 때 다음에 할 한 줄을 남기고 새 과목의 첫 자료를 미리 펼쳐 둡니다", "record": "공부 시간과 함께 전환에 걸린 시간과 다시 시작할 때 찾은 메모를 표시합니다", "review": "전환이 오래 걸린 날은 과목 수보다 종료 기준과 준비 자료를 먼저 단순화합니다"},
    {"label": "완료 기준 카드", "start": "과제를 시작하기 전에 제출·설명·재현 가운데 오늘 필요한 완료 기준을 한 문장으로 정합니다", "record": "끝낸 분량과 아직 설명하지 못한 근거를 같은 카드에 함께 남깁니다", "review": "체크 표시가 있어도 핵심 판단을 설명하지 못하면 완료 대신 재확인 날짜를 둡니다"},
    {"label": "단계별 작은 실험", "start": "출발 습관을 기록한 뒤 한 행동만 바꾸고 충분한 간격 뒤 같은 과제로 비교합니다", "record": "변화시킨 조건과 그대로 둔 조건을 나누어 결과를 과장하지 않고 기록합니다", "review": "변화가 없으면 학생 탓으로 결론 내리지 않고 과제 크기·자료·도움 시점 가운데 하나를 다시 바꿉니다"},
)


SECTION_PURPOSES = (
    "검색 의도와 학교 자료의 경계",
    "학교 유형에 맞춘 확인 질문",
    "고1·고2·고3 학년별 경로",
    "국어·영어·수학·탐구 과목 배분",
    "내신·수행평가·모의고사 역할 분리",
    "주간 일정과 복습 간격",
    "질문과 독립 재현의 증거",
    "합성 사례로 보는 계획 수정",
    "과외 방식 비교 기준",
    "학부모 피드백과 누적 기록",
    "공식 정보와 학교별 과목 페이지",
    "다음 시험 뒤 계획을 고치는 방법",
)


PROFILE_RULES = (
    (
        "과학영재|영재학교",
        {
            "label": "탐구·연구 일정과 교과 복습",
            "cue": "학교명에 영재학교 표기가 있지만 실제 연구 활동과 교과 편성은 공식 교육과정에서 확인해야 합니다",
            "verify": "공식 교육과정, 탐구·연구 일정, 학생이 받은 과제 안내를 서로 구분해 확인합니다",
            "balance": "긴 탐구 과제를 조사·실험·분석·발표 단계로 나누고 국어·영어·수학의 짧은 복원을 주중에 유지합니다",
            "avoid": "학교명만으로 모든 학생의 연구 분야, 진도, 진학 방향이 같다고 가정하지 않습니다",
        },
    ),
    (
        "과학고|일과학",
        {
            "label": "수학·과학 탐구와 공통교과 연결",
            "cue": "학교명에 과학 관련 표기가 있어도 선택 과목과 탐구 활동은 학년과 학생에 따라 달라질 수 있습니다",
            "verify": "학교의 공식 교육과정과 학생의 실제 수학·과학 자료, 탐구 마감, 공통교과 범위를 함께 확인합니다",
            "balance": "탐구 활동의 계산·자료 해석·설명 문장을 수학과 국어 학습 기록에 연결합니다",
            "avoid": "학교 유형만 보고 선행 범위나 학생의 수학·과학 수준을 추정하지 않습니다",
        },
    ),
    (
        "외국어|외고",
        {
            "label": "언어 과목과 공통교과 병행",
            "cue": "학교명에 외국어 관련 표기가 있지만 전공어와 과목별 시수는 실제 교육과정에서 확인해야 합니다",
            "verify": "전공어·영어·국어 과제와 수학·탐구 평가 일정을 같은 주간표에서 구분합니다",
            "balance": "언어 과목의 읽기·쓰기·발표 마감과 수학·탐구의 누적 복습을 서로 다른 시간대에 배치합니다",
            "avoid": "학교명만으로 모든 학생의 전공어, 어학 수준, 진로를 단정하지 않습니다",
        },
    ),
    (
        "예술|예고|영상",
        {
            "label": "실기·전공 일정과 교과 학습",
            "cue": "학교명에 예술 관련 표기가 있어도 전공과 실기 일정은 학생별·학기별로 다를 수 있습니다",
            "verify": "공식 교육과정, 실제 실기 일정, 공연·작품 마감, 교과 평가 범위를 학생 자료로 확인합니다",
            "balance": "긴 실기 일정이 있는 날에는 교과 복원을 짧게 유지하고 집중 가능한 날에 서술형과 누적 오답을 배치합니다",
            "avoid": "예술계열 학교라는 이유로 교과 학습을 줄이거나 모든 학생의 입시 계획을 같게 보지 않습니다",
        },
    ),
    (
        "해사|해양",
        {
            "label": "전공·실습 일정과 일반교과 관리",
            "cue": "학교명에 해사·해양 표기가 있지만 전공 교과와 실습 여부는 공식 교육과정과 학생 안내에서 확인해야 합니다",
            "verify": "전공 교과, 실습·행사 일정, 일반교과 시험 범위와 귀가 이후 시간을 따로 확인합니다",
            "balance": "실습과 전공 과제의 마감을 먼저 고정하고 국어·영어·수학 복원 단위를 짧게 나누어 유지합니다",
            "avoid": "학교명만으로 학생의 전공, 자격 준비, 진로 선택을 추정하지 않습니다",
        },
    ),
    (
        "공업|상업|관광|마이스터|정보|디자인|자동차|소프트웨어|항공|조리|미래",
        {
            "label": "전공 교과와 기초교과 연결",
            "cue": "학교명에 전공 분야를 떠올리게 하는 표기가 있어도 실제 학과와 교과 편성은 공식 자료에서 확인해야 합니다",
            "verify": "전공 과제·실습·자격 관련 일정과 국어·영어·수학의 현재 범위를 학생 자료에서 구분합니다",
            "balance": "전공 과제의 산출물과 기초교과의 읽기·계산·설명 활동을 주간 결과물로 나누어 관리합니다",
            "avoid": "학교명만으로 학생의 학과, 취업 준비, 대학 진학 여부를 단정하지 않습니다",
        },
    ),
)


DEFAULT_PROFILE = {
    "label": "교과·평가 일정의 균형",
    "cue": "학교명만으로 선택 과목, 수행평가 방식, 방과 후 일정을 알 수 없으므로 현재 학생 자료가 출발점입니다",
    "verify": "학교 공식 공지와 학생이 받은 범위표·교과서·학습지·수행평가 안내를 순서대로 확인합니다",
    "balance": "국어·영어·수학·탐구의 마감과 누적 공백을 한 주 안에서 서로 다른 역할로 배치합니다",
    "avoid": "같은 학교 학생에게 동일한 진도와 과제량을 적용하거나 학교별 성취를 추정하지 않습니다",
}


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
def school_general_contexts() -> dict[str, SchoolGeneralContext]:
    math_contexts = sorted(school_math_contexts().values(), key=lambda item: item.general_slug)
    contexts: dict[str, SchoolGeneralContext] = {}
    for index, item in enumerate(math_contexts):
        town_candidate = f"{item.city}{item.town}과외" if item.town else ""
        district_candidate = f"{item.city}{item.district}과외" if item.district else ""
        if (
            town_candidate
            and town_candidate != item.general_slug
            and (ROOT / "output" / town_candidate / "index.html").exists()
        ):
            region_slug = town_candidate
        elif (
            district_candidate
            and district_candidate != item.general_slug
            and (ROOT / "output" / district_candidate / "index.html").exists()
        ):
            region_slug = district_candidate
        else:
            region_slug = f"{item.city}과외"
        contexts[item.general_slug] = SchoolGeneralContext(
            slug=item.general_slug,
            math_slug=item.slug,
            english_slug=item.english_slug,
            city=item.city,
            district=item.district,
            town=item.town,
            official_name=item.official_name,
            display_name=item.display_name,
            homepage=item.homepage,
            region_slug=region_slug,
            theme_index=index // len(METHODS),
            method_index=index % len(METHODS),
        )
    return contexts


def is_school_general_slug(slug: str) -> bool:
    return slug in school_general_contexts()


def _profile(context: SchoolGeneralContext) -> dict[str, str]:
    for pattern, profile in PROFILE_RULES:
        if re.search(pattern, context.official_name):
            return profile
    return DEFAULT_PROFILE


def _source_details(source_body: str, context: SchoolGeneralContext) -> dict[str, str]:
    headings = [_clean_html(item) for item in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", source_body, flags=re.I | re.S)]
    paragraphs = [_clean_html(item) for item in re.findall(r"<p[^>]*>(.*?)</p>", source_body, flags=re.I | re.S)]
    source_focus = "학교자료와 주간 학습계획"
    for heading in headings:
        match = re.search(r"(.+?)을 중심으로 보는 학교별 학습 관점", heading)
        if match:
            source_focus = match.group(1).strip()
            break
    basic = _first_sentence(next((item for item in paragraphs if context.official_name in item and "에 위치한" in item), ""))
    stats = _first_sentence(next((item for item in paragraphs if "2025년 4월 1일 교육통계" in item), ""))
    grades = _first_sentence(next((item for item in paragraphs if "학년별 학생 수" in item), ""))
    if not basic:
        place = " ".join(item for item in (context.city, context.district, context.town) if item)
        basic = f"{context.official_name}의 위치와 학교 유형은 공식 홈페이지와 교육통계에서 확인하며, {place} 표기는 지역 탐색 범위입니다."
    if not stats:
        stats = "학생 수와 학급 수는 기준일에 따라 달라질 수 있으므로 최신 학교 안내와 교육통계를 함께 확인합니다."
    if not grades:
        grades = "학년별 규모는 학교를 이해하는 배경 정보이며 학생 개인의 성취나 과목 수준을 판단하는 자료가 아닙니다."
    return {"source_focus": source_focus, "basic": basic, "stats": stats, "grades": grades}


def school_general_focus(slug: str, source_body: str = "") -> str:
    context = school_general_contexts()[slug]
    profile = _profile(context)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    return f"{profile['label']}·{theme['label']}·{method['label']}"


def build_school_general_meta(slug: str, source_body: str = "") -> tuple[str, str]:
    context = school_general_contexts()[slug]
    profile = _profile(context)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    title = f"{slug} | {profile['label']}·{method['label']} 학습계획"
    description = (
        f"{slug}는 {context.official_name}의 공식 자료를 확인하며 {profile['label']}, "
        f"{theme['label']}, {method['label']} 순서로 고1·고2·고3의 교과·수행평가·모의고사 계획을 정리합니다."
    )
    return title, description


@lru_cache(maxsize=1)
def _variant_option_map() -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    slugs = sorted(school_general_contexts())
    theme_sets = list(combinations(range(len(THEMES)), 3))
    method_sets = list(combinations(range(len(METHODS)), 3))
    theme_sets.sort(key=lambda values: hashlib.sha256(f"school-general-theme:{values}".encode()).digest())
    method_sets.sort(key=lambda values: hashlib.sha256(f"school-general-method:{values}".encode()).digest())
    orders = list(permutations(range(3)))
    result: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for index, slug in enumerate(slugs):
        digest = hashlib.sha256(f"school-general-order:{slug}".encode("utf-8")).digest()
        themes = theme_sets[index]
        methods = method_sets[index]
        theme_order = orders[digest[0] % len(orders)]
        method_order = orders[digest[1] % len(orders)]
        result[slug] = (
            tuple(themes[position] for position in theme_order),
            tuple(methods[position] for position in method_order),
        )
    return result


def _variant(context: SchoolGeneralContext, section_index: int) -> tuple[dict[str, str], dict[str, str], str]:
    theme_options, method_options = _variant_option_map()[context.slug]
    theme = THEMES[theme_options[section_index % len(theme_options)]]
    method = METHODS[method_options[(section_index + context.theme_index) % len(method_options)]]
    return theme, method, f"{theme['label']}·{method['label']}"


def _heading(context: SchoolGeneralContext, section_index: int, label: str) -> str:
    _, _, focus = _variant(context, section_index)
    return f"{context.slug}: {label} — {focus}"


def _standard_section(context: SchoolGeneralContext, section_index: int, label: str, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-section school-general-section-{section_index + 1}" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, label))}</h2>
<p>{slug}의 이번 점검은 <strong>{escape(focus)}</strong>입니다. {school} 학생이라는 이유만으로 시험 난도·과제량·진로를 추정하지 않고, 학생이 실제로 받은 학교 자료와 현재 생활시간에서 확인 가능한 행동을 먼저 찾습니다. {_topic(source_focus)} 기존 페이지에서 이어 받은 학습 소재이며 학교의 고정된 특성을 뜻하지 않습니다.</p>
<p>{school} 학습계획에서는 {escape(_object(theme['evidence']))} 먼저 만듭니다. {escape(method['start'])}. {slug} 상담에서 공부 시간을 묻기 전에 시작 시각, 마감, 완료 기준을 확인하면 {escape(_subject(theme['problem']))} 반복되는 이유를 학생 성향 하나로 단정하지 않을 수 있습니다.</p>
<p>{escape(_object(focus))} 행동으로 옮길 때는 {escape(theme['action'])}. {escape(method['record'])}. 결과는 {escape(theme['output'])}으로 남기고 {school}의 실제 일정이 바뀌면 분량보다 순서와 확인 날짜를 먼저 조정합니다.</p>
<p>{slug}의 완료 기준은 한 번의 점수나 체크 표시가 아닙니다. {escape(method['review'])}. 학생이 설명하지 못한 단계는 새 과제로 덮지 않고 다음 질문으로 옮기며, {escape(focus)} 기록이 쌓이면 교과·수행평가·모의고사의 서로 다른 부담을 구분할 수 있습니다.</p>
</section>"""


def _profile_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    profile = _profile(context)
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-profile" data-school-profile="{escape(profile['label'])}" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, profile['label']))}</h2>
<p>{slug}에서 학교 유형을 다루는 기준은 <strong>{escape(profile['cue'])}</strong>. {escape(profile['verify'])}. 학교명은 공식 자료를 찾는 출발점일 뿐 학생의 성취나 수업 결과를 예측하는 값이 아닙니다.</p>
<table>
<thead><tr><th>{slug} 확인 항목</th><th>먼저 볼 자료</th><th>{escape(focus)} 적용</th></tr></thead>
<tbody>
<tr><td>학교 일정</td><td>{school} 공식 공지와 학생이 받은 안내</td><td>{escape(method['start'])}.</td></tr>
<tr><td>과목·활동</td><td>현재 시간표, 과제 설명, 평가 범위</td><td>{escape(theme['action'])}.</td></tr>
<tr><td>생활시간</td><td>실제 귀가 시각과 주중 마감</td><td>{escape(method['record'])}.</td></tr>
</tbody>
</table>
<p>{slug}의 학교 유형별 균형 원칙은 {escape(profile['balance'])}. 동시에 {escape(profile['avoid'])}. {_object(source_focus)} 적용할 때도 학교 이름보다 학생의 실제 자료와 독립 재현 기록을 우선합니다.</p>
</section>"""


def _grade_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-grade" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '고1·고2·고3 학년별 경로'))}</h2>
<p>{slug}의 학년 계획은 같은 과제량을 세 단계로 늘리는 방식이 아닙니다. {school}의 실제 시간표와 평가 자료를 확인하고 <strong>{escape(focus)}</strong>을 공통 기준으로 사용하되, 고1은 수업 복원, 고2는 선택과목과 누적 공백, 고3은 내신 마무리와 실전 운영에 서로 다른 비중을 둡니다.</p>
<table>
<thead><tr><th>학년</th><th>{escape(source_focus)} 출발 행동</th><th>주간 확인 증거</th><th>피해야 할 판단</th></tr></thead>
<tbody>
<tr><td>고1</td><td>{slug} 학생은 수업 당일 교과서·학습지의 핵심을 자료 없이 세 문장으로 복원합니다.</td><td>{escape(theme['evidence'])}</td><td>중학교 점수만으로 고등학교 전체 학습 수준을 고정하지 않습니다.</td></tr>
<tr><td>고2</td><td>{school}의 실제 선택과목과 마감을 확인한 뒤 누적 공백을 주간표의 별도 칸에 둡니다.</td><td>{escape(method['record'])}</td><td>관심 과목만 오래 공부하고 취약 과목을 시험 직전까지 미루지 않습니다.</td></tr>
<tr><td>고3</td><td>{slug} 기록에 내신 범위와 모의고사 시간·보류 판단을 서로 다른 결과로 남깁니다.</td><td>{escape(method['review'])}</td><td>수면을 줄인 공부 시간을 독립 재현과 정확도의 증가로 오해하지 않습니다.</td></tr>
</tbody>
</table>
<p>{school}의 학년별 시험일·선택과목·수행평가 형식은 달라질 수 있습니다. 이 표는 확정된 학교 정보가 아니라 공식 공지와 학생 안내를 확인한 뒤 수정하는 {slug} 점검 틀이며, {escape(_object(focus))} 현재 학년 자료에 맞추어 적용합니다.</p>
</section>"""


def _subject_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-subjects" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '국어·영어·수학·탐구 과목 배분'))}</h2>
<p>{slug}에서 과목 균형은 모든 과목에 같은 시간을 쓰는 뜻이 아닙니다. {school}의 현재 시험 범위와 마감을 적은 뒤 <strong>{escape(focus)}</strong>으로 각 과목에서 남겨야 할 증거를 다르게 정합니다. {_subject(theme['problem'])} 보이면 우선순위와 과제 크기를 함께 조정합니다.</p>
<table>
<thead><tr><th>과목군</th><th>{slug}에서 남길 증거</th><th>완료 질문</th></tr></thead>
<tbody>
<tr><td>국어</td><td>지문 구조, 작품 근거, 서술형 답안의 핵심 문장을 한 장에 연결합니다.</td><td>{school} 자료 없이 근거와 결론을 설명할 수 있나요?</td></tr>
<tr><td>영어</td><td>시험 지문의 핵심 문장, 어휘, 문장 구조, 틀린 선택지 근거를 구분합니다.</td><td>{escape(method['record'])}.</td></tr>
<tr><td>수학</td><td>조건, 첫 식, 최초 오류, 검산을 남겨 맞힌 답과 풀이 판단을 분리합니다.</td><td>{escape(theme['output'])}이 남았나요?</td></tr>
<tr><td>탐구·기타</td><td>개념 관계, 자료 해석, 수행평가 산출물과 마감 단계를 표시합니다.</td><td>{slug}의 실제 평가 범위와 연결되나요?</td></tr>
</tbody>
</table>
<p>{school} 학생의 과목별 시수와 선택은 개인마다 다를 수 있습니다. {slug} 표는 과목의 중요도를 서열화하지 않고, {escape(_object(source_focus))} 현재 자료에서 확인한 마감·이해·재현 증거로 바꾸기 위한 도구입니다.</p>
</section>"""


def _schedule_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-schedule" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '주간 일정과 복습 간격'))}</h2>
<p>{slug} 주간표는 매일 같은 공부량을 요구하지 않습니다. {school} 학생의 실제 귀가 시각과 제출 마감을 적고 <strong>{escape(_object(focus))}</strong> 기준으로 집중일·유지일·회복일을 나눕니다. 계획이 밀리면 의지 부족으로 결론 내리기 전에 시간대와 과제 크기를 확인합니다.</p>
<table>
<thead><tr><th>주간 구간</th><th>{escape(source_focus)} 행동</th><th>{slug} 기록</th></tr></thead>
<tbody>
<tr><td>수업 당일</td><td>{escape(method['start'])}.</td><td>{school} 자료에서 기억으로 복원한 범위와 확인 뒤 보완한 범위를 구분합니다.</td></tr>
<tr><td>간격 후 재확인</td><td>{escape(theme['action'])}.</td><td>{slug}에서 시작 시각, 도움받은 단계, 다시 볼 날짜를 남깁니다.</td></tr>
<tr><td>주말 점검</td><td>{escape(method['review'])}.</td><td>{escape(theme['output'])}</td></tr>
</tbody>
</table>
<p>{school}의 일정이 바뀌거나 다른 과목 마감이 겹치면 {slug} 표의 순서를 바꿉니다. 지우고 다시 쓰기보다 무엇을 줄였고 왜 옮겼는지 남겨야 {escape(_subject(focus))} 다음 주 계획을 결정하는 자료가 됩니다.</p>
</section>"""


def _case_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    grade = ("고1", "고2", "고3")[(context.theme_index + context.method_index) % 3]
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-case" data-case-model="composite" data-case-grade="{grade}" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '합성 사례로 보는 계획 수정'))}</h2>
<p><strong>아래 내용은 {school}의 실제 학생·성적·수업 결과가 아니라 여러 학습 장면을 합쳐 만든 가상 사례입니다.</strong> {slug}의 {grade} 학생이 {escape(_object(theme['problem']))} 겪는다고 가정합니다. 처음에는 밀린 분량만 늘렸지만 시작 지점이 보이지 않았고, 이후 <strong>{escape(_object(focus))}</strong> 적용해 마감·자료·행동·완료 증거를 나누었습니다.</p>
<table>
<thead><tr><th>관찰 시점</th><th>{slug} 가상 학생의 행동</th><th>수정 기준</th></tr></thead>
<tbody>
<tr><td>처음</td><td>학교 과제와 개인 문제집을 한 목록에 적어 우선순위를 설명하지 못했습니다.</td><td>{escape(theme['evidence'])}</td></tr>
<tr><td>일주일</td><td>{escape(method['record'])}.</td><td>{escape(theme['action'])}</td></tr>
<tr><td>재점검</td><td>{escape(method['review'])}.</td><td>{escape(theme['output'])}</td></tr>
</tbody>
</table>
<ol>
<li>{school}에서 받은 실제 자료와 가상 사례가 다른 부분을 학생이 먼저 표시합니다.</li>
<li>{slug} 기록에는 점수 예상이 아니라 이번 주에 바꿀 한 행동과 다시 볼 날짜를 적습니다.</li>
<li>{escape(_object(focus))} 적용해도 변화가 없으면 과제 크기·자료·도움 시점 가운데 하나를 바꿉니다.</li>
</ol>
<p>이 사례는 {school}의 출제 방식이나 특정 학생의 성과를 설명하지 않습니다. {slug}에서 보여 주려는 것은 {escape(_object(source_focus))} 관찰 가능한 증거로 바꾸고 증거가 없을 때 계획을 수정하는 과정입니다.</p>
</section>"""


def _decision_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    theme, method, focus = _variant(context, section_index)
    slug, school = escape(context.slug), escape(context.official_name)
    return f"""
<section class="school-general-decision" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '과외 방식 비교 기준'))}</h2>
<p>{escape(_object(slug))} 비교할 때는 학교 이름을 안다는 말보다 <strong>{escape(_object(focus))}</strong> 어떻게 관찰하고 수정하는지 질문해야 합니다. {school} 자료를 학생이 제공했을 때 수업 전후에 무엇이 남는지, 설명을 들은 뒤 {escape(_object(source_focus))} 혼자 재현하는 간격을 어떻게 확인하는지 답을 들어야 합니다.</p>
<table>
<thead><tr><th>비교 질문</th><th>확인할 답변</th><th>{slug} 경계 신호</th></tr></thead>
<tbody>
<tr><td>{escape(_topic(theme['problem']))} 어떻게 구분하나요?</td><td>{escape(theme['evidence'])}처럼 학생 행동에서 확인 가능한 증거가 제시되는지 봅니다.</td><td>상담 전부터 점수 상승과 학교별 출제 경향을 단정합니다.</td></tr>
<tr><td>수업 뒤 혼자 할 행동은 무엇인가요?</td><td>{escape(method['start'])}처럼 재현 순서와 완료 기준이 있는지 봅니다.</td><td>교재와 숙제량만 있고 학생의 설명과 기록이 남지 않습니다.</td></tr>
<tr><td>계획이 실패하면 무엇을 바꾸나요?</td><td>{escape(method['review'])}처럼 수정 시점과 판단 기준이 있는지 봅니다.</td><td>{school} 학생이라는 이유만으로 같은 분량을 계속 요구합니다.</td></tr>
</tbody>
</table>
<p>대면과 온라인 가운데 어느 방식이 맞는지도 {slug}에서 미리 단정할 수 없습니다. 같은 짧은 학교 자료 과제를 각각 한 번 수행해 준비 시간, 질문 시점, 필기 공유, 수업 뒤 독립 복원을 비교하고 {escape(focus)} 기록이 온전히 남는 방식을 선택합니다.</p>
</section>"""


def _tracker_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    _, _, focus = _variant(context, section_index)
    moments = (
        "학교 일정 확인", "도움 전 첫 시작", "과목 우선순위 선택", "완료 기준 말하기",
        "학교 자료 복원", "마감과 복습 조정", "미완료 원인 분류", "간격 뒤 재확인",
        "학생 질문 정리", "보호자 확인 대화", "독립 실행 점검", "다음 계획 결정",
        "과제 목적 확인", "교과 자료 대조", "주요 개념 회상", "근거 자료 선택",
        "도움 받은 위치", "수정 전후 비교", "새 과제 적용", "학교 과제 연결",
        "수행평가 준비", "시험 범위 확인", "학습 기록 재구성", "미완료 재설명",
        "귀가 후 첫 행동", "마감 전 자기점검", "보호자 질문 기록", "다음 수업 준비",
    )
    phases = ("일정관찰", "과목배분", "독립복원", "계획수정")
    rows: list[str] = []
    for offset, moment in enumerate(moments):
        theme, method, daily_focus = _variant(context, section_index + offset + 1)
        phase = phases[offset // 7]
        row_variants = (
            (
                f"{context.slug}에서 {source_focus}와 {theme['label']}의 {phase} 행동을 학생이 직접 시작합니다.",
                f"{context.official_name} 자료와 {method['label']} 기록을 대조해 선택 이유와 수정 근거를 남깁니다.",
                f"{focus}와 {daily_focus} 가운데 유지할 행동과 줄이거나 옮길 과제를 구분합니다.",
            ),
            (
                f"{context.official_name} 일정에서 {phase}에 필요한 자료와 {theme['label']} 우선순위를 학생이 먼저 고릅니다.",
                f"{context.slug} 기록에는 {method['label']} 전후의 시작 시각과 완료 기준을 나란히 둡니다.",
                f"다음에는 {daily_focus}를 다른 과목에 적용하고 필요한 도움만 남깁니다.",
            ),
            (
                f"도움 없이 {source_focus} 과제를 시작한 위치와 {theme['label']} 판단을 {context.slug} 표에 표시합니다.",
                f"{method['label']} 과정에서 바꾼 순서와 {context.official_name} 원본의 마감을 함께 대조합니다.",
                f"{focus}가 유지되면 범위를 넓히고, 흔들리면 과제 크기와 도움 시점을 조정합니다.",
            ),
            (
                f"{phase} 장면에서는 {context.official_name}의 {source_focus} 자료를 학생 계획으로 다시 구성합니다.",
                f"첫 시작, 질문 위치, {method['label']} 뒤 달라진 완료 행동을 {context.slug} 기록에 남깁니다.",
                f"후속 점검은 {daily_focus}의 독립 실행 여부에 따라 유지하거나 더 작은 단계로 나눕니다.",
            ),
        )
        start_text, evidence_text, decision_text = row_variants[
            hashlib.sha256(f"{context.slug}:general-tracker:{offset}".encode("utf-8")).digest()[0] % len(row_variants)
        ]
        rows.append(
            "<tr>"
            f"<td>{escape(moment)}</td>"
            f"<td>{escape(start_text)}</td>"
            f"<td>{escape(evidence_text)}</td>"
            f"<td>{escape(decision_text)}</td>"
            "</tr>"
        )
    return f"""
<section class="school-general-tracker" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '학부모 피드백과 누적 학습 기록'))}</h2>
<p>{escape(context.slug)}의 학부모 피드백은 매일 점수와 진도를 확인하기보다 <strong>{escape(focus)}</strong>의 증거를 주 1회 함께 읽는 방식으로 진행합니다. {escape(context.official_name)} 학생이 직접 적은 마감·시작·완료 행동을 먼저 듣고, 보호자는 미완료 원인을 자료·과제 크기·시간·도움 시점 가운데 어디에서 찾았는지 질문합니다.</p>
<ul>
<li>{escape(context.slug)} 기록에는 정확한 집 주소나 불필요한 개인정보를 적지 않습니다.</li>
<li>{escape(context.official_name)} 이름과 학년은 학교 자료를 구분하는 데 필요한 범위에서만 사용합니다.</li>
<li>{escape(source_focus)} 상담에는 최근 학교 자료와 반복되는 미완료 행동을 먼저 준비합니다.</li>
<li>{escape(context.slug)} 피드백은 유지할 판단 하나와 바꿀 행동 하나로 끝냅니다.</li>
<li>{escape(context.official_name)} 일정이 바뀌면 공부 시간보다 마감과 복습 순서를 먼저 고칩니다.</li>
<li>{escape(focus)} 기록은 보관 목적과 공유 범위를 확인한 뒤 전달합니다.</li>
</ul>
<p>아래 표는 {escape(context.slug)}에서 일정관찰·과목배분·독립복원·계획수정을 구분하기 위한 누적 기록지입니다. 정해진 날짜를 채우기보다 현재 학교 일정에 맞는 점검 장면을 선택하고, 각 칸에는 학생의 시작 행동과 수정 이유를 남깁니다. {escape(context.official_name)}의 실제 시험 기간에는 학교 자료를 우선해 순서를 바꿉니다.</p>
<table class="school-general-evidence-tracker">
<thead><tr><th>점검 장면</th><th>학생의 시작</th><th>남길 증거</th><th>다음 결정</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p>{escape(context.slug)}의 누적 표는 성적 향상을 보장하는 프로그램이 아닙니다. 출발 시점과 간격을 둔 시점에 같은 짧은 {escape(source_focus)} 과제를 수행해 시작 지연, 설명 가능한 완료, 다시 확인한 범위를 비교하는 도구이며 변화가 보이지 않으면 학생을 압박하기보다 과제 크기와 도움 시점을 먼저 수정합니다.</p>
</section>"""


def _links_section(context: SchoolGeneralContext, section_index: int, source_focus: str) -> str:
    _, _, focus = _variant(context, section_index)
    place = " ".join(item for item in (context.city, context.district, context.town) if item) or context.city
    return f"""
<section class="school-general-links" data-section-focus="{escape(focus)}">
<h2>{escape(_heading(context, section_index, '공식 정보와 학교별 과목 페이지'))}</h2>
<p>{escape(context.slug)}에서 학교 일정·교육과정·평가 안내처럼 바뀔 수 있는 내용은 <a class="source-link" href="{escape(context.homepage)}" target="_blank" rel="noopener noreferrer external">{escape(context.official_name)} 공식 홈페이지</a>에서 직접 확인하십시오. 홈페이지는 학교 정보 확인용 외부 출처이며 EduNext가 학교를 대표하거나 학교와 제휴했다는 뜻이 아닙니다. {escape(place)} 표기는 지역 매핑을 위한 범위일 뿐 통학 시간이나 배정을 보장하지 않습니다.</p>
<p>{escape(context.slug)}의 수학 풀이와 오답 복원은 <a href="/{escape(context.math_slug)}/">{escape(context.math_slug)}</a>, 영어 지문·어휘·서술형 점검은 <a href="/{escape(context.english_slug)}/">{escape(context.english_slug)}</a>에서 과목별로 확인할 수 있습니다. 학교 한 곳을 넘어 생활권 전체 과외 정보를 보려면 <a href="/{escape(context.region_slug)}/">{escape(context.region_slug)}</a>로 이동합니다. 본문 링크는 이 세 탐색 목적과 공식 홈페이지에만 제한해 키워드 나열을 피했습니다.</p>
<p>{escape(context.official_name)}의 최신 자료와 학생이 실제로 받은 안내가 다르면 현재 학교 자료를 먼저 확인합니다. {_topic(source_focus)} 학교 정보를 추정하는 문구가 아니라, 확인된 자료를 바탕으로 {escape(_object(focus))} 적용하는 {escape(context.slug)}의 고유한 점검 소재입니다.</p>
</section>"""


def _faq_section(context: SchoolGeneralContext, source_body: str) -> str:
    details = _source_details(source_body, context)
    profile = _profile(context)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    primary = f"{profile['label']}·{theme['label']}·{method['label']}"
    questions = (
        (
            f"{context.slug}에서는 학습 계획을 무엇부터 확인하나요?",
            f"{context.official_name}의 실제 공지·시간표·과제 안내를 먼저 모은 뒤 {_object(theme['evidence'])} 만드십시오. {method['start']}. 처음부터 학습량을 늘리기보다 학생이 어느 시간과 과목에서 시작을 미루는지 남기고, 일주일 뒤 같은 행동을 혼자 반복하는지 확인해야 {context.slug}의 출발점이 구체적으로 보입니다.",
        ),
        (
            f"{context.slug}에서 학교 홈페이지는 왜 확인해야 하나요?",
            f"{context.official_name}의 시험일·행사·교육과정과 평가 안내는 시기에 따라 바뀔 수 있기 때문입니다. EduNext 본문은 확정된 학교 일정을 대신하지 않으므로 공식 홈페이지와 학생이 받은 안내를 대조해야 합니다. 확인 뒤에는 {method['record']}. 이렇게 해야 {context.slug} 계획이 추정 정보가 아니라 현재 자료를 기준으로 움직입니다.",
        ),
        (
            f"{context.slug}에서 내신·수행평가·모의고사를 함께 관리할 수 있나요?",
            f"역할을 나누면 함께 유지할 수 있습니다. 시험 전에는 {context.official_name}에서 실제로 사용하는 교과서와 학교 자료, 수행평가 마감을 우선하고 모의고사는 판단 감각을 유지하는 짧은 범위로 둡니다. 시험 뒤에는 {theme['action']}을 적용해 {details['source_focus']}에서 확인한 행동이 다른 과목과 낯선 조건에서도 재현되는지 점검합니다.",
        ),
        (
            f"{_object(context.slug)} 비교할 때 무엇을 질문해야 하나요?",
            f"교재와 숙제량보다 {_object(theme['problem'])} 어떤 학습 증거로 구분할지 물어보십시오. 수업 뒤 학생이 혼자 할 행동, 기록을 다시 보는 날짜, 계획이 실패했을 때 바꿀 기준까지 답에 포함되어야 합니다. {method['review']}. 이 과정이 설명되지 않으면 {context.slug} 학생에게 맞는 방식인지 판단하기 어렵습니다.",
        ),
        (
            f"학부모는 {context.slug} 진행을 어떻게 확인하면 좋나요?",
            f"점수 예상이나 공부 시간을 매일 묻기보다 주 1회 시작 시각, 반복 미완료, 설명 가능한 결과를 확인하십시오. 정확한 주소나 불필요한 개인정보를 먼저 공유할 필요는 없습니다. {context.official_name}, 학년, 실제 귀가 시각, 최근 학교 자료와 {theme['output']}만으로 시작하고, {context.slug} 기록의 변화가 없으면 분량보다 진단 가설을 고칩니다.",
        ),
    )
    items = "\n".join(f"<h3>{escape(question)}</h3>\n<p>{escape(answer)}</p>" for question, answer in questions)
    return f"""
<section class="school-general-faq-section" data-faq-focus="{escape(primary)}">
<h2 class="school-general-faq">{escape(context.slug)} 종합 학습 FAQ</h2>
{items}
</section>"""


def build_school_general_body(slug: str, source_body: str = "") -> str:
    context = school_general_contexts()[slug]
    details = _source_details(source_body, context)
    source_focus = details["source_focus"]
    profile = _profile(context)
    theme = THEMES[context.theme_index]
    method = METHODS[context.method_index]
    primary = f"{profile['label']}·{theme['label']}·{method['label']}"
    intro = f"""
<section class="school-general-guide" data-content-version="school-general-individual-v1" data-school-general-focus="{escape(primary)}" data-official-school="{escape(context.official_name)}">
<h2>{escape(context.slug)}: {escape(context.official_name)} 종합 학습의 고유 점검 주제</h2>
<p>{escape(context.slug)}는 <strong>{escape(_object(primary))}</strong> 중심으로 구성했습니다. 학교명을 검색한 사용자가 필요한 것은 확인되지 않은 출제 경향이나 성과 약속이 아니라, {escape(context.official_name)}의 최신 공식 자료와 학생이 가진 교과·평가 자료를 구분하고 실제 생활시간에 맞는 학습 순서를 정하는 일입니다. 이 페이지는 학교와 제휴하거나 학교를 대표하지 않으며 특정 학생의 결과를 보장하지 않습니다.</p>
<p>{escape(details['basic'])} {escape(details['stats'])} {escape(details['grades'])} 이 교육통계는 학교 규모를 이해하는 참고자료일 뿐 학생 개인의 성취나 학교의 우수성을 판단하는 근거가 아닙니다.</p>
<p>{escape(context.official_name)} 학생의 계획은 같은 학교 안에서도 학년·선택과목·귀가 시각·현재 이해도에 따라 달라집니다. {escape(context.slug)}에서는 {_object(source_focus)} 하나의 출발 소재로 두고 국어·영어·수학·탐구, 내신·수행평가·모의고사를 서로 다른 역할로 나누어 설명합니다.</p>
"""
    sections: list[str] = []
    for index, label in enumerate(SECTION_PURPOSES):
        if index == 1:
            sections.append(_profile_section(context, index, source_focus))
        elif index == 2:
            sections.append(_grade_section(context, index, source_focus))
        elif index == 3:
            sections.append(_subject_section(context, index, source_focus))
        elif index == 5:
            sections.append(_schedule_section(context, index, source_focus))
        elif index == 7:
            sections.append(_case_section(context, index, source_focus))
        elif index == 8:
            sections.append(_decision_section(context, index, source_focus))
        elif index == 9:
            sections.append(_tracker_section(context, index, source_focus))
        elif index == 10:
            sections.append(_links_section(context, index, source_focus))
        else:
            sections.append(_standard_section(context, index, label, source_focus))
    return intro + "\n".join(sections) + "\n" + _faq_section(context, source_body) + "\n</section>"


def individualize_school_general_body(body: str, slug: str) -> str:
    if not is_school_general_slug(slug):
        return body
    return build_school_general_body(slug, body)
