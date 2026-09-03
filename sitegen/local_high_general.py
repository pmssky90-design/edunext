from __future__ import annotations

import re
from html import unescape

from sitegen.local_elementary_math import _obj, _pick, _stable_index, _subject, _topic, _with
from sitegen.local_high_english import SCHOOL_CONTEXT
from sitegen.utils import escape


LOCAL_HIGH_GENERAL_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)고등과외$")
CONTENT_VERSION = "high-general-individual-v2"
CONTENT_MARKER = "local-high-general-content"


def is_local_high_general_slug(slug: str) -> bool:
    return bool(LOCAL_HIGH_GENERAL_PATTERN.fullmatch(slug))


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _parts(slug: str) -> tuple[str, str, str]:
    location = slug.removesuffix("고등과외")
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    return location, city, location.removeprefix(city)


STUDY_PACKS: tuple[dict[str, object], ...] = (
    {
        "focuses": (
            "고등학교 첫 시험 뒤 과목별 복습 전환",
            "교과서 진도와 누적 취약점의 분리",
            "학교 수업 당일의 짧은 복원",
            "선행보다 먼저 확인하는 선수 학습",
            "새 학기 학습량과 생활 리듬 조정",
            "첫 내신 전 영어·수학 시작점 진단",
            "중학교식 공부에서 고등 학습으로 전환",
            "과목별 공백을 현재 진도에 연결하기",
        ),
        "signal": "설명을 본 직후의 정답이 아니라 다음 날 학교 자료를 가리고 첫 개념과 문장을 다시 시작하는지",
        "english": "영어는 교과서 본문과 유인물에서 핵심 문장·어휘·구문을 복원하고 새 지문에서 같은 근거를 찾습니다.",
        "math": "수학은 정의와 예제를 가린 뒤 조건·식·그래프의 관계를 설명하고 숫자가 바뀐 문제에서 첫 전략을 다시 고릅니다.",
        "task": "최근 학교 영어 자료 한 단락과 수학 예제 한 문제를 가리고 각각 첫 단서와 막힌 위치를 표시합니다.",
        "transfer": "도움을 받은 자료가 아닌 같은 단원의 새 문장과 새 문제에서 시작 행동을 재현합니다.",
        "grade1": "고1은 과목 수와 학습량이 늘어나는 시기이므로 학교 수업 당일의 짧은 복원과 일주일 누적 기록부터 만듭니다.",
        "grade2": "고2는 선택과목과 난도가 달라지는 만큼 과목별 공백을 현재 시험 범위에 연결하고 무관한 전 범위 반복을 줄입니다.",
        "grade3": "고3은 수능형 실전 학습을 유지하면서 내신 자료와 취약 단원의 역할이 서로 밀어내지 않도록 우선순위를 정합니다.",
        "parent": "공부시간보다 학교 수업 뒤 무엇을 가리고 복원했는지와 다음 날 혼자 시작한 자료를 묻습니다.",
    },
    {
        "focuses": (
            "내신 원문과 모의고사 새 자료의 구분",
            "시험 범위와 실전 대비의 주간 배치",
            "서술형 근거와 객관식 시간 관리",
            "내신 직후 오답을 누적 학습으로 전환",
            "모의고사 등급보다 영역별 판단 기록",
            "중간·기말고사 사이 취약 영역 복구",
            "학교 평가와 전국 단위 평가의 역할 분리",
            "시험 일정에 맞춘 과목 우선순위",
        ),
        "signal": "내신과 모의고사 자료를 섞지 않고 각각의 범위·시간·근거 오류를 다른 기록으로 설명하는지",
        "english": "영어 내신은 학교 원문과 서술형 조건을 우선하고 모의고사는 낯선 지문의 논리와 시간 판단을 별도로 기록합니다.",
        "math": "수학 내신은 학교 범위의 정의·유형·서술 과정을 보고 모의고사는 여러 단원을 오가는 첫 판단과 검산 시간을 확인합니다.",
        "task": "최근 내신과 모의고사에서 틀린 문항뿐 아니라 오래 걸린 정답을 골라 자료 목적과 오류 원인을 나눕니다.",
        "transfer": "같은 오류가 학교 범위의 변형 문제와 낯선 실전 자료에서도 반복되는지 비교합니다.",
        "grade1": "고1은 첫 내신과 첫 전국연합 평가를 같은 점수표로 보지 않고 범위 학습과 실전 판단의 차이를 익힙니다.",
        "grade2": "고2는 선택과목과 학교 일정에 맞춰 내신 원본·누적 취약점·모의고사 시간 연습을 주간표에서 구분합니다.",
        "grade3": "고3은 수능 실전 루틴을 고정하되 학교 평가 기간에는 원문과 서술형을 짧고 명확한 단위로 배치합니다.",
        "parent": "점수의 높고 낮음보다 내신과 모의고사에서 각각 무엇을 근거로 바꾸었는지 질문합니다.",
    },
    {
        "focuses": (
            "영어 독해와 수학 풀이의 병행",
            "영어 어휘와 수학 개념의 간격 복습",
            "국영수 과목별 시작 시간의 현실화",
            "영어 서술형과 수학 서술 과정의 기록",
            "취약 과목 집중과 강점 과목 유지의 균형",
            "과목 전환 때 집중이 끊기는 원인 점검",
            "여러 과목 숙제를 완료 기준으로 나누기",
            "과목별 질문을 다음 수업에 연결하기",
        ),
        "signal": "한 과목의 긴 공부시간이 아니라 영어와 수학에서 각각 남긴 근거·풀이·재시도 기록이 이어지는지",
        "english": "영어는 어휘 뜻만 외우지 않고 문장 근거, 글의 흐름, 직접 만든 한 문장으로 이해와 출력을 연결합니다.",
        "math": "수학은 문제 수보다 조건 표시, 선택한 개념, 중간 식, 검산을 남겨 다른 문제에 옮길 전략을 확인합니다.",
        "task": "영어 20분과 수학 20분의 첫 시도를 보존하고 시작까지 걸린 시간·중단 이유·완료 행동을 비교합니다.",
        "transfer": "과목 순서를 바꾸어도 각 과목의 첫 학습 행동과 종료 기준을 스스로 선택합니다.",
        "grade1": "고1은 영어와 수학의 학습량을 중학교 때와 비교하기보다 학교 진도와 실제 시작 가능 시간으로 다시 계산합니다.",
        "grade2": "고2는 선택과목까지 포함해 취약 과목에 긴 시간을 주되 강점 과목의 간격 복습이 사라지지 않게 합니다.",
        "grade3": "고3은 실전 세트와 취약 영역 복습을 분리하고 하루 안에서 과목 전환에 쓰이는 시간을 계획에 포함합니다.",
        "parent": "총 공부시간보다 영어와 수학에서 각각 끝낸 행동과 다음에 다시 시작할 위치를 확인합니다.",
    },
    {
        "focuses": (
            "늦은 귀가 뒤 최소 학습 행동",
            "주중 피로와 주말 보충의 균형",
            "수행평가가 겹친 주간 계획 복구",
            "학원·과외·자기학습 자료의 역할 분리",
            "계획이 밀린 날의 과목별 재시작",
            "집중 시간이 짧은 날의 완료 기준",
            "시험 기간 수면과 복습 간격 관리",
            "방학 계획을 개학 뒤 루틴으로 연결",
        ),
        "signal": "계획한 시간보다 실제 귀가 시각과 피로도에 맞춰 최소 과제를 끝내고 다음 시작점을 남기는지",
        "english": "영어는 피로한 날에는 어휘·핵심 문장 복원, 여유 있는 날에는 독해와 서술형 출력으로 역할을 나눕니다.",
        "math": "수학은 짧은 날에는 정의·오류 한 줄·대표 예제를 복원하고 긴 날에는 변형 문제와 검산까지 이어 갑니다.",
        "task": "일주일의 실제 귀가 시각과 학습 시작 시각을 적고 계획이 끊긴 날의 첫 원인을 자료·시간·난도로 구분합니다.",
        "transfer": "예상보다 늦은 날에도 미리 정한 최소 행동을 끝내고 다음 날 밀린 전체 분량을 그대로 더하지 않습니다.",
        "grade1": "고1은 갑자기 늘어난 학교 과제와 이동시간을 먼저 기록해 지속할 수 있는 평일 최소 루틴을 만듭니다.",
        "grade2": "고2는 수행평가와 선택과목 일정이 겹칠 때 마감·시험 범위·누적 공백을 서로 다른 우선순위로 둡니다.",
        "grade3": "고3은 실전 학습 시간을 유지하되 수면을 줄여 밀린 과제를 채우는 계획을 반복하지 않습니다.",
        "parent": "계획을 지키지 못한 태도를 평가하기보다 실제로 시작을 막은 시간·자료·난도 조건 하나를 묻습니다.",
    },
    {
        "focuses": (
            "오답 원인을 개념·해석·시간으로 분류",
            "맞았지만 오래 걸린 문제의 재검토",
            "첫 풀이와 첫 해석을 지우지 않는 기록",
            "해설 이해와 독립 재현의 구분",
            "질문 뒤 바뀐 판단을 다음 문제에 적용",
            "실수와 개념 공백을 다른 과제로 연결",
            "오답노트 분량보다 재시도 날짜 관리",
            "근거 없는 정답을 설명 가능한 답으로 전환",
        ),
        "signal": "오답을 베끼지 않고 처음 판단·멈춘 위치·수정 이유·며칠 뒤 독립 재현을 나눠 남기는지",
        "english": "영어 오답은 어휘·구문·논리·표현·시간 가운데 근거가 사라진 위치를 표시하고 새 지문에서 다시 확인합니다.",
        "math": "수학 오답은 개념·조건·전략·계산·검산 가운데 첫 오류를 찾아 같은 원인의 변형 문제로 재시도합니다.",
        "task": "최근 영어와 수학 오답 한 개씩에서 첫 답을 지우지 않고 오류가 시작된 줄과 수정 근거를 말합니다.",
        "transfer": "해설을 가린 뒤 이틀 이상 지나 같은 원인의 다른 자료에서 첫 판단부터 다시 수행합니다.",
        "grade1": "고1은 오답노트 형식보다 첫 판단과 수정 이유를 남기는 습관을 만들어 과목별 오류 언어를 익힙니다.",
        "grade2": "고2는 누적된 오답을 전부 다시 풀지 않고 현재 선택과목과 직접 연결되는 원인부터 재시도합니다.",
        "grade3": "고3은 실전 세트의 오답과 오래 걸린 정답을 함께 분류해 점수 변동보다 다음 판단 시간을 줄입니다.",
        "parent": "틀린 문제 수보다 처음 어디서 판단이 달라졌고 며칠 뒤 무엇을 혼자 재현했는지 묻습니다.",
    },
    {
        "focuses": (
            "질문을 만드는 자기주도 복습",
            "도움을 줄여 가는 독립 학습 기록",
            "교재 수보다 자료별 역할을 정하는 방법",
            "완료한 공부와 설명 가능한 공부의 구분",
            "성적표보다 다음 행동을 정하는 상담 준비",
            "학생이 직접 고르는 재시도 기준",
            "학부모 확인 질문과 학생 설명의 균형",
            "수업 전 질문과 수업 후 복원의 연결",
        ),
        "signal": "교사의 다음 지시를 기다리지 않고 사용할 자료·완료 행동·질문·재시도 날짜를 스스로 말하는지",
        "english": "영어는 답을 확인하기 전에 근거 문장과 모르는 표현을 질문으로 만들고 수업 뒤 같은 문장을 가려 복원합니다.",
        "math": "수학은 막힌 줄과 시도한 전략을 질문으로 만들고 설명 뒤에는 같은 조건을 혼자 다시 식으로 나타냅니다.",
        "task": "다음 수업 전에 영어 질문 하나와 수학 질문 하나를 자료의 정확한 위치와 함께 적고 예상 답을 먼저 남깁니다.",
        "transfer": "교재와 교사가 달라져도 질문 형식과 재시도 순서를 유지하며 필요한 도움의 양을 줄입니다.",
        "grade1": "고1은 질문을 ‘모르겠어요’로 끝내지 않고 자료 위치·첫 판단·막힌 이유의 세 항목으로 말합니다.",
        "grade2": "고2는 선택과목마다 질문과 복습의 종료 기준을 달리 정하고 도움 뒤 독립 재현을 확인합니다.",
        "grade3": "고3은 실전 중에는 표시만 남기고 검토 시간에 질문을 원인별로 묶어 취약 영역 복습으로 연결합니다.",
        "parent": "정답을 대신 설명하기보다 학생이 어떤 자료와 근거로 질문을 만들었는지 먼저 듣습니다.",
    },
)


def _pack_and_focus(slug: str) -> tuple[dict[str, object], str]:
    pack = STUDY_PACKS[_stable_index(slug, "general-pack") % len(STUDY_PACKS)]
    focuses = pack["focuses"]
    assert isinstance(focuses, tuple)
    base = str(_pick(focuses, slug, "general-focus"))
    qualifiers = (
        "답안 비교", "주간 점검", "자료 선택", "간격 재시도", "시간 조정", "질문 기록",
        "과목 전이", "오류 추적", "학교 일정", "독립 복원", "완료 기준", "실전 연결",
    )
    qualifier = _pick(qualifiers, slug, "general-focus-qualifier")
    lenses = (
        "첫 시도", "수정 이유", "다음 행동", "혼자 복원", "학교 원본", "과목 전환",
        "학년 단계", "시험 목적", "부모 질문", "생활 리듬", "근거 설명", "이틀 뒤 확인",
    )
    lens = _pick(lenses, slug, "general-focus-lens")
    return pack, f"{base}·{qualifier}·{lens}"


def _focus_from_body(body: str, slug: str) -> str:
    marker = re.search(r'data-high-general-focus="([^"]+)"', body, flags=re.I)
    if marker:
        return unescape(marker.group(1)).strip()
    return _pack_and_focus(slug)[1]


def build_local_high_general_meta(slug: str, body: str) -> tuple[str, str]:
    focus = _focus_from_body(body, slug)
    location, _, _ = _parts(slug)
    title = _pick(
        (
            f"{slug} | {focus} 학년별 설계",
            f"{slug} | {focus} 내신·모의고사 기준",
            f"{slug} | 영어·수학 기록으로 보는 {focus}",
            f"{slug} | {focus} 주간 학습 계획",
        ),
        slug,
        "general-meta-title",
    )
    if len(title) > 60:
        title = f"{slug} | {focus}"
    description = _pick(
        (
            f"{slug}에서 {focus} 학습을 실제 학교 자료와 학생 기록으로 점검합니다. 고1·고2·고3 계획, 영어·수학 진단, 내신·모의고사·수능의 우선순위를 안내합니다.",
            f"{location} 고등학생의 {focus} 과정을 정리했습니다. 학교 공식 정보, 과목별 시작점, 주간 복습, 합성 사례와 학부모 확인 질문을 구체적으로 살펴봅니다.",
            f"{slug} 검색 뒤 확인할 {focus} 기준입니다. 학교 일정과 실제 답안, 영어·수학 오류, 간격 재시도와 학년별 다음 행동을 한 페이지에 담았습니다.",
        ),
        slug,
        "general-meta-description",
    )
    return title, description


def _opening(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location}고등과외에서 {_obj(focus)} 먼저 보는 이유",
            f"점수보다 학습 기록을 먼저 보는 {location}의 {focus}",
            f"{location} 고등학생의 {_obj(focus)} 실제 자료로 구분하기",
            f"학교 일정에서 출발하는 {location} {focus} 계획",
        ),
        slug,
        "general-opening-heading",
    )
    paragraph = _pick(
        (
            f"{location}이라는 지역명만으로 학생의 재학 학교, 성적, 시험 범위나 입시 결과를 판단할 수는 없습니다. 이 페이지는 {_obj(focus)} 중심으로 학교에서 실제로 받은 자료, 첫 답안, 도움 뒤 수정, 며칠 뒤 재시도를 비교해 다음 학습 행동을 정하는 교육 정보를 제공합니다.",
            f"같은 학년과 생활권의 학생도 {location}에서 필요한 고등 학습은 다릅니다. {str(pack['signal'])}를 영어·수학 자료에서 확인하고 학교 일정과 귀가 이후 가능한 시간을 함께 기록해야 계획의 크기를 현실적으로 정할 수 있습니다.",
            f"{location}고등과외를 찾을 때 교재 수와 공부시간만 비교하면 학생이 실제로 멈추는 지점이 가려질 수 있습니다. {focus} 기록에서는 처음 사용한 근거, 질문이 필요했던 위치, 수정 이유와 시간차 재현을 구분합니다.",
        ),
        slug,
        "general-opening-paragraph",
    )
    return (
        f'<section class="high-general-block high-general-opening" data-content-marker="{CONTENT_MARKER}" '
        f'data-content-version="{CONTENT_VERSION}" data-high-general-focus="{escape(focus)}">'
        f"<h2>{escape(heading)}</h2><p>{escape(paragraph)}</p></section>"
    )


def _search_intent(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location}고등과외 검색을 실제 {focus} 진단으로 바꾸기",
            f"내신·모의고사·수능에서 달라지는 {location} {focus}의 목적",
            f"{location} 학생에게 필요한 {focus} 자료부터 구분하기",
            f"과목과 시험 목적에 따라 나누는 {location}의 {focus}",
        ),
        slug,
        "general-search-heading",
    )
    intro = _pick(
        (
            f"{location}고등과외를 찾는 목적이 학교 내신인지, 누적 공백 보완인지, 모의고사와 수능 준비인지에 따라 {focus}의 자료와 종료 기준은 달라집니다. 학교명이나 지역명으로 출제 경향을 추측하지 않고 범위표·교과서·시험지와 학생 기록을 우선합니다.",
            f"검색어가 같아도 {location} 학생의 {focus} 계획은 같을 수 없습니다. {str(pack['signal'])}를 첫 기준으로 삼고 평가일까지 남은 날짜, 과목별 자료, 실제 시작 가능 시간을 함께 확인합니다.",
            f"{location}의 {focus}에서 선행 범위를 정하기 전에 학교 학습과 실전 학습의 역할을 나눕니다. 내신은 실제 범위와 서술 조건을, 실전은 낯선 자료의 판단과 시간을 보며 같은 오답도 목적별로 기록합니다.",
        ),
        slug,
        "general-search-intro",
    )
    rows = (
        ("학교 내신", "범위표·교과서·유인물·최근 시험지", "원본의 개념과 문장을 설명하고 서술 조건을 충족하는지"),
        ("누적 공백 보완", "오래 걸린 정답·첫 오답·질문 기록", str(pack["signal"])),
        ("모의고사·수능", "새 지문·복합 문항·실전 시간 기록", str(pack["transfer"])),
    )
    row_html = "".join(
        f"<tr><td>{escape(purpose)}</td><td>{escape(material)}</td><td>{escape(location)} {escape(focus)} 기록: {escape(check)}</td></tr>"
        for purpose, material, check in rows
    )
    steps = (
        "학교 시험 범위와 평가 날짜를 확인하고 사용할 원본 자료를 한곳에 모읍니다.",
        str(pack["task"]),
        "영어와 수학의 오류를 같은 점수로 합치지 않고 과목별 원인과 다음 행동으로 나눕니다.",
        f"{str(pack['transfer'])} 그 결과를 다음 주 {focus} 계획에 반영합니다.",
    )
    shift = _stable_index(slug, "general-search-order") % 4
    steps = steps[shift:] + steps[:shift]
    items = "".join(f"<li>{escape(location)} 기준: {escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"이 순서는 {location} 학생을 평가하는 등급표가 아닙니다. {focus}에 필요한 원본·첫 시도·수정·재시도의 역할을 구분해 다음 과제를 줄이거나 유지하거나 확장하는 근거로 사용합니다.",
            f"{location}의 학교별 시험을 일반화하지 않습니다. {focus}의 실제 범위는 학생이 받은 자료에서 확인하고 공개되지 않은 난도와 출제 경향을 페이지 내용으로 추측하지 않습니다.",
            f"목적이 정해지면 {location}의 {_obj(focus)} 영어·수학·일정·실전 가운데 어느 영역에서 먼저 조정할지도 구체적으로 결정할 수 있습니다.",
        ),
        slug,
        "general-search-closing",
    )
    return (
        f'<section class="high-general-block high-general-search-intent" data-search-intent="local-high-general">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>학습 목적</th><th>먼저 볼 자료</th><th>완료를 판단할 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(location)} 학생의 {escape(focus)} 시작 순서는 다음 네 단계입니다.</p><ol>{items}</ol><p>{escape(closing)}</p></section>"
    )


def _grade_plan(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"고1·고2·고3에서 달라지는 {location} {focus} 계획",
            f"학년 이름보다 역할로 나누는 {location}의 {focus}",
            f"{location} 학생의 {_obj(focus)} 세 학년 단계로 연결하기",
            f"학교 진도와 입시 시기를 잇는 {location} {focus} 학년표",
        ),
        slug,
        "general-grade-heading",
    )
    grade_rows = (
        ("고1", str(pack["grade1"]), "학교 수업 당일 복원과 첫 시험 기록"),
        ("고2", str(pack["grade2"]), "선택과목·누적 공백·평가 일정 조정"),
        ("고3", str(pack["grade3"]), "실전 루틴과 취약 영역 재시도"),
    )
    shift = _stable_index(slug, "general-grade-order") % 3
    grade_rows = grade_rows[shift:] + grade_rows[:shift]
    grade_content: list[str] = []
    for index, (grade, text, role) in enumerate(grade_rows):
        note = _pick(
            (
                f"{location}에서는 정답 수와 별도로 혼자 연 자료, 시작한 단계, 다음 재시도 날짜를 기록합니다.",
                f"{location} 학생은 도움을 받기 전 답안과 도움 뒤 달라진 판단을 나란히 남깁니다.",
                f"{location} 기록에서는 완료한 분량보다 다음 날 스스로 되살린 첫 행동을 확인합니다.",
                f"{location}의 학년 계획은 학교 원본, 질문 위치, 수정 이유가 이어질 때 다음 범위로 넓힙니다.",
                f"{location} 학생에게는 같은 학년 진도보다 현재 자료에서 혼자 설명할 수 있는 단계가 출발점입니다.",
                f"{location}에서는 과목별 공백을 한꺼번에 채우지 않고 학교 범위와 직접 닿는 행동부터 다시 시도합니다.",
            ),
            slug,
            f"general-grade-note-{index}",
        )
        grade_content.append(
            f"<h3>{escape(location)} {grade} {escape(focus)}: {escape(role)}</h3><p>{escape(text)} {escape(note)}</p>"
        )
    content = "".join(grade_content)
    closing = _pick(
        (
            f"학년이 같아도 {location} 학생의 시작점은 다릅니다. {_obj(focus)} 막는 한 과목의 공백만 짧게 복원한 뒤 현재 학교 범위와 실전 자료에서 바로 사용하게 합니다.",
            f"{location}에서 {_obj(focus)} 학년 이름만으로 정하지 않습니다. 혼자 가능한 단계, 질문 뒤 가능한 단계, 다시 배울 단계를 나눠 과목과 과제의 깊이를 조절합니다.",
            f"고1·고2·고3 표는 {location} 학생에게 같은 진도를 강요하는 기준이 아닙니다. {focus} 기록에 따라 과목별 시작점과 완료 행동을 다시 배치합니다.",
        ),
        slug,
        "general-grade-closing",
    )
    return f'<section class="high-general-block high-general-grade" data-grade-bands="high1,high2,high3"><h2>{escape(heading)}</h2>{content}<p>{escape(closing)}</p></section>'


def _subject_plan(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"영어·수학·공통 루틴으로 나누는 {location} {focus}",
            f"{location} 학생의 {_obj(focus)} 과목별 증거로 확인하기",
            f"과목 시간이 아니라 완료 행동을 보는 {location} {focus}",
            f"영어 해석과 수학 풀이를 함께 기록하는 {location} 기준",
        ),
        slug,
        "general-subject-heading",
    )
    parts = (
        ("영어", str(pack["english"]), "근거 문장·표현 수정·새 지문 재현"),
        ("수학", str(pack["math"]), "조건 표시·중간 풀이·다른 문제 검산"),
        ("공통 학습 루틴", str(pack["task"]), "시작 시각·멈춘 이유·다음 자료"),
    )
    shift = _stable_index(slug, "general-subject-order") % 3
    parts = parts[shift:] + parts[:shift]
    subject_content: list[str] = []
    for index, (subject, text, evidence) in enumerate(parts):
        note = _pick(
            (
                f"{location} 기록에는 {_obj(evidence)} 남겨 수업 전후의 차이를 확인합니다.",
                f"{location} 학생은 {_obj(evidence)} 비교해 어느 도움부터 줄일지 정합니다.",
                f"{location}에서는 {_obj(evidence)} 근거로 다음 과제의 길이와 자료를 고릅니다.",
                f"{location} 과목 노트에는 {_obj(evidence)} 따로 표시해 독립 재현과 설명 직후의 성공을 구분합니다.",
                f"{location} 학생이 {_obj(evidence)} 말할 수 있으면 같은 기준을 새 자료에 옮겨 봅니다.",
                f"{location}의 다음 수업은 {_obj(evidence)} 확인한 뒤 가장 약한 연결 하나에서 시작합니다.",
            ),
            slug,
            f"general-subject-note-{index}",
        )
        subject_content.append(
            f"<h3>{escape(location)} {escape(focus)} — {escape(subject)}</h3><p>{escape(text)} {escape(note)}</p>"
        )
    content = "".join(subject_content)
    closing = _pick(
        (
            f"영어와 수학을 매일 같은 시간만큼 공부할 필요는 없습니다. {location}의 {focus}에서 가장 약한 연결에 시간을 더 주되 강점 과목도 며칠 뒤 짧게 복원해 학습 간격이 끊기지 않게 합니다.",
            f"{location} 학생이 한 과목에서 오래 머물면 공부 의지만 평가하지 않습니다. {focus} 기록으로 자료 선택, 시작 지연, 이해 공백, 출력 부담 가운데 실제 병목을 찾아 다음 과제를 바꿉니다.",
            f"과목별 학습량은 {location} 학생의 학교 일정과 현재 자료로 정합니다. {_obj(focus)} 위해 새 교재를 추가하기 전에 기존 자료에서 첫 판단과 완료 행동이 남는지 확인합니다.",
        ),
        slug,
        "general-subject-closing",
    )
    return f'<section class="high-general-block high-general-subjects" data-subjects="english,math,routine"><h2>{escape(heading)}</h2>{content}<p>{escape(closing)}</p></section>'


def _assessment_map(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"내신·모의고사·수능에서 확인할 {location} {focus} 증거",
            f"시험 이름보다 자료 목적을 먼저 보는 {location}의 {focus}",
            f"{location} {_obj(focus)} 세 평가 장면으로 나누기",
            f"학교 원문에서 낯선 실전 자료로 옮기는 {location} 기준",
        ),
        slug,
        "general-assessment-heading",
    )
    parts = (
        ("학교 내신", "범위표와 교과서·유인물의 원문, 서술형 조건을 우선하고 근거를 원본에서 다시 찾습니다."),
        ("모의고사", "틀린 문항뿐 아니라 오래 걸린 정답을 영역·판단·시간으로 분류하고 낯선 자료의 첫 단서를 남깁니다."),
        ("수능 준비", f"누적 취약 영역을 실전 세트와 분리해 복습하고 {str(pack['transfer'])}"),
    )
    assessment_content: list[str] = []
    for index, (name, text) in enumerate(parts):
        note = _pick(
            (
                f"{location} 학생은 첫 기록을 보존하고 수정 이유와 다시 볼 날짜를 덧붙입니다.",
                f"{location}에서는 점수 옆에 처음 고른 근거와 판단이 바뀐 위치를 함께 적습니다.",
                f"{location} 기록은 해설을 읽은 당일과 며칠 뒤 혼자 푼 결과를 분리합니다.",
                f"{location} 학생이 맞힌 문항도 오래 걸렸다면 시간 판단과 검토 순서를 남깁니다.",
                f"{location}의 평가 자료에는 받은 질문과 학생이 스스로 고친 표현을 다른 칸에 씁니다.",
                f"{location}에서는 같은 오류가 새 자료에 이어지는지 확인한 뒤 다음 평가 과제를 정합니다.",
            ),
            slug,
            f"general-assessment-note-{index}",
        )
        assessment_content.append(
            f"<h3>{escape(location)} {escape(focus)} 평가 {index + 1}: {escape(name)}</h3><p>{escape(text)} {escape(note)}</p>"
        )
    content = "".join(assessment_content)
    closing = _pick(
        (
            f"세 평가의 점수를 단순 평균 내어 {location} 학생의 {_obj(focus)} 판단하지 않습니다. 자료 목적마다 요구한 근거와 시간을 따로 본 뒤 반복되는 원인만 다음 주 우선 과제로 옮깁니다.",
            f"{location}의 {focus}에서 학교 시험과 수능형 문제의 역할을 섞으면 원본 암기와 낯선 자료 판단이 모두 흐려질 수 있습니다. 같은 개념도 평가 목적에 맞는 완료 행동으로 구분합니다.",
            f"시험 일정이 가까워져도 {location} 학생의 {focus} 기록을 전부 긴급 과제로 바꾸지 않습니다. 현재 범위와 직접 연결되는 공백, 오래 걸린 정답, 설명이 끊긴 답안 순으로 선택합니다.",
        ),
        slug,
        "general-assessment-closing",
    )
    return f'<section class="high-general-block high-general-assessment" data-assessments="school,mock,csat"><h2>{escape(heading)}</h2>{content}<p>{escape(closing)}</p></section>'


def _weekly_plan(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} 생활시간에 맞춘 {focus} 주간 계획",
            f"학교 수업·가정 복습·실전을 잇는 {location} 일정표",
            f"밀린 분량보다 재시작을 정하는 {location} {focus}",
            f"평일과 주말에 역할을 나누는 {location} 고등 학습",
        ),
        slug,
        "general-weekly-heading",
    )
    intro = _pick(
        (
            f"{location} 안에서도 통학, 방과 후 일정, 귀가 시각과 집중 시간은 학생마다 다릅니다. {_obj(focus)} 매일 같은 분량으로 배치하지 않고 학교 수업 당일, 주중 적용, 주말 실전, 간격 뒤 재시도의 역할로 나눕니다.",
            f"{location} 학생의 {_topic(focus)} 계획표의 공부시간 총합보다 실제 시작과 완료 행동이 중요합니다. 피로한 날에는 가장 짧은 복원을 두고 여유 있는 날에는 {str(pack['transfer'])}",
            f"주간 계획에서 {location}의 {_obj(focus)} 영어·수학·학교 일정·실전으로 나눕니다. 계획을 지키지 못한 날에는 밀린 전체 분량을 다음 날 더하지 않고 시작을 막은 조건 하나만 바꿉니다.",
        ),
        slug,
        "general-weekly-intro",
    )
    rows = (
        ("학교 수업 당일", "짧게 시작", "교과서·공책의 핵심 개념과 문장을 가리고 복원"),
        ("주중 과목 적용", "집중 가능한 범위", str(pack["task"])),
        ("주말 평가 연결", "여유 있게 확인", str(pack["transfer"])),
        ("다음 주 시작점", "마무리 점검", "막힌 원인과 다시 사용할 자료, 완료 행동을 학생이 직접 정합니다."),
    )
    row_html = "".join(
        f"<tr><td>{escape(when)}</td><td>{escape(duration)}</td><td>{escape(location)} {escape(focus)}: {escape(task)}</td></tr>"
        for when, duration, task in rows
    )
    closing = _pick(
        (
            f"시간은 {location} 학생의 학년과 실제 집중 지속 시간에 맞춰 줄이거나 늘립니다. {focus} 기록에는 시작 시각, 도움 횟수, 끝낸 행동, 다시 볼 날짜가 남아야 다음 계획을 조정할 수 있습니다.",
            f"{location}에서 {focus} 계획이 밀렸다면 학생의 태도를 결론 내리지 않습니다. 자료 길이, 과목 순서, 시작 시각 가운데 한 조건만 바꾸고 다음 주 같은 요일의 기록과 비교합니다.",
            f"방학에도 {location} 학생의 {_obj(focus)} 새 교재 진도로만 채우지 않습니다. 학교 자료 복원, 취약 영역, 실전 적용, 휴식일을 구분해 개학 뒤에도 유지할 수 있는 리듬을 만듭니다.",
        ),
        slug,
        "general-weekly-closing",
    )
    return (
        f'<section class="high-general-block high-general-weekly"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>'
        f'<div class="table-wrap"><table><thead><tr><th>시점</th><th>권장 범위</th><th>완료 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(closing)}</p></section>"
    )


def _school_section(slug: str, location: str, city: str, town: str, focus: str) -> str:
    schools = SCHOOL_CONTEXT.get((city, town), [])
    heading = _pick(
        (
            f"주소 기준으로 확인한 {location} 고등학교 공식 정보",
            f"{town} 주소의 고등학교 정보와 {focus} 자료 확인",
            f"{location} 학교 일정을 학습 계획과 구분해서 보는 법",
            f"공식 학교 정보에서 출발하는 {location} {focus}",
        ),
        slug,
        "general-school-heading",
    )
    intro = _pick(
        (
            f"학교명과 주소는 저장된 고등학교 지역 매핑 자료에서 {_subject(town)} 정확히 일치하는 항목만 사용했습니다. 학교 링크는 일정과 공식 공지를 확인하는 경로이며 {location} 학생의 재학·배정·통학시간을 의미하지 않습니다.",
            f"{location}이라는 주소만으로 재학 학교나 시험 범위를 추정하지 않습니다. 공식 홈페이지에서는 학교명과 일정을 확인하고 {focus}의 실제 범위와 과제는 학생이 받은 범위표·교과서·시험지에서 다시 확인합니다.",
            f"지역 정보와 학습 정보의 역할을 나눕니다. {_with(town)} 정확히 연결된 학교명은 공식 안내의 출처를 찾는 데 사용하고 {focus}의 난도와 진도는 학생 개인의 자료로 판단합니다.",
        ),
        slug,
        "general-school-intro",
    )
    if schools:
        items = []
        for school in schools[:4]:
            name = str(school["name"])
            homepage = str(school["homepage"])
            items.append(
                f'<li><strong><a class="source-link" href="{escape(homepage)}" target="_blank" rel="noopener noreferrer external">{escape(name)} 공식 홈페이지</a></strong>'
                f" — {escape(town)} 주소와 연결된 학교입니다. 일정은 공식 공지에서, {escape(focus)}의 실제 자료는 학생이 받은 범위표와 답안에서 확인합니다.</li>"
            )
        summary = f"{town} 주소와 정확히 연결된 고등학교는 {len(schools)}곳이며 학교 공식 링크는 최대 네 곳만 표시했습니다. 이 목록만으로 가까운 학교나 배정 가능성을 판단하지 않습니다."
        block = f"<p>{escape(summary)}</p><ul class=\"high-general-school-links\">{''.join(items)}</ul>"
    else:
        block = (
            f"<p>{escape(f'저장된 매핑 자료에서는 {town} 주소와 정확히 일치하는 고등학교를 확인하지 못했습니다. 다른 동의 학교를 가깝다고 추측해 연결하지 않으며 실제 재학 학교명을 기준으로 공식 홈페이지와 범위표를 확인해야 합니다.')}</p>"
        )
    closing = _pick(
        (
            f"학교 홈페이지에 시험 범위가 공개되지 않았더라도 {location} 학생이 받은 자료가 우선입니다. {focus} 항목의 날짜, 첫 판단, 수정 이유와 재시도 결과를 같은 기록에 남깁니다.",
            f"공식 정보 확인 뒤에는 {focus} 과제를 학교명으로 일반화하지 않습니다. 같은 학교 학생도 선택과목과 현재 이해가 다르므로 {location} 페이지의 진단 순서를 개인별 자료에 적용합니다.",
            f"학교 정보는 바뀔 수 있으므로 최종 일정은 해당 학교의 공식 안내에서 확인합니다. {location}의 {focus} 계획은 일정 확인 뒤 학생의 실제 자료와 생활시간으로 조정합니다.",
        ),
        slug,
        "general-school-closing",
    )
    return f'<section class="high-general-block high-general-school-context" data-school-count="{min(len(schools), 4)}"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>{block}<p>{escape(closing)}</p></section>'


def _student_case(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    grades = ("고1", "고2", "고3")
    grade = grades[_stable_index(slug, "general-case-grade") % 3]
    heading = _pick(
        (
            f"{focus} 과제를 조정한 {location} {grade} 합성 사례",
            f"설명 직후와 이틀 뒤가 달랐던 {location} {grade} {focus} 기록",
            f"공부시간보다 시작 행동을 바꾼 {location} {grade} 합성 사례",
            f"영어와 수학의 병목을 나눈 {location} {grade} {focus} 사례",
        ),
        slug,
        "general-case-heading",
    )
    intro = f"다음은 {location} 학생 한 명의 실제 상담이나 성적 향상 후기가 아니라 반복되는 고등 학습 장면을 교육적으로 재구성한 {grade} 합성 사례입니다. {_obj(focus)} 점검할 때 관찰 가능한 자료와 다음 재시도만 보여 줍니다."
    rows = (
        ("첫 관찰", str(pack["signal"]), "도움 전 답안과 시작까지 걸린 시간을 보존"),
        ("한 조건 조정", str(pack["task"]), "자료·시간·질문 가운데 한 조건만 변경"),
        ("간격 뒤 확인", str(pack["transfer"]), "혼자 재현한 단계와 필요한 힌트를 비교"),
    )
    row_html = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(location)} {escape(grade)} {escape(focus)}: {escape(action)}</td><td>{escape(record)}</td></tr>"
        for stage, action, record in rows
    )
    steps = (
        f"{location} 학생의 영어와 수학 첫 답안을 수업 중에 지우거나 고쳐 쓰지 않습니다.",
        f"{_obj(focus)} 자료·이해·표현·시간 가운데 한 행동으로 줄여 같은 주에 다시 사용합니다.",
        f"이틀 이상 뒤에 {str(pack['transfer'])} 다음 과제는 이 기록을 보고 학생과 정합니다.",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"이 합성 사례의 목적은 {location}에서 {_obj(focus)} 며칠 만에 해결했다는 결론이 아닙니다. 필요한 도움과 시작 시간을 줄이고 학생이 다음 행동을 설명하는 변화를 기록하는 데 있습니다.",
            f"합성 사례는 {location} 학생에게 그대로 적용할 처방이 아닙니다. {focus}의 과목 비율과 학습 시간은 실제 학년, 학교 일정, 자료, 수면과 피로도에 맞춰 다시 조정합니다.",
            f"{location} {grade} 학생의 결과가 달라지지 않았다면 태도를 평가하지 않습니다. {_obj(focus)} 막은 자료 난도, 질문 길이, 재시도 간격 중 하나만 바꾸고 나머지는 유지합니다.",
        ),
        slug,
        "general-case-closing",
    )
    return (
        f'<section class="high-general-block high-general-student-case" data-case-model="composite" data-case-grade="{grade}">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>단계</th><th>관찰과 실행</th><th>남길 기록</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<ol>{items}</ol><p>{escape(closing)}</p></section>"
    )


def _error_map(slug: str, location: str, focus: str) -> str:
    heading = _pick(
        (
            f"{location} {focus} 오류를 다섯 갈래로 기록하기",
            f"점수가 같아도 원인이 다른 {location}의 {focus}",
            f"자료·이해·표현·시간·재현으로 나누는 {location} 기록",
            f"다음 과제를 고르기 위한 {location} {focus} 오류 지도",
        ),
        slug,
        "general-error-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 {focus} 과제를 끝내지 못했다고 원인이 모두 의지나 개념 부족인 것은 아닙니다. 첫 기록을 남긴 채 자료 선택, 개념·내용 이해, 표현과 풀이, 시간 판단, 간격 뒤 재현을 나누면 같은 점수에서도 다음 행동이 달라집니다.",
            f"영어와 수학의 오답을 정답과 해설만으로 묶으면 {location} 학생의 {_subject(focus)} 어느 순간 끊겼는지 사라집니다. 아래 다섯 갈래는 학생을 평가하는 등급이 아니라 도움 위치와 재시도 날짜를 정하는 관찰 지도입니다.",
            f"{location}의 {focus} 기록에서는 틀린 문제뿐 아니라 맞았지만 오래 걸린 정답과 설명하지 못한 문장도 봅니다. 오류 원인을 한 갈래로 정한 뒤 그 행동과 직접 연결된 짧은 과제를 배치합니다.",
        ),
        slug,
        "general-error-intro",
    )
    errors = (
        ("자료 선택", "시험 목적과 관계없는 교재를 먼저 열거나 학교 원본과 실전 자료의 역할을 섞었는지 봅니다.", "오늘 사용할 원본 한 개와 완료 행동 한 개를 정합니다."),
        ("개념·내용 이해", "영어의 문장 근거와 수학의 정의·조건을 가렸을 때 자기 말로 복원하는지 확인합니다.", "핵심 문장이나 정의를 예시와 함께 다시 만듭니다."),
        ("표현·풀이", "이해한 내용을 영어 문장이나 수학의 식·그래프로 옮길 때 빠진 근거가 있는지 봅니다.", "표현 한 가지를 다른 방식으로 바꾸고 대응 관계를 표시합니다."),
        ("시간 판단", "시작 지연, 한 문제에 머문 시간, 과목 전환과 검토 시간을 분리해 기록합니다.", "제한 시간 뒤 멈춘 위치와 다음에 먼저 할 판단을 적습니다."),
        ("독립 재현", "도움 직후가 아니라 이틀 이상 지나 같은 원인의 새 자료를 혼자 시작하는지 봅니다.", "해설 없이 첫 단서와 완료 행동을 재현하고 이전 기록과 비교합니다."),
    )
    shift = _stable_index(slug, "general-error-order") % 5
    errors = errors[shift:] + errors[:shift]
    error_content: list[str] = []
    for index, (name, check, action) in enumerate(errors):
        action_label = action.rstrip(".")
        note = _pick(
            (
                f"{location} 기록에는 ‘{action_label}’라는 다음 행동과 재시도 날짜를 함께 남깁니다.",
                f"{location} 학생은 ‘{action_label}’를 실행한 뒤 같은 원인의 새 자료에서 결과를 비교합니다.",
                f"{location}에서는 ‘{action_label}’를 다음 과제로 정하고 도움을 준 위치도 따로 표시합니다.",
                f"{location} 오류표에는 ‘{action_label}’와 다시 확인할 요일을 적어 단순 오답 복사를 피합니다.",
                f"{location} 학생에게 필요한 첫 조정은 ‘{action_label}’이며 다른 조건은 이번 재시도에서 유지합니다.",
                f"{location}의 다음 기록은 ‘{action_label}’에서 시작해 과목과 자료가 바뀌어도 유지되는지 봅니다.",
            ),
            slug,
            f"general-error-note-{index}",
        )
        error_content.append(
            f"<h3>{escape(location)} {escape(focus)}의 {escape(name)} 오류</h3><p>{escape(check)} {escape(note)}</p>"
        )
    content = "".join(error_content)
    closing = _pick(
        (
            f"다섯 갈래가 동시에 흔들려도 {location}의 {_obj(focus)} 한 주에 모두 고치지 않습니다. 현재 학교 일정과 가장 직접적인 한 갈래부터 바꾸고 다른 과목과 시간차 재현에서도 유지되면 다음 오류로 이동합니다.",
            f"{location} 학생의 오류 지도에는 점수 대신 사용한 자료, 첫 근거, 수정한 표현, 풀이 시간과 다시 시작한 날짜를 씁니다. 이 기록이 {focus}의 다음 과제를 선택하는 근거가 됩니다.",
            f"오류 분류가 달라지는 것도 {location}의 {focus} 학습 과정입니다. 처음에는 시간 문제로 보였지만 개념을 가리자 멈췄다면 새 기록에 맞춰 과제와 질문을 다시 정합니다.",
        ),
        slug,
        "general-error-closing",
    )
    return f'<section class="high-general-block high-general-error-map" data-error-map="five-signals"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>{content}<p>{escape(closing)}</p></section>'


def _protocol(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 의사결정 프로토콜",
            f"여섯 번의 기록으로 구분하는 {location} 학생의 {focus}",
            f"수업 전후와 간격 뒤를 잇는 {location} {focus} 카드",
            f"한 주 동안 추적하는 {location} 고등 학습 기록",
        ),
        slug,
        "general-protocol-heading",
    )
    intro = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 한 번의 긴 시험으로 결론 내리지 않습니다. 목적이 다른 여섯 번의 짧은 기록으로 처음부터 알던 내용, 질문 뒤 가능해진 단계, 과목과 자료가 바뀌자 드러난 공백, 며칠 뒤에도 남은 행동을 구분합니다.",
            f"{focus} 직후에는 교사의 설명과 해설이 기억에 남아 독립 수준보다 높게 보일 수 있습니다. {location}에서는 첫 판단·과목 전환·자료 변형·오류 설명·시간 제한·간격 재현을 다른 카드로 나눕니다.",
            f"{location}의 {focus} 여섯 카드는 성적표가 아닙니다. 각 카드에는 문제 수보다 사용한 자료, 첫 근거, 멈춘 이유, 받은 질문, 수정 행동과 다음 날짜를 적습니다.",
        ),
        slug,
        "general-protocol-intro",
    )
    sequence_parts = (
        "학교 범위 확인", "영어 원문 복원", "수학 조건 표시", "첫 답안 보존", "오래 걸린 정답 분류",
        "학생 질문 만들기", "과목 순서 전환", "새 자료에 적용", "검토 시간 기록", "도움 한 단계 줄이기",
        "이틀 뒤 재현", "다음 주 시작점 선택",
    )
    sequence = sorted(sequence_parts, key=lambda item: _stable_index(slug, f"general-sequence-{item}"))[:8]
    sequence_note = (
        f"{location} {focus} 활동의 이번 순서는 {' → '.join(sequence)}입니다. 이 배열은 고정 처방이 아니라 학생 기록에서 먼저 끊긴 입력·판단·출력에 따라 다음 수업에서 바꾸는 관찰 경로입니다."
    )
    materials = (
        "학교에서 최근 사용한 범위표와 공책",
        "답을 가린 영어 원문과 수학 예제",
        "오래 걸린 정답 두 문항",
        "표현과 숫자 한 조건을 바꾼 자료",
        "질문과 첫 판단을 적는 빈 기록지",
        "시간 제한이 있는 짧은 실전 세트",
        "도움 뒤 수정한 영어 문장과 수학 풀이",
        "이틀 전에 끝낸 과제를 가린 재현 카드",
        "학생이 직접 고른 취약 영역 자료",
        "학교 일정과 실제 시작 시각을 적은 주간표",
    )
    actions = (
        "답을 보기 전에 자료 목적과 첫 단서를 한 문장으로 말합니다.",
        "영어 근거와 수학 조건을 서로 다른 색으로 표시합니다.",
        "멈춘 위치와 질문이 필요했던 이유를 자료 위에 남깁니다.",
        "도움 전 답안과 수정 답안을 나란히 두고 바뀐 판단을 설명합니다.",
        "과목 순서를 바꾼 뒤에도 첫 학습 행동을 스스로 선택합니다.",
        "시간이 끝난 위치에서 검토할 항목과 버릴 항목을 구분합니다.",
        "학교 원본의 기준을 새 문장과 새 문제에 적용합니다.",
        "다음에 같은 오류를 만났을 때 할 첫 행동을 학생이 적습니다.",
        "자료를 가리고 기억에서 핵심 문장과 풀이 순서를 복원합니다.",
        "부모나 교사가 준 질문과 학생이 고친 부분을 따로 기록합니다.",
    )
    evidence = (
        "혼자 고른 첫 자료와 시작까지 걸린 시간",
        "영어 문장 근거와 수학 조건 표시",
        "처음 답을 바꾼 정확한 이유",
        "도움이 필요했던 질문과 위치",
        "새 자료에서 유지한 판단 기준",
        "맞았지만 오래 걸린 단계의 원인",
        "과목 전환 뒤 다시 시작한 행동",
        "제한 시간 뒤 남긴 검토 순서",
        "자료 없이 재현한 첫 두 단계",
        "다음 카드에서 줄일 힌트 한 가지",
    )
    stages = ("첫 판단", "과목 전환", "자료 변형", "오류 설명", "시간 제한", "간격 재현")
    cards = []
    for index, stage in enumerate(stages):
        duration = 14 + _stable_index(slug, f"general-duration-{index}") % 23
        gap = 1 + _stable_index(slug, f"general-gap-{index}") % 5
        material = _pick(materials, slug, f"general-material-{index}")
        action = _pick(actions, slug, f"general-action-{index}")
        record = _pick(evidence, slug, f"general-evidence-{index}")
        note = _pick(
            (
                f"{location}의 카드에는 {_obj(record)} 남기고 간격을 둔 뒤 같은 도움 없이 재시작합니다.",
                f"간격을 둔 뒤 {location} 학생이 같은 기준을 꺼내는지 보려고 {_obj(record)} 보존합니다.",
                f"{location} 기록에서 {_obj(record)} 확인한 다음 충분한 간격을 둔 새 자료로 옮깁니다.",
                f"{_obj(record)} 적어 둔 뒤 {location} 학생에게 간격을 두고 첫 판단을 다시 설명하게 합니다.",
                f"{location}에서는 {_obj(record)} 비교하고 다음 확인에서 필요한 힌트를 한 단계 줄입니다.",
                f"독립 재현을 위해 {location} 카드에 {_obj(record)} 따로 남기고 간격 뒤 다시 확인합니다.",
            ),
            slug,
            f"general-protocol-note-{index}",
        )
        purpose = _pick(
            (
                "정답 개수보다 학생이 다음 판단을 다시 선택하는지가 이 카드의 기준입니다.",
                "완료 분량은 보조 기록이며 혼자 시작한 단계가 이번 카드의 핵심입니다.",
                "설명 직후의 성공과 간격 뒤 독립 재현을 서로 다른 결과로 해석합니다.",
                "학생이 받은 질문의 위치와 스스로 수정한 행동을 구분해 봅니다.",
                "한 번의 점수 대신 자료가 바뀌어도 남은 판단 기준을 확인합니다.",
                "이 기록은 성실성 평가가 아니라 다음 도움을 줄일 위치를 정하는 자료입니다.",
            ),
            slug,
            f"general-protocol-purpose-{index}",
        )
        cards.append(
            f"<h3>{escape(location)} {escape(focus)} {escape(stage)} 카드</h3>"
            f"<p>{escape(_obj(material))} 사용해 학생이 집중할 수 있는 짧은 시간 동안 {escape(action)} {escape(note)} {escape(purpose)}</p>"
        )
    closing = _pick(
        (
            f"여섯 카드가 끝나면 {location} 학생의 {_obj(focus)} 공부시간이나 문제 수로 합산하지 않습니다. 혼자 시작한 카드, 과목을 바꾼 카드, 새 자료에 적용한 카드와 간격 뒤 재현한 카드를 나눠 가장 약한 연결만 다음 주 첫 과제로 옮깁니다.",
            f"{location}의 {focus} 여섯 번이 모두 완벽해야 다음 단계로 가는 것은 아닙니다. 학생이 도움을 요청할 위치와 수정 이유를 말하고 같은 힌트를 반복해서 기다리지 않으면 자료 길이와 난도를 조금씩 넓힙니다.",
            f"이 프로토콜은 {location} 학생의 학년과 시험 일정에 맞춰 시간을 줄여도 됩니다. {focus}의 핵심은 카드 수가 아니라 첫 기록을 보존하고 다른 과목·자료·날짜에서 같은 판단을 재현하는지 비교하는 데 있습니다.",
        ),
        slug,
        "general-protocol-closing",
    )
    return f'<section class="high-general-block high-general-protocol" data-protocol-cards="6"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><p class="high-general-sequence">{escape(sequence_note)}</p>{"".join(cards)}<p>{escape(closing)}</p></section>'


def _local_experiment(slug: str, location: str, focus: str) -> str:
    """Create a deterministic, page-specific four-session observation plan."""
    days = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")
    materials = (
        "최근 영어 교과서의 표시 없는 한 단락", "수학 공책에서 풀이가 멈춘 예제",
        "학교 범위표와 제출 일정 메모", "맞았지만 오래 걸린 실전 문항",
        "도움을 받은 뒤 다시 쓴 영어 답안", "조건 하나를 바꾼 수학 변형 문제",
        "수행평가 안내문과 학생의 첫 초안", "이틀 전에 끝낸 과제를 가린 복원지",
        "학생이 직접 고른 취약 영역 자료", "내신과 모의고사 오답 각 한 문항",
        "이번 주 실제 시작 시각 기록", "질문을 적어 둔 학교 수업 공책",
    )
    actions = (
        "자료의 목적과 완료 행동을 먼저 말합니다", "첫 답을 지우지 않고 막힌 줄에 표시합니다",
        "영어 근거와 수학 조건을 다른 칸에 적습니다", "받은 힌트와 스스로 바꾼 판단을 나눕니다",
        "과목 순서를 바꾼 뒤 첫 행동을 다시 고릅니다", "시간이 끝난 지점에서 검토 순서를 정합니다",
        "학교 원본과 새 자료의 공통 기준을 찾습니다", "정답보다 오래 머문 단계의 원인을 설명합니다",
        "다음 수업에 가져갈 질문을 한 문장으로 만듭니다", "자료를 가린 뒤 기억에서 첫 두 단계를 복원합니다",
        "완료하지 못한 이유를 시간·자료·난도로 구분합니다", "다시 볼 날짜와 줄일 힌트 하나를 학생이 정합니다",
    )
    evidence = (
        "혼자 자료를 연 시각", "처음 고른 문장 근거", "조건을 표시한 순서", "풀이가 끊긴 정확한 줄",
        "질문 전후에 달라진 판단", "맞았지만 오래 걸린 이유", "과목 전환 뒤의 첫 행동",
        "제한 시간 뒤 남긴 검토 항목", "도움 없이 복원한 단계", "다음에 줄일 힌트",
        "학생이 정한 완료 기준", "이틀 뒤에도 유지된 설명",
    )
    headings = ("첫 시도 보존", "자료 목적 전환", "도움 한 단계 줄이기", "간격 뒤 독립 재현")
    cards: list[str] = []
    used_days: set[str] = set()
    for index, label in enumerate(headings):
        day_index = _stable_index(slug, f"general-experiment-day-{index}") % len(days)
        while days[day_index] in used_days:
            day_index = (day_index + 1) % len(days)
        day = days[day_index]
        used_days.add(day)
        hour = 18 + _stable_index(slug, f"general-experiment-hour-{index}") % 5
        minute = (5 * (_stable_index(slug, f"general-experiment-minute-{index}") % 12)) % 60
        duration = 17 + _stable_index(slug, f"general-experiment-duration-{index}") % 29
        material = _pick(materials, slug, f"general-experiment-material-{index}")
        action = _pick(actions, slug, f"general-experiment-action-{index}")
        record = _pick(evidence, slug, f"general-experiment-evidence-{index}")
        gap = 1 + _stable_index(slug, f"general-experiment-gap-{index}") % 4
        cards.append(
            f"<h3>{escape(location)} {_with(focus)} 연결한 {escape(label)} 점검</h3>"
            f"<p>가상 일정은 {escape(day)}의 집중 가능한 시간대로 둡니다. "
            f"{escape(_obj(material))} 사용해 {escape(action)}. {escape(location)} 기록에는 {escape(_obj(record))} 남기고 "
            f"충분한 간격을 둔 뒤 같은 설명 없이 다시 시작합니다. 이 시각과 분량은 실제 학생의 일정이 아니라 "
            f"{escape(_obj(focus))} 관찰할 때 한 번에 한 조건만 바꾸는 방법을 보여 주는 예시입니다.</p>"
        )
    intro = (
        f"{location}의 생활시간이나 학교 일정을 임의로 단정하지 않고 {_obj(focus)} 시험하는 네 번의 짧은 예시입니다. "
        "실제 적용에서는 학생이 받은 자료와 가능한 시각으로 바꾸되, 첫 시도와 수정 뒤 시도, 간격 뒤 재현을 같은 기준으로 비교합니다."
    )
    closing = (
        f"네 기록을 합산해 {location} 학생의 성실성 점수를 만들지 않습니다. {_obj(focus)} 위해 어떤 자료에서 혼자 시작했고 "
        "어느 질문 뒤 판단이 달라졌는지 확인한 다음, 가장 약한 연결 한 가지만 다음 주 계획으로 옮깁니다."
    )
    return (
        '<section class="high-general-block high-general-local-experiment" data-experiment-sessions="4">'
        f"<h2>{escape(location)} {escape(focus)} 단계별 미니 점검</h2><p>{escape(intro)}</p>"
        f'{"".join(cards)}<p>{escape(closing)}</p></section>'
    )


def _parent_section(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} 가정에서 {_obj(focus)} 확인하는 질문",
            f"공부시간과 점수 대신 묻는 {location} {focus} 대화",
            f"학생의 설명을 끌어내는 {location} {focus} 기준",
            f"도움을 줄일 위치를 정하는 {location} 학부모 질문",
        ),
        slug,
        "general-parent-heading",
    )
    intro = _pick(
        (
            f"{location} 가정에서 {_obj(focus)} 도울 때 ‘공부했니’나 ‘더 풀어’처럼 넓은 말은 다음 행동을 알려 주지 못합니다. {str(pack['parent'])} 학생의 답에서는 완벽한 설명보다 실제 자료와 바뀐 판단을 다시 짚습니다.",
            f"학부모가 영어 해석과 수학 풀이를 먼저 말하면 {location} 학생의 {focus} 독립 수준을 보기 어렵습니다. {str(pack['parent'])} 질문 하나 뒤에는 학생이 자료를 열고 자기 근거를 말할 시간을 둡니다.",
            f"{location}의 {_topic(focus)} 성적표와 숙제 완료만으로 확인하지 않습니다. {str(pack['parent'])} 도움 뒤 어느 단계부터 혼자 이어 갔는지와 다음 날 같은 순서를 재현했는지 기록합니다.",
        ),
        slug,
        "general-parent-intro",
    )
    questions = (
        "오늘 가장 먼저 연 학교 자료와 그 이유는 무엇인가요?",
        "영어 답과 수학 풀이를 결정한 근거를 각각 말할 수 있나요?",
        "오래 걸린 정답에서 시간이 늘어난 단계는 어디인가요?",
        "질문을 받은 뒤 바꾼 판단과 그대로 유지한 부분은 무엇인가요?",
        f"{focus}의 기준을 이틀 뒤 새 자료에서도 사용할 수 있나요?",
    )
    shift = _stable_index(slug, "general-parent-order") % 5
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(location)} {escape(focus)} 질문: {escape(question)}</li>" for question in questions)
    closing = _pick(
        (
            f"질문은 {location} 학생의 모든 문제에 사용하지 않습니다. {_with(focus)} 직접 연결되는 대표 자료 두세 개에서만 깊게 설명하게 하고 나머지는 같은 기준으로 혼자 시작하도록 기다립니다.",
            f"칭찬도 ‘열심히 했다’보다 {location} 학생이 {_obj(focus)} 위해 원본을 확인한 행동, 첫 답을 보존한 행동, 수정 이유를 말한 행동처럼 반복 가능한 장면에 붙입니다.",
            f"{location} 가정에서 {focus} 대화가 길어지면 학생이 부모의 다음 말을 기다릴 수 있습니다. 질문 하나, 생각 시간, 학생 설명, 짧은 확인 순서로 끝냅니다.",
        ),
        slug,
        "general-parent-closing",
    )
    return f'<section class="high-general-block high-general-parent"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ul>{items}</ul><p>{escape(closing)}</p></section>'


def _transfer(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 학습이 끝났다고 보는 기준",
            f"도움 직후보다 다음 날 확인할 {location}의 {focus}",
            f"과목·자료·시간을 바꾸는 {location} {focus} 전이",
            f"익숙한 정답을 새 문제로 옮기는 {location} 기준",
        ),
        slug,
        "general-transfer-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 익숙한 문제를 맞힌 것만으로 {_subject(focus)} 자리 잡았다고 판단하지 않습니다. 과목과 표현을 바꾸고, 자료 조건을 바꾸고, 시간을 둔 뒤 다시 시작하는 세 단계에서 같은 학습 기준을 꺼내는지 확인합니다.",
            f"{_obj(focus)} 설명할 수 있어도 {location} 학생이 새 자료를 혼자 열지 못하면 전이 활동이 필요합니다. {str(pack['transfer'])} 이때 힌트는 답이 아니라 첫 단서를 떠올릴 최소 질문으로 제한합니다.",
            f"{location}의 {_topic(focus)} 학습 당일보다 이틀 뒤 기록이 중요합니다. {str(pack['signal'])}를 확인하고 수정 이유까지 말하면 다음 과목과 자료로 연결합니다.",
        ),
        slug,
        "general-transfer-intro",
    )
    steps = (
        f"과목 전이: {location}의 {focus} 기준을 영어 근거와 수학 풀이에서 각각 사용합니다.",
        f"자료 전이: {str(pack['transfer'])}",
        f"시간 전이: 이틀 이상 뒤에 {str(pack['signal'])}를 다시 확인합니다.",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"세 단계가 모두 가능할 때 {location} 학생의 {focus} 과제를 다음 길이와 난도로 넓힙니다. 하나가 흔들리면 문제 수를 늘리지 않고 해당 전이만 짧게 다시 설계합니다.",
            f"{location}에서 {focus}의 목표는 모든 과목을 같은 속도로 끝내는 것이 아닙니다. 학교와 실전 자료에서 필요한 첫 행동과 완료 기준을 학생이 고르면 다음 단계로 볼 수 있습니다.",
            f"전이 기록은 {location} 학생을 비교하는 점수가 아닙니다. {_obj(focus)} 어떤 과목과 조건에서 유지하고 어디에서 잃는지 찾아 다음 주 과제를 정확하게 고르는 자료입니다.",
        ),
        slug,
        "general-transfer-closing",
    )
    return f'<section class="high-general-block high-general-transfer"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ol>{items}</ol><p>{escape(closing)}</p></section>'


def _context_links(location: str, city: str, focus: str) -> str:
    links = (
        (f"/{city}고등과외/", f"{city} 고등과외의 학년별 큰 기준"),
        (f"/{location}고등영어과외/", f"{location} 고등영어 학습 기록"),
        (f"/{location}고등수학과외/", f"{location} 고등수학 풀이 기록"),
    )
    items = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for href, label in links)
    intro = f"{location}의 {_obj(focus)} 확인한 뒤 필요한 상위 범위와 과목 자료만 이어 보도록 세 페이지를 골랐습니다. 모든 키워드를 링크로 만들지 않고 도시 단위 고등과외와 같은 지역의 고등영어·고등수학 기준만 연결합니다."
    return f'<aside class="high-general-context-links" data-link-count="3"><h2>{escape(location)} {escape(focus)} 다음에 볼 학습 기준</h2><p>{escape(intro)}</p><ul>{items}</ul></aside>'


def _faq(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    pairs = [
        (
            f"{location} 고등 학습은 언제부터 점검해야 하나요?",
            f"{location}에서는 특정 학년까지 기다리지 않고 현재 학교 자료와 일주일 기록으로 {_obj(focus)} 확인합니다. 고1은 수업 당일 복원, 고2는 선택과목과 누적 공백의 연결, 고3은 실전 루틴과 취약 영역의 우선순위를 보며 학생이 혼자 시작할 수 있는 단계에서 과제 길이를 정합니다.",
        ),
        (
            f"{location}고등과외를 찾기 전에 집에서 무엇을 확인하나요?",
            f"{location} 가정에서는 {str(pack['task'])} 활동을 30~40분 안에 진행하고 첫 답안을 지우지 않습니다. {focus}의 정답만 보지 말고 사용한 자료, 첫 근거, 막힌 위치, 질문 뒤 바뀐 판단을 적은 다음 이틀 뒤 같은 도움 없이 다시 시작하게 합니다.",
        ),
        (
            f"{location} 학생의 학습이 흔들리면 공부시간부터 늘려야 하나요?",
            f"{location} 학생의 {_subject(focus)} 약하다고 전체 공부시간과 교재부터 늘리면 실제 공백을 가릴 수 있습니다. {str(pack['signal'])}를 살핀 뒤 자료 선택, 이해, 표현·풀이, 시간 판단, 독립 재현 가운데 막힌 한 지점을 고르고 그 행동과 연결된 짧은 과제를 먼저 반복합니다.",
        ),
        (
            f"{location} 고등 학습에서 영어와 수학은 어떻게 나누나요?",
            f"{location}에서는 {str(pack['english'])} {str(pack['math'])} 두 과목 시간을 같게 만드는 대신 현재 학교 범위와 시험 목적에서 가장 약한 연결에 시간을 더 주고 강점 과목은 간격 복습으로 유지합니다.",
        ),
        (
            f"{location} 가정에서 부모는 어디까지 도와야 하나요?",
            f"{location}에서 부모는 영어 답이나 수학 풀이를 대신하지 않습니다. {str(pack['parent'])} 질문 하나를 한 뒤 학생이 자료와 근거를 고르게 하고 도움을 준 위치와 이후 혼자 이어 간 단계를 구분해 다음 재시도에서 힌트를 줄입니다.",
        ),
    ]
    shift = _stable_index(slug, "general-faq-order") % 5
    pairs = pairs[shift:] + pairs[:shift]
    content = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in pairs)
    heading = _pick(
        (
            f"{location} {focus} 고등 학습에 자주 묻는 질문",
            f"{location}고등과외와 {focus} FAQ",
            f"학년·과목·시험으로 나눈 {location} {focus} FAQ",
        ),
        slug,
        "general-faq-heading",
    )
    return f'<section class="high-general-block high-general-faq"><h2 class="high-general-faq" data-faq-focus="{escape(focus)}">{escape(heading)}</h2>{content}</section>'


def _closing(slug: str, location: str, focus: str, pack: dict[str, object]) -> str:
    heading = _pick(
        (
            f"{location} {focus}의 다음 한 단계",
            f"새 교재보다 먼저 정할 {location}의 {focus} 재시도",
            f"{location} 학생이 혼자 시작할 때까지 남길 기록",
            f"{location}고등과외 정보를 실제 {focus} 행동으로 옮기기",
        ),
        slug,
        "general-closing-heading",
    )
    paragraph = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 돕는 핵심은 교재와 공부시간을 일괄적으로 늘리는 데 있지 않습니다. {str(pack['task'])} 그리고 정한 날짜에 {str(pack['transfer'])} 이 기록이 쌓이면 학생은 새로운 학교 자료와 실전 문제에서도 필요한 첫 행동을 자기 힘으로 고를 수 있습니다.",
            f"이 페이지의 {location} 학교 정보와 {focus} 계획은 상담이나 성취를 보장하는 문구가 아닙니다. 실제 범위표와 첫 답안, 학교 공식 안내, 간격 뒤 재현을 함께 확인하고 가장 작은 다음 행동부터 조정하는 교육용 기준입니다.",
            f"{location}에서 {_obj(focus)} 오래 유지하려면 시험 직후의 점수만 남기지 않습니다. 영어 근거, 수학의 첫 전략, 수정 이유, 공부를 시작한 시간과 다시 볼 날짜를 기록해 다음 평가에서도 같은 기준을 꺼내 쓰게 합니다.",
        ),
        slug,
        "general-closing-paragraph",
    )
    evidence_open = _pick(
        (
            f"{location}의 {focus} 점검을 마칠 때는 {str(pack['signal'])}를 다시 읽고 학생이 고른 자료와 도움 전 첫 행동을 함께 보관합니다.",
            f"{location} 학생의 {focus} 기록은 {str(pack['task'])}에서 처음 남긴 판단과 수정 뒤 달라진 근거를 나란히 둘 때 의미가 있습니다.",
            f"{location}에서 {focus} 계획을 정리할 때는 다음 전이 행동이 실제 답안과 학습 기록에서 확인되는지 먼저 봅니다. 확인할 행동은 다음과 같습니다. {str(pack['transfer'])}",
            f"{location}의 학교 일정과 {focus} 학습을 연결하려면 {str(pack['signal'])}를 관찰 기준으로 두고 첫 시도와 도움 뒤 행동을 구분합니다.",
            f"{location} 학생에게 새 교재를 더하기 전에는 {str(pack['task'])}의 시작 위치와 마지막으로 혼자 설명한 근거를 보존합니다.",
            f"{location}의 {focus} 자료를 검토할 때는 {str(pack['signal'])}가 반복되는 장면과 그렇지 않은 장면을 별도로 기록합니다.",
        ),
        slug,
        "closing-evidence-open",
    )
    evidence_compare = _pick(
        (
            "다음 확인에서는 같은 답을 외웠는지보다 학교 일정과 과목이 달라져도 판단 순서를 스스로 꺼내 쓰는지 살핍니다.",
            "후속 점검에서는 정답 수보다 자료 선택, 첫 근거, 질문 시점, 도움 없이 마친 범위가 어떻게 달라졌는지 비교합니다.",
            "시간을 둔 재시도에서는 해설을 기억하는지보다 새 조건에서 필요한 자료와 첫 행동을 혼자 고르는지 확인합니다.",
            "시험 전후 기록은 점수만 비교하지 않고 시작 지연, 근거 설명, 수정 행동, 독립 재현의 변화를 같은 기준으로 읽습니다.",
            "학교 자료가 바뀐 뒤에도 학생이 과제 목적을 말하고 완료 기준을 정할 수 있는지 살펴 이전 성공과 구분합니다.",
            "영어와 수학의 결과를 한 점수로 합치지 않고 각 과목에서 유지된 판단과 다시 도움이 필요한 위치를 나누어 봅니다.",
        ),
        slug,
        "closing-evidence-compare",
    )
    evidence_adjust = _pick(
        (
            "근거가 부족하면 분량보다 관찰 기준과 도움 시점부터 고칩니다.",
            "변화가 보이지 않으면 학생을 압박하지 않고 과제 크기와 자료 순서를 먼저 조정합니다.",
            "독립 수행이 이어지지 않으면 새 진도를 더하기 전에 질문 방식과 재확인 간격을 바꿉니다.",
            "판단 흔적이 남지 않으면 공부 시간을 늘리기보다 기록 방법과 완료 조건을 더 분명하게 정합니다.",
            "한 장면의 성공만으로 결론 내리지 않고 다른 과목과 자료에서도 같은 행동이 재현되는지 다시 봅니다.",
            "다음 계획은 보호자의 기대가 아니라 학생이 실제로 남긴 근거와 학교 일정에 맞춰 줄이거나 넓힙니다.",
        ),
        slug,
        "closing-evidence-adjust",
    )
    evidence_note = f"{evidence_open} {evidence_compare} {evidence_adjust}"
    specific_note = {
        "부산전포동고등과외": (
            "부산전포동 페이지의 첫 내신 준비는 영어와 수학을 한 시간표에 섞기보다 학교 원본과 누적 공백의 역할을 먼저 나눕니다. 영어는 범위 안 문장의 "
            "근거와 서술 조건을, 수학은 조건 표시와 첫 식·검산을 별도 기록으로 남깁니다. 모의고사 자료는 학교 범위를 대신하지 않고 낯선 자료에서 판단 순서를 "
            "유지하는 확인용으로 둡니다. 시험 뒤에는 점수만 비교하지 않고 도움 전에 시작한 위치, 수정 이유, 간격 뒤 다시 설명한 범위를 대조해 다음 과목 배분을 정합니다."
        ),
    }.get(slug, "")
    specific_html = f"<p>{escape(specific_note)}</p>" if specific_note else ""
    return f'<section class="high-general-block high-general-closing"><h2>{escape(heading)}</h2><p>{escape(paragraph)}</p><p>{escape(evidence_note)}</p>{specific_html}</section>'


def build_local_high_general_body(slug: str, focus: str) -> str:
    location, city, town = _parts(slug)
    pack, _ = _pack_and_focus(slug)
    sections = {
        "grade": _grade_plan(slug, location, focus, pack),
        "subjects": _subject_plan(slug, location, focus, pack),
        "assessment": _assessment_map(slug, location, focus, pack),
        "weekly": _weekly_plan(slug, location, focus, pack),
        "school": _school_section(slug, location, city, town, focus),
        "case": _student_case(slug, location, focus, pack),
        "errors": _error_map(slug, location, focus),
        "protocol": _protocol(slug, location, focus, pack),
        "experiment": _local_experiment(slug, location, focus),
        "parent": _parent_section(slug, location, focus, pack),
        "transfer": _transfer(slug, location, focus, pack),
    }
    orders = (
        ("grade", "subjects", "assessment", "weekly", "school", "errors", "protocol", "experiment", "case", "parent", "transfer"),
        ("subjects", "grade", "school", "assessment", "protocol", "experiment", "errors", "weekly", "parent", "case", "transfer"),
        ("assessment", "grade", "subjects", "case", "school", "errors", "weekly", "experiment", "protocol", "transfer", "parent"),
        ("grade", "weekly", "subjects", "errors", "case", "assessment", "protocol", "experiment", "school", "parent", "transfer"),
        ("school", "grade", "assessment", "subjects", "parent", "weekly", "errors", "experiment", "protocol", "case", "transfer"),
        ("subjects", "assessment", "grade", "protocol", "experiment", "weekly", "school", "case", "errors", "transfer", "parent"),
    )
    order = _pick(orders, slug, "general-section-order")
    body = _opening(slug, location, focus, pack) + _search_intent(slug, location, focus, pack)
    body += "".join(sections[key] for key in order)
    body += _context_links(location, city, focus)
    body += _faq(slug, location, focus, pack)
    body += _closing(slug, location, focus, pack)
    return body


def individualize_local_high_general_body(body: str, slug: str) -> str:
    if not is_local_high_general_slug(slug):
        return body
    _, focus = _pack_and_focus(slug)
    return build_local_high_general_body(slug, focus)
