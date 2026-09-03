from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path

from sitegen.utils import escape


LOCAL_HIGH_ENGLISH_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)고등영어과외$")
CONTENT_MARKER = "local-high-english-content"
CONTENT_VERSION = "high-english-individual-v4"
SCHOOL_CONTEXT_MARKER = "high-english-school-context"
SEARCH_INTENT_MARKER = "high-english-search-intent"
STUDENT_CASE_MARKER = "high-english-student-case"
FAQ_MARKER = "high-english-faq"
CONTEXT_LINKS_MARKER = "high-english-context-links"

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


def _particle(value: str, final_form: str, open_form: str) -> str:
    if not value:
        return open_form
    code = ord(value[-1])
    has_final = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    return final_form if has_final else open_form


def _with_particle(value: str, final_form: str, open_form: str) -> str:
    return f"{value}{_particle(value, final_form, open_form)}"


def is_local_high_english_slug(slug: str) -> bool:
    return bool(LOCAL_HIGH_ENGLISH_PATTERN.fullmatch(slug))


def _focus_from_body(body: str) -> str:
    current = re.search(r'data-high-english-focus="([^"]+)"', body, flags=re.I)
    if current:
        return unescape(current.group(1)).strip()
    heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    heading_text = _plain_text(heading.group(1)) if heading else ""
    patterns = (
        r"고등영어과외,\s*(.+?)\s*중심의\s*고등\s*영어",
        r"고등영어과외에서\s*(.+?)(?:을|를)\s*중심으로",
        r"고등영어과외,\s*(.+?)(?:을|를)\s*확인하는",
    )
    for pattern in patterns:
        match = re.search(pattern, heading_text)
        if match:
            return match.group(1).strip()
    paragraph = re.search(r"페이지에서는\s*(.+?)(?:을|를)\s*중심으로", _plain_text(body))
    if paragraph:
        return paragraph.group(1).strip()
    return "학교 영어 자료의 근거 확인"


def _kind_for_focus(focus: str) -> str:
    if any(word in focus for word in ("듣기", "발음", "강세", "연음", "대화")):
        return "listening"
    if any(word in focus for word in ("쓰기", "영작", "서술형", "답안", "발표", "말하기", "바꿔쓰기", "교정")):
        return "output"
    if any(
        word in focus
        for word in (
            "구문", "절", "주어", "동사", "수식", "어순", "문법", "분사", "관계사",
            "전치사", "병렬", "도치", "강조", "명사", "부사", "접속사", "동격",
        )
    ):
        return "grammar"
    if any(
        word in focus
        for word in (
            "독해", "지문", "빈칸", "순서", "삽입", "요지", "제목", "내용 일치", "요약문",
            "도표", "정보", "문해력", "본문", "추론", "논리", "주제문",
        )
    ):
        return "reading"
    if any(word in focus for word in ("어휘", "단어", "표현", "철자", "유의어", "반의어")):
        return "vocabulary"
    return "routine"


HIGH_ENGLISH_PACKS: dict[str, dict[str, str]] = {
    "reading": {
        "name": "독해 판단",
        "material": "학교 시험 범위의 본문과 유인물, 최근 모의고사 지문, 학생이 근거를 표시한 첫 답안",
        "signal": "낱문장의 뜻을 넘어 문단 기능과 연결 관계, 선택지를 고른 근거를 설명하는지",
        "diagnosis": "모르는 단어에서 멈춘 것인지, 중심절을 잘못 묶은 것인지, 문단 사이의 논리를 놓친 것인지 세 층으로 분류합니다.",
        "action": "각 문단의 역할을 주장·예시·대조·결론 가운데 하나로 적고 답의 근거가 된 문장을 표시합니다.",
        "transfer": "소재와 표현이 달라진 지문에서도 같은 관계 표지를 찾아 판단 순서를 다시 적용합니다.",
        "check": "정답을 본 뒤 이해했다고 넘기지 않고 근거 문장을 가린 상태에서 선택 이유를 다시 말합니다.",
        "finish": "새 지문에서 문단 관계와 답의 근거를 제한 시간 안에 혼자 설명할 수 있는가",
        "grade1": "교과서 문장 구조와 문단의 중심 내용을 정확하게 연결해 긴 글을 읽는 기본 순서를 만듭니다.",
        "grade2": "추상적 소재와 복합 문장을 읽을 때 접속 표현, 지시어, 문단 기능을 한 흐름으로 묶습니다.",
        "grade3": "시간 제한 속에서 모든 문장을 번역하지 않고 유형별 핵심 근거와 선택지의 왜곡을 빠르게 구분합니다.",
    },
    "grammar": {
        "name": "구문·문법 적용",
        "material": "교과서와 학교 유인물의 핵심 문장, 어법 문항, 학생이 주절과 수식 범위를 표시한 분석 기록",
        "signal": "문법 이름을 외우는 데서 끝나지 않고 형태·문장 역할·의미 변화를 연결하는지",
        "diagnosis": "형태를 찾지 못한 것인지, 절과 수식 범위를 잘못 나눈 것인지, 규칙은 알지만 변형 문장에 적용하지 못한 것인지 구분합니다.",
        "action": "주어와 동사, 주절과 종속절, 수식 대상에 서로 다른 표시를 하고 해당 형태를 선택한 이유를 한 문장으로 적습니다.",
        "transfer": "주어·시제·수식 대상 중 한 조건을 바꾼 문장을 만들고 원문과 의미가 어떻게 달라지는지 설명합니다.",
        "check": "문장 성분을 지운 뒤 구조를 복원하고 번역과 문법 판단이 서로 어긋나지 않는지 확인합니다.",
        "finish": "처음 보는 문장에서 핵심절과 수식 범위를 나누고 형태를 선택한 근거를 설명할 수 있는가",
        "grade1": "기본 문형과 품사, 절의 경계를 교과서 예문에서 확인하고 해석과 어법 문제에 함께 적용합니다.",
        "grade2": "관계사·분사·도치처럼 정보가 길어진 문장에서 핵심절을 보존하고 의미 관계를 정확히 읽습니다.",
        "grade3": "복합 구문을 빠르게 구조화하되 어법 판단에 필요한 형태와 독해에 필요한 의미를 따로 검산합니다.",
    },
    "listening": {
        "name": "듣기 단서",
        "material": "학교 듣기 자료와 모의고사 음원, 선택지, 첫 청취에서 놓친 시점을 적은 기록과 확인용 대본",
        "signal": "소리를 못 들은 문제, 표현 뜻을 놓친 문제, 들었지만 선택을 잘못한 문제를 구분하는지",
        "diagnosis": "오답을 소리 인식·의미 연결·선택 판단의 세 단계로 나누고 대본을 보기 전후에 달라진 이해를 비교합니다.",
        "action": "재생 전에 선택지의 차이를 질문으로 바꾸고 첫 청취에서 답을 결정한 실제 표현과 시점을 표시합니다.",
        "transfer": "놓친 구간만 받아쓴 뒤 비슷한 발음이나 의도를 가진 새 문장에서 같은 단서를 다시 찾습니다.",
        "check": "전체 음원을 반복하기보다 오류 구간을 짧게 재생하고 대본을 덮은 상태에서 뜻과 선택 근거를 복원합니다.",
        "finish": "처음 듣는 대화에서 필요한 정보를 미리 정하고 놓친 이유를 소리·의미·판단으로 설명할 수 있는가",
        "grade1": "숫자·시간·관계·목적처럼 기본 정보의 단서를 듣고 선택지와 대응하는 습관을 만듭니다.",
        "grade2": "연음과 약화, 간접 표현이 늘어난 대화에서 전환 표현과 화자의 태도를 함께 확인합니다.",
        "grade3": "수능 듣기 흐름을 유지하면서 자주 놓치는 유형만 짧은 구간 훈련과 선택지 예측으로 보완합니다.",
    },
    "output": {
        "name": "쓰기·말하기 산출",
        "material": "학교 서술형 문항과 수행평가 안내, 학생의 첫 초안, 교정 전후 문장과 채점 조건표",
        "signal": "모범답안을 외우기보다 요구 조건을 해석하고 초안의 오류를 이유와 함께 수정하는지",
        "diagnosis": "요구 조건을 놓친 것인지, 내용은 있으나 영어 문장으로 만들지 못한 것인지, 교정 뒤에도 같은 오류가 남는지 구분합니다.",
        "action": "시제·필수 표현·문장 수·내용 조건을 먼저 표시하고 핵심어만 본 상태에서 첫 문장을 만듭니다.",
        "transfer": "조건 하나를 바꾼 새 질문에 같은 답안 구조를 사용하고 바뀌어야 할 표현을 스스로 찾습니다.",
        "check": "교정된 문장을 베끼지 않고 수정 이유를 설명한 뒤 자료를 가린 상태에서 다시 쓰거나 말합니다.",
        "finish": "새 과제에서도 조건을 먼저 확인하고 초안·수정·재작성의 세 단계를 혼자 실행할 수 있는가",
        "grade1": "짧은 서술형에서 문장 완결성과 기본 어순, 요구한 정보를 빠짐없이 담는 기준을 익힙니다.",
        "grade2": "요약·의견·발표 과제에서 근거와 연결 표현을 사용하고 문장 간 논리를 스스로 교정합니다.",
        "grade3": "제한 시간과 분량 안에서 채점 조건을 우선 확인하고 정확한 문장으로 답을 압축합니다.",
    },
    "vocabulary": {
        "name": "어휘 문맥 적용",
        "material": "교과서와 학교 유인물의 핵심 어휘, 모의고사에서 뜻을 잘못 적용한 단어, 학생의 예문 기록",
        "signal": "대표 뜻만 외우지 않고 품사·문맥·함께 쓰이는 표현에 따라 적절한 뜻을 고르는지",
        "diagnosis": "처음 보는 단어인지, 뜻은 알지만 문맥에 맞추지 못한 것인지, 철자와 형태를 혼동한 것인지 나눕니다.",
        "action": "원문 문장을 가리고 품사와 주변 단서를 이용해 뜻을 예상한 뒤 사전 뜻과 비교합니다.",
        "transfer": "같은 단어가 다른 품사나 의미로 쓰인 문장을 찾아 공통점과 달라진 단서를 적습니다.",
        "check": "단어장 순서가 아닌 학교 본문과 새 지문에서 뜻·형태·쓰임을 각각 한 번씩 복원합니다.",
        "finish": "간격을 둔 새 문장에서 주변 단서를 이용해 뜻과 품사를 고르고 직접 예문을 만들 수 있는가",
        "grade1": "교과서 핵심어의 뜻과 품사, 철자를 문장 단위로 연결해 기본 어휘망을 만듭니다.",
        "grade2": "다의어와 추상어를 문맥 관계로 구분하고 유의어 사이의 사용 조건을 비교합니다.",
        "grade3": "빈출 어휘를 무작정 늘리지 않고 오답을 만든 의미와 표현부터 실전 지문에서 재확인합니다.",
    },
    "routine": {
        "name": "시험·학습 운영",
        "material": "실제 학교 범위표와 최근 시험지, 모의고사 오답, 일주일의 시작·중단·재시도 기록",
        "signal": "공부시간보다 어떤 자료에서 시작했고 왜 멈췄으며 다음 날 어디까지 혼자 복원했는지",
        "diagnosis": "시간 부족·자료 선택·이해 공백·집중 전환 가운데 학습을 실제로 끊은 원인을 기록으로 구분합니다.",
        "action": "오늘 사용할 학교 자료 한 개와 완료를 증명할 행동 한 개를 정하고 시작·중단 시각을 남깁니다.",
        "transfer": "시험 일정이나 귀가 시간이 달라져도 최소 복습 행동과 다음 시작점을 유지합니다.",
        "check": "밀린 분량을 그대로 옮기지 않고 이번 주 영어 학습을 막은 조건 하나만 바꿔 다시 비교합니다.",
        "finish": "새로운 일정에서도 우선 자료와 종료 기준을 정하고 간격 뒤 복습을 스스로 다시 시작할 수 있는가",
        "grade1": "학교 수업 당일 본문과 문법 표시를 짧게 복원해 고등영어 학습량이 갑자기 늘어나는 시기에 대응합니다.",
        "grade2": "내신 자료와 모의고사를 목적별로 나누고 취약 유형과 수행평가 일정을 한 주 안에서 조정합니다.",
        "grade3": "수능 실전 루틴을 유지하면서 학교 평가와 취약 영역 복습이 서로 밀어내지 않도록 우선순위를 정합니다.",
    },
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


def _opening(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{location}고등영어과외에서 {focus} 학습을 확인하는 출발점",
        f"첫 정답보다 첫 근거를 보는 {location}의 {focus} 기록",
        f"{focus} 판단 과정을 남기는 {location} 고등영어 학습",
        f"{location} 학생의 {focus} 이해를 실제 자료로 확인하는 방법",
        f"학교 영어 자료에서 {focus} 기준을 다시 찾는 {location} 안내",
        f"{location}고등영어과외, {focus} 학습을 재현 가능한 과정으로 바꾸기",
    )
    paragraph_frames = (
        f"{location}이라는 지역명만으로 학생의 학교, 시험 범위, 영어 수준을 추정할 수는 없습니다. 이 페이지는 {focus} 주제를 중심으로 학생이 실제로 받은 학교 자료와 첫 시도, 도움 뒤 수정, 간격을 둔 재시도를 비교하는 교육 정보를 제공합니다.",
        f"고등영어는 같은 정답을 얻어도 판단 근거와 걸린 시간이 다를 수 있습니다. {location} 페이지에서는 {focus} 활동에서 사용한 단서와 중단 위치를 남겨 어휘·구문·논리·시간 문제를 구분합니다.",
        f"{focus} 문제를 많이 풀었다는 사실과 새로운 자료에서도 같은 순서를 사용할 수 있다는 사실은 다릅니다. {location} 학생의 현재 상태는 해설 직후가 아니라 하루 이상 뒤에 첫 판단을 다시 설명하는지로 확인합니다.",
        f"이 페이지는 {location} 학생 모두가 같은 어려움을 겪는다고 말하지 않습니다. ‘{focus}’라는 고유한 점검 주제를 이용해 내신 자료와 모의고사 기록을 어떻게 나누고 다시 연결할지 구체적인 순서로 설명합니다.",
    )
    method_frames = (
        f"{location}의 {focus} 점검은 정답 채점, 근거 표시, 자료를 가린 재현, 새 지문 적용의 네 장면을 섞지 않는 데서 시작합니다. {pack['action']} 이때 교사가 알려 준 부분과 학생이 혼자 찾은 부분을 다른 색으로 남깁니다.",
        f"먼저 {location} 학생의 최근 자료 한 개를 고릅니다. {pack['diagnosis']} 그다음 {focus} 활동에서 처음 바꿀 행동을 한 가지로 제한해야 다음 기록과 비교할 수 있습니다.",
        f"{focus} 학습을 시작할 때 새 교재부터 추가하지 않습니다. {location} 학생이 이미 사용한 자료에서 {pack['signal']}를 확인하고, 표시가 없는 단계만 짧은 과제로 다시 구성합니다.",
        f"{location} 페이지의 기준은 점수 상승을 약속하는 방법이 아닙니다. {focus} 주제에서 학생이 혼자 한 판단과 필요한 도움을 분리해 다음 과제의 크기와 확인 시점을 정하는 관찰 절차입니다.",
    )
    return (
        f"<h2>{escape(_pick(heading_frames, slug, 'opening-heading'))}</h2>"
        f"<p>{escape(_pick(paragraph_frames, slug, 'opening'))}</p>"
        f"<h3>{escape(location)}의 {escape(focus)} 첫 기록을 남기는 방법</h3>"
        f"<p>{escape(_pick(method_frames, slug, 'opening-method'))}</p>"
    )


def _diagnosis_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus} 오류를 세 단계로 나누는 {location} 진단",
        f"{location}의 {focus} 학습이 멈춘 위치 찾기",
        f"정답률보다 먼저 보는 {location} {focus} 진단 기록",
        f"{focus}의 첫 판단·수정·재시도를 분리하는 {location} 기준",
    )
    rows = (
        ("첫 시도", "답·해석·문장 완성 전에 사용한 단서와 예상", pack["signal"]),
        ("도움 뒤 수정", "힌트의 내용과 학생이 실제로 바꾼 부분", pack["action"]),
        ("간격 뒤 재시도", "자료를 가린 뒤 혼자 복원한 단계", pack["finish"]),
    )
    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(evidence)}</td><td>{escape(location)}의 {escape(focus)} 기록: {escape(check)}</td></tr>"
        for label, evidence, check in rows
    )
    closing_frames = (
        f"{location} 학생이 {focus} 활동에서 막힌 원인을 여러 개 적었다면 가장 먼저 멈춘 단계 하나만 다음 과제로 고릅니다. 나머지는 관찰 목록에 남겨 두고 같은 주에 모두 고치려 하지 않습니다.",
        f"진단 결과는 {location} 학생의 능력을 고정하는 이름표가 아닙니다. {focus} 자료, 질문의 길이, 재시도 간격 가운데 한 조건을 바꾸고 다른 조건은 유지해야 변화의 원인을 비교할 수 있습니다.",
        f"{focus} 정답이 맞더라도 시간이 길거나 근거를 말하지 못하면 {location} 기록에는 ‘완료’와 ‘실전 안정’을 따로 표시합니다. 이미 안정된 단계는 반복하지 않고 다음 공백에 시간을 씁니다.",
    )
    return (
        f'<section class="high-english-block high-english-diagnosis" data-english-kind="{escape(pack["name"])}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'diagnosis-heading'))}</h2>"
        f"<p>{escape(location)}에서 {escape(focus)} 주제를 진단할 때 {escape(pack['diagnosis'])} 처음 기록을 지우지 않아야 설명을 들은 결과와 혼자 해결한 결과를 구분할 수 있습니다.</p>"
        f"<table><thead><tr><th>진단 장면</th><th>남길 증거</th><th>확인 질문</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(focus)} 진단 뒤 한 가지만 바꾸기</h3><p>{escape(_pick(closing_frames, slug, 'diagnosis-closing'))}</p></section>"
    )


def _search_intent_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{location}의 {focus} 학습을 내신·모의고사·수능 자료로 구분하기",
        f"{focus} 검색 뒤 실제로 확인할 {location} 고등영어 자료",
        f"학교 시험과 수능형 문제에서 달라지는 {focus}의 역할",
        f"{location} {focus} 목표를 평가 자료별로 나누는 방법",
    )
    intro_frames = (
        f"{location}고등영어과외를 찾는 이유가 학교 내신인지 모의고사인지에 따라 같은 {focus} 활동도 확인 순서가 달라집니다. 시작 자료는 {pack['material']}이며 확인되지 않은 학교별 난도나 출제 경향을 지역명으로 단정하지 않습니다.",
        f"검색어가 같아도 필요한 도움은 다를 수 있습니다. {location} 학생의 {focus} 계획은 {pack['signal']}를 첫 기준으로 삼고 실제 시험 범위와 남은 날짜에 맞춰 자료와 분량을 정합니다.",
        f"{focus} 문제 수보다 자료의 역할을 먼저 구분합니다. {location}에서는 {_with_particle(pack['material'], '을', '를')} 나란히 놓고 내신의 범위 적합성, 모의고사의 판단 과정, 장기 복습의 재현 여부를 따로 기록합니다.",
    )
    rows = (
        ("학교 내신", "교과서·학교 유인물·서술형 범위", "표현과 근거를 학교 자료에서 정확히 찾는지"),
        ("모의고사", "틀린 문항과 오래 걸린 정답 문항", pack["signal"]),
        ("수능·장기 복습", "간격을 둔 새 지문과 시간 기록", pack["finish"]),
    )
    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(material)}</td><td>{escape(location)}의 {escape(focus)} 기준: {escape(check)}</td></tr>"
        for label, material, check in rows
    )
    steps = (
        "학교 범위표와 평가 날짜를 먼저 확인하고 사용할 원본 자료를 한곳에 모읍니다.",
        pack["action"], pack["transfer"], pack["check"],
    )
    shift = _stable_index(slug, "search-order") % len(steps)
    steps = steps[shift:] + steps[:shift]
    items = "".join(f"<li>{escape(location)}의 {escape(focus)} 실행: {escape(step)}</li>" for step in steps)
    closing_frames = (
        f"{location} 학생의 {focus} 내신 기록과 모의고사 기록을 한 점수표에 섞지 않습니다. 범위 정확도와 시간 판단을 따로 본 뒤 공통으로 반복된 오류만 다음 주 우선 과제로 정합니다.",
        f"학교별 영어 시험을 {location}이라는 주소만으로 일반화하지 않습니다. {focus}의 실제 범위는 학생이 받은 자료에서 확인하고 공개되지 않은 출제 정보를 추측해 문장에 넣지 않습니다.",
        f"{focus} 학습에서 새 자료를 추가하는 시점은 {location} 학생이 현재 자료의 첫 판단과 수정 이유를 설명한 뒤입니다. 자료 수보다 목적이 겹치지 않는지가 중요합니다.",
    )
    return (
        f'<section class="high-english-block {SEARCH_INTENT_MARKER}" data-search-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'search-heading'))}</h2>"
        f"<p>{escape(_pick(intro_frames, slug, 'search-intro'))}</p>"
        f"<table><thead><tr><th>평가 목적</th><th>우선 자료</th><th>{escape(focus)} 확인 기준</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(location)}의 {escape(focus)} 자료 확인 순서</h3><ol>{items}</ol>"
        f"<p>{escape(_pick(closing_frames, slug, 'search-closing'))}</p></section>"
    )


def _grade_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"고1·고2·고3에서 달라지는 {location} {focus} 확인 기준",
        f"{location} 학생의 학년별 {focus} 연결 순서",
        f"진도보다 먼저 구분할 {focus}의 학년별 역할",
        f"내신과 수능 준비를 잇는 {location} {focus} 학년 계획",
    )
    grades = [("고1", pack["grade1"]), ("고2", pack["grade2"]), ("고3", pack["grade3"])]
    shift = _stable_index(slug, "grade-order") % len(grades)
    grades = grades[shift:] + grades[:shift]
    items = "".join(
        f"<li><strong>{grade}:</strong> {escape(text)} {escape(location)}의 {escape(focus)} 기록에서는 이 행동이 실제 답안과 복습에 남는지 확인합니다.</li>"
        for grade, text in grades
    )
    closing_frames = (
        f"학년이 같아도 시작점은 다릅니다. {location} 학생에게 앞선 내용을 모두 반복하게 하지 않고 {focus} 활동을 막은 어휘·구문·논리 단계 하나만 복원한 뒤 현재 학교 범위에 바로 적용합니다.",
        f"선행 진도만으로 {focus} 과제를 정하지 않습니다. {location} 학생이 혼자 가능한 단계와 짧은 질문 뒤 가능한 단계를 나누면 현재 학년의 공백을 감추지 않고 계획을 세울 수 있습니다.",
        f"고3이라고 새 지문만 늘리거나 고1이라고 기본 문제만 반복하지 않습니다. {location}의 {focus} 첫 시도에서 확인된 오류 위치를 기준으로 정확도·속도·재현의 비중을 다르게 둡니다.",
    )
    return (
        f'<section class="high-english-block high-english-grade" data-high-grade-plan="three-years">'
        f"<h2>{escape(_pick(heading_frames, slug, 'grade-heading'))}</h2>"
        f"<p>{escape(location)}의 {escape(focus)} 학습은 학년 이름보다 실제 학교 자료와 학생 기록에서 출발합니다. 다음 기준은 일괄 진도가 아니라 각 학년에서 우선 확인할 역할입니다.</p>"
        f"<ul>{items}</ul><h3>{escape(focus)} 학년 계획을 조정하는 기준</h3>"
        f"<p>{escape(_pick(closing_frames, slug, 'grade-closing'))}</p></section>"
    )


def _school_context_section(slug: str, location: str, focus: str) -> str:
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    town = location.removeprefix(city)
    schools = SCHOOL_CONTEXT.get((city, town), [])
    heading_frames = (
        f"{location} 학교 자료를 {focus} 계획에 연결하는 방법",
        f"{town} 주소의 고등학교 공식 정보와 {focus} 확인 순서",
        f"{focus} 복습 전에 구분할 {location} 학교 자료",
        f"{location}에서 공식 학교 정보와 영어 기록을 함께 보는 기준",
    )
    intro_frames = (
        f"학교명과 주소는 저장된 고등학교 지역 매핑 자료에서 {town}이 정확히 일치하는 항목만 사용했습니다. 학교 링크는 일정과 공식 공지를 확인하는 경로이며 {location} 학생의 재학·배정·통학시간을 의미하지 않습니다.",
        f"{location}이라는 주소만으로 재학 학교나 시험 범위를 추정하지 않습니다. 공식 홈페이지에서는 학교명과 일정을 확인하고 {focus}의 실제 범위와 문항은 학생이 받은 범위표·교과서·시험지에서 다시 확인합니다.",
        f"지역 정보와 영어 학습 정보의 역할을 나눕니다. {town}과 정확히 연결된 학교명은 공식 공지의 출처를 찾는 데 사용하고 {focus}의 난도와 진도는 학생 개인의 자료로 판단합니다.",
    )
    if schools:
        items: list[str] = []
        for school in schools[:4]:
            name, homepage = school["name"], school["homepage"]
            if homepage:
                items.append(
                    f'<li><a class="source-link" href="{escape(homepage)}" target="_blank" '
                    f'rel="noopener noreferrer external">{escape(name)} 공식 홈페이지 <span aria-hidden="true">↗</span></a></li>'
                )
            else:
                items.append(f"<li>{escape(name)} — 저장 자료에 개별 홈페이지 주소 없음</li>")
        names = ", ".join(school["name"] for school in schools)
        summary = f"{town} 주소와 정확히 연결된 고등학교는 {len(schools)}곳이며 {names}입니다. 이 목록만으로 가까운 학교나 배정 가능성을 판단하지 않습니다."
        school_block = f'<p>{escape(summary)}</p><ul class="high-english-school-links">{"".join(items)}</ul>'
    else:
        school_block = (
            f"<p>{escape(f'저장된 매핑 자료에서는 {town} 주소와 정확히 일치하는 고등학교를 확인하지 못했습니다. 다른 동의 학교를 가깝다고 추측해 연결하지 않으며 실제 재학 학교명을 기준으로 홈페이지와 범위표를 확인해야 합니다.')}</p>"
        )
    closing_frames = (
        f"학교 홈페이지에 영어 시험 범위가 공개되지 않았더라도 {location} 학생이 받은 자료가 우선입니다. {focus} 항목을 찾아 날짜, 첫 판단, 수정 이유, 재시도 결과를 같은 기록에 남깁니다.",
        f"공식 정보 확인 뒤에는 {focus} 과제를 학교명으로 일반화하지 않습니다. 같은 학교 학생도 과목 편성과 현재 이해가 다르므로 {location} 페이지의 진단 순서를 개인별 답안에 적용합니다.",
        f"학교 정보는 바뀔 수 있으므로 최종 일정은 해당 학교의 공식 안내에서 확인합니다. {focus} 학습 계획은 일정 확인 뒤 학생의 실제 자료와 생활시간을 기준으로 조정합니다.",
    )
    return (
        f'<section class="high-english-block {SCHOOL_CONTEXT_MARKER}" data-school-match="exact-town">'
        f"<h2>{escape(_pick(heading_frames, slug, 'school-heading'))}</h2>"
        f"<p>{escape(_pick(intro_frames, slug, 'school-intro'))}</p>{school_block}"
        f"<p>{escape(_pick(closing_frames, slug, 'school-closing'))}</p></section>"
    )


def _practice_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus} 학습을 원본·변형·재현으로 나누는 {location} 실습",
        f"{location}의 {focus} 판단을 새 자료로 옮기는 연습",
        f"설명을 들은 뒤 혼자 다시 하는 {location} {focus} 과정",
        f"{focus}에서 같은 오류를 반복하지 않는 {location} 연습 순서",
    )
    step_sets = (
        ("원본 자료에서 첫 판단을 지우지 않고 단서와 중단 위치를 표시합니다.", pack["action"], pack["transfer"], pack["check"]),
        (pack["action"], "교정과 해설을 닫고 핵심 단서만 본 상태에서 판단을 다시 설명합니다.", pack["check"], pack["transfer"]),
        ("시험과 같은 조건으로 짧게 시도하되 막힌 순간에 사용하려던 전략을 적습니다.", pack["diagnosis"], pack["action"], pack["transfer"]),
    )
    steps = step_sets[_stable_index(slug, "practice-set") % len(step_sets)]
    items = "".join(f"<li>{escape(location)}의 {escape(focus)} 연습: {escape(step)}</li>" for step in steps)
    closing_frames = (
        f"{location} 학생이 {focus} 활동을 한 번 성공했다고 바로 난도를 올리지 않습니다. 도움 없이 같은 판단을 재현한 시점과 새로운 조건에서 적용한 시점을 따로 기록한 뒤 다음 자료를 정합니다.",
        f"연습량을 늘리기 전에 {location}의 {focus} 오류가 같은 단계에서 반복되는지 봅니다. 반복된다면 완성 답을 다시 보여 주지 않고 그 단계 직전의 질문과 자료 표시만 조정합니다.",
        f"{focus} 연습을 마친 뒤 {location} 기록에는 맞힌 수보다 처음 단서, 수정 이유, 간격 뒤 결과를 남깁니다. 세 항목이 비어 있으면 다음 수업에서 같은 조건으로 한 번 더 관찰합니다.",
    )
    return (
        f'<section class="high-english-block high-english-practice" data-practice-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'practice-heading'))}</h2>"
        f"<p>{escape(location)}에서 {escape(focus)} 연습을 설계할 때에는 원본 이해, 힌트 뒤 수정, 자료를 가린 재현을 서로 다른 단계로 둡니다. ‘{escape(pack['finish'])}’라는 질문에 답할 수 있도록 각 단계의 증거를 남깁니다.</p>"
        f"<h3>{escape(focus)} 실습의 네 단계</h3><ol>{items}</ol>"
        f"<p>{escape(_pick(closing_frames, slug, 'practice-closing'))}</p></section>"
    )


def _schedule_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{location} 생활시간에 맞춘 {focus} 주간 운영",
        f"학교 수업 당일과 주말을 나누는 {location} {focus} 계획",
        f"{focus} 복습을 밀리지 않게 하는 {location} 일정표",
        f"귀가 시각이 달라도 유지할 {location} {focus} 최소 과제",
    )
    rows = (
        ("학교 수업 당일", "학교 자료의 표시와 과제 마감 확인", pack["action"]),
        ("24~48시간 뒤", "원본을 가리고 첫 판단 복원", pack["check"]),
        ("주말", "오류를 원인별로 묶고 새 자료에 적용", pack["transfer"]),
    )
    shift = _stable_index(slug, "schedule-order") % len(rows)
    rows = rows[shift:] + rows[:shift]
    row_html = "".join(
        f"<tr><td>{escape(when)}</td><td>{escape(location)}의 {escape(focus)} 자료: {escape(material)}</td><td>{escape(action)}</td></tr>"
        for when, material, action in rows
    )
    closing_frames = (
        f"{location} 학생의 귀가가 늦은 날에는 {focus} 새 범위를 넣지 않고 전날 오류의 단서 한 개만 복원합니다. 다음 날 원래 계획을 모두 더하지 않고 학교 수업에 필요한 항목부터 다시 시작합니다.",
        f"주간 완료율이 낮다면 {location}의 {focus} 과제를 학생 의지로 설명하지 않습니다. 실제 시작 시각, 처음 멈춘 자료, 다음 날 재개 위치를 보고 분량·자료·시작 신호 중 하나를 바꿉니다.",
        f"시험 일정이 바뀌면 {focus} 계획의 순서는 유지하고 자료 수만 조정합니다. {location} 학생이 이미 남긴 첫 판단과 재시도 기록이 다음 학습의 출발점이 되도록 합니다.",
    )
    return (
        f'<section class="high-english-block high-english-schedule" data-schedule-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'schedule-heading'))}</h2>"
        f"<p>{escape(location)}의 {escape(focus)} 주간 계획은 매일 같은 분량을 요구하지 않습니다. 학교 일정과 실제 시작 가능 시간을 확인하고 짧게 끝내는 날에도 다음 복습으로 이어질 증거를 남깁니다.</p>"
        f"<table><thead><tr><th>시점</th><th>우선 자료</th><th>완료 행동</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(focus)} 계획이 밀린 날의 복구 기준</h3><p>{escape(_pick(closing_frames, slug, 'schedule-closing'))}</p></section>"
    )


def _student_case_section(slug: str, location: str, focus: str, kind: str, pack: dict[str, str]) -> str:
    grade = ("고1", "고2", "고3")[_stable_index(slug, "case-grade") % 3]
    profile_frames = (
        f"학교 범위는 반복했지만 {focus} 판단 근거를 말하지 못하는 {grade} 학생",
        f"정답은 맞아도 {focus} 문제에서 시간이 크게 달라지는 {grade} 학생",
        f"설명 직후에는 가능하지만 간격 뒤 {focus} 활동을 다시 시작하지 못하는 {grade} 학생",
        f"내신 자료와 모의고사를 섞어 {focus} 복습 순서를 정하지 못한 {grade} 학생",
    )
    profile = _pick(profile_frames, slug, "case-profile")
    rows = (
        ("첫 관찰", f"{pack['diagnosis']}", "처음 멈춘 단계와 사용한 단서를 보존"),
        ("한 조건 변경", f"{pack['action']}", "힌트의 길이와 학생이 바꾼 행동을 분리"),
        ("간격 뒤 확인", f"{pack['transfer']}", "새 자료에서 혼자 재현한 단계와 걸린 시간 기록"),
    )
    row_html = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(location)}의 {escape(focus)} 사례 행동: {escape(action)}</td><td>{escape(record)}</td></tr>"
        for stage, action, record in rows
    )
    next_steps = (
        f"{focus} 첫 시도에서 사용한 단서를 학생 말로 한 문장 남깁니다.",
        f"{location} 일정에 맞춰 같은 자료를 다시 볼 날짜와 종료 기준을 정합니다.",
        f"다른 {kind} 자료에서 도움 없이 시작한 마지막 단계를 비교합니다.",
    )
    shift = _stable_index(slug, "case-order") % len(next_steps)
    next_steps = next_steps[shift:] + next_steps[:shift]
    items = "".join(f"<li>{escape(step)}</li>" for step in next_steps)
    closing_frames = (
        f"이 합성 사례에서 {location} 학생의 {focus} 결과가 바로 좋아졌다고 가정하지 않습니다. 같은 조건의 재시도가 두 번 이상 쌓였을 때 필요한 도움과 판단 근거가 어떻게 달라졌는지를 비교합니다.",
        f"사례의 목적은 {location} 학생을 한 유형으로 설명하는 것이 아닙니다. {focus} 학습에서 기록할 장면을 보여 주는 가상 예시이며 실제 계획은 학생의 학교 자료와 생활시간으로 다시 정해야 합니다.",
        f"{focus} 활동이 달라지지 않았다면 {location} 학생의 태도를 평가하지 않습니다. 자료 난도, 질문의 길이, 재시도 간격 중 하나만 바꾸고 나머지 조건은 그대로 두어 다음 기록을 비교합니다.",
    )
    return (
        f'<section class="high-english-block {STUDENT_CASE_MARKER}" data-case-model="composite" data-case-grade="{grade}">'
        f"<h2>{escape(location)}의 {escape(profile)} — 가상 합성 사례</h2>"
        f"<p>다음 내용은 개인정보나 실제 성과 후기가 아니라 {escape(location)}의 {escape(focus)} 학습 과정을 설명하기 위해 여러 상황을 합친 가상 사례입니다. 특정 학교와 학생의 결과로 해석하지 않습니다.</p>"
        f"<table><thead><tr><th>관찰 단계</th><th>실행</th><th>남길 기록</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(focus)} 사례에서 다음 주로 넘길 세 행동</h3><ol>{items}</ol>"
        f"<p>{escape(_pick(closing_frames, slug, 'case-closing'))}</p></section>"
    )


def _decision_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus} 기록으로 유지·축소·변경을 정하는 {location} 기준",
        f"{location}의 {focus} 다음 과제를 고르는 결정표",
        f"정답과 도움의 양을 함께 보는 {location} {focus} 판단",
        f"{focus} 학습량을 늘리기 전에 확인할 {location} 증거",
    )
    rows = (
        ("유지", "근거 설명과 간격 뒤 재현이 이어짐", "같은 난도에서 도움만 조금 줄이기"),
        ("축소", "첫 판단 전에 멈추거나 피로로 기록이 끊김", "자료 길이와 한 번의 완료 행동 줄이기"),
        ("변경", "같은 오류가 같은 단계에서 두 번 이상 반복됨", "자료·질문·재시도 간격 중 하나 바꾸기"),
    )
    row_html = "".join(
        f"<tr><td>{escape(choice)}</td><td>{escape(location)}의 {escape(focus)} 근거: {escape(reason)}</td><td>{escape(action)}</td></tr>"
        for choice, reason, action in rows
    )
    questions = (
        f"{location}의 {focus} 첫 시도에서 학생이 혼자 사용한 단서는 무엇인가",
        f"{focus} 설명 중 {location} 학생이 처음 도움을 요청한 위치는 어디인가",
        f"하루 이상 뒤에 {location} 학생이 {focus} 활동을 어느 단계까지 복원했는가",
        f"다음 {focus} 과제에서 {location} 학생에게 그대로 유지할 행동은 무엇인가",
    )
    shift = _stable_index(slug, "decision-order") % len(questions)
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(question)}</li>" for question in questions)
    closing_frames = (
        f"{location}의 다음 상담에서는 {focus} 문제 수를 먼저 묻지 않습니다. 유지·축소·변경 중 어떤 결정을 했고 그 근거가 답안과 시간 기록에 남아 있는지 확인합니다.",
        f"이 결정표는 {location} 학생의 점수 상승을 예측하는 도구가 아닙니다. {focus} 학습에서 혼자 할 수 있는 범위와 필요한 도움을 더 정확히 구분해 과도한 반복을 줄이는 기준입니다.",
        f"{focus} 정답이 맞았지만 시간이 크게 늘었다면 {location} 기록에서는 정확도는 유지하고 시간 판단만 별도 과제로 둡니다. 이미 안정된 이해를 처음부터 다시 반복하지 않습니다.",
    )
    return (
        f'<section class="high-english-block high-english-decision" data-decision-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'decision-heading'))}</h2>"
        f"<p>{escape(location)}의 {escape(focus)} 기록은 학생을 평가하기 위한 표가 아니라 다음 과제의 크기와 도움 방식을 정하는 자료입니다. {escape(pack['check'])}</p>"
        f"<table><thead><tr><th>결정</th><th>관찰 근거</th><th>다음 행동</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>학생과 보호자가 함께 확인할 {escape(focus)} 질문</h3><ul>{items}</ul>"
        f"<p>{escape(_pick(closing_frames, slug, 'decision-closing'))}</p></section>"
    )


def _focus_language_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    terms = [term for term in re.split(r"[·\s]+", focus) if term]
    first_term = terms[0] if terms else focus
    last_term = terms[-1] if terms else focus
    heading_frames = (
        f"{focus} 표현을 실제 영어 판단 질문으로 바꾸는 {location} 방법",
        f"{location} 학생이 {focus}의 핵심어를 설명하는 순서",
        f"{focus}의 단서·관계·답을 분리하는 {location} 기록",
        f"영어 자료에서 {focus} 판단 단서를 찾는 {location} 기준",
    )
    lead_frames = (
        f"{location} 학생이 {focus} 풀이 방법을 기억해도 실제 지문과 문장에서 단서를 찾지 못하면 첫 판단이 흔들릴 수 있습니다. ‘{first_term}’와 ‘{last_term}’가 자료에서 무엇을 가리키는지 표시하고 두 표현 사이의 관계를 말한 뒤 답을 고릅니다.",
        f"‘{focus}’라는 이름만 외우지 않습니다. {location}의 기록에 ‘{first_term}에서 먼저 볼 단서는 무엇인가’, ‘{last_term} 판단에서 버릴 정보는 무엇인가’를 따로 적습니다. {pack['action']}",
        f"영어 자료를 읽거나 듣고 바로 답을 고르기 전에 {location} 학생은 {focus}의 핵심 표현인 ‘{first_term}’와 ‘{last_term}’를 찾습니다. 각 표현 옆에 근거 위치, 판단, 확인 행동을 한 칸씩 둡니다.",
    )
    questions = (
        f"{location}의 {focus} 자료에서 ‘{first_term}’는 어떤 단서나 구조를 가리키는가",
        f"‘{last_term}’를 판단하려면 {focus}의 어떤 문장 또는 소리가 필요한가",
        f"{focus} 조건 하나를 바꾸면 {location} 학생의 첫 해석·선택·문장 중 무엇이 달라지는가",
        f"최종 답이 {focus}의 처음 질문과 {location} 자료의 요구 조건에 맞는가",
    )
    shift = _stable_index(slug, "language-order") % len(questions)
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(question)}</li>" for question in questions)
    closing_frames = (
        f"네 질문의 답은 길 필요가 없습니다. {location} 학생이 {focus}의 ‘{first_term}’와 ‘{last_term}’를 실제 근거에 연결하고 ‘{pack['check']}’라는 확인 행동까지 이어 가면 질문 수를 줄여 혼자 시작하는 범위를 넓힙니다.",
        f"{focus} 방법을 설명했지만 적용하지 못하면 {location} 학생에게 완성 답을 다시 보여 주지 않습니다. ‘{first_term}’ 단서와 ‘{last_term}’ 판단 사이에 빈 한 줄을 두고 필요한 관계만 스스로 채우게 합니다.",
        f"{location} 기록에는 {focus} 정답과 함께 학생이 만든 질문 하나를 남깁니다. 다음 날 ‘{first_term}’와 ‘{last_term}’ 표현이 달라진 자료에서 같은 질문을 다시 만들 수 있는지 확인합니다.",
    )
    return (
        f'<section class="high-english-block high-english-focus-language" data-focus-language="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'language-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'language-lead'))}</p>"
        f"<h3>{escape(focus)} 핵심어를 학습 행동으로 바꾸는 네 질문</h3><ul>{items}</ul>"
        f"<p>{escape(_pick(closing_frames, slug, 'language-closing'))}</p></section>"
    )


def _deep_dive_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus} 학습을 기본·변형·실전 자료로 확장하는 {location} 방법",
        f"{location}의 {focus} 판단을 근거·전환·검증으로 깊게 보는 과정",
        f"{focus} 유형에서 같은 오류를 줄이기 위한 {location} 기록 설계",
        f"학교 원문에서 새로운 지문까지 이어 가는 {location} {focus} 연습",
    )
    intro_frames = (
        f"{location} 학생이 {focus} 활동의 한 문제를 해결했더라도 표현과 소재가 달라지면 같은 전략을 쓰지 못할 수 있습니다. 먼저 학교 자료의 기본형에서 단서를 설명하고, 조건을 하나 바꾼 변형형과 시간을 제한한 실전형으로 옮기며 어느 단계에서 근거가 사라지는지 확인합니다.",
        f"{focus} 학습은 쉬운 문제와 어려운 문제를 단순히 나누는 방식으로 깊어지지 않습니다. {location}에서는 학생이 근거를 보존한 채 자료의 길이, 표현, 제한 시간 가운데 한 조건씩 바꾸고 첫 판단과 수정 이유를 비교합니다.",
        f"{location}의 {focus} 기록을 세 단계로 확장하면 설명을 들은 직후의 익숙함과 실제 전이를 구분할 수 있습니다. 같은 날에는 기본형을 확인하고, 다음 날에는 표현을 바꾼 자료, 주말에는 시간 조건이 있는 자료에서 판단을 다시 만듭니다.",
        f"새 지문을 많이 추가하기 전에 {location} 학생이 {focus} 활동에서 무엇을 보고 시작했는지 고정합니다. 시작 단서가 분명해야 자료가 달라졌을 때 전략을 유지한 부분과 우연히 맞힌 부분을 나누어 볼 수 있습니다.",
    )
    rows = (
        ("기본형", "학교 원문과 최근 답안", pack["action"], "첫 단서와 선택 이유"),
        ("변형형", "표현·소재·조건 중 하나가 달라진 자료", pack["transfer"], "달라진 정보와 유지한 전략"),
        ("실전형", "시간 제한과 선택지가 있는 새 자료", pack["check"], "완료 시간과 마지막 검증"),
    )
    row_html = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(location)}의 {escape(focus)} 자료: {escape(material)}</td>"
        f"<td>{escape(action)}</td><td>{escape(record)}</td></tr>"
        for stage, material, action, record in rows
    )
    checks = (
        f"{location}의 {focus} 기본형에서 학생이 먼저 표시한 단서와 그 이유를 보존합니다.",
        f"{focus} 변형형에서는 달라진 조건을 찾은 뒤 전략을 유지할지 바꿀지 말로 결정합니다.",
        f"{location} 실전형에서는 오래 걸린 정답도 남기고 어느 판단에서 시간이 늘었는지 표시합니다.",
        f"{focus} 검토가 끝나면 해설 없이 다시 볼 날짜와 처음 시작할 자료를 한 줄로 적습니다.",
    )
    shift = _stable_index(slug, "deep-check-order") % len(checks)
    checks = checks[shift:] + checks[:shift]
    items = "".join(f"<li>{escape(item)}</li>" for item in checks)
    closing_frames = (
        f"세 단계의 정답률이 같아도 {location} 학생이 {focus} 근거를 말하는 데 필요한 질문과 시간이 줄었다면 학습 과정은 달라진 것입니다. 반대로 기본형만 가능하다면 새 자료를 더하지 않고 변형 조건을 한 가지로 줄여 다시 연결합니다.",
        f"{focus} 실전형에서 결과가 흔들리면 {location} 학생에게 기본 설명 전체를 반복하지 않습니다. 처음 사라진 단서가 어휘인지 구조인지 판단인지 찾고 해당 단계의 변형형 한 개만 복원한 뒤 다시 시간을 확인합니다.",
        f"{location}의 {focus} 심화 기록은 어려운 문제를 푼 횟수가 아니라 전략을 옮긴 증거를 남깁니다. 기본형·변형형·실전형에서 같은 질문을 사용해야 자료 차이와 학생 행동의 변화를 구분할 수 있습니다.",
    )
    return (
        f'<section class="high-english-block high-english-deep-dive" data-deep-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'deep-heading'))}</h2>"
        f"<p>{escape(_pick(intro_frames, slug, 'deep-intro'))}</p>"
        f"<table><thead><tr><th>자료 단계</th><th>사용 자료</th><th>{escape(focus)} 실행</th><th>남길 증거</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(location)}의 {escape(focus)} 전이를 확인하는 네 항목</h3><ul>{items}</ul>"
        f"<p>{escape(_pick(closing_frames, slug, 'deep-closing'))}</p></section>"
    )


def _error_map_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading_frames = (
        f"{focus} 오답을 원인과 다음 행동으로 연결하는 {location} 분류표",
        f"{location}의 {focus} 오류를 어휘·구조·판단·표현·시간으로 나누기",
        f"오답노트를 다시 풀 수 있는 과제로 바꾸는 {location} {focus} 기준",
        f"{focus} 결과보다 수정 이유를 남기는 {location} 복습 기록",
    )
    lead_frames = (
        f"{location} 학생의 {focus} 오답을 문제 번호와 정답만으로 모으면 다음 복습 행동이 분명하지 않을 수 있습니다. 처음 오류가 발생한 위치를 어휘, 구조, 판단, 표현, 시간 중 하나로 정하고 그 원인에 맞는 짧은 재시도를 연결합니다.",
        f"{focus} 오답이 모두 같은 이유에서 생기지는 않습니다. {location} 기록에서는 모르는 단어, 잘못 나눈 문장, 근거 없는 선택, 조건을 놓친 답안, 늦은 시간 판단을 서로 다른 표식으로 남겨 복습 순서를 정합니다.",
        f"오답노트의 목적은 틀린 문제를 오래 보관하는 일이 아닙니다. {location} 학생이 {focus} 오류를 다시 만났을 때 먼저 할 행동을 즉시 고를 수 있도록 원인과 자료, 재시도 날짜를 한 줄로 연결하는 것입니다.",
        f"{location}의 {focus} 학습에서 맞힌 문항도 시간이 길거나 근거가 불분명하면 시간 또는 판단 기록에 넣습니다. 정답과 안정성을 구분해야 이미 아는 내용을 반복하지 않고 실전에서 흔들린 단계만 다시 볼 수 있습니다.",
    )
    error_rows = (
        ("어휘", "뜻·품사·문맥 적용이 끊김", "원문 주변 단서로 뜻을 예상하고 새 문장에서 확인"),
        ("구조", "주절·수식 범위·문장 관계를 잘못 묶음", "핵심절을 복원하고 수식 대상을 화살표로 연결"),
        ("판단", "지문 근거와 선택지의 차이를 설명하지 못함", "근거 문장과 틀린 선택지의 왜곡을 한 쌍으로 기록"),
        ("표현", "서술형·쓰기·말하기 조건을 빠뜨림", "조건표를 먼저 만들고 초안의 수정 이유를 설명"),
        ("시간", "정답이어도 특정 단계에서 시간이 크게 늘어남", "문제를 더 풀기 전에 지연된 판단 한 단계만 제한 시간으로 재시도"),
    )
    shift = _stable_index(slug, "error-order") % len(error_rows)
    error_rows = error_rows[shift:] + error_rows[:shift]
    row_html = "".join(
        f"<tr><td>{escape(kind)}</td><td>{escape(location)}의 {escape(focus)} 관찰: {escape(signal)}</td><td>{escape(action)}</td></tr>"
        for kind, signal, action in error_rows
    )
    review_frames = (
        f"{location} 학생이 {focus} 오류를 분류한 뒤에는 가장 많이 나온 항목보다 다음 시험 범위와 직접 연결된 항목을 먼저 봅니다. 같은 오류가 두 번 반복되면 문제 수를 늘리지 않고 {pack['diagnosis']}",
        f"분류 이름이 달라져도 다음 행동이 같다면 하나로 묶을 수 있습니다. {location}의 {focus} 기록에서 학생이 실제로 실행할 수 있는 복습 행동과 날짜가 적혔는지 확인하고 비어 있는 항목부터 정리합니다.",
        f"{focus} 오답을 다시 맞혔다면 {location} 학생이 답을 기억한 것인지 판단을 복원한 것인지 확인합니다. {pack['transfer']} 이 과정까지 이어졌을 때 해당 오류를 완료 목록으로 옮깁니다.",
        f"시험 직전에는 {location}의 {focus} 오류를 모두 다시 풀지 않습니다. 자주 틀린 유형, 오래 걸린 정답, 서술형 조건 누락 가운데 현재 범위와 겹치는 한 항목씩만 자료를 가리고 재현합니다.",
    )
    return (
        f'<section class="high-english-block high-english-error-map" data-error-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'error-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'error-lead'))}</p>"
        f"<table><thead><tr><th>오류 범주</th><th>관찰 장면</th><th>{escape(focus)} 다음 행동</th></tr></thead><tbody>{row_html}</tbody></table>"
        f"<h3>{escape(focus)} 오답 분류 뒤 복습 순서 정하기</h3>"
        f"<p>{escape(_pick(review_frames, slug, 'error-review'))}</p></section>"
    )


def _focus_protocol_section(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    terms = [term for term in re.split(r"[·\s]+", focus) if term]
    first_term = terms[0] if terms else focus
    last_term = terms[-1] if terms else focus
    evidence_words = (
        ("첫 표시", "근거 위치", "수정 문장", "재시도 날짜"),
        ("예상 답", "멈춘 단서", "도움 내용", "새 자료 결과"),
        ("시작 시각", "판단 이유", "바꾼 조건", "완료 기준"),
        ("원본 표현", "학생 질문", "교정 이유", "간격 뒤 복원"),
    )[_stable_index(slug, "protocol-evidence") % 4]
    heading_frames = (
        f"{location}의 {focus} 전용 기록지 구성",
        f"{focus} 핵심어로 만드는 {location} 한 페이지 학습 기록",
        f"{location} 학생이 {focus} 판단을 다시 꺼내는 네 칸 기록",
        f"{focus} 첫 시도부터 재시도까지 잇는 {location} 기록 양식",
    )
    lead_frames = (
        f"{location}의 {focus} 기록지는 다른 영어 유형의 오답과 섞지 않습니다. 첫 칸에는 ‘{first_term}’ 단서를 본 위치를, 둘째 칸에는 ‘{last_term}’ 판단을 선택한 이유를 적습니다. 셋째 칸에는 {focus} 수정 전후를 나란히 두고 마지막 칸에는 {location} 일정에 맞춘 재시도 날짜를 남깁니다.",
        f"{focus} 활동을 한 페이지 기록으로 줄이면 {location} 학생이 다음에 무엇을 다시 해야 하는지 확인하기 쉽습니다. ‘{first_term}’에서 시작한 질문, ‘{last_term}’에서 멈춘 이유, 도움 뒤 달라진 {focus} 행동, 자료를 가린 뒤의 결과를 순서대로 적습니다.",
        f"{location} 학생의 {focus} 기록은 긴 해설을 옮기는 노트가 아닙니다. ‘{first_term}’ 관련 첫 단서와 ‘{last_term}’ 관련 최종 판단 사이에서 실제로 바뀐 한 행동을 남겨 같은 오류가 반복될 때 비교할 수 있게 합니다.",
        f"{focus} 학습을 다시 시작하려면 {location} 기록만 보고도 사용할 자료와 첫 질문을 알 수 있어야 합니다. ‘{first_term}’의 근거, ‘{last_term}’의 선택 이유, {focus} 확인 행동, 다음 날짜를 각각 한 줄로 제한해 비어 있는 칸을 찾습니다.",
    )
    cells = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(location)}의 {escape(focus)} 활동에서 ‘{escape(first_term)}’와 ‘{escape(last_term)}’ 가운데 관련 단서를 한 줄로 남깁니다.</li>"
        for label in evidence_words
    )
    closing_frames = (
        f"네 칸 가운데 같은 칸이 계속 비면 {location}의 {focus} 과제를 늘리지 않습니다. {pack['action']} 다음 {focus} 기록에서는 비어 있던 칸만 먼저 확인하고 나머지 조건은 유지합니다.",
        f"{location} 학생이 {focus} 기록을 혼자 완성하면 질문 수를 줄입니다. {pack['transfer']} 그 결과를 처음 네 칸과 비교해 ‘{first_term}’ 단서와 ‘{last_term}’ 판단이 새 자료에서도 이어졌는지 봅니다.",
        f"{focus} 기록지는 시험이 끝난 뒤 버리지 않습니다. {location} 학생이 다음 범위를 시작할 때 ‘{first_term}’와 ‘{last_term}’ 관련 오류가 다시 나타나는지 확인하고 겹치는 한 칸만 복습 목록으로 옮깁니다.",
        f"보호자는 {location}의 {focus} 네 칸을 대신 채우지 않습니다. 학생이 남긴 ‘{first_term}’ 근거와 ‘{last_term}’ 질문을 주 1회 확인하고, 설명이 비어 있으면 정답보다 사용한 자료와 다음 재시도부터 묻습니다.",
    )
    return (
        f'<section class="high-english-block high-english-focus-protocol" data-protocol-focus="{escape(focus)}">'
        f"<h2>{escape(_pick(heading_frames, slug, 'protocol-heading'))}</h2>"
        f"<p>{escape(_pick(lead_frames, slug, 'protocol-lead'))}</p>"
        f"<h3>{escape(location)}의 {escape(focus)} 기록지 네 칸</h3><ul>{cells}</ul>"
        f"<p>{escape(_pick(closing_frames, slug, 'protocol-closing'))}</p></section>"
    )


def _context_links(slug: str, location: str, focus: str) -> str:
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    broader_slug = f"{city}고등영어과외"
    local_english_slug = f"{location}영어과외"
    broader_labels = (f"{city} 고등영어 학습 범위", f"{city} 고등영어과외 안내", f"{city} 지역의 고등영어 기준")
    local_labels = (f"{location} 영어과외 전체 안내", f"{location} 영어 학습 페이지", f"{location} 영어과외 기준")
    broader = f'<a href="/{broader_slug}/" data-link-role="broader-high-english">{escape(_pick(broader_labels, slug, "broader-label"))}</a>'
    local = f'<a href="/{local_english_slug}/" data-link-role="local-all-english">{escape(_pick(local_labels, slug, "local-label"))}</a>'
    frames = (
        f"{focus}의 학년 전체 연결을 비교할 때에는 {broader}에서 도시 단위 기준을 확인할 수 있습니다. 초·중·고 영어의 큰 흐름이 필요할 때만 {local}를 보고 현재 시험 범위와 관계없는 페이지까지 확장하지 않습니다.",
        f"이 페이지의 {focus} 기록만으로 다른 영어 영역까지 일반화하지 않습니다. 상위 지역의 고등영어 흐름은 {broader}, 학년을 넓힌 영어 안내는 {local}에서 목적에 맞게 한 번씩 확인합니다.",
        f"{location} 학생의 {focus} 계획이 한 유형의 문제인지 영어 전체의 공백인지 구분하려면 {broader}와 대조합니다. 학년 밖의 연결이 필요한 경우에만 {local}를 참고하고 실제 학교 자료를 우선합니다.",
        f"{focus} 복습을 마친 뒤 다음 영역으로 옮길 기준은 {broader}에서 비교할 수 있습니다. 더 넓은 영어 계획이 필요할 때에는 {local}를 사용하고 같은 키워드 링크를 문장마다 반복하지 않습니다.",
    )
    return (
        f'<aside class="{CONTEXT_LINKS_MARKER}" data-link-count="2" aria-label="{escape(location)} 고등영어 관련 페이지">'
        f"<p>{_pick(frames, slug, 'context-frame')}</p></aside>"
    )


def _faq(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    grade = ("고1", "고2", "고3")[_stable_index(slug, "faq-grade") % 3]
    object_focus = _with_particle(focus, "을", "를")
    questions = (
        f"{location}고등영어과외에서는 {object_focus} 무엇부터 점검하나요?",
        f"{location} {grade} 학생의 {focus} 학습량은 어떻게 정하나요?",
        f"{location} 내신과 모의고사에서 {object_focus} 어떻게 다르게 준비하나요?",
        f"{location} 학생이 {object_focus} 이해했다고 말할 때 무엇으로 확인하나요?",
        f"{location}에서 {focus} 다음 유형으로 넘어가는 기준은 무엇인가요?",
    )
    answers = (
        f"{_with_particle(pack['material'], '을', '를')} 나란히 놓고 {pack['signal']}를 먼저 확인합니다. {location} 학생의 {focus} 첫 시도를 지우지 않은 채 {pack['action']} 하루 이상 뒤에는 해설 없이 같은 판단을 다시 시작하고 필요한 도움의 양을 비교합니다.",
        f"{grade}이라고 정해진 문제 수를 일괄 적용하지 않습니다. {location}의 {focus} 기록에서 혼자 가능한 단계, 짧은 질문 뒤 가능한 단계, 자료를 다시 확인해야 하는 단계를 나누고 시험일까지 남은 날짜에 맞춰 한 번에 바꿀 행동을 하나만 정합니다.",
        f"내신은 실제 교과서와 학교 범위, 서술형 조건을 먼저 보고 모의고사는 틀린 문항뿐 아니라 오래 걸린 정답도 확인합니다. {location}의 {focus} 기록에서는 두 평가의 오류를 어휘·구문·논리·표현·시간으로 같은 방식으로 분류하되 자료의 목적은 섞지 않습니다.",
        f"이해했다는 말은 출발점으로만 봅니다. {location} 학생에게 {pack['transfer']} 이어 {pack['check']} {focus} 정답이 같더라도 필요한 힌트가 줄었는지와 판단 근거를 혼자 설명했는지를 각각 기록합니다.",
        f"완료 질문은 ‘{pack['finish']}?’입니다. {location} 학생이 한 번 맞힌 것만으로 {focus} 학습을 끝내지 않고 다른 소재·표현·조건에서도 같은 단서와 확인 행동이 남는지 본 뒤 다음 유형으로 이동합니다.",
    )
    pairs = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in zip(questions, answers))
    heading_frames = (
        f"{location}고등영어과외와 {focus}에 관해 자주 묻는 질문",
        f"{location} {grade} 학생의 {focus} 학습 FAQ",
        f"{focus} 진단부터 시험 복습까지 묻는 {location} FAQ",
        f"{location}에서 {focus} 계획을 세울 때 자주 묻는 질문",
    )
    return f'<h2 class="{FAQ_MARKER}" data-faq-focus="{escape(focus)}">{escape(_pick(heading_frames, slug, "faq-heading"))}</h2>{pairs}'


def build_local_high_english_meta(slug: str, body: str) -> tuple[str, str]:
    focus = _focus_from_body(body)
    frames = (
        f"{slug}에서 ‘{focus}’ 학습을 학교 자료와 실제 답안 기록으로 점검합니다. 내신·모의고사·수능의 판단 근거, 학년별 계획, 합성 사례와 재시도 기준을 정리했습니다.",
        f"{slug}의 ‘{focus}’ 학습 순서를 안내합니다. 자료 구분과 영어 판단 근거, 학교 정보 확인, 고1·고2·고3 계획, 간격 복습과 주제별 FAQ를 제공합니다.",
        f"{slug} 페이지는 ‘{focus}’에서 막힌 위치를 찾는 기준을 다룹니다. 시험 목적 구분부터 가상 학생 사례, 답안 수정, 다음 유형 이동 조건까지 확인할 수 있습니다.",
        f"{slug} 고등학생이 ‘{focus}’ 학습에서 남길 기록을 정리했습니다. 실제 학교 범위, 첫 단서, 수정 이유, 시간 판단과 간격 뒤 재시도를 함께 확인하세요.",
    )
    title = f"{slug} | {focus}"
    description = _pick(frames, slug, f"meta-{_kind_for_focus(focus)}")
    return title, description


def _individualize_headings(body: str, location: str, focus: str) -> str:
    def replace(match: re.Match[str]) -> str:
        opening, inner, closing = match.groups()
        text = _plain_text(inner)
        additions: list[str] = []
        if location not in text:
            additions.append(location)
        if focus not in text:
            additions.append(focus)
        if not additions:
            return match.group(0)
        return f"{opening}{inner} — {escape(' · '.join(additions))} 기준{closing}"

    return re.sub(r"(<h[23]\b[^>]*>)(.*?)(</h[23]>)", replace, body, flags=re.I | re.S)


def _individualize_paragraphs(body: str, location: str, focus: str) -> str:
    def replace(match: re.Match[str]) -> str:
        opening, inner, closing = match.groups()
        text = _plain_text(inner)
        if location in text or focus in text:
            return match.group(0)
        addition = f" {escape(location)}의 {escape(focus)} 기록에서는 같은 질문을 첫 시도와 간격 뒤 재시도에 각각 적용합니다."
        return f"{opening}{inner}{addition}{closing}"

    return re.sub(r"(<p\b[^>]*>)(.*?)(</p>)", replace, body, flags=re.I | re.S)


def build_local_high_english_body(slug: str, focus: str) -> str:
    location = slug.removesuffix("고등영어과외")
    focus = focus.strip()
    kind = _kind_for_focus(focus)
    pack = HIGH_ENGLISH_PACKS[kind]
    sections = {
        "diagnosis": _diagnosis_section(slug, location, focus, pack),
        "search": _search_intent_section(slug, location, focus, pack),
        "grade": _grade_section(slug, location, focus, pack),
        "school": _school_context_section(slug, location, focus),
        "practice": _practice_section(slug, location, focus, pack),
        "schedule": _schedule_section(slug, location, focus, pack),
        "case": _student_case_section(slug, location, focus, kind, pack),
        "decision": _decision_section(slug, location, focus, pack),
        "language": _focus_language_section(slug, location, focus, pack),
        "deep": _deep_dive_section(slug, location, focus, pack),
        "errors": _error_map_section(slug, location, focus, pack),
        "protocol": _focus_protocol_section(slug, location, focus, pack),
    }
    orders = (
        ("diagnosis", "search", "grade", "language", "protocol", "deep", "practice", "errors", "school", "case", "decision", "schedule"),
        ("search", "diagnosis", "practice", "deep", "grade", "school", "language", "protocol", "errors", "case", "schedule", "decision"),
        ("grade", "school", "diagnosis", "search", "protocol", "language", "errors", "deep", "practice", "decision", "case", "schedule"),
        ("diagnosis", "case", "search", "practice", "errors", "language", "grade", "protocol", "deep", "school", "schedule", "decision"),
        ("practice", "diagnosis", "grade", "deep", "protocol", "language", "search", "case", "errors", "schedule", "school", "decision"),
        ("school", "search", "diagnosis", "language", "errors", "practice", "deep", "grade", "protocol", "decision", "schedule", "case"),
    )
    order = orders[_stable_index(slug, "section-order") % len(orders)]
    core = "".join(sections[name] for name in order)
    body = (
        f'<section class="{CONTENT_MARKER}" data-content-version="{CONTENT_VERSION}" '
        f'data-high-english-focus="{escape(focus)}" data-english-kind="{escape(kind)}">'
        f"{_opening(slug, location, focus, pack)}{core}{_context_links(slug, location, focus)}"
        f"{_faq(slug, location, focus, pack)}</section>"
    )
    body = _individualize_headings(body, location, focus)
    return _individualize_paragraphs(body, location, focus)


def individualize_local_high_english_body(body: str, slug: str) -> str:
    if not is_local_high_english_slug(slug):
        return body
    if f'data-content-version="{CONTENT_VERSION}"' in body:
        return body
    return build_local_high_english_body(slug, _focus_from_body(body))
