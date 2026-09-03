from __future__ import annotations

import hashlib
import re
from html import unescape

from sitegen.local_elementary_math import ELEMENTARY_SCHOOL_CONTEXT, ELEMENTARY_SCHOOL_SOURCE
from sitegen.utils import escape


LOCAL_ELEMENTARY_GENERAL_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)초등과외$")
CONTENT_VERSION = "elementary-general-individual-v1"


def _plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _stable_index(slug: str, salt: str = "") -> int:
    return int(hashlib.sha256(f"{slug}|{salt}".encode("utf-8")).hexdigest()[:12], 16)


def _pick(items: tuple[str, ...], slug: str, salt: str = "") -> str:
    return items[_stable_index(slug, salt) % len(items)]


def _has_final(value: str) -> bool:
    if not value:
        return False
    code = ord(value[-1])
    return 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0


def _suffix(value: str, final_form: str, open_form: str) -> str:
    return f"{value}{final_form if _has_final(value) else open_form}"


def _obj(value: str) -> str:
    return _suffix(value, "을", "를")


def _topic(value: str) -> str:
    return _suffix(value, "은", "는")


def _subject(value: str) -> str:
    return _suffix(value, "이", "가")


def is_local_elementary_general_slug(slug: str) -> bool:
    return bool(LOCAL_ELEMENTARY_GENERAL_PATTERN.fullmatch(slug))


STUDY_PACKS: tuple[dict[str, object], ...] = (
    {
        "name": "읽기 근거와 문해력",
        "focuses": (
            "질문과 근거를 잇는 읽기", "문단의 중심을 자기 말로 복원하기", "낯선 어휘를 문맥에서 추론하기",
            "정보글의 구조를 표로 바꾸기", "이야기의 원인과 결과를 구분하기", "교과서 지시문을 정확히 읽기",
            "읽은 내용을 짧은 글로 설명하기", "독서와 교과 문해력을 함께 점검하기",
        ),
        "signal": "답을 말하기 전에 어느 문장과 표현에서 판단했는지 가리키고, 같은 내용을 다른 말로 다시 설명하는지",
        "korean": "국어에서는 문단마다 핵심 문장과 뒷받침 근거를 다른 색으로 표시하고 제목을 새로 붙입니다.",
        "math": "수학에서는 문장제의 질문과 조건을 먼저 나눈 뒤 각 숫자가 뜻하는 양과 단위를 말합니다.",
        "english": "영어에서는 아는 낱말과 그림, 문장 순서를 이용해 뜻을 예상한 뒤 소리와 철자를 다시 확인합니다.",
        "lower": "1~2학년은 짧은 글을 읽고 인물·장소·행동을 그림과 한 문장으로 연결합니다.",
        "middle": "3~4학년은 설명글의 중심 문장과 예시를 나누고 질문의 답이 되는 근거를 직접 찾습니다.",
        "upper": "5~6학년은 여러 문단의 관계를 비교하며 사실, 해석, 자신의 의견을 다른 칸에 기록합니다.",
        "home": "읽은 쪽수보다 오늘 만든 질문 하나와 그 답을 뒷받침한 문장 하나를 부모에게 설명하게 합니다.",
        "transition": "중학교 과목별 교과서가 길어지기 전에 지시문, 핵심어, 근거 문장의 위치를 스스로 표시하는 습관으로 연결합니다.",
        "material": "교과서 한 쪽, 학생이 밑줄 친 첫 읽기 기록, 제목을 가린 짧은 정보글",
    },
    {
        "name": "쓰기와 설명의 순서",
        "focuses": (
            "생각을 세 문장으로 조직하기", "서술형 답의 조건을 빠짐없이 담기", "관찰한 사실과 느낌을 나누어 쓰기",
            "말한 내용을 문장으로 옮기기", "초안을 고친 이유까지 기록하기", "문장 사이 연결어를 정확히 선택하기",
            "풀이와 답을 문장으로 설명하기", "발표 전에 핵심어로 말의 순서를 세우기",
        ),
        "signal": "길게 쓰는 것보다 질문의 조건에 맞는 내용을 고르고, 초안에서 빠진 근거를 스스로 찾아 고치는지",
        "korean": "국어에서는 말하고 싶은 내용을 사실·이유·정리의 세 칸에 놓은 뒤 한 문단으로 이어 씁니다.",
        "math": "수학에서는 식을 세운 이유와 계산 뒤 확인한 내용을 짧은 문장으로 남겨 풀이의 빈칸을 찾습니다.",
        "english": "영어에서는 알고 있는 낱말로 짧은 문장을 먼저 완성하고 주어·동사·뜻이 맞는지 소리 내어 확인합니다.",
        "lower": "1~2학년은 그림을 보고 누가 무엇을 했는지 말한 뒤 한 문장으로 정확하게 옮깁니다.",
        "middle": "3~4학년은 문단마다 한 가지 중심 생각을 두고 이유나 예시가 연결되는지 점검합니다.",
        "upper": "5~6학년은 과제 조건표를 먼저 읽고 초안·수정·완성본에서 바뀐 이유를 표시합니다.",
        "home": "맞춤법을 바로 고쳐 주기 전에 아이가 가장 전하고 싶은 문장과 그 이유를 먼저 말하게 합니다.",
        "transition": "중학교 서술형과 수행평가에 대비해 분량보다 요구 조건, 근거, 수정 이유를 확인하는 순서를 유지합니다.",
        "material": "학생의 첫 초안, 과제 조건표, 고치기 전후 문장과 설명 녹음 메모",
    },
    {
        "name": "수와 관계의 설명",
        "focuses": (
            "연산 원리를 말로 설명하기", "문장제의 관계를 그림과 식으로 바꾸기", "분수와 소수의 기준량 확인하기",
            "도형의 성질을 조건으로 구분하기", "계산 실수의 첫 위치를 찾기", "표와 그래프의 단위를 정확히 읽기",
            "어림과 검산으로 답의 범위 확인하기", "여러 풀이의 공통 근거를 비교하기",
        ),
        "signal": "정답을 맞힌 뒤에도 어떤 관계와 단위를 사용했는지 설명하고 숫자가 바뀐 문제에서 같은 원리를 다시 선택하는지",
        "korean": "국어에서는 수학 문제의 질문과 조건을 자기 말로 바꾸어 읽고 필요한 정보에만 표시합니다.",
        "math": "수학에서는 말·그림·표·식을 오가며 각 표현이 같은 관계를 나타내는 이유를 설명합니다.",
        "english": "영어에서는 수, 시간, 비교 표현이 들어간 짧은 문장을 읽고 실제 양과 순서를 그림으로 확인합니다.",
        "lower": "1~2학년은 묶음과 수 모형으로 덧셈·뺄셈 장면을 만들고 계산의 뜻을 말합니다.",
        "middle": "3~4학년은 곱셈·나눗셈과 두 단계 문장제를 단위와 관계 중심으로 나누어 풉니다.",
        "upper": "5~6학년은 분수·소수·비율에서 기준량과 결과의 가능한 범위를 먼저 예상합니다.",
        "home": "문제 수를 늘리기 전에 처음 선택한 식, 막힌 줄, 고친 근거, 검산 방법을 한 칸씩 남깁니다.",
        "transition": "중학교 수학으로 넘어갈 때 연산 속도만 보지 않고 식의 의미와 조건을 문자로 설명하는 힘을 확인합니다.",
        "material": "학생 공책의 첫 풀이, 수 모형이나 막대그림, 단위를 표시한 문장제와 검산 기록",
    },
    {
        "name": "영어 소리와 의미 연결",
        "focuses": (
            "들은 낱말을 문장 뜻으로 연결하기", "파닉스 이후 문장 읽기로 넘어가기", "짧은 영어 문장을 자기 말로 바꾸기",
            "그림과 문맥으로 낯선 표현 추론하기", "소리·철자·뜻을 함께 회상하기", "영어 질문에 완전한 문장으로 답하기",
            "반복 듣기보다 놓친 구간을 구분하기", "교과 영어와 생활 표현을 이어 쓰기",
        ),
        "signal": "외운 단어를 말하는 데서 멈추지 않고 짧은 문장에서 소리와 뜻을 찾고 다른 장면에 표현을 바꾸어 사용하는지",
        "korean": "국어에서는 영어 문장의 뜻을 자연스러운 한국어로 설명하고 핵심 정보가 빠지지 않았는지 확인합니다.",
        "math": "수학에서는 수와 도형, 위치를 나타내는 기초 영어 표현을 실제 그림과 대응하며 관계를 봅니다.",
        "english": "영어에서는 첫 듣기에서 알아들은 내용, 놓친 소리, 뜻을 잘못 고른 표현을 서로 다른 표시로 남깁니다.",
        "lower": "1~2학년은 소리와 그림, 짧은 행동 문장을 연결해 영어 활동의 시작과 끝을 익힙니다.",
        "middle": "3~4학년은 문장 속 아는 표현을 단서로 의미를 예상하고 질문과 답을 한 쌍으로 말합니다.",
        "upper": "5~6학년은 짧은 글의 중심 내용과 세부 정보를 나누고 근거 문장을 다시 읽습니다.",
        "home": "단어 시험 점수보다 새 문장에서 뜻을 고른 근거와 들리지 않은 소리를 어떻게 확인했는지 묻습니다.",
        "transition": "중학교 영어의 어휘·문법량이 늘기 전에 문장을 읽고 듣고 다시 말하는 독립 복습 순서를 만듭니다.",
        "material": "학교 영어 자료, 첫 듣기 표시, 그림이 있는 짧은 글과 학생이 직접 만든 예문",
    },
    {
        "name": "자기주도 시작과 마무리",
        "focuses": (
            "공부 시작 신호를 스스로 만들기", "과제를 작은 완료 행동으로 나누기", "계획이 어긋난 이유를 다시 정리하기",
            "도움받을 지점을 정확히 말하기", "숙제와 복습의 역할을 구분하기", "학습 준비물을 혼자 점검하기",
            "짧은 공부를 매일 다시 시작하기", "완료량보다 다음 행동을 기록하기",
        ),
        "signal": "보호자의 반복 지시 없이 사용할 자료와 끝낼 행동을 말하고, 멈춘 뒤 다음 시작점을 남기는지",
        "korean": "국어에서는 읽기와 쓰기의 종료 기준을 ‘문단 하나 설명하기’처럼 눈에 보이는 행동으로 정합니다.",
        "math": "수학에서는 문제 수 대신 예제 설명, 기본 적용, 오류 한 줄 수정으로 과제의 목적을 나눕니다.",
        "english": "영어에서는 단어 보기, 문장 회상, 짧은 듣기를 다른 과제로 구분해 피로도에 맞게 배치합니다.",
        "lower": "1~2학년은 가방 정리 뒤 교재를 꺼내고 한 활동을 끝내는 고정 순서를 반복합니다.",
        "middle": "3~4학년은 오늘 할 일 두 가지를 직접 고르고 예상 시간과 실제 시간을 비교합니다.",
        "upper": "5~6학년은 마감·중요도·도움 필요 여부에 따라 과제를 나누고 남은 일을 다시 배치합니다.",
        "home": "부모는 시작을 재촉하기보다 어떤 자료로 무엇을 끝낼 것인지 아이가 한 문장으로 말하게 합니다.",
        "transition": "중학교의 과목별 과제와 수행평가가 겹치기 전에 마감과 복습을 분리하는 계획 언어를 연습합니다.",
        "material": "일주일 시작 시각 기록, 학교 과제 목록, 학생이 고른 완료 기준과 다음 시작 메모",
    },
    {
        "name": "학교 적응과 학습 감정",
        "focuses": (
            "어려운 과제 앞에서 다시 시작하기", "실수를 숨기지 않고 도움 요청하기", "새 학년의 학습 리듬 만들기",
            "발표와 평가 불안을 작은 행동으로 나누기", "친숙한 문제에서 낯선 문제로 옮겨가기", "틀린 답을 학습 자료로 사용하는 태도",
            "잘하는 과목의 전략을 다른 과목에 옮기기", "과제 회피와 이해 부족을 구분하기",
        ),
        "signal": "어려움을 만났을 때 멈춘 이유를 말하고 혼자 할 부분, 질문할 부분, 다시 시도할 시점을 나누는지",
        "korean": "국어에서는 이해되지 않은 문장에 표시하고 모르는 점을 구체적인 질문으로 바꾸어 말합니다.",
        "math": "수학에서는 틀린 풀이를 지우기 전에 맞는 줄과 달라진 줄을 분리해 실수와 개념 공백을 구분합니다.",
        "english": "영어에서는 들리지 않음, 뜻을 모름, 말하기가 부담됨을 같은 어려움으로 묶지 않고 각각 기록합니다.",
        "lower": "1~2학년은 도움을 요청할 수 있는 짧은 문장과 활동을 다시 시작하는 신호를 익힙니다.",
        "middle": "3~4학년은 성공한 방법과 막힌 방법을 비교하고 다음 시도에서 바꿀 한 가지를 고릅니다.",
        "upper": "5~6학년은 평가 결과와 학습 감정을 분리해 오류 원인과 재시도 날짜를 직접 적습니다.",
        "home": "점수를 묻기 전에 가장 어려웠던 순간, 사용한 도움, 다음에 혼자 해 볼 첫 행동을 차례로 듣습니다.",
        "transition": "중학교의 평가 횟수가 늘어도 한 번의 결과로 능력을 단정하지 않고 오류와 감정을 다른 기록으로 남깁니다.",
        "material": "학생의 수정 전 과제, 도움 요청 메모, 다시 시도한 날짜와 성공 조건을 적은 짧은 기록",
    },
    {
        "name": "고학년 전환과 중학교 준비",
        "focuses": (
            "고학년 누적 공백을 찾아 보완하기", "교과별 공부 방법을 스스로 구분하기", "중학교 전 과제 관리 언어 익히기",
            "선행보다 현재 학년 설명력을 확인하기", "긴 글과 여러 단계 문제를 끝까지 따라가기", "평가 범위와 복습 우선순위를 정하기",
            "교재가 달라도 유지할 학습 기준 만들기", "초등 학습 기록을 중학교 계획으로 옮기기",
        ),
        "signal": "현재 학년의 핵심 개념을 설명하고 과목에 따라 읽기·풀이·암기·재시도 방법을 다르게 선택하는지",
        "korean": "국어에서는 긴 지시문을 과제 조건으로 나누고 여러 자료의 공통점과 차이를 근거로 말합니다.",
        "math": "수학에서는 5·6학년 분수·비율·도형 개념을 식과 문장으로 설명해 중학교 선수 개념의 공백을 찾습니다.",
        "english": "영어에서는 단어 암기와 문장 이해, 듣기와 쓰기의 목적을 나누어 일주일 복습 순서를 정합니다.",
        "lower": "1~2학년은 먼 선행보다 읽고 말하고 정리하는 기본 행동을 안정적으로 반복합니다.",
        "middle": "3~4학년은 과목별 공책 사용과 오답 설명을 시작해 자신의 공부 흔적을 남깁니다.",
        "upper": "5~6학년은 현재 학년의 공백과 다음 단계의 새 개념을 구분해 한꺼번에 진도를 늘리지 않습니다.",
        "home": "중학교 문제집을 먼저 고르기보다 아이가 현재 교과서 내용을 자료 없이 어디까지 설명하는지 확인합니다.",
        "transition": "진학 직전에는 선행 진도보다 과목별 자료 선택, 마감 확인, 질문 작성, 간격 복습을 혼자 수행하는지 봅니다.",
        "material": "5·6학년 교과서와 공책, 최근 평가 원본, 과목별 과제표와 간격을 둔 재설명 기록",
    },
    {
        "name": "집중과 실행 기능",
        "focuses": (
            "집중이 끊기는 정확한 지점 찾기", "읽기 전에 문제 조건을 끝까지 확인하기", "여러 단계 과제를 순서대로 수행하기",
            "학습 도구를 바꾸며 집중을 회복하기", "시간 감각과 실제 소요 시간을 비교하기", "작업 기억의 부담을 기록으로 줄이기",
            "충동적인 답보다 확인 순서를 세우기", "긴 과제를 작은 단위로 다시 시작하기",
        ),
        "signal": "오래 앉아 있는 시간보다 어느 활동에서 흐름이 끊겼고 어떤 표시나 도구로 다시 시작했는지 설명하는지",
        "korean": "국어에서는 읽을 범위와 찾을 정보를 먼저 표시해 문단을 건너뛰거나 질문을 놓치는 일을 줄입니다.",
        "math": "수학에서는 문제를 읽자마자 계산하지 않고 질문·조건·단위·검산의 순서를 눈에 보이게 둡니다.",
        "english": "영어에서는 소리 듣기, 문장 읽기, 쓰기 활동을 짧게 전환하며 각 활동의 종료 기준을 분명히 합니다.",
        "lower": "1~2학년은 한 번에 한 가지 도구만 꺼내고 시작과 정리 행동을 같은 순서로 반복합니다.",
        "middle": "3~4학년은 두 단계 지시를 체크 칸으로 나누고 끝낸 뒤 빠진 행동을 스스로 찾습니다.",
        "upper": "5~6학년은 예상 시간과 실제 시간을 비교해 과제 분량과 휴식 시점을 직접 조정합니다.",
        "home": "집중하지 않았다고 평가하기 전에 멈춘 시각, 직전 행동, 다시 시작한 도움을 짧게 기록합니다.",
        "transition": "중학교 시간표에 대비해 과목을 바꿀 때 필요한 준비와 이전 과제의 마무리를 분리합니다.",
        "material": "시작·중단·재시작 시각표, 단계별 체크 칸, 학생이 고른 최소 완료 행동",
    },
    {
        "name": "탐구와 교과 연결",
        "focuses": (
            "관찰한 사실에서 질문 만들기", "사회·과학 자료의 근거를 비교하기", "일상 경험을 교과 개념으로 설명하기",
            "표와 사진에서 말할 수 있는 범위 구분하기", "예상과 결과가 다른 이유 기록하기", "여러 자료를 한 주제로 묶어 발표하기",
            "실험 절차와 결과를 순서대로 쓰기", "교과 지식을 새로운 장면에 적용하기",
        ),
        "signal": "정답을 외우기보다 관찰, 예상, 자료, 결론을 구분하고 결론보다 강한 표현을 사용하지 않는지",
        "korean": "국어에서는 자료의 출처와 핵심 내용을 확인하고 사실과 자신의 해석을 다른 문장으로 씁니다.",
        "math": "수학에서는 조사한 값을 표와 그래프로 바꾸고 축·단위·전체 수가 맞는지 검산합니다.",
        "english": "영어에서는 탐구 주제의 핵심 낱말을 짧은 문장에 사용하고 그림이나 행동으로 뜻을 설명합니다.",
        "lower": "1~2학년은 보고 들은 사실을 순서대로 말하고 궁금한 점 하나를 질문으로 남깁니다.",
        "middle": "3~4학년은 예상과 관찰 결과를 표에 나누고 달라진 이유를 자료에서 찾습니다.",
        "upper": "5~6학년은 서로 다른 자료의 출처와 범위를 확인하며 결론을 근거보다 크게 말하지 않습니다.",
        "home": "완성품의 모양보다 어떤 질문으로 시작했고 예상과 결과 사이에서 무엇을 바꾸었는지 묻습니다.",
        "transition": "중학교 수행평가에 대비해 자료 출처, 역할 분담, 과정 기록, 발표 근거를 한 흐름으로 정리합니다.",
        "material": "사회·과학 교과 자료, 관찰 메모, 예상과 결과를 나눈 표, 출처를 적은 사진이나 그래프",
    },
)


def _parts(slug: str) -> tuple[str, str, str]:
    location = slug.removesuffix("초등과외")
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    return location, city, location.removeprefix(city)


def _pack_and_focus(slug: str) -> tuple[dict[str, object], str]:
    pack = STUDY_PACKS[_stable_index(slug, "pack") % len(STUDY_PACKS)]
    focuses = pack["focuses"]
    assert isinstance(focuses, tuple)
    base = str(_pick(focuses, slug, "focus"))
    qualifier = _pick(
        (
            "첫 기록", "주간 점검", "도움 줄이기", "간격 복습", "교과 전이", "과제 선택", "부모 질문",
            "학교 자료", "오류 분류", "설명 연습", "생활 리듬", "중학교 연결", "자기 점검", "학년군 비교",
        ),
        slug,
        "qualifier",
    )
    lens = _pick(
        (
            "시작 행동", "근거 문장", "완료 기준", "다음 질문", "독립 재현", "표현 전환", "수정 이유",
            "예상 시간", "학교 공책", "재시도 날짜", "과목 연결", "학부모 관찰", "학생 설명", "자료 선택",
        ),
        slug,
        "lens",
    )
    return pack, f"{base}·{qualifier}·{lens}"


def build_local_elementary_general_meta(slug: str, body: str = "") -> tuple[str, str]:
    del body
    pack, focus = _pack_and_focus(slug)
    location, _, _ = _parts(slug)
    pack_name = str(pack["name"])
    title = _pick(
        (
            f"{slug} | {focus} 학년별 학습 설계",
            f"{slug} | {focus} 가정학습 점검법",
            f"{slug} | {pack_name} 중심 초등 학습 계획",
            f"{slug} | {focus} 학교생활 연결 기준",
        ),
        slug,
        "meta-title",
    )
    if len(title) > 60:
        title = f"{slug} | {pack_name}·{_pick(('학년별 계획','가정 점검','학교 연결','주간 복습'), slug, 'short-title')}"
    description = _pick(
        (
            f"{slug}에서 {focus} 과정을 저·중·고학년으로 나누어 살펴봅니다. {location} 초등학교 공식 정보와 학생 기록, 국어·수학·영어 학습, 합성 사례와 부모 점검 질문을 정리했습니다.",
            f"{location} 초등학생의 {focus} 학습 기준입니다. 1~6학년 단계, 2025년 학교 자료, 교과별 첫 행동, 주간 재시도와 중학교 전환 준비를 구체적으로 안내합니다.",
            f"{slug} 검색 뒤 확인할 {pack_name} 계획을 담았습니다. 학교 공식 홈페이지, 학년군별 진단, 국어·수학·영어 연결, 가정 피드백과 다음 행동을 한 페이지에서 확인하세요.",
        ),
        slug,
        "meta-description",
    )
    return title, description


def _opening(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location}초등과외에서 {_obj(focus)} 먼저 기록하는 이유",
            f"학년보다 학습 행동을 먼저 보는 {location}의 {focus}",
            f"{location} 초등학생의 {_obj(focus)} 실제 자료로 구분하기",
            f"학교생활에서 출발하는 {location} {focus} 계획",
        ),
        slug,
        "opening-heading",
    )
    paragraph = _pick(
        (
            f"{location}이라는 지역명만으로 초등학생의 학년 진도나 학습 성향을 단정할 수는 없습니다. 이 페이지는 {focus} 과정을 고유한 점검 주제로 삼아 {pack['material']}에서 시작 행동과 설명, 도움 뒤의 독립 재현을 비교합니다. 같은 교재를 사용해도 막힌 이유가 다르므로 먼저 관찰할 증거를 정하고 한 주에 바꿀 행동 하나만 선택합니다.",
            f"{_topic(focus)} 문제집의 권수나 앉아 있던 시간으로 확인하기 어렵습니다. {location} 학생이 {pack['signal']}를 학교 공책과 가정 기록에서 살핀 뒤 저학년·중학년·고학년의 다음 행동을 다르게 정해야 합니다. 아래 내용은 특정 학생의 성취를 약속하지 않으며 실제 자료를 읽는 교육용 기준입니다.",
            f"{location}초등과외를 검색했다면 수업 횟수보다 학생이 혼자 시작할 수 있는 행동과 도움을 요청하는 문장을 먼저 확인할 필요가 있습니다. 여기서는 {focus} 과정을 국어·수학·영어, 학교 일정, 가정 피드백과 연결하고 며칠 뒤 같은 판단을 다시 수행하는지까지 살펴봅니다.",
        ),
        slug,
        "opening-paragraph",
    )
    return (
        f'<section class="elementary-general-block elementary-general-opening" data-content-version="{CONTENT_VERSION}" '
        f'data-elementary-general-focus="{escape(focus)}"><h2>{escape(heading)}</h2><p>{escape(paragraph)}</p></section>'
    )


def _search_intent(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location}초등과외 검색 뒤 {_obj(focus)} 세 가지 자료로 확인하기",
            f"수업 소개보다 먼저 비교할 {location} {focus} 기록",
            f"{location}에서 {_obj(focus)} 상담 질문으로 바꾸는 순서",
        ),
        slug,
        "search-heading",
    )
    school_material = _pick(
        (
            "최근 교과서와 공책, 과제 안내", "이번 주 수업 원본과 학생 필기", "학교에서 사용한 활동지와 교과서",
            "최근 단원 공책과 제출 과제", "정규 수업 뒤 남은 필기와 알림장", "교과서 예제와 학생의 첫 답안",
            "학교 진도표와 최근 공책 한 쪽", "수정 흔적이 남은 교과 활동지",
        ),
        slug,
        "search-school-material",
    )
    school_check = _pick(
        (
            "배운 범위와 자료 없이 복원 가능한 범위를 따로 봅니다.", "교사가 제시한 내용과 학생이 독립적으로 수행한 부분을 나눕니다.",
            "진도량보다 아이가 근거를 설명한 마지막 지점을 찾습니다.", "완료 표시와 실제 이해가 일치하는지 첫 기록으로 대조합니다.",
            "수업에서 다룬 개념과 집에서 질문이 필요한 대목을 구별합니다.", "학교 원본에서 혼자 읽고 시작한 첫 단계를 표시합니다.",
            "정답 수보다 처음 선택한 표현과 막힌 위치를 확인합니다.", "제출 여부와 별개로 다음 날 다시 설명한 범위를 봅니다.",
        ),
        slug,
        "search-school-check",
    )
    gap_material = _pick(
        (
            "도움 직후와 2~4일 뒤의 재시도", "설명을 들은 날과 다음 확인일의 기록", "첫 수행과 시간을 둔 후속 문제",
            "힌트가 있던 답안과 도움 없는 복원", "당일 설명과 주말의 독립 수행", "수정 직후 자료와 사흘 뒤 새 자료",
            "처음 질문한 날과 다음 재현 날짜", "부모 도움 전후와 간격 복습 기록",
        ),
        slug,
        "search-gap-material",
    )
    gap_check = _pick(
        (
            "기억한 답보다 다시 선택한 판단 순서를 확인합니다.", "같은 힌트를 기다리지 않고 첫 단계를 복원하는지 봅니다.",
            "표현이 달라도 유지된 개념과 이유를 대조합니다.", "도움이 줄어도 질문과 완료 기준이 남는지 살핍니다.",
            "새 조건에서 스스로 바꾼 전략과 그 이유를 기록합니다.", "원본을 가린 뒤 자료 선택부터 다시 수행하는지 봅니다.",
            "시간이 지나도 남은 설명과 사라진 단계를 나눕니다.", "다른 과목에서도 같은 학습 행동을 꺼내 쓰는지 확인합니다.",
        ),
        slug,
        "search-gap-check",
    )
    rows = (
        ("학교 원본", school_material, school_check),
        ("학생 행동", f"{pack['material']}와 {location} 학생의 첫 기록", f"{focus} 과정에서 {pack['signal']}"),
        ("간격 확인", gap_material, gap_check),
    )
    table_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{escape(material)}</td><td>{escape(check)}</td></tr>"
        for name, material, check in rows
    )
    step_pool = (
        f"최근 학교 자료에서 {focus} 과정이 드러나는 한 쪽을 고릅니다.",
        "정답과 지운 흔적을 가리지 않고 도움 전 첫 행동을 그대로 남깁니다.",
        "학생이 막힌 이유를 읽기·개념·표현·시간·도움 요청 가운데 하나로 말하게 합니다.",
        "한 행동만 바꾸고 날짜를 정해 같은 기준으로 다시 관찰합니다.",
        f"{location} 학생이 직접 선택한 자료와 부모가 권한 자료를 다른 칸에 적습니다.",
        "공부시간 대신 시작까지 걸린 시간과 질문이 나온 정확한 위치를 표시합니다.",
        "학교에서 끝낸 활동과 집에서 다시 설명할 활동의 목적을 한 줄씩 씁니다.",
        "답을 보기 전 예상, 도움을 받은 문장, 도움 뒤 혼자 이어 간 단계를 보존합니다.",
        "저학년은 말과 그림, 중학년은 표와 문장, 고학년은 조건과 근거 중 두 표현을 고릅니다.",
        "같은 날 여러 원인을 바꾸지 않고 자료·시간·도움 가운데 한 조건만 조정합니다.",
        "이틀 이상 지난 뒤 원본을 덮고 다음 시작 행동을 학생의 말로 복원합니다.",
        f"{focus} 기록을 국어·수학·영어 가운데 다른 한 과목에도 짧게 적용합니다.",
    )
    start = _stable_index(slug, "search-step-start") % len(step_pool)
    stride = (5, 7)[_stable_index(slug, "search-step-stride") % 2]
    steps = tuple(step_pool[(start + stride * index) % len(step_pool)] for index in range(4))
    intro = _pick(
        (
            "광고 문구보다 현재 자료와 학생의 설명을 먼저 놓으면 분량·설명·생활시간 중 어느 조건을 조정할지 구분하기 쉽습니다.",
            "수업 횟수를 정하기 전에 학교 원본, 도움 전 행동, 간격 뒤 복원을 한 줄씩 모으면 실제 시작점이 보입니다.",
            "좋다는 교재 목록보다 아이가 사용한 자료와 막힌 위치를 나란히 보면 상담 질문을 더 구체적으로 만들 수 있습니다.",
            "성적표만 보지 않고 첫 답안과 질문, 며칠 뒤 재수행을 함께 비교해야 한 주에 바꿀 행동을 좁힐 수 있습니다.",
            "지역명 검색 뒤에는 생활권을 추정하기보다 학교 자료와 가정 기록에서 확인 가능한 증거 세 가지를 먼저 준비합니다.",
            "교재 난도와 공부시간을 동시에 바꾸지 않고 자료·행동·간격의 세 기록을 같은 기준으로 읽습니다.",
        ),
        slug,
        "search-intro",
    )
    return (
        f'<section class="elementary-general-block elementary-general-search-intent" data-search-rows="3">'
        f"<h2>{escape(heading)}</h2><p>{escape(location)}에서 {_obj(escape(focus))} 살필 때 {escape(intro)} 아래 세 기록은 특정 수업의 효과를 보장하지 않고 현재 학습을 관찰하는 기준으로만 사용합니다.</p>"
        "<table><thead><tr><th>비교 자료</th><th>준비할 것</th><th>판단 기준</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table><ol>"
        + "".join(f"<li>{escape(step)}</li>" for step in steps)
        + "</ol></section>"
    )


def _grade_plan(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 계획을 세 학년군으로 나누기",
            f"같은 {focus}, 다른 시작점: {location} 1~6학년",
            f"{location}초등과외의 {_obj(focus)} 학년군별로 조정하기",
        ),
        slug,
        "grade-heading",
    )
    items = (
        (
            "1~2학년",
            str(pack["lower"]),
            (
                "짧게 시작하고 말·그림·행동 가운데 하나로 끝을 보여 줍니다.", "한 활동의 시작과 정리를 같은 순서로 반복해 예측 가능한 학습을 만듭니다.",
                "손으로 조작한 뒤 눈으로 보고 말한 내용을 한 줄 기록으로 옮깁니다.", "보호자의 설명보다 아이가 직접 고른 표현과 질문을 먼저 남깁니다.",
                "성공적으로 끝낸 짧은 활동 뒤에 새로운 조건 하나만 덧붙입니다.", "정답을 재촉하지 않고 무엇을 보고 첫 행동을 골랐는지 듣습니다.",
            ),
        ),
        (
            "3~4학년",
            str(pack["middle"]),
            (
                "표현을 두 가지로 바꾸고 선택한 이유를 한 문장으로 남깁니다.", "교과서 예와 숫자·문장·자료가 달라진 예를 나란히 비교합니다.",
                "질문·조건·설명의 세 칸을 사용해 빠진 정보를 스스로 찾습니다.", "처음 풀이와 수정 뒤 풀이를 보존하고 달라진 판단을 말합니다.",
                "학교 숙제와 별도 복습의 목적을 구분해 같은 활동을 겹치지 않습니다.", "혼자 가능한 단계와 힌트가 필요한 단계를 학생의 말로 나눕니다.",
            ),
        ),
        (
            "5~6학년",
            str(pack["upper"]),
            (
                "학교 진도와 누적 공백, 다음 단계 준비를 서로 다른 과제로 배치합니다.", "현재 학년 복원과 중학교 예고를 다른 날짜와 자료로 나누어 수행합니다.",
                "과목별 마감과 재시도 날짜를 적고 계획을 바꾼 이유까지 남깁니다.", "정답률뿐 아니라 근거 설명과 며칠 뒤 독립 재현을 함께 확인합니다.",
                "교재를 늘리기 전에 국어·수학·영어의 다른 복습 방법을 직접 선택합니다.", "평가 원본에서 반복된 오류와 오래 걸린 정답을 한 주 계획에 다시 놓습니다.",
            ),
        ),
    )
    closing_options = (
        "도움 없이 수행한 마지막 단계와 질문 뒤 혼자 이어 간 첫 단계를 함께 기록하면 다음 학년군의 과제를 서두르지 않을 수 있습니다.",
        "학생이 설명한 범위와 부모가 대신 말한 범위를 나누면 과제의 난도와 힌트를 더 정확히 조정할 수 있습니다.",
        "한 번의 성공보다 자료가 달라져도 유지된 시작 행동과 판단 기준을 다음 단계로 넘어가는 증거로 사용합니다.",
        "학년 이름보다 현재 행동을 기준으로 삼아 잘하는 부분은 유지하고 막힌 연결 하나만 후속 활동으로 옮깁니다.",
        "완료량이 적은 날에도 멈춘 이유와 다음 시작점을 남기면 계획 실패를 학습 기록으로 바꿀 수 있습니다.",
        "과제 범위는 혼자 설명하고 간격 뒤 다시 수행한 수준에서 넓히며 같은 힌트를 반복해서 기다리는지는 따로 봅니다.",
    )
    cards = "".join(
        f"<h3>{escape(location)} {escape(label)}의 {escape(focus)} 시작점</h3><p>{escape(detail)} "
        f"{escape(_pick(actions, slug, f'grade-action-{label}'))} {escape(location)}에서는 "
        f"{escape(_pick(closing_options, slug, f'grade-closing-{label}'))}</p>"
        for label, detail, actions in items
    )
    return (
        f'<section class="elementary-general-block elementary-general-grade" data-grade-groups="3"><h2>{escape(heading)}</h2>'
        f"<p>{escape(focus)} 학습은 학년명만으로 난도를 정하지 않습니다. 현재 교과서에서 혼자 설명 가능한 범위를 찾고 표현의 수와 도움의 양을 단계적으로 바꿉니다.</p>{cards}</section>"
    )


def _subjects(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"국어·수학·영어에서 다르게 보이는 {location} {focus}",
            f"{location}의 {_obj(focus)} 세 교과 행동으로 연결하기",
            f"과목별 자료로 나누어 보는 {location} {focus}",
        ),
        slug,
        "subjects-heading",
    )
    items = (("국어", pack["korean"]), ("수학", pack["math"]), ("영어", pack["english"]))
    tails = (
        "정답과 별개로 선택한 근거, 질문한 위치, 다음 날 다시 시작한 방법을 남겨 과목 사이에 옮길 행동을 찾습니다.",
        "첫 수행과 도움 뒤 수행을 나란히 두고 다른 교과에서도 유지할 판단 순서를 한 가지 고릅니다.",
        "자료가 바뀐 뒤에도 설명할 수 있는 내용과 새로 필요한 힌트를 서로 다른 칸에 적습니다.",
        "완료한 분량보다 혼자 시작한 단계와 수정 이유를 확인해 다음 교과 활동의 출발점으로 씁니다.",
        "학교 공책에서 막힌 대목을 질문으로 옮기고 며칠 뒤 같은 설명을 다시 꺼내 쓰는지 봅니다.",
        "표현 방법은 과목에 맞게 바꾸되 읽기·설명·확인의 세 행동이 어디까지 유지되는지 기록합니다.",
        "학생이 고른 자료와 부모가 권한 자료를 비교해 스스로 선택할 수 있는 범위를 조금씩 넓힙니다.",
        "맞힌 문제도 오래 걸렸거나 설명이 없었다면 다른 표현으로 바꾸어 이해의 깊이를 확인합니다.",
    )
    content = "".join(
        f"<h3>{escape(location)} {escape(subject)}에서 관찰할 {escape(focus)}</h3><p>{escape(str(detail))} "
        f"{escape(location)}에서는 {escape(_pick(tails, slug, f'subject-tail-{subject}'))}</p>"
        for subject, detail in items
    )
    return (
        f'<section class="elementary-general-block elementary-general-subjects" data-subject-count="3"><h2>{escape(heading)}</h2>'
        f"<p>{escape(focus)} 하나를 모든 과목에서 같은 문제로 해석하지 않습니다. 교과마다 사용 자료와 표현 방법은 다르지만 근거를 찾고 설명하고 다시 시도하는 순서는 연결할 수 있습니다.</p>{content}</section>"
    )


def _diagnosis(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 문제를 다섯 원인으로 가르는 진단표",
            f"과제량을 늘리기 전에 읽는 {location} {focus} 신호",
            f"{location} 학생의 {_obj(focus)} 행동 기록으로 구분하기",
        ),
        slug,
        "diagnosis-heading",
    )
    row_options = (
        (
            "읽기",
            ("질문이나 지시의 핵심 낱말을 놓침", "문장을 읽었지만 무엇을 구하는지 다시 말하지 못함", "자료의 순서와 조건을 건너뛰어 첫 선택이 달라짐", "낯선 표현에서 멈춘 뒤 뒷내용을 이어 읽지 못함"),
            ("질문을 자기 말로 바꾸고 근거 위치를 표시합니다.", "찾아야 할 정보와 주어진 조건을 두 칸에 나누어 적습니다.", "문단이나 문제를 짧게 끊고 각 부분의 역할을 말합니다.", "읽기 전 예상과 읽은 뒤 확인한 정보를 다른 색으로 남깁니다."),
        ),
        (
            "개념",
            ("설명은 들었지만 예시가 바뀌면 시작하지 못함", "용어는 기억하지만 왜 그런지 그림이나 말로 풀지 못함", "익숙한 문제는 풀어도 조건이 달라지면 같은 원리를 찾지 못함", "공식을 사용하지만 각 수와 표현의 뜻을 설명하지 못함"),
            ("핵심 개념을 말·그림·식 중 두 표현으로 바꿉니다.", "쉬운 예와 반대 예를 만들어 개념이 적용되는 경계를 확인합니다.", "조건 하나를 바꾼 뒤 유지되는 원리와 달라지는 절차를 나눕니다.", "교과서 예제를 가리고 개념의 시작 문장을 직접 복원합니다."),
        ),
        (
            "표현",
            ("알고 있으나 말이나 글, 풀이로 완성하지 못함", "답은 고르지만 선택 이유를 문장으로 이어 말하지 못함", "생각은 있으나 과제 조건에 맞는 형식으로 옮기지 못함", "초안에서 빠진 정보와 고칠 순서를 스스로 찾지 못함"),
            ("초안을 보존하고 빠진 조건만 한 번에 하나씩 고칩니다.", "말한 내용을 짧은 글이나 풀이로 옮긴 뒤 달라진 뜻을 봅니다.", "필수 조건표를 만들고 완성본에서 각 항목의 위치를 찾습니다.", "정답을 보기 전에 첫 표현과 막힌 표현을 나란히 둡니다."),
        ),
        (
            "실행",
            ("자료를 고르거나 시작·종료 기준을 정하지 못함", "해야 할 일을 알지만 준비와 시작 사이 시간이 길어짐", "한 활동이 끝난 뒤 다음 자료로 전환하지 못함", "예상 시간과 실제 시간이 달라도 계획을 그대로 옮김"),
            ("최소 완료 행동과 다음 시작점을 먼저 적습니다.", "준비물과 첫 동작을 한 줄로 정하고 시작 시각을 남깁니다.", "과제를 작은 마감으로 나누고 끝난 뒤 다음 자료를 직접 고릅니다.", "남은 분량을 옮기기 전에 시간·이해·준비 중 원인을 선택합니다."),
        ),
        (
            "감정",
            ("틀릴 가능성이 있으면 시도나 질문을 피함", "실수한 흔적을 지우고 어려웠던 대목을 말하지 않음", "낯선 과제 앞에서 잘하는 활동만 반복해 시간을 보냄", "평가 결과를 자신의 능력 전체로 받아들여 재시도를 미룸"),
            ("혼자 할 부분과 도움받을 부분을 분리해 성공 범위를 만듭니다.", "실수와 감정을 다른 칸에 적고 다시 시도할 첫 행동을 고릅니다.", "쉬운 시작점 뒤에 질문 한 개만 붙여 낯선 활동의 범위를 줄입니다.", "점수보다 요청한 도움과 다시 시작한 시점을 변화 증거로 봅니다."),
        ),
    )
    rows = tuple(
        (
            kind,
            _pick(signals, slug, f"diagnosis-signal-{kind}"),
            _pick(actions, slug, f"diagnosis-action-{kind}"),
        )
        for kind, signals, actions in row_options
    )
    body = "".join(
        f"<tr><td>{escape(kind)}</td><td>{escape(signal)}</td><td>{escape(action)}</td></tr>"
        for kind, signal, action in rows
    )
    return (
        f'<section class="elementary-general-block elementary-general-diagnosis" data-diagnosis-rows="5"><h2>{escape(heading)}</h2>'
        f"<p>{escape(location)} 학생에게 {_subject(escape(focus))} 어렵게 보이더라도 원인이 하나라고 단정하지 않습니다. {escape(str(pack['signal']))}를 기준으로 아래 신호를 나누고 가장 자주 반복된 한 행만 먼저 조정합니다.</p>"
        "<table><thead><tr><th>가능한 원인</th><th>첫 기록에서 보이는 신호</th><th>다음 수업의 확인 행동</th></tr></thead>"
        f"<tbody>{body}</tbody></table><p>이 표는 진단명이나 의학적 판단이 아닙니다. {escape(location)}의 실제 학교 자료와 생활 기록에서 학습 행동을 구체적으로 관찰하기 위한 교육용 분류입니다.</p></section>"
    )


def _weekly_plan(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 일주일을 다섯 번의 확인으로 설계하기",
            f"분량보다 목적을 바꾸는 {location} {focus} 주간표",
            f"{location}초등과외에서 {_obj(focus)} 평일과 주말로 나누기",
        ),
        slug,
        "weekly-heading",
    )
    phase_options = (
        (
            "학교 당일 복원",
            (
                "교과서와 공책을 덮고 오늘 배운 핵심을 3분 동안 말한 뒤 빠진 부분만 다시 엽니다.",
                "수업 직후 공책의 제목만 보고 핵심 개념과 예를 기억에서 복원한 다음 원본과 대조합니다.",
                "학교에서 사용한 자료를 가린 채 배운 순서와 질문 하나를 말하고 확인이 필요한 쪽을 표시합니다.",
                "귀가 후 교과서 한 쪽을 골라 읽지 않고 설명한 범위와 다시 봐야 할 범위를 두 칸에 나눕니다.",
                "오늘 배운 내용을 부모에게 가르치듯 말하고 설명이 끊긴 지점만 공책에서 찾아봅니다.",
                "학교 과제의 첫 문제를 다시 풀기 전에 수업에서 사용한 개념과 주의점을 한 줄씩 적습니다.",
            ),
        ),
        (
            "표현 바꾸기",
            (
                "같은 내용을 말·그림·표·식·짧은 글 가운데 다른 표현으로 바꾸고 유지된 근거를 표시합니다.",
                "말로 설명한 내용을 그림이나 표로 옮긴 뒤 새 표현에서 빠진 정보를 직접 찾습니다.",
                "문장을 식으로, 식을 말로, 읽은 내용을 세 개의 핵심어로 바꾸며 뜻이 유지되는지 봅니다.",
                "첫 표현과 전혀 다른 도구를 하나 골라 같은 관계를 나타내고 선택 이유를 남깁니다.",
                "교과서의 예를 학생이 익숙한 장면으로 바꾸되 개념의 조건이 달라지지 않았는지 확인합니다.",
                "답안을 짧은 발표와 한 줄 기록으로 각각 만들어 두 표현의 공통 정보와 빠진 정보를 대조합니다.",
            ),
        ),
        (
            "조건 변형",
            (
                "숫자, 문장 순서, 자료 형태 중 한 조건을 바꾸어도 같은 판단을 선택하는지 봅니다.",
                "익숙한 문제에서 숫자나 인물, 자료 순서 하나만 바꾸고 처음 전략을 유지할지 다시 고릅니다.",
                "예제의 질문을 반대로 만들거나 불필요한 정보를 더해 필요한 조건을 다시 찾습니다.",
                "그림을 글로 바꾸거나 문단 순서를 섞은 자료에서 변하지 않은 핵심 관계를 설명합니다.",
                "쉬운 예와 틀리기 쉬운 반대 예를 나란히 두고 개념이 적용되는 경계를 말합니다.",
                "학교 문제의 형식은 유지하고 소재만 바꾸어 외운 답이 아닌 판단 순서가 남는지 확인합니다.",
            ),
        ),
        (
            "오류 재시도",
            (
                "틀린 답과 오래 걸린 정답을 함께 모아 첫 오류가 시작된 위치만 다시 수행합니다.",
                "지운 흔적을 복원해 처음 판단, 막힌 줄, 도움 뒤 수정, 다음 시작점을 네 칸에 적습니다.",
                "오답을 전부 베끼지 않고 오류가 시작된 문장이나 계산 한 줄만 다른 방법으로 다시 설명합니다.",
                "맞았지만 설명하지 못한 문제도 오답과 함께 두고 공통으로 필요한 개념을 한 가지 찾습니다.",
                "해설을 읽은 문제는 즉시 끝내지 않고 이틀 뒤 비슷한 조건에서 첫 풀이부터 다시 시작합니다.",
                "실수를 읽기·개념·표현·실행으로 분류하고 같은 원인의 새 문제 한 개만 후속 과제로 둡니다.",
            ),
        ),
        (
            "주말 설명",
            (
                "일주일 자료를 보지 않고 잘된 행동, 막힌 행동, 다음 주에 바꿀 행동을 학생이 한 문장씩 정합니다.",
                "이번 주 공책 세 쪽을 골라 혼자 시작한 부분과 도움이 필요했던 부분을 학생이 직접 분류합니다.",
                "주간 기록에서 가장 오래 걸린 활동과 가장 쉽게 재현한 활동을 비교해 다음 계획을 한 줄 고칩니다.",
                "완료율을 계산하기보다 질문이 구체적이었던 날과 재시작이 빨랐던 날의 조건을 찾아봅니다.",
                "부모는 잘한 점 하나와 궁금한 점 하나만 묻고 학생이 다음 주 최소 학습을 결정하게 합니다.",
                "학교 일정이 달라진 날의 기록을 따로 보고 유지할 행동과 줄일 분량을 학생의 말로 정리합니다.",
            ),
        ),
    )
    phases = tuple(
        (name, _pick(details, slug, f"weekly-detail-{name}"))
        for name, details in phase_options
    )
    shift = _stable_index(slug, "weekly-order") % len(phases)
    phases = phases[shift:] + phases[:shift]
    cards = "".join(
        f"<h3>{escape(location)} {escape(focus)} 주간 확인: {escape(name)}</h3><p>{escape(detail)} "
        f"{escape(location)} 가정에서는 학생이 집중할 수 있는 짧은 시간만 진행하고, 끝난 분량보다 학생이 혼자 고른 첫 행동과 다음 시작점을 남깁니다.</p>"
        for name, detail in phases
    )
    return (
        f'<section class="elementary-general-block elementary-general-weekly" data-weekly-checks="5"><h2>{escape(heading)}</h2>'
        f"<p>{escape(str(pack['home']))} 매일 같은 양을 강제하지 않고 학교 일정과 피로에 따라 활동의 목적을 바꾸되, {escape(focus)} 관찰 기준은 일주일 동안 유지합니다.</p>{cards}</section>"
    )


def _school_section(slug: str, location: str, focus: str) -> str:
    schools = ELEMENTARY_SCHOOL_CONTEXT.get(location, [])[:4]
    heading = _pick(
        (
            f"2025년 자료로 확인하는 {location} 초등학교와 {focus}",
            f"{location} 학교 공식 정보에서 출발하는 {focus} 계획",
            f"{location}초등과외 전에 확인할 학교 원본과 {focus}",
        ),
        slug,
        "school-heading",
    )
    source_file = ELEMENTARY_SCHOOL_SOURCE.get("file", "2025년 유초중등 학교별 통계")
    source_date = ELEMENTARY_SCHOOL_SOURCE.get("survey_date", "2025-04-01")
    if schools:
        rows = []
        school_notes = []
        for school in schools:
            name = str(school.get("name") or "")
            homepage = str(school.get("homepage") or "")
            name_html = (
                f'<a class="source-link" href="{escape(homepage)}" target="_blank" rel="noopener noreferrer external">{escape(name)} 공식 홈페이지</a>'
                if homepage
                else escape(name)
            )
            grade_students = school.get("grade_students", {})
            lower = sum(int(grade_students.get(str(grade), 0)) for grade in (1, 2)) if isinstance(grade_students, dict) else 0
            middle = sum(int(grade_students.get(str(grade), 0)) for grade in (3, 4)) if isinstance(grade_students, dict) else 0
            upper = sum(int(grade_students.get(str(grade), 0)) for grade in (5, 6)) if isinstance(grade_students, dict) else 0
            students = int(school.get("students") or 0)
            classes = int(school.get("classes") or 0)
            rows.append(
                f"<tr><td>{name_html}</td><td>{students:,}명</td>"
                f"<td>{classes:,}학급</td><td>5·6학년 {upper:,}명</td></tr>"
            )
            interpretation = _pick(
                (
                    "학년군 학생 수는 교재 난도나 수업 속도를 결정하는 값이 아니므로 학생의 공책과 설명을 별도로 확인합니다.",
                    "이 숫자로 반 편성이나 학업 수준을 추정하지 않고 학교명과 학년 구조를 확인하는 배경 자료로만 사용합니다.",
                    "전체 규모와 학년군 분포는 공개 통계의 한 시점이며 현재 학급 운영과 학생 개인의 학습 상태는 학교 원본에서 다시 확인합니다.",
                    "공개된 수치는 학습 성취를 나타내지 않으므로 과외 계획에는 실제 재학 학년과 최근 교과 자료만 직접 반영합니다.",
                    "학생 수가 많거나 적다는 이유로 수업 방식을 단정하지 않고 학교 과제와 아이의 독립 수행 기록을 함께 봅니다.",
                    "학년별 수치는 통학구역이나 교육과정의 차이를 설명하지 않으므로 공식 홈페이지와 실제 알림장을 우선합니다.",
                ),
                slug,
                f"school-interpretation-{name}",
            )
            school_notes.append(
                f"<h3>{escape(location)} {escape(name)} 학년군 자료와 {escape(focus)} 확인 범위</h3>"
                f"<p>{escape(name)}은 2025년 조사에서 전체 {students:,}명, {classes:,}학급으로 집계됐고 "
                f"1·2학년 {lower:,}명, 3·4학년 {middle:,}명, 5·6학년 {upper:,}명으로 기록되어 있습니다. "
                f"{escape(interpretation)} {escape(location)}초등과외에서는 이 통계를 성취 비교에 쓰지 않고 "
                f"{escape(focus)} 관찰을 어느 학년군의 실제 학교 자료에서 시작할지 확인하는 범위로 제한합니다.</p>"
            )
        school_content = (
            '<table><thead><tr><th>학교 원본</th><th>전체 학생</th><th>학급</th><th>고학년 확인</th></tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table>{''.join(school_notes)}"
        )
        note = (
            f"학생 수와 학급 수는 수업 방식이나 성취도를 뜻하지 않습니다. {location} 학생의 실제 학년, 학교 공책, "
            f"가정 일정을 확인하고 {focus} 과제를 정하기 위한 배경 정보로만 사용합니다."
        )
    else:
        school_content = (
            f'<div class="school-data-empty"><p>{escape(source_date)} 기준 주소 일치 방식으로는 {escape(location)}에 직접 연결되는 '
            "초등학교가 확인되지 않았습니다. 인접 지역 학교를 임의로 넣지 않고 실제 재학 학교의 공식 홈페이지와 알림장을 "
            "학부모가 직접 확인하도록 안내합니다.</p></div>"
        )
        note = f"학교명이 검색되지 않았다는 사실은 {location}에 초등학생이 없다는 뜻이 아니며 주소 표기와 통학구역은 별도로 확인해야 합니다."
    return (
        f'<section class="elementary-general-block elementary-general-school" data-school-count="{len(schools)}"><h2>{escape(heading)}</h2>'
        f"<p>{escape(source_file)}의 {escape(source_date)} 조사값 가운데 학교 주소에 {escape(location)} 명칭이 포함된 항목을 사용했습니다. "
        "학교명 링크는 공식 홈페이지 확인용이며 특정 학교나 수업을 추천하는 의미가 아닙니다.</p>"
        f"{school_content}<p>{escape(note)}</p></section>"
    )


def _student_case(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    grade = _pick(("초등 1학년", "초등 2학년", "초등 3학년", "초등 4학년", "초등 5학년", "초등 6학년"), slug, "case-grade")
    challenge = _pick(
        (
            "과제를 시작하기 전 준비 시간이 길어짐", "답을 고른 근거를 말하지 못함", "틀린 흔적을 모두 지우고 다시 씀",
            "도움을 받은 뒤 혼자 이어 가지 못함", "읽은 내용을 짧게 정리하지 못함", "요일마다 학습 시작 시각이 크게 달라짐",
            "한 문제에 오래 머문 뒤 다음 활동까지 포기함", "학교 숙제와 개인 복습의 목적을 구분하지 못함",
        ),
        slug,
        "case-challenge",
    )
    evidence = _pick(
        (
            "도움 전 첫 행동과 시작까지 걸린 시간", "학생이 가리킨 근거와 질문의 구체성", "수정 전후에 달라진 한 문장",
            "이틀 뒤 자료 없이 복원한 첫 단계", "다른 과목에서 같은 방법을 다시 선택한 장면", "부모의 지시가 줄어든 구간",
        ),
        slug,
        "case-evidence",
    )
    heading = f"{location} {grade} {focus} 합성 사례: {challenge}"
    rows = (
        ("관찰 전", challenge, "평가하지 않고 발생한 시간·과목·직전 행동을 기록합니다."),
        ("한 행동 변경", str(pack["home"]), "부모의 질문 하나와 학생이 고른 최소 완료 행동만 적용합니다."),
        ("간격 뒤 확인", evidence, "같은 답을 외웠는지보다 도움 없이 판단 순서를 다시 고르는지 봅니다."),
    )
    table = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(record)}</td><td>{escape(decision)}</td></tr>"
        for stage, record, decision in rows
    )
    steps = (
        f"{pack['material']}에서 {focus} 과정이 드러나는 자료 하나를 고릅니다.",
        "첫 기록을 지우지 않고 도움을 준 말과 학생이 스스로 한 행동을 다른 색으로 표시합니다.",
        "간격을 둔 뒤 자료를 가리고 같은 판단의 첫 단계를 다시 설명하게 합니다.",
    )
    return (
        f'<section class="elementary-general-block elementary-general-student-case" data-case-model="composite" data-case-grade="{escape(grade)}"><h2>{escape(heading)}</h2>'
        f"<p><strong>합성 사례 안내:</strong> 아래 내용은 {escape(location)}의 실제 학생 상담이나 성적 향상 사례가 아닙니다. {escape(focus)} 관찰 방법을 설명하기 위해 여러 학습 장면을 조합한 가상 예시입니다.</p>"
        f"<table><thead><tr><th>단계</th><th>남길 기록</th><th>다음 판단</th></tr></thead><tbody>{table}</tbody></table><ol>"
        + "".join(f"<li>{escape(step)}</li>" for step in steps)
        + f"</ol><p>{escape(location)} 학생의 변화는 점수 상승으로 단정하지 않습니다. {escape(evidence)}에 변화가 있었는지 확인하고, 변화가 없으면 의지 문제로 결론 내리지 말고 자료·도움·시간 가운데 한 조건을 바꾸어 다시 비교합니다.</p></section>"
    )


def _local_experiment(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    schools = ELEMENTARY_SCHOOL_CONTEXT.get(location, [])
    school_reference = str(schools[0].get("name") or "재학 학교") if schools else "실제 재학 학교"
    heading = _pick(
        (
            f"{location} {focus} 판단을 위한 네 번의 지역 학습 실험",
            f"자료와 시간대를 바꾸어 보는 {location} {focus} 관찰",
            f"{location}초등과외 전에 {_obj(focus)} 직접 비교하는 단계별 기록",
            f"{location} 생활 흐름에 맞춘 {focus} 소규모 실험",
        ),
        slug,
        "experiment-heading",
    )
    scenes = (
        "귀가 뒤 간식과 휴식을 마친 첫 집중 구간", "학교 숙제를 펼치기 직전의 준비 시간", "저녁 식사 전에 남는 짧은 시간",
        "주말 오전에 피로가 적은 시간대", "다른 일정이 끝난 뒤 전환이 필요한 순간", "학교에서 돌아와 가방을 정리한 직후",
        "읽기 활동을 끝내고 수학으로 옮기는 시점", "수학 문제를 마친 뒤 영어를 시작하는 시점", "보호자가 옆에 있지 않은 짧은 구간",
        "평소보다 귀가가 늦어진 날의 최소 학습 시간", "주간 과제를 다시 배치하는 금요일 저녁", "일요일에 다음 주 준비물을 확인하는 시간",
        "학교 알림장을 확인한 직후의 계획 시간", "집중이 한 번 끊긴 뒤 다시 책상으로 온 순간", "오답을 다시 보는 날의 첫 활동",
        "새 단원 첫 수업을 들은 날의 당일 복습 시간",
    )
    materials = (
        "제목을 가린 교과서 한 문단", "정답 표시가 남은 공책 한 쪽", "조건 하나를 바꾼 짧은 문장제",
        "그림과 핵심어만 남긴 영어 카드", "학생이 직접 적은 이번 주 과제표", "수정 전 문장과 수정 뒤 문장",
        "학교에서 받은 활동지의 첫 문제", "단위를 지운 표와 그래프 한 개", "읽기·쓰기·계산 자료를 한 장씩",
        "지난주에 오래 걸렸지만 맞힌 문항", "설명 없이 다시 풀어 볼 오답 한 개", "사회나 과학 자료의 사진과 설명문",
        "듣기에서 놓친 구간을 적은 짧은 메모", "부모 도움 전후가 다른 색으로 남은 기록", "학생이 가장 쉬웠다고 고른 문제",
        "학생이 가장 질문하고 싶다고 고른 자료",
    )
    actions = (
        "찾아야 할 정보 두 개를 먼저 말하고 자료에서 직접 가리킵니다.", "처음 떠오른 답을 지우지 않고 선택한 이유를 옆에 적습니다.",
        "말·그림·표·식 가운데 두 표현을 골라 같은 뜻을 나타냅니다.", "막힌 위치에서 필요한 힌트의 종류를 학생이 한 문장으로 요청합니다.",
        "활동을 끝냈다고 판단할 행동을 먼저 적고 예상 시간을 정합니다.", "문제의 질문과 조건을 나눈 뒤 불필요한 정보를 한 개 골라냅니다.",
        "읽은 내용을 보지 않고 핵심어 세 개와 연결 관계를 복원합니다.", "틀린 줄의 바로 앞에서 사용한 개념과 단위를 다시 확인합니다.",
        "소리·뜻·철자 가운데 놓친 한 층만 짧게 반복합니다.", "초안을 소리 내어 읽고 빠진 조건과 어색한 연결을 표시합니다.",
        "부모가 주는 힌트를 두 가지 중 하나로 제한하고 선택 이유를 듣습니다.", "현재 방법과 다른 풀이 또는 다른 표현을 하나 만들어 비교합니다.",
        "자료를 덮은 상태에서 다음에 할 첫 순서를 네 낱말 안으로 말합니다.", "활동 중 멈춘 시각과 직전 행동을 적고 시작 환경을 한 항목만 바꿉니다.",
        "같은 개념을 다른 과목의 짧은 자료에서 찾아 공통점을 말합니다.", "완료하지 못한 분량을 옮기기 전에 이해·시간·준비 중 원인을 고릅니다.",
    )
    evidence = (
        "첫 표시가 질문과 맞았는지", "설명 없이 시작한 단계가 어디까지인지", "힌트 뒤 혼자 이어 간 문장이 무엇인지",
        "정답 전 예상과 결과의 차이를 말했는지", "사용한 단위와 표현이 끝까지 유지됐는지", "막힌 이유를 구체적인 질문으로 바꾸었는지",
        "처음 계획과 실제 소요 시간의 차이를 설명했는지", "다른 자료에서도 같은 판단 기준을 다시 썼는지", "수정 전 기록을 남기고 바꾼 이유를 말했는지",
        "부모의 지시가 없어도 다음 자료를 골랐는지", "활동의 끝을 학생 스스로 판단했는지", "답보다 먼저 근거 위치를 가리켰는지",
        "틀린 문제와 오래 걸린 정답을 함께 분류했는지", "도움의 양을 이전 시도보다 줄였는지", "새로운 조건에서 첫 전략을 유지하거나 바꾼 이유가 있는지",
        "다음 확인 날짜와 시작 행동을 직접 정했는지",
    )
    adjustments = (
        "자료의 길이를 절반으로 줄이고 설명 횟수는 유지합니다.", "같은 시간대에 표현 방법만 바꾸어 다시 봅니다.",
        "도움 문장을 하나 줄이고 시작 신호는 그대로 둡니다.", "학교 당일 복원과 주말 재현의 간격을 하루 늘립니다.",
        "정답률 대신 질문의 구체성과 재시작 시간을 다음 기준으로 둡니다.", "쉬운 자료에서 성공한 순서를 새 자료의 첫 단계로 옮깁니다.",
        "한 번에 바꾸는 조건을 하나로 제한해 원인을 분명하게 봅니다.", "과제량을 늘리지 않고 학생이 고르는 자료의 범위만 넓힙니다.",
        "부모 확인 시점을 활동 중간에서 마친 뒤로 옮깁니다.", "쓰기 부담을 줄이되 말한 내용을 한 줄 기록으로 남깁니다.",
        "같은 오류가 반복되면 문제 수가 아니라 표현 도구를 바꿉니다.", "예상 시간과 실제 시간 차이가 크면 최소 완료 행동을 다시 정합니다.",
        "다른 과목으로 옮길 때 공통 행동 하나만 유지합니다.", "학생의 질문이 막연하면 자료 위치와 첫 판단을 먼저 붙입니다.",
        "간격 뒤 재현이 어렵다면 도움 직후 설명을 더 짧고 정확하게 만듭니다.", "성공한 날의 환경과 시작 순서를 다음 주 한 번 더 반복합니다.",
    )
    cards = []
    for index in range(4):
        scene = _pick(scenes, slug, f"experiment-scene-{index}")
        material = _pick(materials, slug, f"experiment-material-{index}")
        action = _pick(actions, slug, f"experiment-action-{index}")
        record = _pick(evidence, slug, f"experiment-evidence-{index}")
        adjustment = _pick(adjustments, slug, f"experiment-adjustment-{index}")
        cards.append(
            f"<h3>{escape(location)} {escape(focus)} 관찰: {escape(scene)}</h3>"
            f"<p>{escape(school_reference)}의 공식 정보가 아니라 {escape(location)} 학생의 실제 공책과 생활 기록을 기준으로 합니다. "
            f"{escape(scene)}에 {escape(material)}을 사용해 학생이 집중할 수 있는 짧은 시간 동안 {escape(action)} 관찰표에는 {escape(record)}를 남깁니다. "
            f"한 번의 결과로 결론 내리지 않고 다음 시도에서는 {escape(adjustment)} 이 차이가 반복되면 {escape(focus)} 과제를 그대로 늘리기보다 "
            "자료 선택, 표현 방법, 도움 시점 가운데 실제로 영향을 준 조건을 하나씩 좁힙니다.</p>"
        )
    return (
        f'<section class="elementary-general-block elementary-general-local-experiment" data-experiment-sessions="4"><h2>{escape(heading)}</h2>'
        f"<p>이 실험은 {escape(location)} 학생의 성취를 예측하는 검사가 아닙니다. {escape(str(pack['material']))}에서 {escape(focus)} 행동을 짧게 관찰하고, "
        "같은 기준을 유지한 채 시간대·자료·도움 조건을 하나씩 바꾸는 교육용 비교입니다.</p>"
        f"{''.join(cards)}<p>네 기록을 모은 뒤에는 가장 높은 점수를 고르지 않습니다. 혼자 출발한 조건, 구체적인 질문이 나온 조건, 며칠 뒤에도 유지된 조건을 찾아 "
        f"{escape(location)} 학생의 다음 주 최소 학습과 부모가 줄일 도움을 각각 하나씩 정합니다.</p></section>"
    )


def _parent_coaching(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} 가정에서 {_obj(focus)} 확인하는 네 가지 대화",
            f"지시를 줄이고 기록을 남기는 {location} {focus} 질문",
            f"{location} 학부모가 {_obj(focus)} 도울 때 지킬 경계",
        ),
        slug,
        "parent-heading",
    )
    items = (
        ("시작 전", "무엇부터 할래?", "교재명보다 끝났다고 판단할 행동을 아이가 직접 고르게 합니다."),
        ("막힌 순간", "어디까지는 혼자 설명할 수 있어?", "정답을 알려 주기 전에 맞는 단계와 도움이 필요한 한 단계를 분리합니다."),
        ("끝난 직후", "처음 생각과 무엇이 달라졌어?", "결과 칭찬보다 판단을 바꾼 근거와 사용한 자료를 말하게 합니다."),
        ("며칠 뒤", "다시 한다면 첫 행동은 무엇이야?", "복습량보다 기억에서 꺼낸 시작 순서와 줄일 힌트를 확인합니다."),
    )
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)} {escape(stage)} 대화</h3><p><strong>{escape(question)}</strong> {escape(detail)} "
        f"{escape(location)}에서 {escape(focus)} 과정을 살필 때는 {escape(str(pack['home']))} 이 질문은 한 번에 하나만 사용하고 학생의 답을 고쳐 말하지 않은 채 다음 기록에 옮깁니다.</p>"
        for stage, question, detail in items
    )
    return (
        f'<section class="elementary-general-block elementary-general-parent" data-parent-prompts="4"><h2>{escape(heading)}</h2>'
        f"<p>{escape(location)}초등과외에서 부모의 역할은 교사를 대신하는 일이 아니라 {escape(focus)} 관찰 기준이 집에서도 이어지도록 질문과 환경을 정리하는 일입니다.</p>{content}</section>"
    )


def _transition(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 기록을 다음 학년과 중학교로 옮기기",
            f"선행 진도보다 먼저 확인할 {location} {focus} 전환 기준",
            f"{location} 고학년의 {_obj(focus)} 과목별 계획으로 바꾸기",
        ),
        slug,
        "transition-heading",
    )
    current_detail = _pick(
        (
            "교과서와 최근 평가에서 설명하지 못한 핵심 개념을 한 과목에 한 개씩 찾습니다.", "학교 공책을 덮고 이번 단원의 핵심을 말한 뒤 빠진 연결만 다시 엽니다.",
            "최근 과제의 첫 답안을 보존하고 반복해서 막힌 개념과 단순 실수를 나눕니다.", "현재 학년 예제에서 자료 없이 시작하지 못한 한 단계를 우선 복원합니다.",
            "국어·수학·영어의 학교 원본을 한 쪽씩 골라 설명 가능한 범위를 표시합니다.", "맞힌 결과보다 오래 걸린 판단과 질문이 필요한 위치를 현재 학년 보완 목록에 둡니다.",
        ),
        slug,
        "transition-current",
    )
    next_detail = _pick(
        (
            "낯선 용어를 많이 외우기보다 현재 개념과 연결되는 첫 질문만 미리 만듭니다.", "다음 교과서의 제목과 핵심어를 보고 지금 배운 내용과 이어지는 지점을 하나 찾습니다.",
            "선행 문제 수를 늘리지 않고 새 형식에서 질문과 조건을 읽는 순서만 짧게 연습합니다.", "다음 학년 예제 한 개를 현재 표현으로 설명하고 새로 필요한 개념을 표시합니다.",
            "새 단원의 용어를 뜻·예·반대 예로 나누되 현재 학년 공백과 섞지 않습니다.", "다음 단계 자료는 학생이 현재 내용을 독립적으로 복원한 뒤 한 항목만 추가합니다.",
        ),
        slug,
        "transition-next",
    )
    items = (("현재 학년 복원", current_detail), ("다음 학년 예고", next_detail), ("중학교 학습 운영", str(pack["transition"])))
    transition_tails = (
        "학교 자료를 고르고 완료 기준과 재시도 날짜를 말할 수 있을 때 범위를 넓히며 현재 학년 공백을 선행으로 덮지 않습니다.",
        "학생이 시작 자료와 필요한 도움을 스스로 정한 뒤 다음 단계를 한 개만 추가해 독립 수행이 유지되는지 봅니다.",
        "현재 개념을 설명한 기록과 새 문제의 첫 판단을 나란히 두고 연결되지 않은 한 대목만 후속 과제로 옮깁니다.",
        "학년이 달라져도 자료 선택·질문 작성·간격 복습을 혼자 수행하는지를 진도보다 먼저 확인합니다.",
        "부모가 정한 분량보다 학생이 말한 마감과 질문이 계획에 반영되는지 살펴 다음 학기의 도움 수준을 조정합니다.",
        "새 교재를 시작하기 전에 학교 원본에서 확인한 강점과 공백을 다른 칸에 적고 첫 주 과제를 작게 정합니다.",
    )
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)} {escape(name)} 전환</h3><p>{escape(detail)} "
        f"{escape(location)}에서는 {escape(_pick(transition_tails, slug, f'transition-tail-{index}'))}</p>"
        for index, (name, detail) in enumerate(items, 1)
    )
    return (
        f'<section class="elementary-general-block elementary-general-transition" data-transition-steps="3"><h2>{escape(heading)}</h2>'
        f"<p>{escape(focus)} 학습의 목표는 초등 과정을 빨리 끝내는 것이 아니라 새로운 교과와 일정에서도 필요한 자료와 도움을 스스로 선택하는 데 있습니다.</p>{content}</section>"
    )


def _protocol(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 누적 관찰을 위한 여섯 개 학습 카드",
            f"설명과 재시도를 연결하는 {location} {focus} 여섯 단계",
            f"{location}초등과외에서 {_obj(focus)} 직접 시험하는 방법",
        ),
        slug,
        "protocol-heading",
    )
    materials = (
        str(pack["material"]), "정답을 가린 최근 학교 과제", "학생이 틀린 흔적을 남긴 공책 한 쪽",
        "조건 하나만 바꾼 짧은 문제", "말·그림·표 가운데 빈 표현 카드", "이틀 뒤 다시 꺼낸 동일 개념 자료",
        "부모의 도움 문장을 기록한 메모", "학생이 직접 고른 다음 과제 한 개",
    )
    actions = (
        "처음 90초 동안 질문하지 않고 시선과 손의 첫 움직임을 봅니다.",
        "질문과 조건, 알고 있는 내용과 모르는 내용을 서로 다른 칸에 적습니다.",
        "정답을 가린 채 처음 선택한 근거만 한 문장으로 말합니다.",
        "도움을 요청한 정확한 위치와 필요한 힌트의 종류를 학생이 고릅니다.",
        "같은 내용을 다른 표현으로 바꾸고 유지된 관계를 표시합니다.",
        "오류를 지우지 않고 처음 판단이 달라진 지점과 수정 이유를 적습니다.",
        "다른 과목의 짧은 자료에서 같은 학습 행동을 다시 선택합니다.",
        "자료를 덮은 뒤 다음에 시작할 첫 행동과 종료 기준을 복원합니다.",
    )
    records = (
        "혼자 시작한 행동", "처음 가리킨 근거", "도움을 요청한 문장", "표현을 바꾼 이유",
        "오류가 시작된 위치", "자료 없이 복원한 단계", "다른 과목에 옮긴 행동", "다음 재시도 날짜",
    )
    stages = ("첫 관찰", "근거 표시", "표현 전환", "도움 선택", "조건 변형", "간격 재현")
    cards = []
    for index, stage in enumerate(stages, 1):
        minutes = 9 + _stable_index(slug, f"protocol-minutes-{index}") % 14
        gap = 1 + _stable_index(slug, f"protocol-gap-{index}") % 4
        material = _pick(materials, slug, f"protocol-material-{index}")
        action = _pick(actions, slug, f"protocol-action-{index}")
        record = _pick(records, slug, f"protocol-record-{index}")
        cards.append(
            f"<h3>{escape(location)} {escape(focus)} {escape(stage)} 점검</h3>"
            f"<p>{escape(material)}을 사용해 학생이 집중할 수 있는 짧은 시간 동안 {escape(action)} {escape(record)}을 학생의 말 그대로 남기고 "
            f"간격을 둔 뒤 같은 도움 없이 다시 시작합니다. 이 점검의 목적은 정답 수가 아니라 {escape(location)} 학생이 "
            f"{escape(focus)} 과정에서 판단과 질문을 다시 선택하는지 확인하는 것입니다.</p>"
        )
    return (
        f'<section class="elementary-general-block elementary-general-protocol" data-protocol-cards="6"><h2>{escape(heading)}</h2>'
        f"<p>모든 점검을 한날에 수행하지 않습니다. {escape(location)}의 학교 일정과 피로를 고려해 여러 날에 나누고, {escape(focus)} 관찰 기준만 유지한 채 자료와 표현을 바꿉니다.</p>"
        f"{''.join(cards)}<p>마지막 점검 뒤에는 잘한 점 하나, 반복해서 막힌 지점 하나, 다음 주에 시험할 행동 하나만 남깁니다. 변화가 작더라도 학생이 도움을 더 정확히 요청하거나 혼자 시작하는 범위가 넓어졌다면 그 기록을 다음 계획의 근거로 사용합니다.</p></section>"
    )


def _context_links(location: str, city: str, focus: str) -> str:
    links = (
        (f"/{city}초등과외/", f"{city} 초등 학습의 상위 지역 기준"),
        (f"/{location}초등영어과외/", f"{location} 초등영어 학습의 과목별 기준"),
        (f"/{location}초등수학과외/", f"{location} 초등수학 학습의 과목별 기준"),
    )
    return (
        f'<aside class="elementary-general-context-links" data-link-count="3"><h2>{escape(location)} {escape(focus)} 다음에 볼 세 페이지</h2>'
        f"<p>{escape(location)}의 {_obj(escape(focus))} 전체 학습에서 확인한 뒤 필요한 범위만 이어 봅니다. 모든 키워드를 링크로 만들지 않고 상위 지역 페이지와 같은 지역의 초등영어·초등수학 페이지만 연결합니다.</p><ul>"
        + "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for href, label in links)
        + "</ul></aside>"
    )


def _faq(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    questions = (
        f"{location}초등과외는 무엇부터 점검해야 하나요?",
        f"{location} 가정에서는 수업 전에 무엇을 확인할 수 있나요?",
        f"{location} 학생의 학습이 흔들리면 공부 시간을 먼저 늘려야 하나요?",
        f"{location}초등과외와 학교 숙제는 어떻게 나누어야 하나요?",
        f"{location} 고학년은 중학교 준비를 어떻게 연결하나요?",
    )
    answers = (
        f"{location}에서는 특정 학년부터 일괄 시작하기보다 현재 학교 자료에서 {_obj(focus)} 먼저 확인합니다. 1~2학년은 짧은 행동과 말하기, 3~4학년은 두 표현의 연결, 5~6학년은 조건·근거·재시도 기록을 사용합니다. {pack['signal']}를 학생이 보여 주는 단계에서 과제의 깊이와 도움의 양을 정하는 편이 좋습니다.",
        f"{location} 가정에서는 {pack['material']} 가운데 한 가지만 준비하고 10~15분 동안 도움 전 첫 행동을 지우지 않습니다. {pack['home']} 끝난 뒤에는 시작까지 걸린 시간, 막힌 위치, 요청한 도움, 혼자 이어 간 단계를 적고 며칠 뒤 같은 자료를 가린 상태에서 첫 판단을 다시 설명하게 합니다.",
        f"{location} 학생의 {_subject(focus)} 약해 보인다고 학습시간부터 늘리면 읽기·개념·표현·실행·감정 중 실제 원인을 가릴 수 있습니다. {pack['signal']}를 기준으로 가장 자주 반복된 한 지점만 고르고, 짧은 활동에서 혼자 시작하고 마친 증거가 생긴 뒤 시간과 분량을 단계적으로 넓힙니다.",
        f"학교 숙제는 {location} 학생이 당일 배운 내용을 확인하는 원본으로 사용하고, 별도 학습은 {_obj(focus)} 설명·표현 전환·오류 재시도에 사용합니다. 같은 문제를 여러 번 푸는 방식으로 겹치게 하지 말고 학교 과제에서 막힌 첫 위치를 다음 수업 질문으로 옮겨 두 활동의 역할을 분리합니다. 주말에는 두 기록을 나란히 놓고 겹친 활동과 빠진 복습을 학생이 직접 고르게 합니다.",
        f"{location} 5·6학년은 {pack['transition']} 현재 학년 교과서에서 혼자 설명하지 못하는 개념을 먼저 보완하고, 다음 단계는 낯선 문제를 많이 푸는 대신 자료 선택·마감 확인·질문 작성·간격 복습을 스스로 수행할 때 한 항목씩 넓히는 것이 안전합니다. 전환 전후에 같은 기준으로 남긴 기록을 비교해 아이가 혼자 유지한 행동도 확인합니다.",
    )
    answer_extensions = (
        "확인 결과는 다음 수업에서 바꿀 행동 하나와 부모가 줄일 도움 하나로 끝냅니다.",
        "한 번의 성공이나 실패보다 일주일 안에서 같은 행동이 다시 나타나는지를 봅니다.",
        "학생이 사용한 실제 표현을 고쳐 쓰지 않고 남겨 다음 기록과 같은 기준으로 비교합니다.",
        "교재가 달라져도 시작 자료와 끝낼 행동을 아이가 말할 수 있는지를 함께 살핍니다.",
        "잘한 부분을 유지하면서 반복해서 막힌 연결 하나만 다음 확인일의 첫 활동으로 둡니다.",
        "답을 들은 직후가 아니라 시간을 둔 뒤 같은 판단을 다시 수행하는지도 확인해야 합니다.",
        "학교 알림과 실제 공책이 다르면 최신 학교 원본을 우선하고 계획을 다시 조정합니다.",
        "집중 시간은 일괄적으로 늘리지 않고 성공적으로 마친 활동의 끝에서 조금씩 확장합니다.",
        "부모의 설명이 길어졌다면 다음번에는 질문을 한 문장으로 줄여 학생의 말을 먼저 듣습니다.",
        "아이가 선택한 자료가 너무 쉽거나 어렵다면 분량보다 표현 방법과 도움 시점을 먼저 바꿉니다.",
        "변화가 없을 때는 태도 문제로 단정하지 않고 읽기·개념·표현·실행 기록을 다시 나눕니다.",
        "다른 과목에서도 같은 학습 행동이 유지되면 그 순서를 주간 계획의 공통 기준으로 씁니다.",
        "끝낸 문제 수와 함께 질문의 구체성, 재시작 시간, 독립 설명 범위를 기록합니다.",
        "학교생활과 가정 일정이 달라진 주에는 최소 학습만 유지하고 관찰 기간을 한 주 더 둡니다.",
        "학생의 개인정보나 정확한 주소 없이도 학년·학교 자료·학습 행동으로 먼저 비교할 수 있습니다.",
        "상담 전에는 성적 전체보다 최근 자료 한 쪽과 반복된 질문 한 개를 준비하는 편이 실용적입니다.",
    )
    extension_start = _stable_index(slug, "faq-extension-start") % len(answer_extensions)
    answers = tuple(
        f"{answer} {answer_extensions[(extension_start + 7 * index) % len(answer_extensions)]}"
        for index, answer in enumerate(answers)
    )
    pairs = list(zip(questions, answers))
    shift = _stable_index(slug, "faq-order") % len(pairs)
    pairs = pairs[shift:] + pairs[:shift]
    content = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in pairs)
    heading = _pick(
        (
            f"{location} 초등 학습 FAQ",
            f"{location}초등과외 자주 묻는 질문",
            f"{location} 학년·숙제·가정 점검 FAQ",
        ),
        slug,
        "faq-heading",
    )
    return (
        f'<section class="elementary-general-block elementary-general-faq"><h2 class="elementary-general-faq" data-faq-focus="{escape(focus)}">{escape(heading)}</h2>{content}</section>'
    )


def _closing(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 계획을 다음 한 행동으로 끝내기",
            f"{location} 학생이 혼자 시작할 때까지 남길 {focus} 기록",
            f"과제량보다 먼저 정할 {location} {focus} 재시도",
        ),
        slug,
        "closing-heading",
    )
    paragraph = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 돕는 핵심은 모든 과목의 분량을 동시에 늘리는 데 있지 않습니다. {pack['home']} 학교 원본과 첫 행동, 도움받은 지점, 며칠 뒤 독립 재현을 한 줄씩 남기면 학생에게 필요한 다음 과제를 더 작고 정확하게 정할 수 있습니다.",
            f"이 페이지의 {location} 학교 정보와 {focus} 계획은 상담 결과나 성취를 보장하지 않습니다. 학생의 실제 교과서와 공책, 학교 안내, 생활시간을 함께 확인하고 한 번에 하나의 행동만 바꾸어 같은 기준으로 다시 관찰하는 교육용 안내입니다.",
            f"{location}에서 {_obj(focus)} 오래 유지하려면 정답 직후의 결과만 남기지 않습니다. 학생이 고른 근거, 표현을 바꾼 이유, 요청한 도움, 다음 재시도 날짜를 기록해 학년과 교과가 달라져도 같은 판단을 꺼내 쓰도록 돕습니다.",
        ),
        slug,
        "closing-paragraph",
    )
    evidence_note = (
        f"{location}의 {focus} 점검을 마칠 때는 {pack['signal']}를 다시 읽고, 학생이 고른 자료와 도움 전 첫 행동을 함께 보관합니다. "
        "다음 확인에서는 같은 답을 기억했는지가 아니라 교과와 과제 조건이 달라져도 시작 순서를 혼자 꺼내 쓰는지 살핍니다. 근거가 부족하면 과제량을 늘리기 전에 관찰 기준과 도움 시점부터 조정합니다."
    )
    return f'<section class="elementary-general-block elementary-general-closing"><h2>{escape(heading)}</h2><p>{escape(paragraph)}</p><p>{escape(evidence_note)}</p></section>'


def _individualize_diction(body: str, slug: str) -> str:
    """Disperse recurring instructional wording while preserving meaning and markup."""
    _, focus = _pack_and_focus(slug)
    escaped_focus = escape(focus)
    placeholder = "EDUNEXT_ELEMENTARY_FOCUS_PLACEHOLDER"
    body = body.replace(escaped_focus, placeholder)
    variants: dict[str, tuple[str, ...]] = {
        "학생이 직접": ("아이가 직접", "학습자가 스스로", "학생 본인이", "아이가 자기 힘으로", "학습자가 직접", "학생 스스로"),
        "학생이 스스로": ("아이가 스스로", "학습자가 자기 힘으로", "학생 본인이", "아이가 직접", "학습자가 스스로", "학생이 자기 힘으로"),
        "학생이": ("아이가", "학습자가", "학생 본인이", "초등 학습자가", "해당 학생이", "자녀가", "학습 당사자가", "학생 스스로가"),
        "학생은": ("아이는", "학습자는", "학생 본인은", "초등 학습자는", "해당 학생은", "자녀는", "학습 당사자는", "학생 스스로는"),
        "학생의": ("아이의", "학습자의", "학생 본인의", "초등 학습자의", "해당 학생의", "자녀의", "학습 당사자의", "학생 스스로의"),
        "학생에게": ("아이에게", "학습자에게", "학생 본인에게", "초등 학습자에게", "해당 학생에게", "자녀에게", "학습 당사자에게", "학생 스스로에게"),
        "부모는": ("보호자는", "가정에서는", "학부모는", "부모가", "보호자가", "가정의 어른은", "부모 역할은", "학부모가"),
        "부모의": ("보호자의", "가정의", "학부모의", "부모가 건넨", "보호자가 준", "가정에서 제공한", "부모 역할의", "학부모가 사용한"),
        "학교 자료": ("교실 자료", "정규 수업 자료", "학교에서 사용한 원본 자료", "교과 시간 자료", "학교 학습 원본 자료", "수업 자료", "교과 원자료", "학교 수업 기록 자료"),
        "학교 일정": ("교내 일정", "정규 수업 일정", "학교의 주간 일정", "교과 일정", "학사 흐름", "학교생활 시간표 항목", "학교 계획", "수업 일정"),
        "학교 과제": ("교실 과제", "정규 수업 과제", "학교에서 받은 과제", "교과 과제", "학교 숙제", "수업 후 과제", "학교의 제출 과제", "교실에서 이어진 과제"),
        "가정에서는": ("집에서는", "가정 학습 때는", "귀가 후에는", "집에서 살필 때는", "가정 점검에서는", "보호자와 볼 때는", "집 공부에서는", "가정 내 학습에서는"),
        "도움 없이": ("힌트 없이", "지원받지 않고", "스스로", "추가 설명 없이", "혼자 힘으로", "별도 도움 없이", "교사의 개입 없이", "보호자 힌트 없이"),
        "혼자 시작": ("스스로 착수", "자기 힘으로 출발", "도움 전에 시작", "독립적으로 착수", "첫 단계를 자력으로 수행", "안내 없이 시작", "혼자 첫 행동을 선택", "스스로 첫 순서를 실행"),
        "첫 행동": ("최초 행동", "시작 동작", "맨 처음 선택", "출발 행동", "도움 전 행동", "초기 선택", "첫 번째 수행", "시작할 때의 선택"),
        "다음 행동": ("후속 행동", "이어 할 활동", "다음번 선택", "뒤이을 수행", "후속 학습", "다음 학습 동작", "이후의 실천", "뒤에 실행할 일"),
        "종료 기준": ("마무리 기준", "끝냈다는 증거", "완료 조건", "활동의 끝 기준", "마칠 행동", "완료를 판단할 조건", "학습 마감 기준", "끝나는 지점"),
        "다시 시작": ("재착수", "한 번 더 출발", "후속 시도", "다음번 시작", "새로 착수", "독립적으로 재개", "이어 시작", "다음 시도에 착수"),
        "기록합니다": ("기록으로 남깁니다", "적어 둡니다", "관찰표에 씁니다", "구체적으로 남깁니다", "별도 칸에 적습니다", "메모로 보존합니다", "학습지에 표시합니다", "짧게 문장화합니다"),
        "확인합니다": ("점검합니다", "살펴봅니다", "대조합니다", "근거로 판단합니다", "다시 살핍니다", "기록에서 찾아봅니다", "직접 검토합니다", "차이를 읽습니다"),
        "살펴봅니다": ("점검해 봅니다", "기록에서 찾습니다", "비교합니다", "구체적으로 봅니다", "차이를 확인합니다", "근거를 읽습니다", "직접 대조합니다", "행동으로 판단합니다"),
        "말하게 합니다": ("자기 말로 표현하게 합니다", "직접 답하게 합니다", "문장으로 밝히게 합니다", "소리 내어 정리하게 합니다", "이유까지 말하도록 합니다", "스스로 설명하도록 합니다", "한 문장으로 답하게 합니다", "근거와 함께 말하도록 합니다"),
        "설명하게 합니다": ("자기 말로 풀어내게 합니다", "근거와 함께 말하도록 합니다", "문장으로 나타내게 합니다", "과정을 밝혀 말하게 합니다", "직접 정리하게 합니다", "이유를 붙여 표현하게 합니다", "소리 내어 복원하게 합니다", "스스로 풀이하게 합니다"),
        "구분합니다": ("나누어 봅니다", "서로 가려냅니다", "별도로 분류합니다", "차이를 표시합니다", "다른 항목으로 봅니다", "각각 판별합니다", "두 기록으로 나눕니다", "역할을 따로 둡니다"),
        "표시합니다": ("표시로 남깁니다", "서로 다른 기호로 둡니다", "직접 체크합니다", "기록에 구별해 둡니다", "눈에 보이게 만듭니다", "별도 색으로 남깁니다", "해당 칸에 적습니다", "자료 위에 구분해 둡니다"),
        "사용합니다": ("활용합니다", "자료로 삼습니다", "판단에 씁니다", "기준으로 둡니다", "확인 도구로 씁니다", "비교 자료로 둡니다", "학습에 적용합니다", "근거로 활용합니다"),
        "정합니다": ("결정합니다", "선택합니다", "구체화합니다", "기준을 세웁니다", "학생과 합의합니다", "한 가지로 좁힙니다", "실행 항목으로 고릅니다", "다음 순서로 둡니다"),
        "정답": ("맞힌 답", "답", "채점 결론", "최종 답", "맞고 틀린 결과값", "완성 답", "문항 결과값", "답안"),
        "같은 내용을": ("동일한 개념을", "앞서 배운 바를", "특정 개념을", "배운 내용을", "해당 내용을", "앞의 학습을", "하나의 내용을", "그 개념을"),
        "서로 다른": ("각기 다른", "차이가 나는", "별개의", "둘 이상의", "구별되는", "상이한", "역할이 다른", "나누어진"),
        "일주일 동안": ("한 주에 걸쳐", "7일의 기록에서", "이번 주 내내", "주간 관찰 기간에", "한 주 동안", "이번 주 기록에서", "주중과 주말에 걸쳐", "일주일의 흐름에서"),
        "며칠 뒤": ("시간을 둔 뒤", "간격을 둔 다음", "다음 확인일에", "이틀 이상 지난 뒤", "후속 관찰일에", "다음번 점검 때", "일정한 간격 후", "복습 날짜에"),
        "자료를 가리고": ("원본을 덮고", "자료 없이", "참고물을 보지 않고", "원문을 접어 둔 뒤", "자료를 뒤집고", "확인 자료를 치운 뒤", "원본을 감춘 상태에서", "참고 자료를 덮은 채"),
        "과정을": ("흐름을", "수행 순서를", "학습 경로를", "진행을", "사고 순서를", "학습 과정을", "실행 흐름을", "풀이 경로를"),
        "과정에서": ("진행 중", "학습 흐름에서", "수행하는 동안", "실행 단계에서", "사고 순서 안에서", "학습 과정 중", "풀이 흐름에서", "활동 중"),
        "비교합니다": ("서로 대조합니다", "차이를 읽습니다", "나란히 살핍니다", "기록을 견줍니다", "변화를 대조합니다", "두 결과를 봅니다", "전후를 살핍니다", "같은 기준으로 봅니다"),
        "연결합니다": ("이어 봅니다", "다음 학습에 붙입니다", "함께 묶습니다", "후속 활동으로 옮깁니다", "교과에 적용합니다", "연결해 봅니다", "다음 순서로 이어 갑니다", "하나의 흐름으로 만듭니다"),
        "늘립니다": ("확장합니다", "조금씩 넓힙니다", "단계적으로 더합니다", "범위를 키웁니다", "서서히 확대합니다", "한 수준 높입니다", "필요한 만큼 더합니다", "다음 범위로 넓힙니다"),
    }
    for source in sorted(variants, key=len, reverse=True):
        body = body.replace(source, _pick(variants[source], slug, f"diction-{source}"))
    return body.replace(placeholder, escaped_focus)


def build_local_elementary_general_body(slug: str) -> str:
    location, city, _ = _parts(slug)
    pack, focus = _pack_and_focus(slug)
    fixed = [_opening(slug, location, focus, pack), _search_intent(slug, location, focus, pack)]
    sections = {
        "grade": _grade_plan(slug, location, focus, pack),
        "subjects": _subjects(slug, location, focus, pack),
        "diagnosis": _diagnosis(slug, location, focus, pack),
        "weekly": _weekly_plan(slug, location, focus, pack),
        "school": _school_section(slug, location, focus),
        "case": _student_case(slug, location, focus, pack),
        "experiment": _local_experiment(slug, location, focus, pack),
        "parent": _parent_coaching(slug, location, focus, pack),
        "transition": _transition(slug, location, focus, pack),
        "protocol": _protocol(slug, location, focus, pack),
    }
    orders = (
        ("grade", "subjects", "diagnosis", "weekly", "school", "case", "experiment", "parent", "protocol", "transition"),
        ("diagnosis", "grade", "school", "subjects", "weekly", "parent", "case", "experiment", "protocol", "transition"),
        ("school", "grade", "subjects", "case", "diagnosis", "weekly", "experiment", "protocol", "parent", "transition"),
        ("subjects", "diagnosis", "grade", "weekly", "case", "school", "parent", "experiment", "protocol", "transition"),
        ("grade", "school", "diagnosis", "subjects", "parent", "weekly", "protocol", "case", "experiment", "transition"),
        ("grade", "subjects", "weekly", "parent", "diagnosis", "school", "case", "protocol", "experiment", "transition"),
    )
    order = _pick(orders, slug, "section-order")
    body = "".join(fixed + [sections[key] for key in order])
    body += _context_links(location, city, focus)
    body += _faq(slug, location, focus, pack)
    body += _closing(slug, location, focus, pack)
    return _individualize_diction(body, slug)


def individualize_local_elementary_general_body(body: str, slug: str) -> str:
    if not is_local_elementary_general_slug(slug):
        return body
    return build_local_elementary_general_body(slug)
