from __future__ import annotations

from config import GRADE_CATEGORIES, SUBJECT_CATEGORIES, SUBJECT_GRADE_CATEGORIES
from sitegen.models import Page
from sitegen.utils import escape


def fallback_content(page: Page) -> str:
    name = page.title
    if page.category == "과외":
        blocks = [
            ("지역 학습 환경", f"{name}를 찾을 때는 학생의 통학 동선, 학교 수업 흐름, 가정 학습 시간이 함께 이어지는지 살펴보는 것이 중요합니다."),
            ("내신과 시험 준비", "정기고사와 수행평가 일정은 학년마다 다르게 움직이므로, 주간 계획 안에서 교과서 확인과 문제 적용 시간을 분리해 두는 편이 안정적입니다."),
            ("학습 습관 점검", "수업 횟수보다 중요한 기준은 학생이 혼자 복습할 수 있는 단위가 남는지, 오답 이유를 말로 설명할 수 있는지입니다."),
        ]
    elif page.category in SUBJECT_CATEGORIES:
        subject = page.category.replace("과외", "")
        blocks = [
            (f"{subject} 학습 단계", f"{name}는 개념 확인, 예제 적용, 학교 시험형 문제 풀이가 순서대로 연결될 때 학습 부담이 줄어듭니다."),
            ("오답 관리", "틀린 문제를 다시 푸는 것에서 멈추지 않고 왜 그 선택을 했는지 기록해야 다음 단원의 이해도가 안정됩니다."),
            ("학년별 차이", "초등은 습관, 중등은 내신 구조, 고등은 범위 관리와 심화 적용이 핵심 기준이 됩니다."),
        ]
    elif page.category in GRADE_CATEGORIES:
        grade = page.category.replace("과외", "")
        blocks = [
            (f"{grade} 시기 변화", f"{name}는 학교 수업 난도와 생활 리듬이 바뀌는 시점을 함께 보며 계획해야 합니다."),
            ("학교 수업 연결", "예습보다 먼저 확인할 부분은 수업 시간에 놓친 개념과 과제 수행 과정에서 반복되는 실수입니다."),
            ("과목 우선순위", "영어와 수학은 매일 짧게라도 확인할 항목을 정해 두면 시험 직전 부담이 크게 줄어듭니다."),
        ]
    elif page.category in SUBJECT_GRADE_CATEGORIES:
        blocks = [
            ("개념과 적용", f"{name}는 학년 특성에 맞춰 개념 설명과 문제 적용의 간격을 좁히는 방식이 필요합니다."),
            ("시험 대비", "학교 시험 범위가 공개되면 단원별 약점을 먼저 표시하고, 풀이 속도보다 정확한 근거 확인을 우선합니다."),
            ("복습 기준", "수업 후에는 새 문제를 많이 푸는 것보다 틀린 문제의 조건을 다시 읽는 시간이 필요합니다."),
        ]
    else:
        blocks = [
            ("학습 기준", f"{name}는 학생의 현재 이해도와 학교 생활 흐름을 함께 살펴볼 때 현실적인 계획을 세울 수 있습니다."),
            ("점검 항목", "수업 내용, 복습 시간, 오답 기록, 다음 시험 범위를 한 화면에서 확인하는 습관이 중요합니다."),
        ]
    blocks.extend(
        [
            ("학부모 확인 기준", "상담 전에는 현재 성적만 보지 말고 숙제 수행 방식, 질문 빈도, 시험 전 불안 요인, 주중 복습 가능 시간을 함께 확인하는 편이 좋습니다."),
            ("수업 후 복습 흐름", "수업이 끝난 뒤에는 배운 내용을 다시 설명하기, 대표 문제 한 번 더 풀기, 다음 수업 전 질문 적기처럼 짧고 반복 가능한 절차가 필요합니다."),
            ("관련 허브 활용", "지역 허브와 과목·학년 허브를 함께 살펴보면 같은 생활권 안에서도 학생에게 필요한 수업 기준을 더 구체적으로 비교할 수 있습니다."),
        ]
    )
    return "".join(f"<h2>{escape(h)}</h2><p>{escape(p)}</p>" for h, p in blocks)


def school_intro(slug: str) -> str:
    return (
        f"<h2>{escape(slug)} 학교별 학습 점검</h2>"
        "<p>학교 페이지는 엑셀에 확인된 학교 키워드와 본문이 있을 때만 생성합니다. "
        "내신 범위, 수행평가 일정, 모의고사 복습 흐름을 함께 확인하는 데 초점을 둡니다.</p>"
    )
