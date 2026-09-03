from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path

from sitegen.utils import escape


LOCAL_ELEMENTARY_MATH_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)초등수학과외$")
CONTENT_VERSION = "elementary-math-individual-v1"
CONTENT_MARKER = "local-elementary-math-content"
ROOT = Path(__file__).resolve().parents[1]
SCHOOL_CONTEXT_PATH = ROOT / "data" / "local_elementary_school_context.json"


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


def _with(value: str) -> str:
    return _suffix(value, "과", "와")


def is_local_elementary_math_slug(slug: str) -> bool:
    return bool(LOCAL_ELEMENTARY_MATH_PATTERN.fullmatch(slug))


def _focus_from_body(body: str) -> str:
    current = re.search(r'data-elementary-math-focus="([^"]+)"', body, flags=re.I)
    if current:
        return unescape(current.group(1)).strip()
    text = _plain_text(body)
    patterns = (
        r"초등수학과외,?\s*(.+?)(?:을|를)\s*중심으로",
        r"초등수학과외에서는\s*(.+?)(?:을|를)\s*어떻게",
        r"여기서는\s*(.+?)(?:을|를)\s*기준으로",
        r"페이지에서는\s*(.+?)(?:을|를)\s*중심으로",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    return _plain_text(heading.group(1)) if heading else "개념을 설명하는 수학 학습"


def _kind_for_focus(focus: str) -> str:
    if any(word in focus for word in ("분수", "소수", "비율", "비를", "단위분수")):
        return "fractions"
    if any(word in focus for word in ("도형", "각도", "대칭", "전개도", "넓이", "둘레", "거리", "시간", "단위", "회전")):
        return "geometry"
    if any(word in focus for word in ("문장", "문해", "조건", "정보", "미지수", "막대모형", "역산", "질문", "서술형")):
        return "word"
    if any(word in focus for word in ("연산", "암산", "어림", "계산", "실수", "속도", "정확도")):
        return "operations"
    if any(word in focus for word in ("표", "그래프", "평균", "규칙", "일반화")):
        return "data"
    if any(
        word in focus
        for word in (
            "루틴", "복습", "공책", "오답", "부모", "숙제", "계획", "시험", "불안",
            "성공", "도움", "공부", "수행평가", "방학", "예습", "채점", "끈기", "메타인지",
        )
    ):
        return "routine"
    return "number"


ELEMENTARY_PACKS: dict[str, dict[str, str]] = {
    "number": {
        "material": "수 모형·수직선·묶음 그림과 학생이 직접 적은 식",
        "signal": "숫자를 읽는 데서 멈추지 않고 크기, 순서, 자릿값과 연산의 뜻을 설명하는지",
        "action": "같은 수를 말·그림·수직선·식으로 바꾸고 각 표현이 같은 양을 나타내는 이유를 적습니다.",
        "transfer": "수의 크기와 자릿수를 바꾼 뒤에도 기준점을 잡고 비교 순서를 다시 세웁니다.",
        "check": "어림한 범위와 실제 계산값을 비교해 답이 가능한 크기인지 확인합니다.",
        "lower": "1~2학년은 열 개씩 묶기, 수의 순서, 덧셈과 뺄셈의 장면을 조작물과 말로 연결합니다.",
        "middle": "3~4학년은 큰 수와 곱셈·나눗셈을 자릿값, 묶음, 역연산으로 설명합니다.",
        "upper": "5~6학년은 자연수의 구조를 분수·소수·비와 연결하고 풀이 근거를 문장으로 남깁니다.",
        "task": "기준 수를 하나 정해 더 큰 수와 더 작은 수를 만들고, 차이를 그림과 식으로 각각 설명합니다.",
        "parent": "답을 먼저 묻기보다 어떤 수를 기준으로 비교했는지, 그 기준을 다른 표현으로도 보여 줄 수 있는지 질문합니다.",
    },
    "operations": {
        "material": "학생의 세로셈 원본, 암산 기록, 받아올림·받아내림 표시와 검산식",
        "signal": "답의 속도보다 계산 원리와 자릿값, 실수가 생긴 정확한 줄을 스스로 찾는지",
        "action": "계산을 자릿값 단위로 읽고 실수를 숫자 옮김·연산 기호·구구·검산 가운데 하나로 분류합니다.",
        "transfer": "숫자와 배열을 바꾼 계산에서도 같은 원리를 설명하고 알맞은 계산 방법을 선택합니다.",
        "check": "역연산과 어림셈을 모두 사용해 계산 결과와 원래 상황이 맞는지 확인합니다.",
        "lower": "1~2학년은 수 모형과 묶음을 이용해 덧셈·뺄셈이 수량을 어떻게 바꾸는지 말합니다.",
        "middle": "3~4학년은 곱셈·나눗셈 알고리즘을 자릿값과 부분 계산으로 나누어 설명합니다.",
        "upper": "5~6학년은 자연수·분수·소수 연산에서 방법을 고른 이유와 검산 기준을 기록합니다.",
        "task": "일부러 한 줄에 오류가 있는 계산을 제시하고 오류 위치, 원인, 고친 근거를 세 칸에 나누어 적습니다.",
        "parent": "틀렸다는 말보다 어느 줄까지는 맞는지, 다음 줄에서 달라진 수나 기호가 무엇인지 차례로 묻습니다.",
    },
    "word": {
        "material": "교과서 문장제, 조건에 밑줄을 그은 문제지, 막대모형과 학생의 첫 식",
        "signal": "문제의 질문, 필요한 조건, 수 사이의 관계와 식이 각각 무엇을 뜻하는지 설명하는지",
        "action": "질문을 먼저 한 문장으로 바꾸고 조건을 단위와 함께 표시한 뒤 그림이나 표에서 관계를 찾습니다.",
        "transfer": "불필요한 정보나 질문의 순서를 바꾼 문제에서도 필요한 조건만 다시 고릅니다.",
        "check": "식의 각 수와 연산 기호를 원래 문장에 대입해 상황과 맞는지 검토합니다.",
        "lower": "1~2학년은 짧은 덧셈·뺄셈 이야기를 말과 그림으로 다시 만드는 연습을 합니다.",
        "middle": "3~4학년은 두 단계 문장제를 작은 질문으로 나누고 단위가 바뀌는 지점을 표시합니다.",
        "upper": "5~6학년은 비율·속력·평균·분수 문장제에서 기준량과 비교 관계를 식과 문장으로 설명합니다.",
        "task": "정답을 가린 문장제에서 구할 것, 주어진 것, 두 양의 관계, 검산 방법을 네 칸 표에 적습니다.",
        "parent": "어떤 계산을 할지 바로 묻지 않고 무엇을 구하는지와 각 숫자가 어떤 양인지 먼저 말하게 합니다.",
    },
    "fractions": {
        "material": "분수 막대·수직선·영역 모형, 단위분수 표시와 학생의 비교·연산 과정",
        "signal": "분모와 분자를 따로 계산하지 않고 기준이 되는 전체와 한 조각의 크기를 함께 보는지",
        "action": "전체, 같은 크기로 나눈 수, 선택한 조각 수를 표시하고 그림·분수·소수를 같은 위치에 대응합니다.",
        "transfer": "전체의 크기나 분할 수를 바꾼 뒤에도 같은 양과 다른 양을 구분해 설명합니다.",
        "check": "결과가 0·1·기준량 사이 어디에 있어야 하는지 먼저 예상하고 계산값과 비교합니다.",
        "lower": "1~2학년은 반, 똑같이 나누기, 남는 양을 생활 장면과 조작물로 경험합니다.",
        "middle": "3~4학년은 단위분수와 동치분수를 그림과 수직선에서 같은 양으로 확인합니다.",
        "upper": "5~6학년은 분수·소수 연산과 비율에서 기준량, 단위량, 결과의 크기를 함께 검토합니다.",
        "task": "크기가 다른 두 전체를 나눈 그림을 비교하게 하고 분모만 보고 판단할 수 없는 이유를 설명합니다.",
        "parent": "분모가 크면 값도 크냐고 묻기보다 전체가 같은지와 한 조각의 실제 크기를 먼저 가리키게 합니다.",
    },
    "geometry": {
        "material": "직접 그린 도형, 모눈종이, 자·각도기, 접고 펼친 흔적과 측정 단위 기록",
        "signal": "눈에 보이는 모양이 아니라 변·각·평행·대칭·길이와 넓이의 조건으로 판단하는지",
        "action": "주어진 조건과 직접 측정한 값을 다른 색으로 표시하고 도형을 돌리거나 다시 그려 성질을 확인합니다.",
        "transfer": "크기와 방향을 바꾼 도형에서도 변하지 않는 성질과 달라지는 측정값을 구분합니다.",
        "check": "길이·넓이·각도의 단위와 가능한 범위를 확인하고 다른 방법으로 한 번 더 측정합니다.",
        "lower": "1~2학년은 모양을 분류하고 합치고 나누면서 위치와 방향을 정확한 말로 표현합니다.",
        "middle": "3~4학년은 각, 평행, 수직, 둘레와 넓이를 그리기와 실제 측정으로 연결합니다.",
        "upper": "5~6학년은 합동·대칭·입체도형·부피에서 조건을 표시하고 공식의 만들어지는 과정을 설명합니다.",
        "task": "조건만 적힌 도형을 먼저 예상해 그리고 실제 측정 뒤 달라진 점과 유지된 성질을 기록합니다.",
        "parent": "그림이 비슷해 보이는지보다 어떤 변과 각을 근거로 이름을 정했는지 손으로 가리키며 설명하게 합니다.",
    },
    "data": {
        "material": "학생이 만든 표·막대그래프·꺾은선그래프, 분류 기준과 원자료",
        "signal": "표와 그래프의 제목·축·단위·기준을 읽고 보이는 사실과 해석을 구분하는지",
        "action": "원자료를 분류한 기준을 적고 표의 한 행과 그래프의 한 지점이 무엇을 뜻하는지 문장으로 바꿉니다.",
        "transfer": "자료 순서와 그래프 종류를 바꾼 뒤에도 같은 경향과 달라진 강조점을 구분합니다.",
        "check": "전체 자료 수, 합계, 축 간격과 단위를 다시 확인해 빠진 값이나 과장된 변화가 없는지 봅니다.",
        "lower": "1~2학년은 사물을 한 가지 기준으로 분류하고 더 많은 쪽과 적은 쪽을 말합니다.",
        "middle": "3~4학년은 표와 그림그래프·막대그래프에서 단위와 항목을 바꾸어 읽습니다.",
        "upper": "5~6학년은 평균과 비율, 여러 그래프를 비교하며 계산값이 자료에서 뜻하는 범위를 설명합니다.",
        "task": "같은 자료를 표와 그래프로 각각 나타내고 한 표현에서 쉽게 보이는 사실과 놓치기 쉬운 사실을 적습니다.",
        "parent": "가장 큰 값만 묻지 않고 축 간격과 단위, 자료 전체에서 말할 수 있는 사실의 범위를 질문합니다.",
    },
    "routine": {
        "material": "학교 진도표, 학생 공책의 첫 풀이, 일주일 학습 기록과 간격을 둔 재시도",
        "signal": "문제 수보다 시작 행동, 멈춘 이유, 도움을 받은 지점과 다시 혼자 해 본 결과가 남는지",
        "action": "과제를 개념 회상·기본 적용·설명 문제·오답 재시도로 나누고 시작과 종료 기준을 적습니다.",
        "transfer": "학교 일정이나 교재가 바뀌어도 같은 기록 기준으로 다음 과제를 스스로 고릅니다.",
        "check": "맞힌 문제도 오래 걸렸거나 설명하지 못했다면 날짜를 정해 해설 없이 다시 시작합니다.",
        "lower": "1~2학년은 짧은 시작 행동과 수 모형 활동을 반복해 수학 시간을 예측 가능하게 만듭니다.",
        "middle": "3~4학년은 학교 복습, 연산, 문장제, 오답을 서로 다른 목적의 과제로 구분합니다.",
        "upper": "5~6학년은 취약 개념과 중학교 선수 개념을 구분하고 주간 계획과 자기점검을 연결합니다.",
        "task": "일주일 기록에서 시작이 늦어진 날과 설명이 막힌 문제를 골라 다음 주 첫 과제와 재시도 날짜를 정합니다.",
        "parent": "공부한 시간보다 혼자 시작한 과제, 멈춘 이유, 다음에 바꿀 행동을 학생의 말로 정리하게 합니다.",
    },
}


def _load_school_context() -> tuple[dict[str, list[dict[str, object]]], dict[str, str]]:
    if not SCHOOL_CONTEXT_PATH.exists():
        return {}, {}
    data = json.loads(SCHOOL_CONTEXT_PATH.read_text(encoding="utf-8"))
    locations = data.get("locations", {}) if isinstance(data, dict) else {}
    source = data.get("source", {}) if isinstance(data, dict) else {}
    return (
        {str(key): list(value) for key, value in locations.items() if isinstance(value, list)},
        {str(key): str(value) for key, value in source.items()},
    )


ELEMENTARY_SCHOOL_CONTEXT, ELEMENTARY_SCHOOL_SOURCE = _load_school_context()


def _parts(slug: str) -> tuple[str, str, str]:
    location = slug.removesuffix("초등수학과외")
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    return location, city, location.removeprefix(city)


def build_local_elementary_math_meta(slug: str, body: str) -> tuple[str, str]:
    focus = _focus_from_body(body)
    location, _, _ = _parts(slug)
    title_frames = (
        f"{slug} | {_obj(focus)} 학년별로 점검하는 법",
        f"{slug} | {_obj(focus)} 설명하는 초등수학",
        f"{slug} | {_with(focus)} 풀이 기록 설계",
        f"{slug} | {_obj(focus)} 가정학습에 연결하기",
        f"{slug} | {_obj(focus)} 진단하고 복습하는 기준",
    )
    title = _pick(title_frames, slug, "meta-title")
    description_frames = (
        f"{slug}에서 {_obj(focus)} 저·중·고학년별로 확인합니다. {location}의 학교 정보, 첫 풀이 진단, 연산·문장제·도형의 복습 순서와 학부모 질문 기준을 정리했습니다.",
        f"{location} 초등학생의 {_with(focus)} 수학 학습을 실제 풀이 기록으로 살펴봅니다. 1~6학년 단계, 2025년 학교 자료, 주간 재시도와 가정학습 점검 방법을 안내합니다.",
        f"{slug} 검색 뒤 확인할 {_obj(focus)} 구체화했습니다. 학년군별 시작점, 대표 진단 과제, 학교 공식 정보, 오답 재시도와 부모의 관찰 질문을 한 페이지에 담았습니다.",
    )
    description = _pick(description_frames, slug, "meta-description")
    return title, description


def _opening(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    headings = (
        f"{location}초등수학과외에서 {_obj(focus)} 확인하는 첫 기록",
        f"정답보다 먼저 살피는 {location} 학생의 {focus}",
        f"{location} 초등수학, {_obj(focus)} 학년별 행동으로 나누기",
        f"{focus}에서 출발하는 {location} 초등수학 점검",
        f"{location}의 {_obj(focus)} 설명 가능한 학습으로 바꾸기",
        f"첫 풀이로 읽는 {location} 학생의 {focus}",
    )
    paragraphs = (
        f"{location}이라는 지역명만으로 학생의 학교 진도나 수학 수준을 판단할 수는 없습니다. 이 페이지는 {_obj(focus)} 고유한 점검 주제로 삼아 {pack['material']}에서 학생의 첫 판단과 설명, 간격을 둔 재시도를 비교하는 교육 정보를 제공합니다.",
        f"{_topic(focus)} 문제를 많이 푸는 것만으로 확인하기 어렵습니다. {location} 학생이 {pack['signal']}를 실제 공책과 말하기에서 보여 주는지 살피고, 확인된 한 가지 공백부터 학교 수업과 가정학습에 다시 연결합니다.",
        f"같은 학년과 교재를 사용해도 {location} 학생마다 막히는 지점은 다릅니다. {_obj(focus)} 점검할 때는 정답률보다 어떤 표현을 선택했는지, 어디서 도움을 구했는지, 다음 날 첫 단계를 혼자 재현했는지를 함께 봅니다.",
        f"이 페이지는 {location}의 모든 초등학생에게 같은 계획을 권하지 않습니다. {_obj(focus)} 중심으로 저학년의 조작과 말하기, 중학년의 관계 표현, 고학년의 조건·근거 기록을 나누어 현재 행동에서 다음 과제를 정합니다.",
    )
    return (
        f'<section class="elementary-math-block elementary-math-opening" data-content-marker="{CONTENT_MARKER}" '
        f'data-content-version="{CONTENT_VERSION}" data-elementary-math-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(headings, slug, 'opening-heading'))}</h2>"
        f"<p>{escape(_pick(paragraphs, slug, 'opening-paragraph'))}</p></section>"
    )


def _search_intent(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    headings = (
        f"{location}에서 {_obj(focus)} 찾을 때 먼저 구분할 세 가지 목적",
        f"{location}초등수학과외 검색을 실제 {_obj(focus)} 진단으로 바꾸기",
        f"선행·학교 복습·취약 보완에서 달라지는 {location}의 {focus}",
        f"{location} 학생에게 필요한 {_obj(focus)} 자료부터 정하기",
    )
    intros = (
        f"{location}초등수학과외를 찾는 이유가 학교 복습인지, 취약 개념 보완인지, 다음 학기 준비인지에 따라 {_obj(focus)} 확인하는 자료와 종료 기준이 달라집니다. 출발 자료는 {pack['material']}이며 지역명만으로 학교별 난도나 학생 성취를 추정하지 않습니다.",
        f"검색어는 같아도 {location} 학생이 필요한 도움은 서로 다릅니다. {_obj(focus)} 수업 분량으로 바꾸기 전에 {pack['signal']}를 첫 풀이에서 확인하고 학교 진도, 학년, 집에서 가능한 복습 시간을 함께 기록합니다.",
        f"{location}의 {_topic(focus)} 선행 여부보다 목적 구분이 먼저입니다. {pack['material']}을 나란히 놓고 학교 수업 직후 이해, 독립 적용, 며칠 뒤 재현을 서로 다른 항목으로 남겨야 과제의 역할이 선명해집니다.",
    )
    rows = (
        ("학교 수업 연결", "교과서·익힘책과 당일 공책", "설명을 가리고 핵심 개념과 첫 예제를 복원합니다."),
        ("취약 지점 확인", "틀린 문제와 오래 걸린 정답", pack["signal"]),
        ("다음 학기 준비", "선수 개념 한 항목과 변형 문제", pack["transfer"]),
    )
    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(material)}</td><td>{escape(location)}에서 {escape(focus)} 기록: {escape(check)}</td></tr>"
        for label, material, check in rows
    )
    steps = (
        "학생이 혼자 푼 첫 기록을 지우지 않고 멈춘 위치와 사용 시간을 표시합니다.",
        pack["action"],
        pack["check"],
        f"{location}의 생활 일정 안에서 이틀 이상 간격을 둔 재시도 날짜와 다음 질문을 정합니다.",
    )
    shift = _stable_index(slug, "search-steps") % len(steps)
    steps = steps[shift:] + steps[:shift]
    items = "".join(f"<li>{escape(step)} {escape(location)}의 {escape(focus)} 점검표에 결과를 남깁니다.</li>" for step in steps)
    closings = (
        f"이 순서를 사용하면 {location}에서 {_obj(focus)} 공부할 때 문제집을 먼저 늘리지 않고 현재 가능한 행동과 다음 한 단계를 구분할 수 있습니다.",
        f"{location} 학생의 {_topic(focus)} 한 번의 정답보다 간격 뒤 재현으로 판단합니다. 그래야 선행 분량이 현재 학년의 설명 공백을 가리는 일을 줄일 수 있습니다.",
        f"목표가 정해지면 {location}의 {_obj(focus)} 연산·개념·적용·재시도 가운데 어느 과제로 배치할지도 구체적으로 결정할 수 있습니다.",
    )
    return (
        f'<section class="elementary-math-block elementary-math-search-intent" data-search-intent="local-elementary-math">'
        f"<h2>{escape(_pick(headings, slug, 'search-heading'))}</h2>"
        f"<p>{escape(_pick(intros, slug, 'search-intro'))}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>학습 목적</th><th>먼저 볼 자료</th><th>확인할 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(location)} 학생의 {escape(focus)} 시작 순서는 다음 네 단계로 기록합니다.</p><ol>{items}</ol>"
        f"<p>{escape(_pick(closings, slug, 'search-closing'))}</p></section>"
    )


def _grade_plan(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    headings = (
        f"1~6학년에서 달라지는 {location}의 {focus} 지도",
        f"{location} 학생의 {_obj(focus)} 세 학년군으로 나누는 기준",
        f"저·중·고학년을 잇는 {location} {focus} 학습",
        f"선행 진도보다 먼저 볼 {location}의 {focus} 학년 단계",
    )
    grade_rows = [
        ("1~2학년", pack["lower"], "조작하고 말하기"),
        ("3~4학년", pack["middle"], "관계를 그림과 식으로 옮기기"),
        ("5~6학년", pack["upper"], "조건·근거·검산을 기록하기"),
    ]
    shift = _stable_index(slug, "grade-order") % 3
    grade_rows = grade_rows[shift:] + grade_rows[:shift]
    sections = "".join(
        f"<h3>{escape(location)} {escape(label)}의 {escape(focus)}: {escape(key)}</h3>"
        f"<p>{escape(text)} {escape(location)} 학생에게는 정답 수가 아니라 이 행동을 혼자 설명하고 다른 문제에 옮기는지까지 확인합니다.</p>"
        for label, text, key in grade_rows
    )
    closings = (
        f"학년이 같아도 {location} 학생의 시작점은 다릅니다. {_obj(focus)} 막는 선수 개념 하나만 짧게 복원한 뒤 현재 학년의 교과서 문제에서 즉시 사용하게 하면 무관한 반복을 줄일 수 있습니다.",
        f"{location}에서 {_obj(focus)} 선행 진도표만으로 정하지 않습니다. 혼자 가능한 단계, 질문 뒤 가능한 단계, 다시 배울 단계를 나누면 학년별 과제의 깊이와 문제 수를 현실적으로 조절할 수 있습니다.",
        f"저학년에게 기록을 과하게 요구하거나 고학년에게 암산만 반복시키지 않습니다. {location}의 {_topic(focus)} 표현 방법과 설명 길이를 바꾸되 근거를 남기고 다시 시도하는 기준은 이어 갑니다.",
    )
    return (
        f'<section class="elementary-math-block elementary-math-grade" data-grade-bands="1-2,3-4,5-6">'
        f"<h2>{escape(_pick(headings, slug, 'grade-heading'))}</h2>{sections}"
        f"<p>{escape(_pick(closings, slug, 'grade-closing'))}</p></section>"
    )


def _concept_map(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    headings = (
        f"{location}의 {_obj(focus)} 연산·개념·적용으로 분리해 보기",
        f"한 문제를 세 번 읽는 {location} {focus} 학습 지도",
        f"{location} 학생의 {_obj(focus)} 표현·관계·전이로 확인하기",
        f"문제 수보다 깊이를 정하는 {location}의 {focus} 기준",
    )
    rows = [
        ("표현", pack["material"], "학생이 선택한 말·그림·표·식이 같은 뜻인지 확인합니다."),
        ("관계", pack["action"], "조건과 연산, 측정값 사이의 연결을 학생의 문장으로 남깁니다."),
        ("전이", pack["transfer"], "숫자·모양·질문이 바뀐 뒤에도 같은 개념을 다시 찾는지 봅니다."),
    ]
    shift = _stable_index(slug, "concept-order") % 3
    rows = rows[shift:] + rows[:shift]
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)}의 {escape(label)} 점검</h3>"
        f"<p><strong>먼저 볼 자료와 행동:</strong> {escape(material)} {escape(action)} 이때 {escape(location)} 학생의 첫 풀이와 수정한 풀이를 나란히 보관해 바뀐 판단을 확인합니다.</p>"
        for number, (label, material, action) in enumerate(rows, 1)
    )
    closing = _pick(
        (
            f"세 기록 가운데 하나만 비어 있어도 {location}의 {_obj(focus)} 같은 문제 반복으로 채우지 않습니다. 비어 있는 연결을 짧은 대표 과제에서 보완한 뒤 다른 단원으로 옮깁니다.",
            f"{location} 학생이 {_obj(focus)} 설명할 때 정답과 과정이 모두 맞아도 새 조건에서 시작하지 못하면 전이 단계가 남아 있습니다. 다음 과제는 난도보다 표현 변화를 기준으로 정합니다.",
            f"표현·관계·전이는 순위를 매기는 점수가 아닙니다. {location}에서 {_obj(focus)} 어느 연결에서 막히는지 찾고 그 연결에 맞는 도구와 질문을 고르는 분류 기준입니다.",
        ),
        slug,
        "concept-closing",
    )
    return (
        f'<section class="elementary-math-block elementary-math-concept-map" data-concept-map="expression-relation-transfer">'
        f"<h2>{escape(_pick(headings, slug, 'concept-heading'))}</h2>{content}<p>{escape(closing)}</p></section>"
    )


def _diagnosis(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}에서 바로 해 볼 {focus} 짧은 진단",
            f"첫 풀이를 지우지 않는 {location} {focus} 관찰 과제",
            f"{location} 학생의 {_obj(focus)} 짧게 확인하는 방법",
            f"설명과 재시도를 함께 보는 {location} {focus} 진단",
        ),
        slug,
        "diagnosis-heading",
    )
    intro = _pick(
        (
            f"{location} 학생에게 새 교재 전체를 풀게 하기 전에 {pack['task']} 정답 여부와 함께 시작까지 걸린 시간, 선택한 표현, 질문 뒤 바뀐 행동을 기록하면 {_topic(focus)} 어느 단계에서 흔들리는지 볼 수 있습니다.",
            f"{location}의 {_obj(focus)} 성적을 매기는 시험이 아니라 다음 과제를 고르는 관찰로 사용합니다. 대표 활동은 ‘{pack['task']}’이며 풀이를 지우지 않고 학생이 멈춘 위치와 이유를 직접 표시하게 합니다.",
            f"짧은 진단에서는 {location} 학생의 {_obj(focus)} 한 번의 성공으로 판단하지 않습니다. {pack['task']} 활동 직후 설명과 이틀 뒤 첫 단계 재현을 비교해 도움에 의존한 부분을 구분합니다.",
        ),
        slug,
        "diagnosis-intro",
    )
    checks = (
        f"시작: {pack['signal']}",
        f"수정: {pack['action']}",
        f"검산: {pack['check']}",
        f"재시도: {pack['transfer']}",
    )
    items = "".join(f"<li>{escape(location)} {escape(focus)} — {escape(item)}</li>" for item in checks)
    closing = _pick(
        (
            f"{location}의 진단 결과는 ‘잘함·못함’으로 끝내지 않습니다. {_obj(focus)} 혼자 설명 가능, 한 질문 뒤 가능, 개념 복원이 필요한 단계로 나누고 다음 주에 다시 볼 날짜까지 정합니다.",
            f"이 기록을 사용하면 {location}에서 {_obj(focus)} 위해 문제 수를 무조건 늘리는 일을 피할 수 있습니다. 학생이 스스로 바꿀 수 있는 한 행동을 다음 과제로 선택합니다.",
            f"{location} 학생의 {_topic(focus)} 활동 직후보다 간격 뒤 재현이 중요합니다. 같은 도구 없이 첫 판단을 다시 말할 수 있을 때 독립 적용에 가까워졌다고 봅니다.",
        ),
        slug,
        "diagnosis-closing",
    )
    return f'<section class="elementary-math-block elementary-math-diagnosis"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ul>{items}</ul><p>{escape(closing)}</p></section>'


def _weekly_plan(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 생활 리듬에 맞춘 {focus} 주간 계획",
            f"학교 수업·가정학습·재시도를 잇는 {location} {focus} 일정",
            f"{location} 학생의 {_obj(focus)} 평일과 주말에 나누기",
            f"분량 대신 과제 역할을 정하는 {location} {focus} 계획표",
        ),
        slug,
        "weekly-heading",
    )
    intro = _pick(
        (
            f"{location} 안에서도 통학, 방과 후 활동, 가족 일정은 학생마다 다릅니다. {_obj(focus)} 매일 같은 분량으로 배치하기보다 집중 시간이 짧은 날에는 개념 회상, 여유 있는 날에는 변형 적용, 주말에는 해설 없는 재시도를 둡니다.",
            f"{location} 학생의 {_topic(focus)} 공부시간 총합보다 과제의 역할이 분명해야 이어집니다. 학교 수업 당일에는 핵심 표현을 복원하고 중간에는 {pack['action']} 주말에는 {pack['check']}",
            f"주간 계획에서 {location}의 {_obj(focus)} 연산·개념·설명·오답으로 나눕니다. 피로가 큰 날에는 짧은 정확성 과제를 두고 사고가 필요한 활동과 {pack['transfer']} 과정은 여유 있는 날로 옮깁니다.",
        ),
        slug,
        "weekly-intro",
    )
    rows = (
        ("수업 당일", "짧게 시작", "교과서 핵심 표현과 첫 예제를 가리고 복원"),
        ("주중 적용", "집중 가능한 범위", pack["action"]),
        ("주말 재시도", "여유 있게 확인", pack["check"]),
        ("다음 주 연결", "마무리 점검", "막힌 이유와 다음 과제 한 가지를 학생이 직접 선택"),
    )
    row_html = "".join(
        f"<tr><td>{escape(when)}</td><td>{escape(time)}</td><td>{escape(location)}의 {escape(focus)}: {escape(task)}</td></tr>"
        for when, time, task in rows
    )
    closing = _pick(
        (
            f"시간은 {location} 학생의 집중 지속 시간에 맞춰 줄이거나 늘립니다. {_obj(focus)} 기록할 때는 페이지 수보다 시작 시각, 도움 횟수, 종료 기준, 재시도 날짜가 남아야 계획을 실제로 조정할 수 있습니다.",
            f"{location}에서 {_obj(focus)} 위한 계획을 지키지 못한 날에는 밀린 분량을 다음 날 더하지 않습니다. 시작을 막은 일정과 과제 난도를 기록하고 가장 작은 복원 활동으로 다시 연결합니다.",
            f"방학에도 {location} 학생의 {_obj(focus)} 새 진도만 채우지 않습니다. 학교 복습과 취약 개념, 설명 문제, 휴식일을 구분해 개학 뒤 유지 가능한 리듬을 남깁니다.",
        ),
        slug,
        "weekly-closing",
    )
    return (
        f'<section class="elementary-math-block elementary-math-weekly-plan"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>'
        f'<div class="table-wrap"><table><thead><tr><th>시점</th><th>권장 범위</th><th>과제 역할</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(closing)}</p></section>"
    )


def _school_section(slug: str, location: str, focus: str) -> str:
    schools = ELEMENTARY_SCHOOL_CONTEXT.get(location, [])[:4]
    heading = _pick(
        (
            f"{location} 초등학교 자료와 {focus} 계획을 함께 보는 법",
            f"주소 기준으로 확인한 {location} 초등학교 공식 정보",
            f"{location} 학교 정보를 {_with(focus)} 연결할 때의 주의점",
            f"통계로 성취를 추정하지 않는 {location} {focus} 학교 자료 읽기",
        ),
        slug,
        "school-heading",
    )
    intro = (
        f"아래 학교는 한국교육개발원 교육통계의 2025년 4월 1일 학교 주소에 ‘{location.removeprefix(next(prefix for prefix in ('부산', '양산', '구미') if location.startswith(prefix)))}’ 표기가 있는 초등학교만 연결했습니다. "
        f"학생 수와 학급 수는 학교 선택이나 {focus} 성취를 평가하는 지표가 아니며, 최신 일정과 교육과정은 각 학교 공식 홈페이지에서 다시 확인해야 합니다."
    )
    if schools:
        items: list[str] = []
        for school in schools:
            name = str(school.get("name") or "")
            homepage = str(school.get("homepage") or "")
            students = int(school.get("students") or 0)
            classes = int(school.get("classes") or 0)
            grade_students = school.get("grade_students") or {}
            lower = sum(int(grade_students.get(str(grade), 0)) for grade in (1, 2)) if isinstance(grade_students, dict) else 0
            middle = sum(int(grade_students.get(str(grade), 0)) for grade in (3, 4)) if isinstance(grade_students, dict) else 0
            upper = sum(int(grade_students.get(str(grade), 0)) for grade in (5, 6)) if isinstance(grade_students, dict) else 0
            label = escape(name)
            if homepage:
                label = f'<a class="source-link" href="{escape(homepage)}" target="_blank" rel="noopener noreferrer external">{label} 공식 홈페이지</a>'
            items.append(
                f"<li><strong>{label}</strong> — 2025년 기준 학생 {students:,}명, 편성 학급 {classes:,}개, "
                f"1~2학년 {lower:,}명·3~4학년 {middle:,}명·5~6학년 {upper:,}명입니다. "
                f"{escape(location)}의 {escape(focus)} 계획은 이 규모가 아니라 학생 개인의 학교 진도와 첫 풀이로 정합니다.</li>"
            )
        list_html = f"<ul>{''.join(items)}</ul>"
        closing = (
            f"{location}에 학교가 여러 곳이어도 학교명만으로 교재, 시험 방식, 숙제량을 단정하지 않습니다. {_obj(focus)} 지도할 때는 재학 학교의 실제 안내와 학생이 받은 자료를 우선하고 통계는 지역의 학교 정보를 확인하는 참고 자료로만 사용합니다."
        )
    else:
        list_html = ""
        closing = (
            f"2025년 자료에서 주소의 읍·면·동 명칭이 {location}과 정확히 일치하는 초등학교를 확인하지 못했습니다. 가까워 보이는 다른 동의 학교를 임의로 넣지 않았으며, {_obj(focus)} 계획할 때는 학생이 실제 재학 중인 학교의 공식 안내와 수업 자료를 직접 확인합니다."
        )
    return (
        f'<section class="elementary-math-block elementary-math-school-context" data-school-count="{len(schools)}">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>{list_html}<p>{escape(closing)}</p></section>"
    )


def _student_case(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    grade_bands = ("1~2학년", "3~4학년", "5~6학년")
    grade = _pick(grade_bands, slug, "case-grade")
    heading = _pick(
        (
            f"{location} {grade} 학생의 {focus} 변화 기록 예시",
            f"{focus} 과제를 조정한 {location} {grade} 합성 사례",
            f"문제 수를 늘리기 전에 바꾼 {location} 학생의 {focus}",
            f"{location} 가정학습에서 {_obj(focus)} 다시 설계한 과정",
        ),
        slug,
        "case-heading",
    )
    intro = (
        f"다음은 {location} 학생 한 명의 실제 상담 기록이 아니라 반복되는 학습 장면을 교육적으로 재구성한 {grade} 합성 사례입니다. "
        f"{_obj(focus)} 점검할 때 진단명이나 성적 향상을 꾸며내지 않고 관찰 가능한 풀이 행동과 다음 재시도만 보여 줍니다."
    )
    rows = (
        ("첫 관찰", pack["signal"], "첫 풀이와 말하기를 그대로 보관"),
        ("과제 조정", pack["action"], "대표 문제 두 개에서 표현과 근거를 수정"),
        ("간격 뒤 확인", pack["transfer"], "도움 없이 시작한 줄과 검산을 비교"),
    )
    row_html = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(location)} {escape(grade)}의 {escape(focus)}: {escape(record)}</td><td>{escape(next_step)}</td></tr>"
        for stage, record, next_step in rows
    )
    steps = (
        f"{location} 학생이 첫 문제를 풀 때 질문과 설명을 중간에 대신하지 않습니다.",
        f"{_obj(focus)} 한 가지 행동으로 줄여 같은 날 짧게 두 번 적용합니다.",
        f"이틀 뒤 {pack['check']} 다음 주 과제를 학생과 함께 정합니다.",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"이 합성 사례의 목표는 {location}에서 {_obj(focus)} 며칠 만에 완성했다는 결론이 아닙니다. 도움의 위치를 줄이고 학생이 막힌 이유와 다음 행동을 더 구체적으로 말하는 변화를 확인하는 데 있습니다.",
            f"{location}의 {_topic(focus)} 정답률 한 번보다 수정 이유와 간격 뒤 재현으로 봅니다. 같은 행동이 다른 숫자와 단원에서도 이어질 때 다음 난도나 선행 범위를 결정합니다.",
            f"합성 사례는 {location} 학생에게 그대로 적용할 처방이 아닙니다. {_obj(focus)} 위한 과제 시간과 표현 방법은 실제 학년, 교재, 학교 진도, 피로도에 맞춰 다시 조정해야 합니다.",
        ),
        slug,
        "case-closing",
    )
    return (
        f'<section class="elementary-math-block elementary-math-student-case" data-case-model="composite" data-case-grade="{grade}">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>단계</th><th>관찰 기록</th><th>다음 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<ol>{items}</ol><p>{escape(closing)}</p></section>"
    )


def _parent_coaching(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 가정에서 {focus} 설명을 끌어내는 질문",
            f"정답을 대신하지 않는 {location} {focus} 학부모 대화",
            f"{location} 학생의 {_obj(focus)} 관찰 가능한 행동으로 묻기",
            f"칭찬과 도움의 위치를 정하는 {location} {focus} 기준",
        ),
        slug,
        "parent-heading",
    )
    intro = _pick(
        (
            f"{location} 가정에서 {_obj(focus)} 도울 때 ‘왜 이것도 모르니’나 ‘천천히 다시 해’처럼 넓은 말은 다음 행동을 알려 주지 못합니다. {pack['parent']} 학생이 답하면 부모는 맞고 틀림보다 사용한 근거를 다시 짚습니다.",
            f"학부모가 {_obj(focus)} 모두 설명하면 {location} 학생의 독립 수준을 보기 어렵습니다. {pack['parent']} 질문 하나 뒤에는 학생이 그림·말·식 가운데 표현을 선택하고 수정할 시간을 둡니다.",
            f"{location}의 {_topic(focus)} 숙제 완료 여부만으로 확인하지 않습니다. {pack['parent']} 도움 뒤에는 어느 단계부터 혼자 이어 갔는지와 다음 날 같은 기준을 다시 사용할 수 있는지 기록합니다.",
        ),
        slug,
        "parent-intro",
    )
    questions = (
        "문제에서 무엇을 구하라고 했는지 한 문장으로 말할 수 있나요?",
        "처음 선택한 그림이나 식은 어떤 조건을 보여 주나요?",
        "막힌 줄 바로 앞까지는 무엇을 알고 있었나요?",
        "답이 가능한 크기와 단위인지 어떻게 확인할 수 있나요?",
        f"{focus}의 기준을 숫자가 다른 문제에도 사용할 수 있나요?",
    )
    shift = _stable_index(slug, "parent-question-order") % len(questions)
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(location)} {escape(focus)} 질문: {escape(question)}</li>" for question in questions)
    closing = _pick(
        (
            f"질문은 {location} 학생의 매 문제에 모두 사용하지 않습니다. {_obj(focus)} 대표 문제 두세 개에서만 깊게 설명하게 하고 나머지는 학생이 같은 기준으로 혼자 적용하도록 기다립니다.",
            f"칭찬도 ‘수학을 잘한다’보다 {location} 학생이 {_obj(focus)} 위해 조건을 다시 표시한 행동, 풀이를 지우지 않고 오류를 찾은 행동처럼 반복 가능한 장면에 붙입니다.",
            f"{location} 가정에서 {_obj(focus)} 묻는 대화가 길어지면 학생이 부모의 답을 기다릴 수 있습니다. 질문 하나, 생각 시간, 학생의 선택, 짧은 확인 순서로 끝냅니다.",
        ),
        slug,
        "parent-closing",
    )
    return f'<section class="elementary-math-block elementary-math-parent"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ul>{items}</ul><p>{escape(closing)}</p></section>'


def _transfer(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}에서 {focus} 학습이 끝났다고 보는 기준",
            f"같은 유형 정답 뒤에 확인할 {location} {focus} 전이",
            f"{location} 학생의 {_obj(focus)} 새 문제로 옮기는 세 단계",
            f"도움 직후가 아닌 다음 날 보는 {location}의 {focus}",
        ),
        slug,
        "transfer-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 같은 문제를 맞힌 것만으로 {_subject(focus)} 자리 잡았다고 판단하지 않습니다. 표현 하나를 바꾸고, 숫자나 조건을 바꾸고, 시간을 둔 뒤 다시 시작하는 세 단계에서 같은 기준을 꺼내 쓰는지 확인합니다.",
            f"{_obj(focus)} 설명할 수 있어도 {location} 학생이 새 조건에서 시작하지 못하면 전이 과제가 필요합니다. {pack['transfer']} 이때 힌트는 답이 아니라 첫 판단을 떠올릴 최소한의 질문으로 제한합니다.",
            f"{location}의 {_topic(focus)} 학습 당일보다 이틀 뒤 기록이 중요합니다. {pack['check']} 학생이 수정 이유까지 말하면 다음 단원에 연결하고, 설명이 사라지면 같은 대표 과제로 되돌아갑니다.",
        ),
        slug,
        "transfer-intro",
    )
    steps = (
        f"표현 전이: {location}의 {focus} 문제를 말·그림·표·식 가운데 다른 방식으로 바꿉니다.",
        f"조건 전이: {pack['transfer']}",
        f"시간 전이: 이틀 이상 뒤에 {pack['check']}",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"세 단계가 모두 가능할 때 {location} 학생의 {_obj(focus)} 다음 난도와 단원으로 넓힙니다. 하나가 흔들리면 많은 문제를 추가하기보다 해당 전이만 짧게 다시 설계합니다.",
            f"{location}에서 {_obj(focus)} 완벽하게 말하는 것이 목표는 아닙니다. 학생의 학년에 맞는 말과 그림으로 근거를 남기고 새 문제에서 첫 행동을 스스로 선택하면 다음 단계로 볼 수 있습니다.",
            f"전이 기록은 {location} 학생을 비교하는 점수가 아닙니다. {_obj(focus)} 어떤 조건에서 유지하고 어떤 조건에서 잃는지 찾아 다음 주 과제를 더 정확하게 고르는 자료입니다.",
        ),
        slug,
        "transfer-closing",
    )
    return f'<section class="elementary-math-block elementary-math-transfer"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ol>{items}</ol><p>{escape(closing)}</p></section>'


def _error_map(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 학생의 {focus} 오류를 다섯 갈래로 기록하기",
            f"틀린 답 하나에서 분리하는 {location} {focus} 학습 신호",
            f"{location}의 {_obj(focus)} 개념·표현·조건·계산·재현으로 점검하기",
            f"같은 오답을 반복하지 않는 {location} {focus} 오류 지도",
        ),
        slug,
        "error-map-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 {_obj(focus)} 다룬 문제에서 틀렸다고 해서 원인이 모두 개념 부족인 것은 아닙니다. 첫 풀이를 남긴 채 개념 기억, 표현 선택, 조건 읽기, 계산·단위, 간격 뒤 재현을 따로 표시하면 같은 정답률 안에서도 다음 과제가 달라집니다.",
            f"오답노트에 정답 풀이만 옮기면 {location} 학생의 {_obj(focus)} 어느 순간에 잃었는지 사라집니다. 아래 다섯 갈래는 학생을 평가하는 등급이 아니라 도움을 줄 위치와 다시 혼자 풀 날짜를 정하기 위한 관찰 지도입니다.",
            f"{location}의 {_topic(focus)} 맞힌 문제에서도 확인할 수 있습니다. 지나치게 오래 걸렸거나 근거를 말하지 못했거나 부모의 첫 문장을 기다렸다면 해당 문제를 성공으로 지우지 않고 어떤 연결이 약했는지 분류합니다.",
        ),
        slug,
        "error-map-intro",
    )
    rows = [
        (
            "개념 기억",
            f"{pack['material']}에서 정의나 원리를 가렸을 때 핵심 뜻을 자기 말로 복원하는지 봅니다.",
            "교과서 예시 하나를 말·그림과 함께 다시 만들고 다음 날 같은 뜻을 설명합니다.",
        ),
        (
            "표현 선택",
            f"{pack['signal']}를 살피며 말·그림·표·식 가운데 왜 그 표현을 골랐는지 묻습니다.",
            "한 표현을 다른 표현으로 바꾸되 계산 결과보다 두 표현의 대응을 먼저 표시합니다.",
        ),
        (
            "조건 읽기",
            "질문, 수치, 단위, 제외할 정보와 숨어 있는 관계를 풀이 전에 구분했는지 확인합니다.",
            "구할 것 한 줄과 필요한 조건만 남긴 뒤 빠진 조건이 없는지 원문과 대조합니다.",
        ),
        (
            "계산과 검산",
            f"계산 과정에서 자릿값·기호·단위가 유지되는지 보고 {pack['check']}",
            "오류가 난 한 줄만 고친 뒤 역연산, 어림, 그림 가운데 다른 방법으로 결과를 검토합니다.",
        ),
        (
            "독립 재현",
            f"도움을 받은 직후가 아니라 이틀 이상 지나 {pack['transfer']}",
            "힌트 없이 시작한 첫 행동과 멈춘 위치를 이전 기록과 비교해 다음 과제의 크기를 정합니다.",
        ),
    ]
    shift = _stable_index(slug, "error-map-order") % len(rows)
    rows = rows[shift:] + rows[:shift]
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)}의 {escape(label)} 오류</h3>"
        f"<p>{escape(observe)} {escape(location)} 학생의 기록에는 ‘{escape(action)}’라는 다음 행동과 재시도 날짜를 함께 남겨 같은 유형의 답만 외우는 일을 피합니다.</p>"
        for index, (label, observe, action) in enumerate(rows, 1)
    )
    closing = _pick(
        (
            f"다섯 갈래가 동시에 흔들려 보여도 {location}의 {_obj(focus)} 한 주에 모두 고치려 하지 않습니다. 현재 학교 단원에 가장 직접적인 한 갈래를 먼저 바꾸고, 다른 표현과 간격 뒤 재시도에서도 유지되면 다음 오류로 이동합니다.",
            f"{location} 학생의 오류 지도에는 점수 대신 증거를 씁니다. {_obj(focus)} 혼자 설명한 문장, 수정한 줄, 확인한 단위, 힌트를 줄인 횟수를 남기면 학부모와 학생이 다음 학습의 이유를 함께 이해할 수 있습니다.",
            f"오류 분류가 바뀌는 것도 {location}에서 {_obj(focus)} 배우는 과정입니다. 처음에는 개념 문제로 보였지만 표현을 바꾸자 해결되거나, 계산은 맞지만 이틀 뒤 시작하지 못했다면 새 기록에 맞춰 과제와 질문을 다시 선택합니다.",
        ),
        slug,
        "error-map-closing",
    )
    return (
        f'<section class="elementary-math-block elementary-math-error-map" data-error-map="five-signals">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>{content}<p>{escape(closing)}</p></section>"
    )


def _focus_protocol(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 관찰 프로토콜",
            f"여섯 번의 기록으로 구분하는 {location} 학생의 {focus}",
            f"{location}에서 {_obj(focus)} 수업 전후로 확인하는 순서",
            f"한 주 동안 추적하는 {location} {focus} 실행 기록",
            f"{location} 학생의 {_obj(focus)} 여섯 장의 학습 카드로 남기기",
        ),
        slug,
        "protocol-heading",
    )
    intros = (
        f"{location} 학생의 {_obj(focus)} 하루의 긴 시험으로 결론 내리지 않습니다. 서로 목적이 다른 여섯 번의 짧은 기록을 남기면 처음부터 알고 있던 부분, 질문 뒤 가능해진 부분, 표현을 바꾸자 드러난 부분, 검산과 간격 뒤에도 남은 부분을 구분할 수 있습니다.",
        f"{_topic(focus)} 학습 직후에는 익숙한 문제와 교사의 설명이 기억에 남아 실제 독립 수준보다 높게 보일 수 있습니다. {location}에서는 첫 풀이·표현 전환·조건 변형·간격 재현을 다른 날의 카드로 나눠 도움의 위치가 줄어드는지 살핍니다.",
        f"{location}의 {_obj(focus)} 점검하는 여섯 카드는 성적표가 아닙니다. 각 카드에는 문제 수보다 선택한 표현, 멈춘 이유, 사용한 힌트, 검산, 다음 날짜를 적어 학생과 학부모가 과제를 바꾼 근거를 이해하게 합니다.",
    )
    materials = (
        "교과서에서 아직 풀지 않은 대표 문제",
        "학생이 전날 틀린 문제의 숫자를 바꾼 과제",
        "정답과 풀이 순서를 가린 익힘책 예제",
        "말·그림·표·식 중 한 표현을 비워 둔 활동지",
        "단위와 질문의 순서를 바꾼 짧은 문장제",
        "일부 조건만 표시한 학생 공책의 복사본",
        "같은 개념을 생활 장면으로 바꾼 구두 문제",
        "오류 한 줄이 섞인 가상 학생의 풀이",
        "답의 범위만 제시한 역방향 문제",
        "두 풀이 중 근거가 더 분명한 것을 고르는 카드",
        "도구 없이 기억에서 다시 만드는 개념 예시",
        "학생이 질문과 조건을 직접 채우는 빈 문제",
    )
    actions = (
        "처음 90초 동안 질문하지 않고 손과 시선의 움직임을 관찰합니다.",
        "사용한 수와 기호 옆에 원래 조건을 짧게 대응시킵니다.",
        "정답을 가린 채 첫 번째 판단만 한 문장으로 녹음하거나 적습니다.",
        "틀린 줄을 지우지 않고 그 앞뒤에서 바뀐 정보를 표시합니다.",
        "그림을 식으로, 식을 말로 바꾸며 빠진 관계를 찾습니다.",
        "학생이 힌트의 종류를 고르고 도움 뒤 혼자 이어 간 줄을 표시합니다.",
        "문제의 숫자 하나를 바꾼 뒤 그대로 유지되는 풀이 기준을 말합니다.",
        "예상한 답의 범위를 먼저 적고 계산값이 그 범위에 드는지 봅니다.",
        "두 방법의 공통 조건과 서로 다른 계산 단계를 색으로 나눕니다.",
        "풀이가 끝난 뒤 문제를 보지 않고 사용한 조건의 순서를 복원합니다.",
        "부모가 말한 문장과 학생이 스스로 말한 문장을 따로 기록합니다.",
        "다음에 같은 오류를 만나면 할 첫 행동을 학생이 직접 정합니다.",
    )
    evidence = (
        "혼자 시작한 첫 표현과 시작까지 걸린 시간",
        "질문을 요청한 정확한 줄과 질문의 내용",
        "처음 선택한 전략을 바꾼 이유",
        "단위·기호·조건을 다시 확인한 위치",
        "정답을 본 뒤가 아니라 보기 전에 남긴 어림",
        "다른 표현으로 바꾸면서 새로 찾은 관계",
        "오류를 고친 근거와 고치지 않은 부분",
        "설명 없이 재현한 첫 두 단계",
        "학생이 스스로 정한 종료 기준",
        "다음 재시도에서 줄일 힌트 한 가지",
        "맞았지만 오래 걸린 단계의 원인",
        "새 문제에서 그대로 사용한 판단 기준",
    )
    closings = (
        f"여섯 카드가 끝나면 {location} 학생의 {_obj(focus)} 문제 수로 합산하지 않습니다. 혼자 시작한 카드, 표현을 바꾼 카드, 조건이 달라도 유지한 카드, 검산을 선택한 카드, 간격 뒤 재현한 카드를 구분해 가장 약한 연결 하나만 다음 주 첫 과제로 옮깁니다.",
        f"{location}의 {_topic(focus)} 여섯 번 모두 완벽해야 다음 단원으로 가는 것이 아닙니다. 학생이 도움을 요청할 위치를 구체적으로 말하고 같은 힌트를 반복해서 기다리지 않으며 검산 기준을 선택하면 난도와 범위를 조금씩 넓힐 수 있습니다.",
        f"이 프로토콜은 {location} 학생의 학년과 피로도에 맞춰 시간을 줄여도 됩니다. {_obj(focus)} 확인하는 핵심은 여섯 카드를 모두 채우는 일이 아니라 첫 기록을 보존하고 서로 다른 조건에서 같은 판단이 남는지 비교하는 데 있습니다.",
        f"{location}에서 {_obj(focus)} 위한 여섯 카드 중 하나를 빠뜨렸다면 밀린 활동처럼 몰아서 하지 않습니다. 학교 진도와 연결되는 카드를 우선하고 나머지는 다음 주에 배치해 독립 재현을 관찰할 간격을 확보합니다.",
    )
    content: list[str] = []
    for index in range(6):
        duration = 11 + _stable_index(slug, f"protocol-duration-{index}") % 13
        gap = 1 + _stable_index(slug, f"protocol-gap-{index}") % 4
        material = _pick(materials, slug, f"protocol-material-{index}")
        action = _pick(actions, slug, f"protocol-action-{index}")
        record = _pick(evidence, slug, f"protocol-evidence-{index}")
        stage = ("첫 풀이", "표현 전환", "조건 변형", "오류 설명", "검산 선택", "간격 재현")[index]
        content.append(
            f"<h3>{escape(location)} {escape(focus)} {escape(stage)} 카드</h3>"
            f"<p>{escape(material)}을 사용해 학생이 집중할 수 있는 짧은 시간 동안 {escape(action)} {escape(location)}의 {escape(focus)} 카드에는 "
            f"{escape(record)}을 남기고, 간격을 둔 뒤 같은 도구 없이 시작할 한 문제와 부모가 줄일 힌트를 정합니다. "
            f"이 카드의 목적은 {escape(focus)} 정답 수가 아니라 {escape(location)} 학생이 자신의 판단을 다시 선택하는지 확인하는 것입니다.</p>"
        )
    return (
        f'<section class="elementary-math-block elementary-math-focus-protocol" data-protocol-cards="6">'
        f"<h2>{escape(heading)}</h2><p>{escape(_pick(intros, slug, 'protocol-intro'))}</p>"
        f"{''.join(content)}<p>{escape(_pick(closings, slug, 'protocol-closing'))}</p></section>"
    )


def _context_links(slug: str, location: str, city: str, focus: str) -> str:
    links = (
        (f"/{city}초등수학과외/", f"{city} 초등수학 학년별 학습 기준"),
        (f"/{location}수학과외/", f"{location} 수학과외의 연령별 연결 구조"),
    )
    items = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for href, label in links)
    intro = (
        f"{location}의 {_obj(focus)} 확인한 다음 필요한 상위 범위만 이어 보도록 두 페이지를 골랐습니다. 모든 키워드를 링크로 만들지 않고 도시 단위 초등수학 기준과 같은 지역의 수학 학습 구조만 연결합니다."
    )
    return (
        f'<aside class="elementary-math-context-links" data-link-count="2"><h2>{escape(location)} {escape(focus)} 다음에 볼 학습 기준</h2>'
        f"<p>{escape(intro)}</p><ul>{items}</ul></aside>"
    )


def _faq(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    questions = (
        f"{location}에서 {_obj(focus)} 초등 몇 학년부터 확인해야 하나요?",
        f"{location}초등수학과외를 찾기 전에 {_obj(focus)} 집에서 어떻게 진단하나요?",
        f"{location} 학생의 {_subject(focus)} 흔들리면 연산 문제부터 늘려야 하나요?",
        f"{location} 가정학습에서 {_obj(focus)} 부모가 어디까지 도와야 하나요?",
        f"{location}에서 {_obj(focus)} 학교 진도와 선행 학습에 어떻게 나누나요?",
    )
    answers = (
        f"{location}에서는 특정 학년부터 일괄 시작하기보다 현재 학년의 대표 문제로 {_obj(focus)} 먼저 확인합니다. 1~2학년은 조작과 말하기, 3~4학년은 그림과 식의 연결, 5~6학년은 조건·근거·검산 기록을 사용하며, 학생이 혼자 가능한 단계에서 과제의 깊이를 정합니다.",
        f"{location} 가정에서는 {pack['task']} 활동을 12분 안에 진행하고 첫 풀이를 지우지 않습니다. {_obj(focus)} 정답으로만 판단하지 말고 시작까지 걸린 시간, 선택한 표현, 막힌 위치, 질문 뒤 바뀐 행동을 적은 다음 이틀 뒤 같은 도구 없이 첫 단계를 다시 설명하게 합니다.",
        f"{location} 학생의 {_subject(focus)} 약하다고 연산량부터 늘리면 실제 공백을 가릴 수 있습니다. {pack['signal']}를 살핀 뒤 계산 원리, 문제 읽기, 표현 선택, 검산, 학습 루틴 가운데 막힌 한 지점을 고르고 그 행동과 연결된 짧은 과제를 먼저 반복합니다.",
        f"{location}에서 부모는 {_obj(focus)} 답이나 풀이 순서로 대신하지 않습니다. {pack['parent']} 질문 하나를 한 뒤 학생이 말·그림·표·식 중 표현을 고르게 하고, 도움을 준 지점과 이후 혼자 이어 간 줄을 구분해 다음 재시도에서 힌트를 줄일 수 있도록 기록합니다.",
        f"{location}의 학교 수업 당일에는 {_obj(focus)} 교과서 표현과 첫 예제로 복원하고, 주중에는 {pack['action']} 선행은 현재 학년 문제에서 이 행동을 혼자 설명하고 며칠 뒤에도 재현한 뒤 선수 개념 한 항목씩 넓히며 학교별 진도는 실제 안내 자료로 확인합니다.",
    )
    pairs = list(zip(questions, answers))
    shift = _stable_index(slug, "faq-order") % len(pairs)
    pairs = pairs[shift:] + pairs[:shift]
    content = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in pairs)
    heading = _pick(
        (
            f"{location} {focus} 초등수학 학습에 자주 묻는 질문",
            f"{location}초등수학과외와 {focus} 자주 묻는 질문 정리",
            f"학년·연산·선행으로 나눈 {location} {focus} FAQ",
        ),
        slug,
        "faq-heading",
    )
    return f'<section class="elementary-math-block elementary-math-faq"><h2 class="elementary-math-faq" data-faq-focus="{escape(focus)}">{escape(heading)}</h2>{content}</section>'


def _closing(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 학습의 다음 한 단계",
            f"{location} 학생이 혼자 시작할 때까지 남길 {focus} 기록",
            f"문제집보다 먼저 정할 {location}의 {focus} 재시도",
            f"{location}초등수학과외 정보를 실제 {focus} 행동으로 옮기기",
        ),
        slug,
        "closing-heading",
    )
    paragraph = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 돕는 핵심은 문제집 분량을 일괄적으로 늘리는 데 있지 않습니다. {pack['action']} 그리고 정한 날짜에 {pack['check']} 이 기록이 쌓이면 학생은 새로운 문제에서도 필요한 표현과 첫 행동을 자기 힘으로 고를 수 있습니다.",
            f"이 페이지의 {location} 학교 정보와 {_obj(focus)} 계획은 상담이나 성취를 보장하는 문구가 아닙니다. 학생의 실제 교재와 첫 풀이, 학교 안내, 간격 뒤 재시도를 함께 확인하고 가장 작은 다음 행동부터 조정하는 교육용 기준입니다.",
            f"{location}에서 {_obj(focus)} 오래 유지하려면 정답 직후의 칭찬만 남기지 않습니다. 학생이 조건을 다시 표시한 이유, 표현을 바꾼 근거, 스스로 검산한 방법, 다음 재시도 날짜를 기록해 다음 학년과 단원에서도 같은 판단을 꺼내 쓰게 합니다.",
        ),
        slug,
        "closing-paragraph",
    )
    evidence_note = (
        f"{location}의 {focus} 다음 점검에서는 {pack['signal']}를 실제 풀이에서 다시 확인하고, "
        "학생이 도움 없이 선택한 첫 표현과 검산 근거를 남겨 새 문제에서도 같은 판단을 꺼내 쓰는지 비교합니다."
    )
    specific_note = {
        "부산재송동초등수학과외": (
            "부산재송동의 학교 수업 당일 복습은 수업 내용을 그대로 다시 베끼는 활동이 아닙니다. 학생 공책에서 오늘 배운 개념을 고르고, 설명을 덮은 상태에서 "
            "핵심 뜻과 첫 예제를 자기 말과 식으로 복원한 뒤 원본과 다른 줄을 표시합니다. 맞힌 문제도 오래 걸렸다면 처음 선택한 연산이나 그림을 보존하고, "
            "간격을 둔 재시도에서는 숫자와 질문 방식이 달라져도 같은 개념을 찾는지 확인합니다. 이렇게 남긴 기록을 학교 안내와 함께 보면 새 진도를 더할지, "
            "현재 단원의 설명 공백을 먼저 보완할지 근거를 갖고 정할 수 있습니다."
        ),
    }.get(slug, "")
    specific_html = f"<p>{escape(specific_note)}</p>" if specific_note else ""
    return f'<section class="elementary-math-block elementary-math-closing"><h2>{escape(heading)}</h2><p>{escape(paragraph)}</p><p>{escape(evidence_note)}</p>{specific_html}</section>'


def _individualize_diction(body: str, slug: str) -> str:
    """Vary recurring instructional vocabulary without changing its educational meaning."""
    focus = _focus_from_body(body)
    escaped_focus = escape(focus)
    placeholder = "EDUNEXT_ELEMENTARY_MATH_FOCUS_PLACEHOLDER"
    body = body.replace(escaped_focus, placeholder)
    variants: dict[str, tuple[str, ...]] = {
        "첫 풀이": ("최초 풀이", "처음 남긴 풀이", "첫 번째 풀이", "시작 풀이", "도움 전 풀이", "초기 풀이 기록"),
        "다음 과제": ("후속 과제", "이어 할 과제", "다음 학습 행동", "뒤이을 활동", "이후 과제", "다음번 활동"),
        "학교 수업": ("교실 수업", "학교에서 배운 내용", "정규 수업", "당일 교과 학습", "학교 진도 학습", "교과 시간"),
        "가정학습": ("집에서의 학습", "가정 복습", "집 공부", "가정 내 수학 활동", "귀가 후 학습", "집에서 이어 하는 복습"),
        "간격 뒤 재현": ("시간을 둔 재현", "며칠 뒤 복원", "간격을 둔 재시도", "다음 날의 독립 복원", "시간차 재현", "도움 없는 후속 재현"),
        "학생이 직접": ("학습자가 스스로", "학생 스스로", "아이가 직접", "학습자가 직접", "학생 본인이", "아이가 자기 힘으로"),
        "문제 수": ("문항 개수", "푼 문항 수", "풀이 문항량", "문항 분량", "연습 문제의 양", "해결한 문제 개수"),
        "기록합니다": ("기록으로 남깁니다", "적어 둡니다", "학습지에 남깁니다", "관찰표에 씁니다", "구체적으로 남깁니다", "별도 칸에 적습니다"),
        "확인합니다": ("점검합니다", "살펴봅니다", "대조합니다", "근거로 판단합니다", "다시 살핍니다", "기록에서 찾아봅니다"),
        "확인할": ("점검할", "살펴볼", "대조할", "판단할", "다시 볼", "기록으로 볼"),
        "확인하는": ("점검하는", "살펴보는", "대조하는", "판단하는", "다시 보는", "기록으로 읽는"),
        "설명합니다": ("말로 풀어냅니다", "근거와 함께 말합니다", "자기 말로 정리합니다", "과정을 밝혀 말합니다", "문장으로 나타냅니다", "이유까지 표현합니다"),
        "다시 연결": ("재연결", "다음 학습에 연결", "교과 내용에 재적용", "현재 단원에 이어 붙이기", "배운 내용과 연결", "후속 활동에 연결"),
        "구분합니다": ("나누어 봅니다", "서로 가려냅니다", "별도로 분류합니다", "차이를 표시합니다", "다른 항목으로 봅니다", "각각 판별합니다"),
        " 정합니다": (" 결정합니다", " 선택합니다", " 구체화합니다", " 기준을 세웁니다", " 학생과 합의합니다", " 한 가지로 좁힙니다"),
    }
    for source in sorted(variants, key=len, reverse=True):
        body = body.replace(source, _pick(variants[source], slug, f"diction-{source}"))
    return body.replace(placeholder, escaped_focus)


def build_local_elementary_math_body(slug: str, focus: str) -> str:
    location, city, _ = _parts(slug)
    kind = _kind_for_focus(focus)
    pack = ELEMENTARY_PACKS[kind]
    fixed_start = [_opening(slug, location, focus, pack), _search_intent(slug, location, focus, pack)]
    sections = {
        "grade": _grade_plan(slug, location, focus, pack),
        "concept": _concept_map(slug, location, focus, pack),
        "diagnosis": _diagnosis(slug, location, focus, pack),
        "weekly": _weekly_plan(slug, location, focus, pack),
        "school": _school_section(slug, location, focus),
        "case": _student_case(slug, location, focus, pack),
        "parent": _parent_coaching(slug, location, focus, pack),
        "transfer": _transfer(slug, location, focus, pack),
        "error": _error_map(slug, location, focus, pack),
        "protocol": _focus_protocol(slug, location, focus, pack),
    }
    orders = (
        ("grade", "concept", "diagnosis", "protocol", "error", "weekly", "school", "case", "parent", "transfer"),
        ("diagnosis", "grade", "school", "concept", "error", "protocol", "weekly", "parent", "case", "transfer"),
        ("grade", "school", "concept", "case", "diagnosis", "protocol", "error", "weekly", "transfer", "parent"),
        ("concept", "diagnosis", "grade", "weekly", "error", "case", "protocol", "school", "parent", "transfer"),
        ("school", "grade", "diagnosis", "concept", "parent", "error", "weekly", "protocol", "case", "transfer"),
        ("grade", "concept", "weekly", "parent", "protocol", "diagnosis", "school", "error", "transfer", "case"),
    )
    order = _pick(orders, slug, "section-order")
    body = "".join(fixed_start + [sections[key] for key in order])
    body += _context_links(slug, location, city, focus)
    body += _faq(slug, location, focus, pack)
    body += _closing(slug, location, focus, pack)
    return _individualize_diction(body, slug)


def individualize_local_elementary_math_body(body: str, slug: str) -> str:
    if not is_local_elementary_math_slug(slug):
        return body
    focus = _focus_from_body(body)
    return build_local_elementary_math_body(slug, focus)
