from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path

from sitegen.local_middle_math import (
    MATH_PACKS,
    _diagnosis_section,
    _fix_focus_particles,
    _practice_section,
    _review_section,
    _schedule_section,
)
from sitegen.utils import escape


LOCAL_HIGH_MATH_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)고등수학과외$")
CONTENT_MARKER = "local-high-math-content"
CONTENT_VERSION = "high-math-individual-v6"
SCHOOL_CONTEXT_MARKER = "high-math-school-context"
SEARCH_INTENT_MARKER = "high-math-search-intent"
STUDENT_CASE_MARKER = "high-math-student-case"
FAQ_MARKER = "high-math-faq"
CONTEXT_LINKS_MARKER = "high-math-context-links"

ROOT = Path(__file__).resolve().parents[1]
SCHOOL_REGION_PATH = ROOT / "data" / "school_region_map.json"
SCHOOL_HOMEPAGE_PATH = ROOT / "data" / "school_official_homepages.json"


def _plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _stable_index(slug: str, salt: str = "") -> int:
    return int(hashlib.sha256(f"{slug}|{salt}".encode("utf-8")).hexdigest()[:12], 16)


def _pick(items: tuple[str, ...], slug: str, salt: str = "") -> str:
    return items[_stable_index(slug, salt) % len(items)]


def _fix_high_focus_particles(value: str, focus: str) -> str:
    """Apply every Korean particle used by the high-school math templates."""
    value = _fix_focus_particles(value, focus)
    last = focus[-1] if focus else ""
    code = ord(last) if last else 0
    has_final = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    subject = "이" if has_final else "가"
    wrong_subject = "가" if has_final else "이"
    naming = "이라는" if has_final else "라는"
    wrong_naming = "라는" if has_final else "이라는"
    for prefix in (focus, f"‘{focus}’"):
        # The longer naming form must be replaced before its subject prefix.
        value = value.replace(f"{prefix}{wrong_naming}", f"{prefix}{naming}")
        value = value.replace(f"{prefix}{wrong_subject}", f"{prefix}{subject}")
    return value


def is_local_high_math_slug(slug: str) -> bool:
    return bool(LOCAL_HIGH_MATH_PATTERN.fullmatch(slug))


def _focus_from_body(body: str) -> str:
    current = re.search(r'data-high-math-focus="([^"]+)"', body, flags=re.I)
    if current:
        return unescape(current.group(1)).strip()
    strong = re.search(r"<strong\b[^>]*>(.*?)</strong>", body, flags=re.I | re.S)
    if strong:
        focus = _plain_text(strong.group(1))
        if focus and not focus.startswith(("고1", "고2", "고3")):
            return focus
    paragraph = re.search(
        r"페이지에서는\s*(.+?)(?:을|를)\s*중심으로",
        _plain_text(body),
    )
    if paragraph:
        return paragraph.group(1).strip()
    heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    heading_text = _plain_text(heading.group(1)) if heading else ""
    patterns = (
        r"고등수학과외에서\s*(.+?)(?:을|를)\s*이해하고",
        r"고등수학과외,\s*(.+?)(?:을|를)\s*중심으로",
        r"고등수학과외,\s*(.+?)의\s*조건과\s*풀이\s*전략",
    )
    for pattern in patterns:
        match = re.search(pattern, heading_text)
        if match:
            return match.group(1).strip()
    return "고등수학 풀이 전략"


def _kind_for_focus(focus: str) -> str:
    if any(word in focus for word in ("미분", "적분", "극대", "극소", "변화율", "가속도", "접선")):
        return "calculus"
    if any(word in focus for word in ("확률", "통계", "표본", "평균", "분산", "순열", "조합", "경우의 수")):
        return "probability"
    if any(word in focus for word in ("도형", "벡터", "이차곡선", "초점", "사인법칙", "코사인법칙", "거리", "각")):
        return "geometry"
    if any(word in focus for word in ("함수", "그래프", "지수", "로그", "삼각함수", "단위원", "주기")):
        return "function"
    if any(
        word in focus
        for word in (
            "내신", "모의고사", "수능", "수면", "서술형", "선택과목", "수행평가",
            "복습", "오류", "취약", "시간 배분", "풀이", "학습 순서", "단원",
        )
    ):
        return "routine"
    return "algebra"


HIGH_PACKS: dict[str, dict[str, str]] = {
    "algebra": {
        "material": "교과서 정의와 예제, 최근 학교 시험지의 식 전개, 학생이 중간 계산을 남긴 공책",
        "signal": "공식은 기억하지만 전제와 결론, 항의 역할, 변형의 근거를 한 문장으로 잇는지",
        "action": "첫 식을 세운 이유와 다음 줄에서 사용한 성질을 나누어 적습니다.",
        "transfer": "문자와 조건의 순서를 바꾼 문항에서도 같은 구조를 찾아 풀이를 시작합니다.",
        "check": "얻은 결과를 원래 조건에 대입하거나 역방향으로 검토해 불필요한 해를 가려냅니다.",
        "written": "전제, 사용한 성질, 계산 과정, 결론의 조건이 한 흐름으로 이어지는가",
        "finish": "표현이 달라져도 식의 구조를 설명하고 첫 변형과 마지막 검산을 혼자 수행하는가",
        "grade1": "식·방정식·부등식·경우의 수를 배울 때 기호의 뜻과 동치 변형을 설명합니다.",
        "grade2": "수열과 여러 함수 단원에서 앞선 대수 개념을 꺼내어 조건에 맞는 식을 구성합니다.",
        "grade3": "시간 제한 안에서 계산 경로를 줄이되 생략한 전제와 검산 기준은 유지합니다.",
    },
    "function": {
        "material": "학교 범위의 함수 문항, 교과서의 식·표·그래프, 축과 정의역을 표시한 학생 풀이",
        "signal": "계산한 값과 그래프의 위치, 두 양의 변화, 문제에서 허용한 범위를 연결하는지",
        "action": "축·단위·정의역을 먼저 적고 식의 변화가 그래프에 나타나는 위치를 표시합니다.",
        "transfer": "식·표·그래프·문장 가운데 하나를 가린 뒤 나머지 표현으로 관계를 복원합니다.",
        "check": "특수한 값과 경계에서 식과 그래프가 같은 결론을 주는지 확인합니다.",
        "written": "정의역과 변화 기준을 밝히고 식에서 얻은 결론을 그래프와 문장으로 설명하는가",
        "finish": "표현과 수치가 바뀌어도 핵심 관계와 범위를 찾아 같은 전략을 다시 선택하는가",
        "grade1": "함수의 정의, 대응 관계, 그래프의 기본 성질을 방정식·부등식과 연결합니다.",
        "grade2": "지수·로그·삼각함수 등에서 식의 변형과 그래프의 변화를 함께 해석합니다.",
        "grade3": "여러 함수 표현을 실전 문항 안에서 비교하고 제한된 시간에 필요한 정보부터 고릅니다.",
    },
    "calculus": {
        "material": "교과서의 극한·미분·적분 정의, 학교 시험의 그래프 문항, 변화 구간을 표시한 풀이",
        "signal": "계산 공식보다 변화율·누적량·그래프의 성질을 문제 조건에 맞게 해석하는지",
        "action": "변수와 구간을 먼저 정하고 식, 그래프, 변화의 의미를 같은 줄에 대응시킵니다.",
        "transfer": "함수식이나 구간이 달라졌을 때 도함수와 누적량의 의미가 어떻게 바뀌는지 설명합니다.",
        "check": "부호, 구간, 경계값을 다시 확인하고 계산 결과가 그래프의 변화와 일치하는지 봅니다.",
        "written": "변화가 일어나는 구간과 사용한 정리, 계산 결과의 의미를 빠짐없이 설명하는가",
        "finish": "공식을 가린 상태에서도 그래프와 정의로 첫 판단을 세우고 결과를 해석하는가",
        "grade1": "함수·방정식·좌표의 언어를 정확히 사용해 이후 변화율 학습의 기초를 만듭니다.",
        "grade2": "극한과 변화율, 넓이와 누적의 의미를 식과 그래프 사이에서 오가며 확인합니다.",
        "grade3": "여러 단원이 섞인 실전 문항에서 구간과 조건을 먼저 정하고 풀이 시간을 관리합니다.",
    },
    "geometry": {
        "material": "학교 범위의 도형·벡터 문항, 교과서 정의와 정리, 조건과 보조 표시가 남은 그림",
        "signal": "그림의 모양이 아니라 좌표·벡터·거리·각의 조건으로 결론을 설명하는지",
        "action": "주어진 조건과 새로 증명할 관계를 나누고 사용할 표현을 선택한 이유를 적습니다.",
        "transfer": "도형의 방향과 좌표를 바꾸어도 같은 불변 관계를 찾아 풀이를 다시 구성합니다.",
        "check": "계산 결과가 길이·각·위치의 가능한 범위에 맞는지 정의와 그림으로 검토합니다.",
        "written": "주어진 조건, 선택한 정리나 표현, 중간 결론, 최종 관계가 논리적으로 이어지는가",
        "finish": "그림이 달라져도 필요한 조건을 골라 식 또는 벡터로 첫 단계를 세우는가",
        "grade1": "좌표와 도형의 방정식에서 대수 계산과 기하적 의미를 함께 읽습니다.",
        "grade2": "삼각함수·벡터·이차곡선 등에서 정의와 성질을 그림과 식으로 연결합니다.",
        "grade3": "낯선 도형에서도 조건을 구조화하고 계산할 관계와 증명할 관계를 빠르게 구분합니다.",
    },
    "probability": {
        "material": "학교 시험의 경우의 수·확률·통계 문항, 교과서 표와 그래프, 표본 기준을 적은 풀이",
        "signal": "전체 경우와 표본, 사건과 변수, 계산값과 해석의 범위를 구분하는지",
        "action": "분류 기준을 먼저 적고 누락·중복 가능성을 확인한 뒤 계산식을 세웁니다.",
        "transfer": "전체 수나 조건을 바꾸어 계산 결과와 해석이 함께 달라지는지 비교합니다.",
        "check": "확률의 범위, 자료 수, 단위와 표본 조건을 이용해 결과가 가능한 값인지 검토합니다.",
        "written": "전체와 선택 기준, 계산 과정, 결과가 뜻하는 집단과 해석의 한계를 밝히는가",
        "finish": "자료나 조건이 달라졌을 때 계산법을 다시 고르고 결과의 의미까지 설명하는가",
        "grade1": "경우의 수를 셀 때 합과 곱의 기준, 누락과 중복을 표나 목록으로 확인합니다.",
        "grade2": "확률변수와 분포, 평균과 분산을 계산값이 아닌 자료의 특성과 연결합니다.",
        "grade3": "표본과 추정 문제에서 모집단·표본·통계량의 관계와 해석 범위를 구분합니다.",
    },
    "routine": {
        "material": "실제 학교 범위표와 최근 시험지, 모의고사 오답, 일주일의 시작·중단·재시도 기록",
        "signal": "공부시간과 문제 수보다 첫 판단, 건너뛴 기준, 도움 뒤 행동, 재시도 결과가 남는지",
        "action": "오답을 개념·조건·전략·계산·시간 가운데 하나로 분류하고 다음 행동을 정합니다.",
        "transfer": "시험 형식과 시간 제한이 달라져도 같은 판단 기준을 사용해 풀이 순서를 조정합니다.",
        "check": "맞힌 문항도 오래 걸렸다면 다시 보고, 정한 날짜에 해설 없이 첫 단계를 재현합니다.",
        "written": "풀이 전략과 수정 이유, 검산, 시간 판단, 다음 재시도 날짜가 기록에 남는가",
        "finish": "새 문제를 늘리지 않아도 취약 지점을 말하고 다음 학습 순서를 스스로 정하는가",
        "grade1": "학교 수업 당일에 정의와 예제를 복원하고 풀이 과정을 생략하지 않는 기록을 만듭니다.",
        "grade2": "과목과 단원의 연결이 늘어날 때 현재 범위와 선수 개념의 공백을 구분합니다.",
        "grade3": "내신과 실전 자료의 목적을 나누고 시간 배분과 취약 단원 재시도를 함께 관리합니다.",
    },
}


BASE_KIND = {
    "algebra": "algebra",
    "function": "function",
    "calculus": "function",
    "geometry": "geometry",
    "probability": "data",
    "routine": "routine",
}


def _load_school_context() -> dict[tuple[str, str], list[dict[str, str]]]:
    if not SCHOOL_REGION_PATH.exists() or not SCHOOL_HOMEPAGE_PATH.exists():
        return {}
    region_rows = json.loads(SCHOOL_REGION_PATH.read_text(encoding="utf-8"))
    homepage_rows = json.loads(SCHOOL_HOMEPAGE_PATH.read_text(encoding="utf-8"))
    homepages = {
        (str(row.get("city") or ""), str(row.get("official_school_name") or "")): str(row.get("homepage") or "")
        for row in homepage_rows
        if isinstance(row, dict)
    }
    contexts: dict[tuple[str, str], list[dict[str, str]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in region_rows:
        if not isinstance(row, dict) or not row.get("mapping_success"):
            continue
        city = str(row.get("city") or "").strip()
        town = str(row.get("town") or "").strip()
        name = str(row.get("official_school_name") or "").strip()
        key = (city, town, name)
        if not city or not town or not name or key in seen:
            continue
        seen.add(key)
        contexts.setdefault((city, town), []).append(
            {"name": name, "homepage": homepages.get((city, name), "").strip()}
        )
    return contexts


SCHOOL_CONTEXT = _load_school_context()


def _opening(slug: str, location: str, focus: str) -> str:
    heading_frames = (
        f"{location}고등수학과외에서 {focus}을 점검하는 출발점",
        f"정답보다 먼저 보는 {location}의 {focus} 풀이 기록",
        f"{focus}의 첫 판단을 남기는 {location} 고등수학 학습",
        f"{location} 학생의 {focus} 이해를 확인하는 방법",
        f"{focus}을 시험지와 공책에서 다시 찾는 {location} 기준",
        f"{location}고등수학과외, {focus}을 설명 가능한 풀이로 바꾸기",
    )
    paragraph_frames = (
        f"{location}이라는 지역명만으로 학생의 학교, 진도, 성적을 추정할 수는 없습니다. 이 페이지는 {focus}을 중심으로 학생이 실제로 받은 범위표와 시험지, 첫 풀이, 간격을 둔 재시도를 비교해 다음 과제를 정하는 교육 정보를 제공합니다.",
        f"고등수학은 같은 답을 얻어도 풀이 판단이 다를 수 있습니다. {location} 페이지에서는 {focus}에서 사용한 조건과 중단 위치, 도움 뒤 바뀐 행동을 따로 남겨 개념 공백과 실전 전략의 문제를 구분합니다.",
        f"{focus}을 많이 풀었다는 사실과 새로운 조건에서 사용할 수 있다는 사실은 다릅니다. {location} 학생의 현재 수준은 해설을 본 직후가 아니라 하루 이상 뒤에 첫 단계를 다시 시작하고 근거를 설명하는지로 확인합니다.",
        f"이 페이지는 {location} 학생 모두가 같은 어려움을 겪는다고 말하지 않습니다. {focus}이라는 고유한 점검 주제를 이용해 내신 자료와 모의고사 기록을 어떻게 나누고 다시 연결할지 구체적인 순서로 설명합니다.",
    )
    return f"<h2>{escape(_pick(heading_frames, slug, 'opening-heading'))}</h2><p>{escape(_pick(paragraph_frames, slug, 'opening'))}</p>"


def _grade_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"고1·고2·고3에서 달라지는 {focus} 확인 기준",
        f"{location} 학생의 학년별 {focus} 연결 순서",
        f"선행 분량보다 먼저 볼 {focus}의 학년별 역할",
        f"학교 진도와 실전 준비를 잇는 {focus} 학년 계획",
    )
    grade_rows = [("고1", pack["grade1"]), ("고2", pack["grade2"]), ("고3", pack["grade3"])]
    shift = _stable_index(slug, "grade-order") % 3
    grade_rows = grade_rows[shift:] + grade_rows[:shift]
    items = "".join(
        f"<li><strong>{grade}:</strong> {escape(text)} {escape(location)}의 {escape(focus)} 기록에서는 이 행동이 실제 풀이에 남는지 확인합니다.</li>"
        for grade, text in grade_rows
    )
    closing_frames = (
        f"학년이 같아도 시작점은 다릅니다. {location} 학생에게 앞선 내용을 모두 반복하게 하지 않고 {focus} 풀이를 막은 선수 개념 한 항목만 복원한 뒤 현재 학교 범위에서 바로 사용하게 합니다.",
        f"진도표만으로 {focus} 과제를 정하지 않습니다. {location} 학생이 혼자 설명 가능한 단계와 짧은 질문 뒤 가능한 단계를 나누면 선행이 현재 학년의 공백을 가리는 일을 줄일 수 있습니다.",
        f"고3이라고 새 문제만 늘리거나 고1이라고 기본 문제만 반복하지 않습니다. {location}의 {focus} 첫 풀이에서 확인된 오류 위치를 기준으로 개념·적용·검산의 비중을 다르게 둡니다.",
    )
    return (
        f'<section class="high-math-block high-math-grade" data-high-grade-plan="three-years">'
        f"<h2>{escape(_pick(heading_frames, slug, 'grade-heading'))}</h2><ul>{items}</ul>"
        f"<p>{escape(_pick(closing_frames, slug, 'grade-closing'))}</p></section>"
    )


def _search_intent_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{location}의 {focus}을 내신·모의고사·수능 자료에서 구분하기",
        f"{focus} 검색 뒤 실제로 확인할 {location} 고등수학 자료",
        f"학교 시험과 실전 문제에서 달라지는 {focus}의 역할",
        f"{location} {focus} 학습 목표를 평가 자료별로 나누기",
    )
    intro_frames = (
        f"{location}고등수학과외를 찾는 이유가 내신인지 모의고사인지에 따라 같은 {focus} 문제도 확인 순서가 달라집니다. 시작 자료는 {pack['material']}이며, 확인되지 않은 학교별 난도나 출제 경향을 지역명으로 단정하지 않습니다.",
        f"검색어가 같아도 필요한 도움은 다를 수 있습니다. {location} 학생의 {focus} 계획은 {pack['signal']}를 첫 기준으로 삼고 실제 학교 범위와 시험일까지 남은 날짜에 맞춰 분량을 정합니다.",
        f"{focus}의 문제 수보다 자료의 역할을 먼저 구분합니다. {location}에서는 {pack['material']}을 나란히 놓고 내신의 범위 적합성, 모의고사의 판단 과정, 장기 복습의 재현 여부를 따로 기록합니다.",
    )
    rows = (
        ("학교 내신", "교과서 정의·학교 자료·서술형", f"{pack['written']}"),
        ("모의고사", "틀린 문항과 오래 걸린 정답 문항", f"{pack['signal']}"),
        ("장기 복습", "해설을 가린 간격 뒤 재시도", f"{pack['finish']}"),
    )
    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(material)}</td><td>{escape(check)} — {escape(location)} {escape(focus)} 기록</td></tr>"
        for label, material, check in rows
    )
    order_frames = (
        (
            f"{pack['action']}", f"{pack['transfer']}", f"{pack['check']}",
            "마지막에는 재시도 날짜와 다음에 시작할 한 문제를 적습니다.",
        ),
        (
            "학교 범위표에서 해당 단원과 평가 날짜를 먼저 확인합니다.",
            f"{pack['action']}", f"{pack['check']}", f"{pack['transfer']}",
        ),
        (
            "첫 풀이를 지우지 않고 막힌 줄과 사용 시간을 표시합니다.",
            f"{pack['action']}", f"{pack['transfer']}",
            "하루 이상 뒤에 해설 없이 첫 판단을 다시 말합니다.",
        ),
    )
    steps = order_frames[_stable_index(slug, "search-order") % len(order_frames)]
    items = "".join(f"<li>{escape(step)} {escape(focus)}의 근거가 남는지 확인합니다.</li>" for step in steps)
    closing_frames = (
        f"{location} 학생이 한 번 맞힌 결과만으로 {focus}을 끝내지 않습니다. 평가 종류가 바뀌어도 첫 판단과 검산이 유지되는지를 본 뒤 다음 단원으로 이동합니다.",
        f"시험까지 시간이 짧다면 새 고난도 문제를 줄이고 {focus}의 대표 오답, 서술형 한 문제, 간격 뒤 재시도를 남깁니다. 재시도 날짜를 없애면 무엇이 유지됐는지 비교하기 어렵습니다.",
        f"학교 홈페이지는 일정과 공식 공지 확인에 사용하고 실제 {focus} 내용은 학생이 받은 자료에서 확인합니다. 두 자료의 역할을 섞지 않는 것이 {location} 계획의 출발점입니다.",
    )
    return (
        f'<section class="high-math-block {SEARCH_INTENT_MARKER}" data-intent-kind="assessment">'
        f"<h2>{escape(_pick(heading_frames, slug, 'search-heading'))}</h2>"
        f"<p>{escape(_pick(intro_frames, slug, 'search-intro'))}</p>"
        "<h3>평가 자료별로 남길 기록</h3><table><thead><tr><th>목적</th><th>먼저 볼 자료</th><th>완료 질문</th></tr></thead>"
        f"<tbody>{row_html}</tbody></table><h3>{escape(focus)} 재시도 순서</h3><ol>{items}</ol>"
        f"<p>{escape(_pick(closing_frames, slug, 'search-closing'))}</p></section>"
    )


def _school_context_section(slug: str, location: str, focus: str) -> str:
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    town = location.removeprefix(city)
    schools = SCHOOL_CONTEXT.get((city, town), [])
    heading_frames = (
        f"{location} 학교 자료를 {focus} 계획에 연결하는 방법",
        f"{town} 주소의 고등학교 공식 정보와 {focus} 확인 순서",
        f"{focus} 복습 전에 구분할 {location} 학교 자료",
        f"{location}에서 공식 학교 정보와 학생 풀이를 함께 보는 기준",
    )
    intro_frames = (
        f"학교명과 주소는 저장된 고등학교 지역 매핑 자료에서 {town}이 정확히 일치하는 항목만 사용했습니다. 학교 링크는 일정과 공식 공지를 확인하는 경로이며 {location} 학생의 재학·배정·통학시간을 의미하지 않습니다.",
        f"{location}이라는 주소만으로 재학 학교나 시험 범위를 추정하지 않습니다. 공식 홈페이지에서는 학교명과 일정만 확인하고, {focus}의 실제 범위와 문항은 학생이 받은 범위표·교과서·시험지에서 다시 확인합니다.",
        f"지역 정보와 학습 정보의 역할을 나눕니다. {town}과 정확히 연결된 학교명은 공식 공지의 출처를 찾는 데 사용하고, {focus}의 난도와 진도는 학생 개인의 자료로 판단합니다.",
    )
    if schools:
        items: list[str] = []
        for school in schools[:4]:
            name = school["name"]
            homepage = school["homepage"]
            if homepage:
                items.append(
                    f'<li><a class="source-link" href="{escape(homepage)}" target="_blank" '
                    f'rel="noopener noreferrer external">{escape(name)} 공식 홈페이지 <span aria-hidden="true">↗</span></a></li>'
                )
            else:
                items.append(f"<li>{escape(name)} — 저장 자료에 개별 홈페이지 주소 없음</li>")
        names = ", ".join(school["name"] for school in schools)
        summary = (
            f"{town} 주소와 정확히 연결된 고등학교는 {len(schools)}곳이며 {names}입니다. "
            "이 목록만으로 가까운 학교나 배정 가능성을 판단하지 않습니다."
        )
        school_block = f'<p>{escape(summary)}</p><ul class="high-math-school-links">{"".join(items)}</ul>'
    else:
        school_block = (
            f"<p>{escape(f'저장된 매핑 자료에서는 {town} 주소와 정확히 일치하는 고등학교를 확인하지 못했습니다. 다른 동의 학교를 가깝다고 추측해 연결하지 않으며, 실제 재학 학교명을 기준으로 홈페이지와 범위표를 확인해야 합니다.')}</p>"
        )
    closing_frames = (
        f"학교 홈페이지에 시험 범위가 공개되지 않았더라도 {location} 학생이 받은 자료가 우선입니다. {focus} 문항을 찾아 날짜, 첫 풀이, 수정 이유, 재시도 결과를 같은 기록에 남깁니다.",
        f"공식 정보 확인 뒤에는 {focus} 과제를 학교명으로 일반화하지 않습니다. 같은 학교 학생도 과목 편성과 현재 이해가 다르므로 {location} 페이지의 진단 순서를 개인별 풀이에 적용합니다.",
        f"학교 정보는 자주 바뀔 수 있으므로 최종 일정은 해당 학교의 공식 안내에서 확인합니다. {focus} 학습 계획은 일정 확인 뒤 학생의 실제 자료와 생활시간을 기준으로 조정합니다.",
    )
    return (
        f'<section class="high-math-block {SCHOOL_CONTEXT_MARKER}" data-school-match="exact-town">'
        f"<h2>{escape(_pick(heading_frames, slug, 'school-heading'))}</h2>"
        f"<p>{escape(_pick(intro_frames, slug, 'school-intro'))}</p>{school_block}"
        f"<p>{escape(_pick(closing_frames, slug, 'school-closing'))}</p></section>"
    )


def _deep_dive_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus}을 기본형·변형형·실전형으로 나누는 {location} 학습 설계",
        f"{location}의 {focus} 풀이를 근거·적용·검산으로 확장하기",
        f"{focus}에서 같은 실수를 반복하지 않는 {location} 기록법",
        f"학교 범위 안에서 {focus}의 적용 깊이를 확인하는 {location} 기준",
    )
    lead_frames = (
        f"{location} 학생의 {focus} 학습은 난도가 높은 문제부터 시작하지 않습니다. 먼저 정의를 보며 푸는 기본형, 핵심 질문만 받는 변형형, 시간과 표현이 달라진 실전형을 분리합니다. 세 단계의 정답 수보다 {pack['signal']}를 각 단계에서 비교해야 도움이 줄어든 이유를 설명할 수 있습니다.",
        f"{focus}의 약점이 계산인지 조건 해석인지 모르면 문제집을 바꾸어도 같은 장면이 반복됩니다. {location}에서는 {pack['material']}을 시간순으로 놓고 첫 판단이 달라진 줄을 찾습니다. 그 줄을 기준으로 기본형 한 문제와 표현이 달라진 한 문제를 짝지어 재시도합니다.",
        f"{location}의 {focus} 계획에서 ‘어려운 문제’는 고정된 분류가 아닙니다. 학생이 정의를 꺼내는 데 막혔는지, 조건을 표현으로 바꾸는 데 막혔는지, 계산 뒤 의미를 확인하는 데 막혔는지에 따라 같은 문항의 역할이 달라집니다. 따라서 과제 이름보다 관찰할 행동을 먼저 적습니다.",
        f"내신과 실전 자료가 함께 쌓이면 {focus}의 오답도 한 묶음처럼 보이기 쉽습니다. {location} 학생은 학교 범위 안의 대표 문항, 시간이 오래 걸린 정답 문항, 해설을 본 오답을 서로 다른 칸에 둡니다. 이후 {pack['action']} 같은 원인이 다시 나온 경우만 우선 복습합니다.",
    )
    stage_rows = (
        (
            "정의 복원",
            f"{focus}의 용어와 조건을 자료를 보지 않고 한 문장으로 설명",
            f"{location} 기록에 빠진 전제와 모르는 수학 용어를 표시",
        ),
        (
            "대표 적용",
            f"{pack['action']}",
            f"{location} 학생이 혼자 선택한 첫 식·그림·그래프를 보존",
        ),
        (
            "조건 변형",
            f"{pack['transfer']}",
            f"{focus}의 변하지 않은 원리와 달라진 조건을 두 줄로 구분",
        ),
        (
            "간격 뒤 확인",
            f"{pack['check']}",
            f"{location}에서 필요한 힌트와 풀이 시간을 첫 시도와 비교",
        ),
    )
    shift = _stable_index(slug, "deep-stage-order") % len(stage_rows)
    stage_rows = stage_rows[shift:] + stage_rows[:shift]
    rows = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(action)}</td><td>{escape(record)}</td></tr>"
        for stage, action, record in stage_rows
    )
    error_frames = (
        f"{focus} 오답을 ‘개념을 모름’으로 한 번에 묶지 않습니다. {location} 학생이 조건을 읽었지만 표현하지 않았는지, 표현했지만 전략을 잘못 골랐는지, 전략은 맞았지만 계산과 검산에서 끊겼는지를 구분합니다. 원인 칸이 달라지면 다음 문제의 난도보다 제공할 힌트의 위치가 먼저 달라집니다.",
        f"한 문제에서 여러 오류를 동시에 고치면 {focus}의 어떤 행동이 실제로 바뀌었는지 알기 어렵습니다. {location}에서는 첫 시도의 가장 앞쪽 오류 하나를 선택하고 나머지는 표시만 남깁니다. 다음 날 같은 원리의 문제에서 그 행동이 유지된 뒤에 두 번째 오류를 다룹니다.",
        f"정답을 맞힌 {focus} 문항도 검토 대상이 될 수 있습니다. {location} 학생이 우연히 식을 골랐거나 제한 시간보다 오래 사용했다면 맞은 결과와 안정된 풀이를 구분해야 합니다. 선택 근거와 검산을 설명하지 못한 정답은 짧은 변형 문제로 다시 확인합니다.",
        f"{location}의 {focus} 기록에서 같은 오류가 두 번 나왔다고 곧바로 학습량을 늘리지 않습니다. 두 문항의 조건과 표현이 같은지 먼저 보고, 같은 상황에서 반복됐다면 과제 크기를 줄입니다. 다른 상황에서 나타났다면 공통으로 놓친 정의나 판단 기준을 찾아 연결합니다.",
    )
    evidence_steps = (
        f"{location}의 실제 시험 범위에서 {focus} 대표 문항 한 개를 선택합니다.",
        f"{focus} 풀이의 첫 전략과 그 전략을 고른 근거를 서로 다른 줄에 적습니다.",
        f"{location} 학생이 힌트를 요청한 시점과 힌트 뒤에 스스로 이어 간 단계를 구분합니다.",
        f"{focus}의 수치·표현·조건 가운데 하나만 바꾼 문항으로 적용 범위를 확인합니다.",
        f"{location} 일정에 재시도 날짜를 남기고 해설 없이 첫 판단과 검산을 다시 수행합니다.",
    )
    step_shift = _stable_index(slug, "deep-evidence-order") % len(evidence_steps)
    evidence_steps = evidence_steps[step_shift:] + evidence_steps[:step_shift]
    items = "".join(f"<li>{escape(step)}</li>" for step in evidence_steps)
    transfer_frames = (
        f"서술형에서는 ‘{pack['written']}?’라는 질문을 {location}의 {focus} 검토 기준으로 사용합니다. 답이 맞아도 전제나 범위가 빠졌다면 완성 풀이를 베끼지 않고 빠진 한 문장만 먼저 복원합니다. 이후 계산 줄과 결론 사이의 연결을 학생이 자신의 말로 설명하게 합니다.",
        f"실전 적용의 완료 질문은 ‘{pack['finish']}?’입니다. {location} 학생이 같은 문제를 외워 푼 것인지 확인하려면 {focus}의 수치와 제시 표현을 바꿉니다. 정답률은 유지돼도 필요한 힌트가 늘었다면 아직 다음 유형으로 빠르게 넘어가지 않습니다.",
        f"시간 관리는 {focus}을 빨리 포기하는 연습이 아닙니다. {location} 학생이 첫 판단을 세운 뒤 진행 여부를 정하도록 기준 시점을 남기고, 넘어간 문항은 시험 종료 전에 다시 볼 조건을 적습니다. 시간 기록은 개념 기록과 분리하지 않고 같은 오답 표에서 비교합니다.",
        f"보호자는 {location} 학생의 {focus} 정답을 다시 설명하기보다 ‘처음 확인한 조건’, ‘도움이 필요했던 줄’, ‘다음 날 혼자 한 행동’을 묻습니다. 세 답이 구체적이면 현재 과제를 유지하고, 답이 계속 달라지면 분량보다 기록 방식을 먼저 단순하게 만듭니다.",
    )
    return (
        f'<section class="high-math-block high-math-deep-dive" data-deep-dive="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'deep-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'deep-lead'))}</p>"
        "<h3>네 단계로 비교하는 풀이 깊이</h3><table><thead><tr><th>단계</th><th>학생이 할 행동</th><th>확인할 기록</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><p>{escape(_pick(error_frames, slug, 'deep-error'))}</p>"
        "<h3>첫 풀이를 다음 과제로 바꾸는 기록 순서</h3>"
        f"<ol>{items}</ol><p>{escape(_pick(transfer_frames, slug, 'deep-transfer'))}</p></section>"
    )


def _student_case_section(slug: str, location: str, focus: str, kind: str, pack: dict[str, str]) -> str:
    grade = ("고1", "고2", "고3")[_stable_index(slug, "case-grade") % 3]
    heading_frames = (
        f"{location} {grade}의 {focus} 과제를 조정하는 합성 사례",
        f"{focus}의 첫 시도와 재시도를 비교하는 {location} {grade} 기록",
        f"정답률 대신 행동을 보는 {location} {grade} 수학 사례",
        f"{location}에서 {focus}의 막힌 위치를 찾는 가상 상담 흐름",
    )
    disclaimer_frames = (
        f"아래 내용은 {location}의 실제 학생이나 학교 성과를 옮긴 후기가 아닙니다. 개인정보가 없는 합성 사례로 {focus}의 관찰 자료를 다음 과제로 바꾸는 방법만 설명합니다.",
        f"이 사례는 {location} 학생의 공통 성향이나 성적 변화를 주장하지 않습니다. 서로 다른 학습 장면을 조합한 가상 기록이며 {focus}에서 확인할 질문과 결정 기준에 초점을 둡니다.",
        f"{location}이라는 지역명으로 학생 수준을 정할 수 없습니다. 다음 {grade} 사례는 실제 인물을 가리키지 않으며 {focus}의 첫 풀이, 도움 뒤 풀이, 간격 뒤 재시도를 비교하기 위한 예시입니다.",
    )
    situation_frames = (
        f"가상의 {grade} 학생은 {focus} 문제의 공식을 말했지만 조건이 달라지자 첫 줄을 정하지 못했습니다. {pack['signal']}를 확인하기 위해 첫 풀이를 지우지 않고 멈춘 위치와 요청한 힌트를 기록했습니다.",
        f"가상의 {grade} 학생은 {focus} 문항을 맞혔지만 풀이 이유를 설명하는 데 시간이 오래 걸렸습니다. 정답을 기준선으로 삼지 않고 {pack['material']}을 나란히 놓아 같은 판단이 다른 문제에도 이어지는지 확인했습니다.",
        f"{location}의 가상 {grade} 학생이 시험 직전 {focus} 문제 수만 늘렸지만 같은 오류가 반복됐다고 가정합니다. 학생의 의지로 평가하지 않고 개념·조건·전략·계산·시간 중 오류가 시작된 한 단계를 찾았습니다.",
        f"가상의 {grade} 학생은 해설을 본 직후에는 {focus} 풀이를 재현했지만 다음 날 첫 판단을 꺼내지 못했습니다. 기억 문제인지 표현 전환의 문제인지 구분하기 위해 도움의 크기와 재시도 간격을 따로 남겼습니다.",
    )
    phases = (
        ("첫 확인", pack["signal"], "첫 풀이와 중단 위치를 보존"),
        ("한 가지 조정", pack["action"], "도움 전후의 학생 행동을 구분"),
        ("간격 뒤 재시도", pack["transfer"], pack["check"]),
    )
    rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(action)}</td><td>{escape(record)} — {escape(focus)}</td></tr>"
        for label, action, record in phases
    )
    decisions = (
        "근거와 검산까지 혼자 이어지면 학교 범위 안의 낯선 문항으로 옮깁니다.",
        "짧은 질문 뒤 가능하면 힌트 문장을 줄이고 같은 위치부터 다시 시작합니다.",
        "첫 판단이 나오지 않으면 단원 전체가 아니라 바로 필요한 선수 개념 하나만 복원합니다.",
    )
    shift = _stable_index(slug, "case-decisions") % 3
    decisions = decisions[shift:] + decisions[:shift]
    items = "".join(f"<li>{escape(item)} {escape(location)}의 {escape(focus)} 기록으로 다시 확인합니다.</li>" for item in decisions)
    closing_frames = (
        f"한 번의 성공을 성적 향상으로 일반화하지 않습니다. {location}의 {focus} 계획에서는 필요한 힌트가 줄었는지, 설명이 구체화됐는지, 정한 날에 다시 시작했는지를 다음 결정에 사용합니다.",
        f"보호자는 ‘왜 또 틀렸니?’보다 ‘{focus}에서 처음 무엇을 보고 시작했니?’라고 묻습니다. {location} 학생의 답을 대신 설명하지 않고 다음 재시도에서 혼자 할 행동 하나를 정합니다.",
        f"결과가 같아도 과정은 달라질 수 있습니다. {location}의 {focus} 기록에서 첫 판단과 검산이 나아졌다면 그 행동을 유지하고, 변화가 없다면 난도·분량·힌트 간격 중 하나만 바꿉니다.",
    )
    return (
        f'<section class="high-math-block {STUDENT_CASE_MARKER}" data-case-model="composite" '
        f'data-case-grade="{grade}" data-case-kind="{kind}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'case-heading'))}</h2>"
        f"<p>{escape(_pick(disclaimer_frames, slug, 'case-disclaimer'))}</p>"
        f"<p>{escape(_pick(situation_frames, slug, 'case-situation'))}</p>"
        "<table><thead><tr><th>관찰 시점</th><th>학생 행동과 과제</th><th>남길 기록</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><ol>{items}</ol>"
        f"<p>{escape(_pick(closing_frames, slug, 'case-closing'))}</p></section>"
    )


def _decision_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{location}의 {focus} 기록으로 다음 주 과제를 결정하는 방법",
        f"유지·축소·변경으로 나누는 {location} {focus} 학습 점검",
        f"{focus} 재시도 결과를 {location} 주간 계획에 반영하기",
        f"문제 수가 아닌 행동으로 정하는 {location}의 {focus} 다음 단계",
    )
    lead_frames = (
        f"{location} 학생의 {focus} 계획은 정답률이 올랐다는 이유만으로 바로 확대하지 않습니다. 첫 시도와 재시도의 조건을 같게 두고, 필요한 힌트와 풀이 근거, 검산이 어떻게 달라졌는지 비교합니다. 세 기록 중 하나만 좋아졌다면 나머지 행동이 안정될 수 있도록 현재 난도를 짧게 유지합니다.",
        f"한 주 동안 {focus} 과제를 모두 끝냈더라도 {location} 학생이 해설 없이 다시 시작하지 못하면 완료로 처리하기 어렵습니다. 분량을 채운 날과 실제로 재현한 날을 구분하고, 다음 주에는 새 문제 수보다 끊긴 단계의 과제를 먼저 배치합니다.",
        f"{location}에서 {focus} 학습을 조정할 때 점수 한 번을 장기 변화로 해석하지 않습니다. 같은 오류가 반복된 조건과 도움 없이 해결한 조건을 나란히 놓고, 유지할 행동 하나와 바꿀 조건 하나만 선택합니다.",
        f"시험 일정이 가까워질수록 {focus} 복습을 모두 같은 긴급 과제로 표시하기 쉽습니다. {location} 학생은 학교 범위 안의 미완료 개념, 오래 걸린 정답, 설명이 끊긴 서술형을 분리하고 다음 학습에서 가장 먼저 확인할 한 항목을 정합니다.",
    )
    rows = (
        (
            "유지",
            f"{focus}의 첫 판단과 {pack['check']}라는 검산이 도움 없이 반복됨",
            f"{location} 학교 범위 안에서 표현만 다른 한 문제로 확장",
        ),
        (
            "축소",
            f"{focus}의 개념은 말하지만 {pack['signal']}라는 관찰에서 흐름이 끊김",
            f"{location} 과제를 대표 문제와 간격 뒤 재시도 한 건으로 줄임",
        ),
        (
            "변경",
            f"{focus}에서 같은 힌트를 받아도 첫 단계가 계속 달라지지 않음",
            f"{location} 기록의 난도·분량·힌트 위치 가운데 하나만 바꿈",
        ),
    )
    shift = _stable_index(slug, "decision-row-order") % 3
    rows = rows[shift:] + rows[:shift]
    row_html = "".join(
        f"<tr><td>{escape(choice)}</td><td>{escape(evidence)}</td><td>{escape(next_step)}</td></tr>"
        for choice, evidence, next_step in rows
    )
    interpretation_frames = (
        f"{location}의 {focus} 표에서 ‘축소’는 학습을 포기한다는 뜻이 아닙니다. 확인할 행동을 줄여 원인을 분명히 만드는 선택입니다. 반대로 ‘유지’는 같은 문제를 반복하는 것이 아니라 같은 판단 기준을 조건이 달라진 문항에서도 사용하게 한다는 뜻입니다.",
        f"{focus} 기록이 ‘변경’에 해당하면 교재를 즉시 추가하지 않습니다. {location} 학생이 막힌 줄에 필요한 설명 방식, 질문의 길이, 재시도 간격 가운데 하나를 바꾸고 다른 조건은 유지해야 변화의 원인을 비교할 수 있습니다.",
        f"다음 과제는 {location} 학생의 의지나 성향을 평가하는 문장으로 적지 않습니다. {focus}에서 관찰할 첫 행동, 도움을 줄 시점, 종료 기준을 동사로 쓰면 학생과 보호자가 같은 기록을 보고도 다른 판단을 내리는 일을 줄일 수 있습니다.",
        f"{location} 학생이 {focus} 문제를 맞혔지만 시간이 크게 늘었다면 정답과 실전 준비를 분리해 기록합니다. 개념 적용은 유지하고 시간 판단만 짧은 문항 묶음에서 다시 확인하면 이미 안정된 개념을 불필요하게 반복하지 않을 수 있습니다.",
    )
    questions = (
        f"{location}의 {focus} 첫 풀이에서 학생이 혼자 확인한 조건은 무엇인가",
        f"{focus} 설명 중 {location} 학생이 처음 도움을 요청한 문장은 어디인가",
        f"하루 이상 뒤에 {location} 학생이 {focus}의 어느 단계까지 자료 없이 복원했는가",
        f"다음 {focus} 과제에서 {location} 학생에게 그대로 유지할 행동은 무엇인가",
    )
    question_shift = _stable_index(slug, "decision-question-order") % len(questions)
    questions = questions[question_shift:] + questions[:question_shift]
    items = "".join(f"<li>{escape(question)}</li>" for question in questions)
    closing_frames = (
        f"보호자와 학생이 함께 볼 때에는 {focus}의 답을 다시 설명하기보다 위 네 질문에 남은 기록을 확인합니다. {location} 일정이 바뀌어도 재시도 날짜와 첫 문제를 구체적으로 적어 두면 학습 흐름을 다시 시작하기 쉽습니다.",
        f"{location}의 다음 상담에서는 {focus} 문제 수를 먼저 묻지 않습니다. 유지·축소·변경 중 어떤 결정을 했고 그 근거가 첫 풀이에 남아 있는지 확인한 뒤, 실제 시험일까지 가능한 과제만 일정표에 넣습니다.",
        f"이 결정표는 {location} 학생의 점수 상승을 예측하는 도구가 아닙니다. {focus}에서 혼자 할 수 있는 범위와 필요한 도움을 더 정확히 구분해 다음 과제를 과도하게 늘리거나 반복하지 않도록 돕는 기록 기준입니다.",
    )
    return (
        f'<section class="high-math-block high-math-decision" data-decision-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'decision-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'decision-lead'))}</p>"
        "<h3>기록에 따라 유지·축소·변경 선택하기</h3>"
        "<table><thead><tr><th>결정</th><th>관찰 근거</th><th>다음 행동</th></tr></thead>"
        f"<tbody>{row_html}</tbody></table><p>{escape(_pick(interpretation_frames, slug, 'decision-interpretation'))}</p>"
        "<h3>학생과 보호자가 함께 확인할 네 질문</h3>"
        f"<ul>{items}</ul><p>{escape(_pick(closing_frames, slug, 'decision-closing'))}</p></section>"
    )


def _focus_language_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    terms = [term.strip() for term in re.split(r"\s+|의\s*", focus) if term.strip()]
    first_term = terms[0] if terms else focus
    last_term = terms[-1] if terms else focus
    heading_frames = (
        f"‘{focus}’이라는 표현을 실제 풀이 질문으로 바꾸는 {location} 방법",
        f"{location} 학생이 {focus}의 핵심어를 설명하는 순서",
        f"{focus}의 용어·조건·결론을 분리하는 {location} 기록",
        f"문제 문장에서 {focus}의 판단 단서를 찾는 {location} 기준",
    )
    lead_frames = (
        f"{location} 학생이 {focus}의 공식은 기억해도 문제 문장의 표현을 자신의 질문으로 바꾸지 못하면 첫 전략이 흔들릴 수 있습니다. ‘{first_term}’와 ‘{last_term}’가 문항에서 각각 무엇을 가리키는지 표시하고, 두 표현 사이의 관계를 말한 뒤 계산을 시작합니다. 답을 고른 뒤에는 처음 만든 질문으로 돌아가 결론이 실제 질문에 답하는지 확인합니다.",
        f"{focus}을 한 덩어리의 공식 이름으로 외우지 않습니다. {location}의 풀이 여백에 ‘{first_term}에서 주어진 것은 무엇인가’, ‘{last_term}에 대해 구할 것은 무엇인가’를 따로 적습니다. 이 두 질문이 정리되면 {pack['action']} 문장이 길어져도 계산에 필요한 조건과 설명용 정보를 구분하기 쉬워집니다.",
        f"문제를 읽고 바로 식을 쓰기 전에 {location} 학생은 {focus}의 핵심 표현인 ‘{first_term}’와 ‘{last_term}’를 표시합니다. 각 표현 옆에 주어진 값, 찾아야 할 관계, 가능한 범위를 한 칸씩 두고 {pack['signal']}를 확인합니다. 이 기록은 정답을 늦추기 위한 절차가 아니라 잘못된 전략을 일찍 발견하기 위한 장치입니다.",
        f"{location}의 {focus} 학습에서 용어 설명과 문제 적용을 분리하지 않습니다. ‘{first_term}’의 뜻을 말한 직후 문항의 어느 조건과 연결되는지 찾고, ‘{last_term}’가 최종 답의 단위나 범위에 어떤 영향을 주는지 확인합니다. 설명이 풀이에 사용되지 않았다면 외운 정의와 적용 가능한 정의를 아직 구분해야 합니다.",
    )
    questions = (
        f"{location}의 {focus} 문항에서 ‘{first_term}’는 어떤 대상이나 조건을 가리키는가",
        f"‘{last_term}’를 판단하려면 {focus}의 어떤 정의 또는 관계가 필요한가",
        f"{focus}의 조건 하나를 바꾸면 {location} 학생의 첫 식·그림·그래프 중 무엇이 달라지는가",
        f"계산 결과가 {focus}의 처음 질문과 {location} 문제의 허용 범위에 맞는가",
    )
    shift = _stable_index(slug, "focus-language-order") % len(questions)
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(question)}</li>" for question in questions)
    closing_frames = (
        f"네 질문에 대한 답은 긴 문장일 필요가 없습니다. {location} 학생이 {focus}의 ‘{first_term}’와 ‘{last_term}’를 실제 조건에 연결하고 {pack['check']}라는 확인 행동까지 이어 가면, 다음에는 질문 수를 줄여 혼자 시작하는 범위를 넓힙니다.",
        f"{focus}의 용어를 설명했지만 문제에 적용하지 못하면 {location} 학생에게 완성 풀이를 다시 보여 주지 않습니다. ‘{first_term}’가 등장한 조건과 ‘{last_term}’가 필요한 결론 사이에 빈 한 줄을 두고, 그 줄에 사용할 정의나 관계만 스스로 채우게 합니다.",
        f"{location}의 기록에는 {focus}의 정답과 함께 학생이 만든 질문 하나를 남깁니다. 다음 날 ‘{first_term}’와 ‘{last_term}’의 표현이 달라진 문항에서 같은 질문을 다시 만들 수 있다면, 외운 문장보다 적용 가능한 수학 언어가 형성됐는지 확인할 수 있습니다.",
        f"시험 직전에는 {focus}의 모든 설명을 다시 외우지 않습니다. {location} 학생이 자주 놓친 ‘{first_term}’ 조건과 ‘{last_term}’ 판단만 짧은 질문으로 복원하고 {pack['transfer']}라는 적용 행동으로 마무리합니다.",
    )
    return (
        f'<section class="high-math-block high-math-focus-language" data-focus-language="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'focus-language-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'focus-language-lead'))}</p>"
        "<h3>핵심어를 풀이 행동으로 바꾸는 네 질문</h3>"
        f"<ul>{items}</ul><p>{escape(_pick(closing_frames, slug, 'focus-language-closing'))}</p></section>"
    )


def _context_links(slug: str, location: str, focus: str) -> str:
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    broader_slug = f"{city}고등수학과외"
    local_math_slug = f"{location}수학과외"
    broader_labels = (
        f"{city} 고등수학 학습 범위",
        f"{city} 고등수학과외 안내",
        f"{city} 지역의 고등수학 기준",
    )
    local_labels = (
        f"{location} 수학과외 전체 안내",
        f"{location} 수학 학습 페이지",
        f"{location} 수학과외 기준",
    )
    broader = f'<a href="/{broader_slug}/" data-link-role="broader-high-math">{escape(_pick(broader_labels, slug, "broader-label"))}</a>'
    local = f'<a href="/{local_math_slug}/" data-link-role="local-all-math">{escape(_pick(local_labels, slug, "local-label"))}</a>'
    frames = (
        f"{focus}의 학년 전체 연결을 비교할 때에는 {broader}에서 도시 단위의 기준을 확인할 수 있습니다. 초·중·고 수학의 큰 흐름이 필요할 때만 {local}를 보고, 현재 시험 범위와 직접 관련 없는 페이지까지 한꺼번에 확장하지 않습니다.",
        f"이 페이지의 {focus} 기록만으로 다른 단원까지 일반화하지 않습니다. 상위 지역의 고등수학 흐름은 {broader}, 학년을 넓힌 과목별 안내는 {local}에서 목적에 맞게 한 번씩 확인합니다.",
        f"{location} 학생의 {focus} 계획이 단원 문제인지 학년 전체의 공백인지 구분하려면 {broader}와 대조합니다. 현재 학년 밖의 수학 연결이 필요한 경우에는 {local}를 참고하되 실제 학교 자료를 우선합니다.",
        f"{focus} 복습을 마친 뒤 다음 단원으로 옮길 기준은 {broader}에서 비교할 수 있습니다. 더 넓은 과목 계획이 필요할 때에는 {local}를 사용하고, 같은 키워드 링크를 문장마다 반복하지 않습니다.",
    )
    return (
        f'<aside class="{CONTEXT_LINKS_MARKER}" data-link-count="2" aria-label="{escape(location)} 고등수학 관련 페이지">'
        f"<p>{_pick(frames, slug, 'context-frame')}</p></aside>"
    )


def _faq(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    grade = ("고1", "고2", "고3")[_stable_index(slug, "faq-grade") % 3]
    questions = (
        f"{location}고등수학과외에서는 {focus}을 무엇부터 점검하나요?",
        f"{location} {grade} 학생의 {focus} 학습량은 어떻게 정하나요?",
        f"{location} 내신과 모의고사에서 {focus}을 어떻게 다르게 준비하나요?",
        f"{location} 학생이 {focus}을 이해했다고 말할 때 무엇으로 확인하나요?",
        f"{location}에서 {focus}의 다음 유형으로 넘어가는 기준은 무엇인가요?",
    )
    answer_frames = (
        (
            f"{pack['material']}을 나란히 놓고 {pack['signal']}를 먼저 확인합니다. {location} 학생의 첫 풀이를 지우지 않은 채 {pack['action']} 하루 이상 뒤에는 해설 없이 같은 원리의 첫 단계를 다시 시작합니다.",
            f"정답률 하나로 {focus}의 시작점을 정하지 않습니다. {location} 학생이 사용한 조건과 중단 위치를 남기고 {pack['action']} 그 뒤 다른 표현의 문항에서 {pack['transfer']}",
        ),
        (
            f"{grade}이라고 정해진 문제 수를 일괄 적용하지 않습니다. {location}의 {focus} 기록에서 혼자 가능한 단계, 짧은 질문 뒤 가능한 단계, 개념 복원이 필요한 단계를 나누고 시험일까지 남은 날짜에 맞춰 한 번에 바꿀 행동을 하나만 정합니다.",
            f"{pack['finish']}라는 질문에 답할 수 있는 분량을 기준으로 삼습니다. {location} 학생이 같은 날에는 가능해도 간격 뒤 시작하지 못하면 새 문제를 늘리지 않고 {focus}의 대표 문항과 재시도 날짜를 남깁니다.",
        ),
        (
            f"내신은 실제 교과서와 학교 범위, 서술형 근거를 먼저 보고 모의고사는 틀린 문항뿐 아니라 오래 걸린 정답 문항도 확인합니다. {location}의 {focus} 기록에서는 두 평가의 오답을 개념·조건·전략·계산·시간으로 같은 방식으로 분류합니다.",
            f"학교별 출제 경향을 지역명으로 추측하지 않습니다. {location} 학생이 받은 자료에서 {focus} 범위를 확인하고 내신에서는 ‘{pack['written']}?’를, 모의고사에서는 시간 안에 첫 판단을 세웠는지를 별도로 봅니다.",
        ),
        (
            f"이해했다는 말은 출발점으로만 봅니다. {location} 학생에게 {pack['transfer']} 이어 {pack['check']} 정답이 같더라도 필요한 힌트가 줄었는지와 근거를 혼자 설명했는지를 각각 기록합니다.",
            f"완성 풀이를 다시 읽는 대신 {focus}의 첫 조건과 전략을 자료 없이 말하게 합니다. {location} 학생이 시작은 하지만 중간에서 멈춘다면 전체 설명을 반복하지 않고 그 줄에 필요한 질문 하나만 제공합니다.",
        ),
        (
            f"완료 질문은 ‘{pack['finish']}?’입니다. {location} 학생이 한 번 맞힌 것만으로 {focus}을 끝내지 않고 다른 수치·표현·조건에서도 같은 근거와 검산이 남는지 확인한 뒤 다음 유형으로 이동합니다.",
            f"{pack['check']}라는 행동과 간격 뒤 재시도가 도움 없이 이어져야 합니다. {location}의 {focus} 결과가 같다면 학생을 평가하지 않고 과제 난도·분량·힌트 간격 중 하나만 바꾸어 다음 기록과 비교합니다.",
        ),
    )
    pairs: list[str] = []
    for idx, question in enumerate(questions):
        answer = answer_frames[idx][_stable_index(slug, f"faq-answer-{idx}") % 2]
        question = _fix_high_focus_particles(question, focus)
        answer = _fix_high_focus_particles(answer, focus)
        pairs.append(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>")
    heading_frames = (
        f"{location}고등수학과외와 {focus}에 관해 자주 묻는 질문",
        f"{location} {grade} 학생의 {focus} 학습 FAQ",
        f"{focus} 진단부터 시험 복습까지 묻는 {location} FAQ",
        f"{location}에서 {focus} 계획을 세울 때 자주 묻는 질문",
    )
    return (
        f'<section class="high-math-faq-section">'
        f'<h2 class="{FAQ_MARKER}" data-faq-focus="{escape(focus)}">'
        f"{escape(_pick(heading_frames, slug, 'faq-heading'))}</h2>{''.join(pairs)}</section>"
    )


def build_local_high_math_meta(slug: str, body: str) -> tuple[str, str]:
    focus = _focus_from_body(body)
    kind = _kind_for_focus(focus)
    frames = (
        f"{slug}에서 ‘{focus}’을 학교 자료와 실제 풀이 기록으로 점검합니다. 내신·모의고사·서술형의 첫 판단, 학년별 계획, 합성 사례와 재시도 기준을 정리했습니다.",
        f"{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 조건 해석과 풀이 근거, 학교 정보 확인, 고1·고2·고3 계획, 오답 재시도와 주제별 FAQ를 제공합니다.",
        f"{slug} 페이지는 ‘{focus}’에서 막힌 위치를 찾는 기준을 다룹니다. 시험 자료 구분부터 가상 학생 사례, 검산, 다음 유형 이동 조건까지 확인할 수 있습니다.",
        f"{slug} 고등학생이 ‘{focus}’을 준비할 때 남길 기록을 정리했습니다. 실제 학교 범위, 첫 전략, 수정 이유, 시간 판단과 간격 뒤 재풀이를 함께 확인하세요.",
    )
    description = _fix_high_focus_particles(_pick(frames, slug, f"meta-{kind}"), focus)
    title = _fix_high_focus_particles(f"{slug} | {focus}", focus)
    return title, description


def _individualize_headings(body: str, location: str, focus: str) -> str:
    def replace(match: re.Match[str]) -> str:
        opening, inner, closing = match.groups()
        text = _plain_text(inner)
        additions: list[str] = []
        if location not in text:
            additions.append(location)
        if not additions:
            return match.group(0)
        suffix = " · ".join(additions)
        return f"{opening}{inner} — {escape(suffix)} 기준{closing}"

    return re.sub(
        r"(<h[23]\b[^>]*>)(.*?)(</h[23]>)",
        replace,
        body,
        flags=re.I | re.S,
    )


def _individualize_paragraphs(body: str, location: str, focus: str) -> str:
    def replace(match: re.Match[str]) -> str:
        opening, inner, closing = match.groups()
        text = _plain_text(inner)
        if location in text or focus in text:
            return match.group(0)
        addition = f" {escape(location)} 학생의 실제 풀이 기록에서는 같은 질문을 첫 시도와 재시도에 각각 적용합니다."
        return f"{opening}{inner}{addition}{closing}"

    return re.sub(r"(<p\b[^>]*>)(.*?)(</p>)", replace, body, flags=re.I | re.S)


def build_local_high_math_body(slug: str, focus: str) -> str:
    location = slug.removesuffix("고등수학과외")
    focus = focus.strip()
    kind = _kind_for_focus(focus)
    pack = HIGH_PACKS[kind]
    base_pack = MATH_PACKS[BASE_KIND[kind]]
    index = _stable_index(slug, "base-sections")
    diagnosis = _diagnosis_section(location, focus, base_pack, index)
    practice = _practice_section(location, focus, base_pack, index + 3)
    schedule = _schedule_section(location, focus, base_pack, index + 7)
    review = _review_section(location, focus, base_pack, index + 11)
    sections = {
        "diagnosis": diagnosis,
        "grade": _grade_section(slug, location, focus, pack),
        "search": _search_intent_section(slug, location, focus, pack),
        "deep": _deep_dive_section(slug, location, focus, pack),
        "practice": practice,
        "schedule": schedule,
        "case": _student_case_section(slug, location, focus, kind, pack),
        "decision": _decision_section(slug, location, focus, pack),
        "language": _focus_language_section(slug, location, focus, pack),
        "school": _school_context_section(slug, location, focus),
        "review": review,
    }
    orders = (
        ("diagnosis", "grade", "search", "language", "deep", "practice", "case", "decision", "school", "schedule", "review"),
        ("search", "diagnosis", "practice", "deep", "grade", "language", "school", "case", "decision", "schedule", "review"),
        ("grade", "diagnosis", "school", "search", "language", "deep", "practice", "decision", "schedule", "case", "review"),
        ("diagnosis", "case", "search", "deep", "language", "grade", "practice", "school", "decision", "schedule", "review"),
        ("practice", "diagnosis", "grade", "deep", "search", "case", "language", "schedule", "decision", "school", "review"),
        ("school", "diagnosis", "search", "language", "practice", "deep", "grade", "case", "decision", "schedule", "review"),
    )
    order = orders[_stable_index(slug, "section-order") % len(orders)]
    core = "".join(sections[name] for name in order)
    body = (
        f'<section class="{CONTENT_MARKER}" data-content-version="{CONTENT_VERSION}" '
        f'data-high-math-focus="{escape(focus)}" data-math-kind="{escape(kind)}">'
        f"{_opening(slug, location, focus)}{core}{_context_links(slug, location, focus)}"
        f"{_faq(slug, location, focus, pack)}</section>"
    )
    body = _individualize_headings(body, location, focus)
    body = _individualize_paragraphs(body, location, focus)
    return _fix_high_focus_particles(body, focus)


def individualize_local_high_math_body(body: str, slug: str) -> str:
    if not is_local_high_math_slug(slug):
        return body
    if f'data-content-version="{CONTENT_VERSION}"' in body:
        return body
    return build_local_high_math_body(slug, _focus_from_body(body))
