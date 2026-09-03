from __future__ import annotations

import re
from html import unescape

from sitegen.local_elementary_math import (
    ELEMENTARY_SCHOOL_CONTEXT,
    _obj,
    _pick,
    _stable_index,
    _subject,
    _topic,
    _with,
)
from sitegen.utils import escape


LOCAL_ELEMENTARY_ENGLISH_PATTERN = re.compile(r"^(부산|양산|구미).+(?:동|읍|면)초등영어과외$")
CONTENT_VERSION = "elementary-english-individual-v1"
CONTENT_MARKER = "local-elementary-english-content"


def _plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def is_local_elementary_english_slug(slug: str) -> bool:
    return bool(LOCAL_ELEMENTARY_ENGLISH_PATTERN.fullmatch(slug))


def _focus_from_body(body: str) -> str:
    current = re.search(r'data-elementary-english-focus="([^"]+)"', body, flags=re.I)
    if current:
        return unescape(current.group(1)).strip()
    text = _plain_text(body)
    for pattern in (
        r"초등영어과외,?\s*(.+?)(?:을|를)\s*중심으로",
        r"초등영어과외에서는\s*(.+?)(?:을|를)\s*어떻게",
        r"여기서는\s*(.+?)(?:을|를)\s*기준으로",
        r"페이지에서는\s*(.+?)(?:을|를)\s*중심으로",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S)
    return _plain_text(heading.group(1)) if heading else "소리와 의미를 연결하는 영어 학습"


def _kind_for_focus(focus: str) -> str:
    if any(word in focus for word in ("소리", "파닉스", "발음", "강세", "음절", "사이트워드", "해독", "받아쓰기")):
        return "phonics"
    if any(word in focus for word in ("어휘", "단어", "유의어", "반의어", "결합")):
        return "vocabulary"
    if any(word in focus for word in ("어순", "관사", "복수", "동사", "시제", "대명사", "의문사", "전치사", "접속사", "형용사", "부사", "수 일치", "문장 결합")):
        return "grammar"
    if any(word in focus for word in ("듣기", "쉐도잉", "에코")):
        return "listening"
    if any(word in focus for word in ("말하기", "묘사", "역할놀이", "질문과 대답", "일상 표현")):
        return "speaking"
    if any(word in focus for word in ("쓰기", "일기", "편지", "메시지", "틀을")):
        return "writing"
    if any(word in focus for word in ("복습", "노트", "숙제", "자기 오류", "독서 기록", "자기주도")):
        return "routine"
    return "reading"


ENGLISH_PACKS: dict[str, dict[str, str]] = {
    "phonics": {
        "material": "짧은 음원, 소리 칸이 있는 단어 카드, 학생의 낭독과 받아쓰기 원본",
        "signal": "규칙 이름을 외우는 데서 멈추지 않고 낯선 단어를 소리 단위로 나누고 다시 합치는지",
        "action": "소리를 듣고 입 모양과 글자 묶음을 대응한 뒤 같은 패턴을 다른 단어와 짧은 문장에서 찾습니다.",
        "transfer": "처음 보는 단어에서 아는 글자 묶음과 예외를 구분하고 문맥으로 발음을 다시 확인합니다.",
        "check": "음원을 가린 낭독, 철자를 가린 듣기, 하루 뒤 받아쓰기를 비교해 기억과 적용을 나눕니다.",
        "lower": "1~2학년은 말소리를 분절하고 합성하며 자주 쓰는 글자와 소리의 대응을 놀이와 짧은 낭독으로 익힙니다.",
        "middle": "3~4학년은 여러 음절과 철자 패턴을 낯선 단어 해독, 문장부호, 의미 덩어리 읽기와 연결합니다.",
        "upper": "5~6학년은 강세·리듬·연음과 철자 예외를 독해 어휘, 받아쓰기, 자신의 발음 점검에 활용합니다.",
        "task": "처음 듣는 단어 네 개를 소리 칸으로 나누고 철자를 예상한 뒤 실제 표기와 다른 부분의 이유를 말합니다.",
        "parent": "발음을 즉시 대신 말하지 않고 어떤 소리를 들었는지, 어느 글자 묶음을 근거로 읽었는지 먼저 묻습니다.",
    },
    "vocabulary": {
        "material": "교과서 문장, 그림·상황 카드, 학생이 만든 어휘 노트와 간격 복습 기록",
        "signal": "뜻 한 개만 말하지 않고 발음·형태·문장 속 역할·함께 쓰이는 단어를 연결하는지",
        "action": "새 단어를 소리 내어 읽고 그림이나 정의로 뜻을 확인한 뒤 익숙한 표현과 자신의 문장에 넣습니다.",
        "transfer": "같은 단어가 다른 문장과 품사 형태로 나왔을 때 핵심 의미와 달라진 쓰임을 구분합니다.",
        "check": "우리말 뜻을 가린 회상, 문맥 빈칸, 직접 만든 문장을 서로 다른 날에 확인합니다.",
        "lower": "1~2학년은 이미지·동작·소리를 이용해 생활 어휘를 짧은 표현 덩어리로 말합니다.",
        "middle": "3~4학년은 주제별 어휘를 유의어·반의어·범주와 묶고 읽기 문장에서 다시 찾습니다.",
        "upper": "5~6학년은 문맥 추론, 접두·접미 형태, 자연스러운 단어 결합을 독해와 쓰기에 적용합니다.",
        "task": "익숙한 단어 하나를 뜻·발음·함께 쓰이는 말·새 문장의 네 칸에 적고 한 칸을 가려 복원합니다.",
        "parent": "뜻을 외웠는지만 묻지 않고 그 단어가 어떤 장면에서 쓰이는지와 다른 문장에서도 자연스러운지 질문합니다.",
    },
    "grammar": {
        "material": "학생이 쓴 짧은 문장, 어순 카드, 교과서 예문과 오류가 남은 수정 기록",
        "signal": "문법 용어보다 누가·무엇을·어떻게 했는지 문장 성분과 의미의 관계를 설명하는지",
        "action": "문장 카드를 움직여 어순이 바뀔 때 의미가 어떻게 달라지는지 말하고 자신의 예문을 만듭니다.",
        "transfer": "주어·시간·장소·수량을 바꾼 문장에서도 필요한 형태와 어순을 다시 선택합니다.",
        "check": "소리 내어 읽기, 문장 성분 표시, 질문문 전환으로 빠진 말과 불필요한 형태를 검토합니다.",
        "lower": "1~2학년은 I am, I like처럼 의미가 분명한 짧은 덩어리에서 어순을 통째로 경험합니다.",
        "middle": "3~4학년은 주어와 동사, 단수와 복수, be동사와 일반동사를 의미와 함께 구분합니다.",
        "upper": "5~6학년은 시제·대명사·관사·전치사·접속사를 독해 문장과 자신의 쓰기에서 수정합니다.",
        "task": "낱말 카드 여섯 장으로 두 문장을 만들고 순서를 바꾸었을 때 자연스럽지 않은 이유를 뜻과 함께 설명합니다.",
        "parent": "문법 이름을 먼저 알려주기보다 누가 한 행동인지, 언제 일어났는지, 빠진 말이 무엇인지 문장 의미로 묻습니다.",
    },
    "reading": {
        "material": "제목·그림이 있는 짧은 글, 학생이 표시한 문장 단서와 읽은 뒤의 요약 기록",
        "signal": "모든 단어를 번역하지 않고 제목·중심 문장·지시어·접속어로 글의 흐름을 복원하는지",
        "action": "읽기 전에는 제목으로 질문을 만들고 읽는 중에는 근거에 표시하며 읽은 뒤에는 한 문장으로 요약합니다.",
        "transfer": "글의 소재와 문단 순서가 달라져도 중심 생각, 세부 근거, 원인과 결과를 다시 찾습니다.",
        "check": "답을 고른 문장 근거와 버린 선택지의 이유를 표시하고 다음 날 글 없이 내용을 다시 말합니다.",
        "lower": "1~2학년은 그림과 반복 문장을 이용해 누가 무엇을 하는지 짧게 예측하고 확인합니다.",
        "middle": "3~4학년은 사건 순서, 중심 문장, 세부 정보를 문단별 한 줄 메모로 정리합니다.",
        "upper": "5~6학년은 비교·대조, 원인·결과, 사실·의견, 추론을 제목과 문장 근거로 설명합니다.",
        "task": "120단어 안팎의 글에서 제목을 가리고 중심 생각과 근거 두 문장을 고른 뒤 새 제목을 붙입니다.",
        "parent": "모르는 단어 뜻부터 알려주지 않고 제목과 그림에서 예상한 내용, 답을 뒷받침한 문장을 먼저 묻습니다.",
    },
    "listening": {
        "material": "20~40초 길이의 짧은 음원, 그림 선택지, 학생이 두 번에 나누어 적은 듣기 메모",
        "signal": "한 단어를 놓쳐도 화자·장소·목적·순서를 이용해 전체 상황을 유지하는지",
        "action": "첫 번째 듣기에는 전체 상황, 두 번째에는 필요한 세부 정보, 마지막에는 들은 표현 한 덩어리를 기록합니다.",
        "transfer": "말하는 속도와 화자가 달라져도 핵심어, 강세, 앞뒤 문맥으로 같은 목적을 찾습니다.",
        "check": "대본을 보기 전 메모와 본 뒤 수정한 메모를 구분하고 다음 날 음원 없이 내용을 다시 말합니다.",
        "lower": "1~2학년은 그림·동작과 짧은 지시를 연결해 들은 소리를 의미 있는 행동으로 바꿉니다.",
        "middle": "3~4학년은 짧은 대화에서 화자·장소·목적과 숫자·시간 같은 세부 정보를 나눠 듣습니다.",
        "upper": "5~6학년은 연결 발음과 핵심 강세를 이용해 전체 내용과 근거 표현을 함께 기록합니다.",
        "task": "30초 음원을 두 번 듣고 첫 메모에는 상황을, 두 번째 메모에는 달라진 세부 정보 세 가지를 적습니다.",
        "parent": "놓친 단어를 바로 들려주지 않고 앞뒤에서 들린 말, 화자의 의도, 그림 단서를 이용해 먼저 추론하게 합니다.",
    },
    "speaking": {
        "material": "그림·역할 카드, 학생의 짧은 녹음, 질문과 대답이 이어진 대화 기록",
        "signal": "외운 문장을 그대로 반복하는 데서 멈추지 않고 상황과 상대의 질문에 맞춰 표현을 바꾸는지",
        "action": "핵심 표현을 한 번 듣고 따라 한 뒤 장소·상대·목적을 바꾸어 자신의 문장으로 대답합니다.",
        "transfer": "예상하지 못한 후속 질문에서도 아는 어휘와 짧은 연결어로 대화를 한 차례 더 이어 갑니다.",
        "check": "첫 녹음과 수정 녹음에서 의미 전달, 문장 완성, 발음 명료도, 스스로 고친 부분을 비교합니다.",
        "lower": "1~2학년은 인사·감정·좋아하는 것처럼 익숙한 장면에서 짧은 요청과 응답을 주고받습니다.",
        "middle": "3~4학년은 그림을 두세 문장으로 묘사하고 이유나 위치를 덧붙여 대답을 확장합니다.",
        "upper": "5~6학년은 역할과 상황이 바뀌어도 질문을 만들고 근거·경험을 붙여 말합니다.",
        "task": "같은 핵심 표현을 집·학교·가게의 세 장면에서 사용하고 상대의 후속 질문에 한 문장을 덧붙입니다.",
        "parent": "틀린 발음을 대화 중 모두 고치지 않고 의미 전달을 마친 뒤 학생이 스스로 다시 말할 한 부분만 고릅니다.",
    },
    "writing": {
        "material": "학생이 처음 쓴 문장, 아이디어 그림, 문장 틀과 두 차례의 수정본",
        "signal": "베껴 쓰기에서 벗어나 목적에 맞는 내용·어순·연결어를 선택하고 수정 이유를 말하는지",
        "action": "말하거나 그림으로 정리한 내용을 문장 틀에 넣고 주어·동사·세부 정보·마침표를 순서대로 확인합니다.",
        "transfer": "받는 사람과 글의 목적이 달라졌을 때 어휘, 인사말, 문장 길이와 연결 방식을 바꿉니다.",
        "check": "소리 내어 읽기와 역번역 대신 누가 무엇을 말하려는지, 빠진 정보가 없는지, 문장이 이어지는지 검토합니다.",
        "lower": "1~2학년은 그림에 알맞은 단어와 짧은 문장을 따라 쓰고 한 낱말을 자신의 말로 바꿉니다.",
        "middle": "3~4학년은 문장 틀을 이용해 경험·그림 묘사·짧은 메시지를 두세 문장으로 완성합니다.",
        "upper": "5~6학년은 아이디어 순서, 접속어, 문법, 독자를 고려해 일기·편지·요약문을 수정합니다.",
        "task": "그림 한 장을 보고 초안을 세 문장으로 쓴 뒤 정보 추가·어순 수정·연결어 확인을 서로 다른 색으로 표시합니다.",
        "parent": "철자 오류를 먼저 모두 고치지 않고 아이가 전달하려는 내용과 문장 순서를 말하게 한 뒤 한 종류의 오류만 수정합니다.",
    },
    "routine": {
        "material": "학교 영어 공책, 일주일 복습표, 첫 시도와 며칠 뒤 재사용이 남은 기록",
        "signal": "공부 시간과 단어 수보다 시작 행동, 멈춘 이유, 도움 뒤 다시 사용한 표현이 남는지",
        "action": "활동을 소리 회상·어휘 재사용·짧은 읽기·한 문장 출력으로 나누고 시작과 종료 기준을 적습니다.",
        "transfer": "교재와 학교 일정이 바뀌어도 같은 표현을 듣기·말하기·읽기·쓰기에서 다시 사용합니다.",
        "check": "맞힌 문제도 설명하지 못했거나 오래 걸리면 날짜를 정해 답과 대본 없이 다시 시작합니다.",
        "lower": "1~2학년은 5~10분의 소리·그림·짧은 말하기를 예측 가능한 순서로 반복합니다.",
        "middle": "3~4학년은 학교 표현을 소리·단어·문장·짧은 글에서 여러 날 다시 만납니다.",
        "upper": "5~6학년은 어휘·문법·독해·쓰기를 과제 목적별로 나누고 중학교 영어의 독립 복습을 준비합니다.",
        "task": "지난 일주일 기록에서 혼자 시작한 활동과 도움 뒤 끝낸 활동을 구분해 다음 주 첫 과제와 재확인 날짜를 정합니다.",
        "parent": "공부한 시간보다 아이가 먼저 고른 활동, 멈춘 이유, 다음 날 다시 사용한 표현을 구체적으로 묻습니다.",
    },
}


def _parts(slug: str) -> tuple[str, str, str]:
    location = slug.removesuffix("초등영어과외")
    city = next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix))
    return location, city, location.removeprefix(city)


def build_local_elementary_english_meta(slug: str, body: str) -> tuple[str, str]:
    focus = _focus_from_body(body)
    location, _, _ = _parts(slug)
    title = _pick(
        (
            f"{slug} | {_obj(focus)} 학년별로 연결하는 법",
            f"{slug} | {_obj(focus)} 듣고 읽고 사용하는 학습",
            f"{slug} | {_with(focus)} 영어 네 기능 설계",
            f"{slug} | {_obj(focus)} 진단하고 복습하는 기준",
            f"{slug} | {_obj(focus)} 가정학습에 옮기기",
        ),
        slug,
        "meta-title",
    )
    description = _pick(
        (
            f"{slug}에서 {_obj(focus)} 1~6학년 단계로 확인합니다. {location} 학교 정보, 영어 네 기능 진단, 일주일 재사용과 학부모 질문 기준을 구체적으로 정리했습니다.",
            f"{location} 초등학생의 {_with(focus)} 영어 학습을 실제 언어 사용 기록으로 살펴봅니다. 학년군별 시작점, 2025년 학교 자료, 듣기·말하기·읽기·쓰기 복습 순서를 안내합니다.",
            f"{slug} 검색 뒤 점검할 {_obj(focus)} 구체화했습니다. 대표 관찰 활동, 학교 공식 정보, 오류 분류, 간격을 둔 재사용과 부모의 확인 질문을 한 페이지에 담았습니다.",
        ),
        slug,
        "meta-description",
    )
    return title, description


def _opening(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}초등영어과외에서 {_obj(focus)} 확인하는 첫 장면",
            f"정답보다 언어 사용을 먼저 보는 {location} 학생의 {focus}",
            f"{location} 초등영어, {_obj(focus)} 학년별 행동으로 나누기",
            f"{focus}에서 출발하는 {location} 영어 학습 기록",
            f"{location}의 {_obj(focus)} 듣고 읽고 말하고 쓰는 과정으로 보기",
            f"첫 시도로 읽는 {location} 학생의 {focus}",
        ),
        slug,
        "opening-heading",
    )
    paragraph = _pick(
        (
            f"{location}이라는 지역명만으로 학생의 학교 영어 진도나 실력을 판단할 수는 없습니다. 이 페이지는 {_obj(focus)} 고유한 점검 주제로 삼아 {pack['material']}에서 처음 사용한 단서, 도움 뒤 수정, 며칠 뒤 재사용을 비교하는 교육 정보를 제공합니다.",
            f"{_topic(focus)} 영어 문제를 많이 맞히는 것만으로 확인하기 어렵습니다. {location} 학생이 {pack['signal']}를 듣기·말하기·읽기·쓰기 기록에서 보여 주는지 살피고 확인된 한 가지 공백부터 학교 학습과 집 복습에 다시 연결합니다.",
            f"같은 학년과 교재를 사용해도 {location} 학생마다 영어에서 멈추는 위치는 다릅니다. {_obj(focus)} 볼 때는 정답률보다 어떤 소리와 문장 단서를 사용했는지, 어디서 도움을 구했는지, 다음 날 같은 표현을 스스로 꺼냈는지를 함께 봅니다.",
            f"이 페이지는 {location}의 모든 초등학생에게 같은 영어 계획을 권하지 않습니다. {_obj(focus)} 중심으로 저학년의 소리와 표현, 중학년의 문장 연결, 고학년의 독해·출력·자기점검을 나누어 현재 행동에서 다음 활동을 정합니다.",
        ),
        slug,
        "opening-paragraph",
    )
    return (
        f'<section class="elementary-english-block elementary-english-opening" data-content-marker="{CONTENT_MARKER}" '
        f'data-content-version="{CONTENT_VERSION}" data-elementary-english-focus="{escape(focus)}">'
        f"<h2>{escape(heading)}</h2><p>{escape(paragraph)}</p></section>"
    )


def _search_intent(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}에서 {_obj(focus)} 찾을 때 구분할 영어 학습 목적",
            f"{location}초등영어과외 검색을 실제 {focus} 진단으로 바꾸기",
            f"학교 복습·기초 보완·중학교 준비에서 달라지는 {location}의 {focus}",
            f"{location} 학생에게 필요한 {focus} 자료부터 정하기",
        ),
        slug,
        "search-heading",
    )
    intro = _pick(
        (
            f"{location}초등영어과외를 찾는 목적이 학교 복습인지, 소리·어휘 기초 보완인지, 중학교 준비인지에 따라 {_obj(focus)} 점검하는 자료와 종료 기준이 달라집니다. 출발 자료는 {pack['material']}이며 지역명만으로 학교별 교재나 영어 수준을 추정하지 않습니다.",
            f"검색어는 같아도 {location} 학생이 필요한 영어 도움은 서로 다릅니다. {_obj(focus)} 활동 분량으로 바꾸기 전에 {pack['signal']}를 첫 시도에서 확인하고 학교 진도, 학년, 집에서 가능한 듣기와 출력 시간을 함께 기록합니다.",
            f"{location}의 {_topic(focus)} 선행 단계보다 목적 구분이 먼저입니다. {pack['material']}을 놓고 수업 직후 이해, 다른 문장에서의 사용, 며칠 뒤 재현을 서로 다른 항목으로 남겨야 영어 과제의 역할이 선명해집니다.",
        ),
        slug,
        "search-intro",
    )
    rows = (
        ("학교 영어 연결", "교과서·공책·학교에서 들은 표현", "대본과 뜻을 가리고 소리와 핵심 문장을 복원합니다."),
        ("기초 공백 보완", "막힌 단어·문장과 오래 걸린 정답", pack["signal"]),
        ("중학교 준비", "새 소재의 짧은 글과 한 문장 출력", pack["transfer"]),
    )
    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(material)}</td><td>{escape(location)} {escape(focus)} 기록: {escape(check)}</td></tr>"
        for label, material, check in rows
    )
    steps = (
        "답과 대본을 보여 주기 전에 학생의 첫 듣기·읽기·말하기·쓰기를 보존합니다.",
        pack["action"],
        pack["check"],
        f"{location}의 생활 일정 안에서 이틀 이상 간격을 둔 재사용 날짜와 다음 표현을 정합니다.",
    )
    shift = _stable_index(slug, "search-steps") % 4
    steps = steps[shift:] + steps[:shift]
    items = "".join(f"<li>{escape(step)} {escape(location)}의 {escape(focus)} 점검표에 언어 사용 증거를 남깁니다.</li>" for step in steps)
    closing = _pick(
        (
            f"이 순서를 사용하면 {location}에서 {_obj(focus)} 위해 단어장이나 문제집부터 늘리지 않고 현재 혼자 가능한 영어 행동과 다음 한 단계를 구분할 수 있습니다.",
            f"{location} 학생의 {_topic(focus)} 수업 직후의 따라 하기보다 간격 뒤 재사용으로 판단합니다. 그래야 익숙한 순서와 교사의 문장이 실제 독립 사용을 가리는 일을 줄일 수 있습니다.",
            f"목적이 정해지면 {location}의 {_obj(focus)} 소리·의미·문장 이해·출력 가운데 어느 활동에 배치할지도 구체적으로 결정할 수 있습니다.",
        ),
        slug,
        "search-closing",
    )
    return (
        f'<section class="elementary-english-block elementary-english-search-intent" data-search-intent="local-elementary-english">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>학습 목적</th><th>먼저 볼 자료</th><th>확인할 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(location)} 학생의 {escape(focus)} 시작 순서는 다음 네 단계로 기록합니다.</p><ol>{items}</ol>"
        f"<p>{escape(closing)}</p></section>"
    )


def _grade_plan(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"1~6학년에서 달라지는 {location}의 {focus} 학습",
            f"{location} 학생의 {_obj(focus)} 세 학년군으로 나누는 기준",
            f"소리에서 문해와 출력으로 잇는 {location} {focus} 계획",
            f"선행 분량보다 먼저 볼 {location}의 {focus} 학년 단계",
        ),
        slug,
        "grade-heading",
    )
    rows = [
        ("1~2학년", pack["lower"], "소리·그림·짧은 표현"),
        ("3~4학년", pack["middle"], "문장 이해와 기능 연결"),
        ("5~6학년", pack["upper"], "근거 독해와 독립 출력"),
    ]
    shift = _stable_index(slug, "grade-order") % 3
    rows = rows[shift:] + rows[:shift]
    content = "".join(
        f"<h3>{escape(location)} {escape(label)}의 {escape(focus)}: {escape(key)}</h3>"
        f"<p>{escape(text)} {escape(location)} 학생에게는 익숙한 예문을 따라 하는 데서 끝내지 않고 같은 영어 단서를 다른 상황에서 알아보고 자기 말이나 글로 사용하는지까지 확인합니다.</p>"
        for label, text, key in rows
    )
    closing = _pick(
        (
            f"학년이 같아도 {location} 학생의 영어 시작점은 다릅니다. {_obj(focus)} 막는 소리·어휘·문장 공백 하나만 짧게 복원한 뒤 현재 교과서 표현에서 바로 사용하게 하면 무관한 반복을 줄일 수 있습니다.",
            f"{location}에서 {_obj(focus)} 교재 단계만으로 정하지 않습니다. 혼자 가능한 단계, 질문 뒤 가능한 단계, 다시 배울 단계를 나누면 학년별 듣기·읽기·출력의 길이와 난도를 현실적으로 조절할 수 있습니다.",
            f"저학년에게 철자 시험만 요구하거나 고학년에게 문법 용어만 반복시키지 않습니다. {location}의 {_topic(focus)} 활동 길이와 표현 방식을 바꾸되 이해한 말을 다시 사용하는 기준은 이어 갑니다.",
        ),
        slug,
        "grade-closing",
    )
    return f'<section class="elementary-english-block elementary-english-grade" data-grade-bands="1-2,3-4,5-6"><h2>{escape(heading)}</h2>{content}<p>{escape(closing)}</p></section>'


def _four_skills(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}의 {_obj(focus)} 듣기·말하기·읽기·쓰기로 연결하기",
            f"한 표현을 여러 기능에서 사용하는 {location} {focus} 영어 흐름",
            f"{location} 학생의 {_obj(focus)} 입력에서 출력으로 옮기기",
            f"기능을 따로 떼지 않는 {location}의 {focus} 학습",
        ),
        slug,
        "skills-heading",
    )
    rows = [
        ("듣기", "전체 상황과 핵심 소리 단서를 먼저 고릅니다.", "들은 내용을 그림이나 한 문장 메모로 남깁니다."),
        ("말하기", "들은 표현을 따라 한 뒤 장소·상대·목적을 바꿉니다.", "완벽한 발음보다 의미 전달과 스스로 고친 부분을 봅니다."),
        ("읽기", "같은 표현을 짧은 글에서 찾아 앞뒤 문맥과 연결합니다.", "답의 근거가 된 단어와 문장을 표시하고 한 줄로 요약합니다."),
        ("쓰기", "말한 내용을 자신의 문장 한두 줄로 바꿉니다.", "내용·어순·철자 가운데 한 항목씩 나눠 수정합니다."),
    ]
    shift = _stable_index(slug, "skills-order") % 4
    rows = rows[shift:] + rows[:shift]
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)}의 {escape(label)} 활동</h3>"
        f"<p>{escape(action)} {escape(check)} {escape(location)} 학생의 {escape(focus)} 기록에는 다음 기능으로 옮길 때 유지한 표현과 달라진 표현을 함께 적습니다.</p>"
        for index, (label, action, check) in enumerate(rows, 1)
    )
    closing = _pick(
        (
            f"네 기능을 매일 같은 비율로 할 필요는 없습니다. {location}의 {_obj(focus)} 중심으로 가장 약한 연결에 시간을 더 주되, 이해한 표현을 한 번은 말하거나 쓰게 해야 수동적인 기억에서 실제 사용으로 옮겨집니다.",
            f"{location} 학생이 {_obj(focus)} 듣기에서 이해했지만 쓰기에서 멈춘다면 처음부터 전부 반복하지 않습니다. 들은 표현을 짧게 말하고 문장 틀 한 칸을 채우는 중간 다리를 만들어 출력 부담을 조절합니다.",
            f"기능별 점수를 단순히 합치지 않습니다. {location}의 {_topic(focus)} 소리에서 의미로, 의미에서 문장으로, 문장에서 자신의 표현으로 이동하는 과정 중 어느 다리가 비었는지 보는 기준입니다.",
        ),
        slug,
        "skills-closing",
    )
    return f'<section class="elementary-english-block elementary-english-four-skills" data-skill-cycle="listening-speaking-reading-writing"><h2>{escape(heading)}</h2>{content}<p>{escape(closing)}</p></section>'


def _diagnosis(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}에서 바로 해 볼 {focus} 짧은 영어 진단",
            f"첫 시도를 지우지 않는 {location} {focus} 관찰 활동",
            f"{location} 학생의 {_obj(focus)} 짧게 점검하는 방법",
            f"이해와 사용을 함께 보는 {location} {focus} 진단",
        ),
        slug,
        "diagnosis-heading",
    )
    intro = _pick(
        (
            f"{location} 학생에게 새 교재 전체를 풀게 하기 전에 {pack['task']} 정답과 함께 시작까지 걸린 시간, 사용한 소리·그림·문장 단서, 도움 뒤 달라진 표현을 기록하면 {_topic(focus)} 어디에서 흔들리는지 볼 수 있습니다.",
            f"{location}의 {focus} 결과에 점수를 매기는 시험이 아니라 다음 영어 활동을 고르는 관찰로 사용합니다. 대표 활동은 ‘{pack['task']}’이며 첫 시도와 수정한 시도를 지우지 않고 나란히 남깁니다.",
            f"짧은 진단에서는 {location} 학생의 {_topic(focus)} 한 번의 따라 말하기나 정답만으로 판단하지 않습니다. {pack['task']} 활동 직후 설명과 이틀 뒤 재사용을 비교해 익숙함과 독립 사용을 나눕니다.",
        ),
        slug,
        "diagnosis-intro",
    )
    checks = (
        f"입력: {pack['signal']}",
        f"연결: {pack['action']}",
        f"자기점검: {pack['check']}",
        f"재사용: {pack['transfer']}",
    )
    items = "".join(f"<li>{escape(location)} {escape(focus)} — {escape(item)}</li>" for item in checks)
    closing = _pick(
        (
            f"{location}의 영어 진단 결과는 ‘잘함·못함’으로 끝내지 않습니다. {_obj(focus)} 혼자 사용 가능, 한 질문 뒤 가능, 소리나 문장 복원이 필요한 단계로 나누고 다시 볼 날짜와 표현을 정합니다.",
            f"이 기록을 사용하면 {location}에서 {_obj(focus)} 위해 단어 수나 문제를 무조건 늘리는 일을 피할 수 있습니다. 학생이 다음번에 스스로 바꿀 영어 행동 하나를 후속 활동으로 선택합니다.",
            f"{location} 학생의 {_topic(focus)} 활동 직후보다 간격 뒤 재사용이 중요합니다. 같은 그림과 문장 틀 없이 표현을 다시 선택할 수 있을 때 독립 사용에 가까워졌다고 봅니다.",
        ),
        slug,
        "diagnosis-closing",
    )
    return f'<section class="elementary-english-block elementary-english-diagnosis"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ul>{items}</ul><p>{escape(closing)}</p></section>'


def _weekly_plan(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 생활 리듬에 맞춘 {focus} 영어 주간 계획",
            f"학교 표현과 집에서의 재사용을 잇는 {location} {focus} 일정",
            f"{location} 학생의 {_obj(focus)} 평일과 주말에 나누기",
            f"분량 대신 기능을 정하는 {location} {focus} 계획표",
        ),
        slug,
        "weekly-heading",
    )
    intro = _pick(
        (
            f"{location} 안에서도 통학, 방과 후 활동, 가족 일정은 학생마다 다릅니다. {_obj(focus)} 매일 같은 분량으로 배치하기보다 피로한 날에는 소리·어휘 회상, 여유 있는 날에는 읽기와 출력, 주말에는 대본 없는 재사용을 둡니다.",
            f"{location} 학생의 {_topic(focus)} 영어 공부시간 총합보다 표현을 다시 만나는 방식이 중요합니다. 학교 학습 당일에는 핵심 표현을 복원하고 중간에는 {pack['action']} 주말에는 {pack['check']}",
            f"주간 계획에서 {location}의 {_obj(focus)} 입력·이해·연습·출력·재사용으로 나눕니다. 짧은 날에는 정확한 소리와 문장 회상을 두고 사고가 필요한 읽기와 {pack['transfer']} 과정은 여유 있는 날로 옮깁니다.",
        ),
        slug,
        "weekly-intro",
    )
    rows = (
        ("학교 학습 당일", "짧게 시작", "핵심 소리·어휘·문장을 가리고 복원"),
        ("주중 기능 연결", "집중 가능한 범위", pack["action"]),
        ("주말 재사용", "여유 있게 확인", pack["check"]),
        ("다음 주 연결", "마무리 점검", "막힌 단서와 다시 사용할 표현 하나를 학생이 직접 선택합니다."),
    )
    row_html = "".join(
        f"<tr><td>{escape(when)}</td><td>{escape(time)}</td><td>{escape(location)} {escape(focus)}: {escape(task)}</td></tr>"
        for when, time, task in rows
    )
    closing = _pick(
        (
            f"시간은 {location} 학생의 영어 경험과 집중 지속 시간에 맞춰 줄이거나 늘립니다. {_obj(focus)} 기록할 때는 페이지 수보다 시작 표현, 도움 횟수, 출력 결과, 다시 사용할 날짜가 남아야 계획을 실제로 조정할 수 있습니다.",
            f"{location}에서 {_obj(focus)} 위한 계획을 지키지 못한 날에는 밀린 단어와 문장을 다음 날 더하지 않습니다. 시작을 막은 일정과 활동 난도를 기록하고 가장 짧은 듣기나 말하기부터 다시 연결합니다.",
            f"방학에도 {location} 학생의 {focus} 학습을 새 교재 진도로만 채우지 않습니다. 학교 표현 복습과 소리·어휘 공백, 읽기, 한 문장 출력, 휴식일을 구분해 개학 뒤 유지 가능한 리듬을 남깁니다.",
        ),
        slug,
        "weekly-closing",
    )
    return (
        f'<section class="elementary-english-block elementary-english-weekly-plan"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>'
        f'<div class="table-wrap"><table><thead><tr><th>시점</th><th>권장 범위</th><th>영어 활동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<p>{escape(closing)}</p></section>"
    )


def _school_section(slug: str, location: str, focus: str) -> str:
    schools = ELEMENTARY_SCHOOL_CONTEXT.get(location, [])[:4]
    town = location.removeprefix(next(prefix for prefix in ("부산", "양산", "구미") if location.startswith(prefix)))
    heading = _pick(
        (
            f"{location} 초등학교 자료와 {focus} 계획을 함께 보는 법",
            f"주소 기준으로 확인한 {location} 초등학교 공식 정보",
            f"{location} 학교 정보를 {_with(focus)} 연결할 때의 주의점",
            f"통계로 영어 수준을 추정하지 않는 {location} {focus} 학교 자료 읽기",
        ),
        slug,
        "school-heading",
    )
    intro = (
        f"아래 학교는 한국교육개발원 교육통계의 2025년 4월 1일 학교 주소에 ‘{town}’ 표기가 있는 초등학교만 연결했습니다. "
        f"학생 수와 학급 수는 학교 선택이나 {focus} 수준을 평가하는 지표가 아니며 최신 일정과 영어 교육 안내는 각 학교 공식 홈페이지에서 다시 확인해야 합니다."
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
                f"{escape(location)}의 {escape(focus)} 영어 계획은 이 규모가 아니라 학생 개인의 학교 진도와 첫 언어 사용 기록으로 정합니다.</li>"
            )
        list_html = f"<ul>{''.join(items)}</ul>"
        closing = f"{location}에 학교가 여러 곳이어도 학교명만으로 영어 교재, 수업 속도, 숙제량을 단정하지 않습니다. {_obj(focus)} 지도할 때는 재학 학교의 실제 안내와 학생이 받은 자료를 우선하고 통계는 지역 학교 정보를 확인하는 참고 자료로만 사용합니다."
    else:
        list_html = ""
        closing = f"2025년 자료에서 주소의 읍·면·동 명칭이 {location}과 정확히 일치하는 초등학교를 확인하지 못했습니다. 가까워 보이는 다른 동의 학교를 임의로 넣지 않았으며 {_obj(focus)} 계획할 때는 학생이 실제 재학 중인 학교의 공식 안내와 수업 자료를 직접 확인합니다."
    return f'<section class="elementary-english-block elementary-english-school-context" data-school-count="{len(schools)}"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>{list_html}<p>{escape(closing)}</p></section>'


def _student_case(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    grade = _pick(("1~2학년", "3~4학년", "5~6학년"), slug, "case-grade")
    heading = _pick(
        (
            f"{location} {grade} 학생의 {focus} 변화 기록 예시",
            f"{focus} 활동을 조정한 {location} {grade} 합성 사례",
            f"단어 수를 늘리기 전에 바꾼 {location} 학생의 {focus}",
            f"{location} 집 복습에서 {_obj(focus)} 다시 설계한 과정",
        ),
        slug,
        "case-heading",
    )
    intro = f"다음은 {location} 학생 한 명의 실제 상담 기록이 아니라 반복되는 영어 학습 장면을 교육적으로 재구성한 {grade} 합성 사례입니다. {_obj(focus)} 점검할 때 진단명이나 성적 향상을 꾸며내지 않고 관찰 가능한 언어 사용과 다음 재사용만 보여 줍니다."
    rows = (
        ("첫 관찰", pack["signal"], "답·대본 전 시도와 사용한 단서를 보존"),
        ("활동 조정", pack["action"], "대표 표현 두 개에서 이해와 출력을 연결"),
        ("간격 뒤 확인", pack["transfer"], "도움 없이 다시 사용한 표현과 자기수정을 비교"),
    )
    row_html = "".join(
        f"<tr><td>{escape(stage)}</td><td>{escape(location)} {escape(grade)} {escape(focus)}: {escape(record)}</td><td>{escape(next_step)}</td></tr>"
        for stage, record, next_step in rows
    )
    steps = (
        f"{location} 학생이 처음 듣거나 읽을 때 뜻과 답을 중간에 대신하지 않습니다.",
        f"{_obj(focus)} 한 가지 영어 행동으로 줄여 같은 표현을 두 기능에서 사용합니다.",
        f"이틀 뒤 {pack['check']} 그 결과로 다음 주 표현과 활동을 정합니다.",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"이 합성 사례의 목표는 {location}에서 {_obj(focus)} 며칠 만에 완성했다는 결론이 아닙니다. 도움의 위치를 줄이고 학생이 사용한 단서와 다음 영어 행동을 더 구체적으로 말하는 변화를 확인하는 데 있습니다.",
            f"{location}의 {_topic(focus)} 단어 시험 한 번보다 수정 이유와 간격 뒤 재사용으로 봅니다. 같은 표현이 다른 화자·문장·글에서도 이어질 때 다음 난도와 교재 범위를 결정합니다.",
            f"합성 사례는 {location} 학생에게 그대로 적용할 처방이 아닙니다. {_obj(focus)} 위한 음원 길이, 읽기 분량, 출력 방식은 실제 학년, 교재, 학교 진도와 영어 불안 정도에 맞춰 다시 조정합니다.",
        ),
        slug,
        "case-closing",
    )
    return (
        f'<section class="elementary-english-block elementary-english-student-case" data-case-model="composite" data-case-grade="{grade}">'
        f"<h2>{escape(heading)}</h2><p>{escape(intro)}</p>"
        f'<div class="table-wrap"><table><thead><tr><th>단계</th><th>관찰 기록</th><th>다음 행동</th></tr></thead><tbody>{row_html}</tbody></table></div>'
        f"<ol>{items}</ol><p>{escape(closing)}</p></section>"
    )


def _error_map(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 학생의 {focus} 오류를 다섯 갈래로 기록하기",
            f"틀린 답 하나에서 분리하는 {location} {focus} 영어 신호",
            f"{location}의 {_obj(focus)} 소리·어휘·문장·이해·출력으로 점검하기",
            f"같은 영어 오류를 반복하지 않는 {location} {focus} 지도",
        ),
        slug,
        "error-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 {_obj(focus)} 다룬 활동에서 틀렸다고 해서 원인이 모두 단어 부족인 것은 아닙니다. 첫 시도를 남긴 채 소리 인식, 어휘 회상, 문장 연결, 내용 이해, 독립 출력을 따로 표시하면 같은 정답률 안에서도 후속 활동이 달라집니다.",
            f"영어 오답노트에 정답과 해석만 옮기면 {location} 학생의 {_obj(focus)} 어느 순간에 잃었는지 사라집니다. 아래 다섯 갈래는 학생을 평가하는 등급이 아니라 도움을 줄 위치와 다시 사용할 날짜를 정하기 위한 관찰 지도입니다.",
            f"{location}의 {_topic(focus)} 맞힌 문제에서도 살펴볼 수 있습니다. 지나치게 오래 걸렸거나 근거를 말하지 못했거나 부모의 첫 문장을 기다렸다면 성공으로 지우지 않고 어떤 영어 연결이 약했는지 분류합니다.",
        ),
        slug,
        "error-intro",
    )
    rows = [
        ("소리 인식", "들은 소리를 음절과 글자 묶음으로 나누고 강세를 찾는지 봅니다.", "짧은 음원을 다시 듣고 들린 부분과 추측한 부분을 다른 색으로 표시합니다."),
        ("어휘 회상", "뜻뿐 아니라 발음·형태·함께 쓰이는 말을 문맥에서 꺼내는지 봅니다.", "그림이나 우리말 뜻을 가리고 새 문장 속에서 같은 어휘를 다시 선택합니다."),
        ("문장 연결", "어순과 문법 형태가 전달하려는 의미와 맞는지 설명하는지 봅니다.", "낱말 카드를 움직여 달라진 의미를 말하고 자신의 문장 한 줄을 만듭니다."),
        ("내용 이해", "제목·중심 문장·세부 근거로 전체 흐름과 질문의 답을 찾는지 봅니다.", "답의 근거 문장을 표시하고 글 없이 핵심 내용을 한 문장으로 다시 말합니다."),
        ("독립 출력", f"도움 직후가 아니라 이틀 뒤 {pack['transfer']}", "힌트 없이 말하거나 쓴 첫 표현과 스스로 수정한 부분을 이전 기록과 비교합니다."),
    ]
    shift = _stable_index(slug, "error-order") % 5
    rows = rows[shift:] + rows[:shift]
    content = "".join(
        f"<h3>{escape(location)} {escape(focus)}의 {escape(label)} 오류</h3>"
        f"<p>{escape(observe)} {escape(location)} 학생의 {escape(focus)} 기록에는 ‘{escape(action)}’라는 다음 영어 행동과 재사용 날짜를 함께 남겨 답이나 해석 순서만 외우는 일을 피합니다.</p>"
        for index, (label, observe, action) in enumerate(rows, 1)
    )
    closing = _pick(
        (
            f"다섯 갈래가 동시에 흔들려 보여도 {location}의 {_obj(focus)} 한 주에 모두 고치려 하지 않습니다. 현재 학교 영어와 가장 직접적인 한 갈래를 먼저 바꾸고 다른 기능과 간격 뒤 재사용에서도 유지되면 다음 오류로 이동합니다.",
            f"{location} 학생의 오류 지도에는 점수 대신 증거를 씁니다. {focus} 기록에 혼자 들은 단서, 고친 문장, 읽기 근거, 다시 사용한 표현, 힌트를 줄인 횟수를 남기면 다음 학습의 이유를 함께 이해할 수 있습니다.",
            f"오류 분류가 바뀌는 것도 {location}에서 {_obj(focus)} 배우는 과정입니다. 처음에는 어휘 문제로 보였지만 소리를 들으니 해결되거나 이해는 했지만 출력하지 못했다면 새 기록에 맞춰 활동과 질문을 다시 선택합니다.",
        ),
        slug,
        "error-closing",
    )
    return f'<section class="elementary-english-block elementary-english-error-map" data-error-map="five-signals"><h2>{escape(heading)}</h2><p>{escape(intro)}</p>{content}<p>{escape(closing)}</p></section>'


def _focus_protocol(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 영어 사용 프로토콜",
            f"여섯 번의 기록으로 구분하는 {location} 학생의 {focus}",
            f"{location}에서 {_obj(focus)} 수업 전후로 확인하는 순서",
            f"한 주 동안 추적하는 {location} {focus} 언어 사용 기록",
            f"{location} 학생의 {_obj(focus)} 여섯 장의 영어 카드로 남기기",
        ),
        slug,
        "protocol-heading",
    )
    intro = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 하루의 긴 시험으로 결론 내리지 않습니다. 서로 목적이 다른 여섯 번의 짧은 기록으로 처음부터 알던 표현, 질문 뒤 가능해진 표현, 기능을 바꾸자 드러난 부분, 며칠 뒤에도 남은 사용을 구분합니다.",
            f"{_topic(focus)} 학습 직후에는 음원과 교사의 표현이 기억에 남아 실제 독립 수준보다 높게 보일 수 있습니다. {location}에서는 첫 시도·기능 전환·문맥 변형·자기수정·출력·간격 재사용을 다른 카드로 나눠 도움의 위치가 줄어드는지 살핍니다.",
            f"{location}의 {_obj(focus)} 점검하는 여섯 카드는 영어 성적표가 아닙니다. 각 카드에는 단어 수보다 사용한 단서, 멈춘 이유, 받은 힌트, 자기수정, 다음 날짜를 적어 활동을 바꾼 근거를 이해하게 합니다.",
        ),
        slug,
        "protocol-intro",
    )
    sequence_parts = (
        "소리 예측 메모",
        "그림 단서 대조",
        "핵심 어휘 표시",
        "의미 덩어리 낭독",
        "문장 순서 바꾸기",
        "질문 한 문장 만들기",
        "짧은 응답 녹음",
        "본문 근거 찾기",
        "오류 이유 설명",
        "상황을 바꿔 표현하기",
        "교사 힌트 한 단계 줄이기",
        "이틀 뒤 기억으로 복원하기",
    )
    sequence = sorted(
        sequence_parts,
        key=lambda item: _stable_index(slug, f"protocol-sequence-{item}"),
    )[:8]
    sequence_note = (
        f"{location} {focus} 활동의 이번 순서표는 {' → '.join(sequence)}로 구성합니다. "
        f"이 배열은 고정 프로그램이 아니라 {location} 학생의 {focus} 기록에서 먼저 막힌 입력과 출력에 따라 "
        "다음 수업 때 앞뒤를 바꾸는 관찰용 경로입니다."
    )
    materials = (
        "학교에서 아직 다루지 않은 짧은 예문",
        "전날 막힌 표현의 상황을 바꾼 카드",
        "뜻과 대본을 가린 25초 음원",
        "그림·소리·문장 중 한 단서를 비운 활동지",
        "질문과 대답의 순서를 바꾼 짧은 대화",
        "중심 문장을 가린 한 문단 읽기",
        "같은 어휘를 다른 뜻으로 사용한 두 문장",
        "오류 한 곳이 섞인 가상 학생의 문장",
        "결론만 제시한 역방향 영어 글쓰기",
        "두 표현 중 상황에 더 맞는 것을 고르는 카드",
        "도구 없이 기억에서 다시 말하는 교과 표현",
        "학생이 질문과 답을 직접 채우는 빈 대화",
    )
    actions = (
        "처음 90초 동안 뜻을 알려주지 않고 눈과 입의 움직임을 관찰합니다.",
        "들은 소리와 글자 묶음, 문장 뜻을 서로 다른 표시로 연결합니다.",
        "답을 가린 채 처음 사용한 영어 단서만 한 문장으로 말합니다.",
        "틀린 표현을 지우지 않고 그 앞뒤에서 달라진 말을 표시합니다.",
        "들은 문장을 그림으로, 읽은 문장을 자신의 말로 바꿉니다.",
        "학생이 힌트의 종류를 고르고 도움 뒤 혼자 말한 부분을 표시합니다.",
        "문장의 주어와 상황을 바꾼 뒤 유지되는 표현을 찾습니다.",
        "내용을 예상한 뒤 실제 듣기나 읽기와 달랐던 단서를 고릅니다.",
        "두 답변의 공통 의미와 서로 다른 어순을 색으로 나눕니다.",
        "활동이 끝난 뒤 자료를 보지 않고 핵심 표현의 순서를 복원합니다.",
        "부모가 알려준 말과 학생이 스스로 고친 말을 따로 적습니다.",
        "다음에 같은 오류를 만나면 할 첫 영어 행동을 학생이 정합니다.",
    )
    evidence = (
        "혼자 시작한 첫 표현과 말하기까지 걸린 시간",
        "질문을 요청한 정확한 단어와 질문 내용",
        "처음 선택한 뜻이나 문장을 바꾼 이유",
        "소리·철자·어순을 다시 확인한 위치",
        "뜻을 보기 전에 남긴 문맥 예상",
        "다른 기능으로 옮기며 새로 찾은 표현",
        "영어 오류를 고친 근거와 유지한 부분",
        "자료 없이 재사용한 첫 두 문장",
        "학생이 스스로 정한 활동 종료 기준",
        "다음 카드에서 줄일 힌트 한 가지",
        "맞았지만 오래 걸린 단서의 원인",
        "새 상황에서도 그대로 사용한 영어 기준",
    )
    stages = ("첫 입력", "기능 전환", "문맥 변형", "오류 설명", "독립 출력", "간격 재사용")
    content: list[str] = []
    for index, stage in enumerate(stages):
        duration = 9 + _stable_index(slug, f"protocol-duration-{index}") % 14
        gap = 1 + _stable_index(slug, f"protocol-gap-{index}") % 4
        material = _pick(materials, slug, f"protocol-material-{index}")
        action = _pick(actions, slug, f"protocol-action-{index}")
        record = _pick(evidence, slug, f"protocol-evidence-{index}")
        content.append(
            f"<h3>{escape(location)} {escape(focus)} {escape(stage)} 카드</h3>"
            f"<p>{escape(_obj(material))} 사용해 학생이 집중할 수 있는 짧은 시간 동안 {escape(action)} {escape(location)}의 {escape(focus)} 카드에는 {escape(_obj(record))} 남기고, "
            f"간격을 둔 뒤 같은 자료 없이 다시 사용할 표현과 부모가 줄일 힌트를 정합니다. 이 카드의 목적은 {escape(focus)} 정답 수가 아니라 {escape(location)} 학생이 영어 단서를 다시 선택하는지 확인하는 것입니다.</p>"
        )
    closing = _pick(
        (
            f"여섯 카드가 끝나면 {location} 학생의 {_obj(focus)} 단어 수나 점수로 합산하지 않습니다. 혼자 시작한 카드, 기능을 바꾼 카드, 새 문맥에서 사용한 카드, 자기수정과 간격 재사용 카드를 나눠 가장 약한 연결 하나만 다음 주 첫 활동으로 옮깁니다.",
            f"{location}의 {_topic(focus)} 여섯 번 모두 완벽해야 다음 단계로 가는 것이 아닙니다. 학생이 도움을 요청할 위치를 구체적으로 말하고 같은 힌트를 반복해 기다리지 않으며 자신의 표현을 한 번 수정하면 난도와 길이를 조금씩 넓힐 수 있습니다.",
            f"이 프로토콜은 {location} 학생의 학년과 영어 불안에 맞춰 시간을 줄여도 됩니다. {_obj(focus)} 확인하는 핵심은 카드 수가 아니라 첫 기록을 보존하고 서로 다른 기능과 상황에서 같은 표현을 다시 사용하는지 비교하는 데 있습니다.",
            f"{location}에서 {_obj(focus)} 위한 여섯 카드 중 하나를 빠뜨렸다면 밀린 활동처럼 몰아서 하지 않습니다. 학교 영어와 연결되는 카드를 우선하고 나머지는 다음 주에 배치해 독립 재사용을 관찰할 간격을 확보합니다.",
        ),
        slug,
        "protocol-closing",
    )
    return f'<section class="elementary-english-block elementary-english-focus-protocol" data-protocol-cards="6"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><p class="elementary-english-sequence">{escape(sequence_note)}</p>{"".join(content)}<p>{escape(closing)}</p></section>'


def _parent_coaching(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} 가정에서 {focus} 영어를 끌어내는 질문",
            f"정답과 해석을 대신하지 않는 {location} {focus} 대화",
            f"{location} 학생의 {_obj(focus)} 관찰 가능한 행동으로 묻기",
            f"칭찬과 영어 도움의 위치를 정하는 {location} {focus} 기준",
        ),
        slug,
        "parent-heading",
    )
    intro = _pick(
        (
            f"{location} 가정에서 {_obj(focus)} 도울 때 ‘외웠니’나 ‘다시 읽어’처럼 넓은 말은 다음 영어 행동을 알려 주지 못합니다. {pack['parent']} 학생이 답하면 부모는 완벽한 문장보다 사용한 소리·그림·문맥 단서를 다시 짚습니다.",
            f"학부모가 {_obj(focus)} 모두 말하거나 해석하면 {location} 학생의 독립 사용 수준을 보기 어렵습니다. {pack['parent']} 질문 하나 뒤에는 학생이 듣기·말하기·읽기·쓰기 중 다음 표현 방식을 선택할 시간을 둡니다.",
            f"{location}의 {_topic(focus)} 숙제 완료 여부만으로 확인하지 않습니다. {pack['parent']} 도움 뒤에는 어느 표현부터 혼자 이어 갔는지와 다음 날 같은 말을 다시 사용할 수 있는지 기록합니다.",
        ),
        slug,
        "parent-intro",
    )
    questions = (
        "처음 들리거나 읽힌 영어 단서는 무엇이었나요?",
        "그 단어와 문장을 선택한 장면과 이유를 말할 수 있나요?",
        "막힌 부분 바로 앞까지 이해한 내용은 무엇인가요?",
        "답과 표현이 자연스러운지 어떤 방법으로 확인할 수 있나요?",
        f"{focus}의 기준을 다른 화자나 글에서도 사용할 수 있나요?",
    )
    shift = _stable_index(slug, "parent-order") % 5
    questions = questions[shift:] + questions[:shift]
    items = "".join(f"<li>{escape(location)} {escape(focus)} 질문: {escape(question)}</li>" for question in questions)
    closing = _pick(
        (
            f"질문은 {location} 학생의 모든 영어 문장에 사용하지 않습니다. {focus} 관련 대표 표현 두세 개에서만 깊게 설명하게 하고 나머지는 학생이 같은 단서로 혼자 듣거나 읽고 말하거나 쓰도록 기다립니다.",
            f"칭찬도 ‘영어를 잘한다’보다 {location} 학생이 {_obj(focus)} 위해 소리를 다시 들은 행동, 근거 문장을 찾은 행동, 자신의 문장을 고친 행동처럼 반복 가능한 장면에 붙입니다.",
            f"{location} 가정에서 {_obj(focus)} 묻는 대화가 길어지면 학생이 부모의 영어를 기다릴 수 있습니다. 질문 하나, 생각 시간, 학생의 표현, 짧은 확인 순서로 끝냅니다.",
        ),
        slug,
        "parent-closing",
    )
    return f'<section class="elementary-english-block elementary-english-parent"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ul>{items}</ul><p>{escape(closing)}</p></section>'


def _transfer(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location}에서 {focus} 영어 학습이 끝났다고 보는 기준",
            f"익숙한 문장 정답 뒤에 확인할 {location} {focus} 전이",
            f"{location} 학생의 {_obj(focus)} 새 상황으로 옮기는 세 단계",
            f"도움 직후가 아닌 다음 날 보는 {location}의 {focus}",
        ),
        slug,
        "transfer-heading",
    )
    intro = _pick(
        (
            f"{location} 학생이 익숙한 활동을 맞힌 것만으로 {_subject(focus)} 자리 잡았다고 판단하지 않습니다. 기능을 바꾸고, 문맥과 화자를 바꾸고, 시간을 둔 뒤 다시 사용하는 세 단계에서 같은 영어 단서를 꺼내는지 확인합니다.",
            f"{_obj(focus)} 설명할 수 있어도 {location} 학생이 새 문장과 상황에서 시작하지 못하면 전이 활동이 필요합니다. {pack['transfer']} 이때 힌트는 답이 아니라 첫 단서를 떠올릴 최소한의 질문으로 제한합니다.",
            f"{location}의 {_topic(focus)} 학습 당일보다 이틀 뒤 기록이 중요합니다. {pack['check']} 학생이 수정 이유까지 말하면 다음 기능과 글로 연결하고 설명이 사라지면 같은 대표 표현으로 되돌아갑니다.",
        ),
        slug,
        "transfer-intro",
    )
    steps = (
        f"기능 전이: {location}의 {focus} 표현을 듣기·말하기·읽기·쓰기 중 다른 방식으로 바꿉니다.",
        f"문맥 전이: {pack['transfer']}",
        f"시간 전이: 이틀 이상 뒤에 {pack['check']}",
    )
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    closing = _pick(
        (
            f"세 단계가 모두 가능할 때 {location} 학생의 {focus} 학습을 다음 길이와 난도로 넓힙니다. 하나가 흔들리면 단어와 문제를 추가하기보다 해당 전이만 짧게 다시 설계합니다.",
            f"{location}의 {focus} 학습에서 완벽한 발음과 문법으로 말하는 것만이 목표는 아닙니다. 학생의 학년에 맞는 표현으로 의미와 근거를 남기고 새 상황에서 첫 영어 행동을 스스로 고르면 다음 단계로 볼 수 있습니다.",
            f"전이 기록은 {location} 학생을 비교하는 점수가 아닙니다. {_obj(focus)} 어떤 기능과 상황에서 유지하고 어디에서 잃는지 찾아 다음 주 활동을 더 정확하게 고르는 자료입니다.",
        ),
        slug,
        "transfer-closing",
    )
    return f'<section class="elementary-english-block elementary-english-transfer"><h2>{escape(heading)}</h2><p>{escape(intro)}</p><ol>{items}</ol><p>{escape(closing)}</p></section>'


def _context_links(slug: str, location: str, city: str, focus: str) -> str:
    links = (
        (f"/{city}초등영어과외/", f"{city} 초등영어 학년별 학습 기준"),
        (f"/{location}영어과외/", f"{location} 영어과외의 연령별 연결 구조"),
    )
    items = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for href, label in links)
    intro = f"{location}의 {_obj(focus)} 점검한 다음 필요한 상위 범위만 이어 보도록 두 페이지를 골랐습니다. 모든 영어 키워드를 링크로 만들지 않고 도시 단위 초등영어 기준과 같은 지역의 영어 학습 구조만 연결합니다."
    return f'<aside class="elementary-english-context-links" data-link-count="2"><h2>{escape(location)} {escape(focus)} 다음에 볼 영어 학습 기준</h2><p>{escape(intro)}</p><ul>{items}</ul></aside>'


def _faq(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    pairs = [
        (
            f"{location}에서 {_obj(focus)} 초등 몇 학년부터 확인해야 하나요?",
            f"{location}에서는 특정 학년부터 일괄 시작하기보다 현재 학년의 짧은 영어 활동으로 {_obj(focus)} 먼저 확인합니다. 1~2학년은 소리·그림·짧은 표현, 3~4학년은 문장 이해와 기능 연결, 5~6학년은 근거 독해와 독립 출력을 사용하며 학생이 혼자 가능한 단계에서 활동 길이를 정합니다.",
        ),
        (
            f"{location}초등영어과외를 찾기 전에 {_obj(focus)} 집에서 어떻게 진단하나요?",
            f"{location} 가정에서는 {pack['task']} 활동을 12분 안에 진행하고 첫 시도를 지우지 않습니다. {_obj(focus)} 정답으로만 판단하지 말고 사용한 소리·그림·문장 단서, 막힌 위치, 질문 뒤 달라진 표현을 적은 다음 이틀 뒤 같은 자료 없이 다시 사용하게 합니다.",
        ),
        (
            f"{location} 학생의 {_subject(focus)} 흔들리면 단어 암기부터 늘려야 하나요?",
            f"{location} 학생의 {_subject(focus)} 약하다고 단어 수부터 늘리면 실제 공백을 가릴 수 있습니다. {pack['signal']}를 살핀 뒤 소리 인식, 어휘 회상, 문장 연결, 내용 이해, 독립 출력 가운데 막힌 한 지점을 고르고 그 행동과 연결된 짧은 활동을 먼저 반복합니다.",
        ),
        (
            f"{location} 집 복습에서 {_obj(focus)} 부모가 어디까지 도와야 하나요?",
            f"{location}에서 부모는 {_obj(focus)} 뜻이나 영어 문장으로 대신하지 않습니다. {pack['parent']} 질문 하나를 한 뒤 학생이 듣기·말하기·읽기·쓰기 중 표현 방식을 고르게 하고 도움을 준 지점과 이후 혼자 이어 간 영어를 구분해 다음 재사용에서 힌트를 줄입니다.",
        ),
        (
            f"{location}에서 {_obj(focus)} 학교 진도와 선행 학습에 어떻게 나누나요?",
            f"{location}의 학교 학습 당일에는 {_obj(focus)} 교과서 소리와 문장으로 복원하고 주중에는 {pack['action']} 선행은 현재 학년 표현을 다른 기능과 상황에서 혼자 사용하고 며칠 뒤에도 재현한 다음 한 단계씩 넓히며 학교별 진도는 실제 안내 자료로 확인합니다.",
        ),
    ]
    shift = _stable_index(slug, "faq-order") % 5
    pairs = pairs[shift:] + pairs[:shift]
    content = "".join(f"<h3>{escape(question)}</h3><p>{escape(answer)}</p>" for question, answer in pairs)
    heading = _pick(
        (
            f"{location} {focus} 초등영어 학습에 자주 묻는 질문",
            f"{location}초등영어과외와 {focus} 자주 묻는 질문 정리",
            f"학년·단어·선행으로 나눈 {location} {focus} FAQ",
        ),
        slug,
        "faq-heading",
    )
    return f'<section class="elementary-english-block elementary-english-faq"><h2 class="elementary-english-faq" data-faq-focus="{escape(focus)}">{escape(heading)}</h2>{content}</section>'


def _closing(slug: str, location: str, focus: str, pack: dict[str, str]) -> str:
    heading = _pick(
        (
            f"{location} {focus} 영어 학습의 다음 한 단계",
            f"{location} 학생이 혼자 사용할 때까지 남길 {focus} 기록",
            f"새 교재보다 먼저 정할 {location}의 {focus} 재사용",
            f"{location}초등영어과외 정보를 실제 {focus} 행동으로 옮기기",
        ),
        slug,
        "closing-heading",
    )
    paragraph = _pick(
        (
            f"{location} 학생의 {_obj(focus)} 돕는 핵심은 단어와 문제집 분량을 일괄적으로 늘리는 데 있지 않습니다. {pack['action']} 그리고 정한 날짜에 {pack['check']} 이 기록이 쌓이면 학생은 새로운 영어에서도 필요한 단서와 표현을 자기 힘으로 고를 수 있습니다.",
            f"이 페이지의 {location} 학교 정보와 {focus} 학습 계획은 상담이나 성취를 보장하는 문구가 아닙니다. 학생의 실제 교재와 첫 언어 사용, 학교 안내, 간격 뒤 재사용을 함께 확인하고 가장 작은 다음 영어 행동부터 조정하는 교육용 기준입니다.",
            f"{location}에서 {_obj(focus)} 오래 유지하려면 시험 직후의 정답만 남기지 않습니다. 학생이 들은 소리, 뜻을 추론한 근거, 자신의 문장을 고친 이유, 다시 사용할 날짜를 기록해 다음 학년과 글에서도 같은 영어 단서를 꺼내 쓰게 합니다.",
        ),
        slug,
        "closing-paragraph",
    )
    evidence_open = _pick(
        (
            f"{location}의 {focus} 점검을 마칠 때는 {pack['material']}에서 처음 남긴 표현과 {pack['signal']}를 함께 보관합니다.",
            f"{location} 학생의 {focus} 기록은 도움 전에 시도한 흔적과 수정 뒤 달라진 표현을 나란히 둘 때 의미가 있습니다. 진단 과제는 {pack['task']}",
            f"{location}에서 {focus} 학습을 정리할 때는 {pack['check']} 그 차이가 학생의 말과 공책에 남는지 먼저 봅니다.",
            f"{location}의 학교 영어와 {focus} 활동을 연결하려면 {pack['signal']}를 관찰 기준으로 두고 첫 반응과 도움 뒤 사용을 구분합니다.",
            f"{location} 학생에게 새 교재를 더하기 전에는 {pack['material']}에서 스스로 고른 단서와 마지막으로 설명한 표현을 보존합니다.",
            f"{location}의 {focus} 자료를 검토할 때는 전이 행동이 나타난 장면과 다시 질문이 필요했던 장면을 별도로 적습니다. 확인할 전이 행동은 다음과 같습니다. {pack['transfer']}",
        ),
        slug,
        "closing-evidence-open",
    )
    evidence_home = _pick(
        (
            f"가정에서는 {pack['parent']} 학교 영어와 나란히 놓고 소리·뜻·문장·읽기 중 어떤 연결이 도움 없이 유지됐는지 학생의 말로 확인합니다.",
            f"보호자는 {pack['parent']} 정답을 대신 말하지 않고 학생이 사용한 영어 단서와 바꾼 이유를 먼저 듣습니다.",
            f"집에서는 {pack['action']} 어느 단계까지 혼자 이어 갔는지와 질문 뒤 달라진 표현을 짧게 기록합니다.",
            f"가정 점검은 외운 단어 수보다 {pack['signal']}를 학생이 다른 문장에서도 보여 주는지 확인하는 데 둡니다.",
            f"보호자와 볼 때는 {pack['check']} 성공한 장면만 남기지 말고 막힌 위치와 요청한 도움도 함께 적습니다.",
            f"집 공부에서는 {pack['transfer']}에 필요한 단서를 학생이 스스로 고르게 하고 선택 이유를 한 문장으로 남깁니다.",
        ),
        slug,
        "closing-evidence-home",
    )
    evidence_next = _pick(
        (
            "다음 확인에서는 같은 문장을 외웠는지보다 어휘나 문장 조건이 달라져도 알맞은 단서와 표현을 스스로 고르는지 살핍니다.",
            "후속 점검에서는 정답 수보다 처음 사용한 표현, 질문 시점, 수정 이유, 도움 없이 마친 범위가 어떻게 달라졌는지 비교합니다.",
            "시간을 둔 재사용에서는 예문을 기억하는지보다 새 장면에서 필요한 영어 표현을 자기 힘으로 구성하는지 확인합니다.",
            "학교 자료가 바뀐 뒤에도 소리와 뜻을 연결하고 문장 안 역할을 설명할 수 있는지 살펴 익숙한 답과 구분합니다.",
            "듣기·말하기·읽기·쓰기의 결과를 한 점수로 합치지 않고 각 기능에서 유지된 단서와 다시 필요한 도움을 나누어 봅니다.",
            "근거가 부족하면 학습량을 늘리기 전에 자료의 길이, 질문 순서, 간격 뒤 재사용 방법부터 조정합니다.",
        ),
        slug,
        "closing-evidence-next",
    )
    evidence_note = f"{evidence_open} {evidence_home} {evidence_next}"
    transfer_note = _pick(
        (
            f"{location} 학생은 {focus} 기록에서 혼자 시작한 범위, 질문이 필요했던 위치, 수정 뒤 다시 사용한 표현이 이어질 때 과제의 길이를 넓힙니다.",
            f"{location}의 {focus} 활동은 첫 반응·근거 설명·간격 뒤 재사용이 모두 남을 때 다음 난도로 옮기고, 비어 있는 단계가 있으면 학교 자료 안에서 다시 확인합니다.",
            f"{location} 학생에게 새 영어 자료를 추가하는 기준은 {focus} 정답률이 아니라 도움 없이 단서를 찾고 자신의 표현으로 바꾼 기록입니다.",
            f"{location}에서는 {focus} 학습의 소리·뜻·문장·글 연결 중 약한 한 지점만 고쳐 본 뒤 같은 기준을 다른 자료에 적용합니다.",
            f"{location} 가정의 다음 영어 과제는 {focus} 기록에서 학생이 유지한 행동은 남기고, 반복해서 막힌 연결만 더 짧게 나누어 정합니다.",
            f"{location} 학생의 {focus} 계획은 익숙한 예문과 낯선 자료에서 같은 단서를 꺼내 쓴 증거가 생길 때 한 단계씩 확장합니다.",
        ),
        slug,
        "closing-transfer-note",
    )
    specific_note = {
        "부산화명동초등영어과외": (
            "부산화명동 페이지의 의미 덩어리 읽기 점검은 한 문장을 단어별로 해석하는 데서 끝내지 않습니다. 학생이 제목과 그림으로 예상한 내용, "
            "접속어 앞뒤에서 바뀐 흐름, 대명사가 가리키는 대상, 중심 문장을 뒷받침한 세부 근거를 서로 다른 표시로 남깁니다. 처음 읽을 때 고른 근거와 "
            "설명 뒤 수정한 근거를 지우지 않고 나란히 두면, 어휘 부족인지 문장 연결 실패인지도 구분하기 쉽습니다. 학교별 진도와 과제는 이 페이지가 대신 "
            "추정하지 않으므로 학생이 받은 교과서·학습지·평가 안내와 연결된 학교 공식 홈페이지를 먼저 대조합니다. 이후에는 같은 글을 반복 암기하기보다 소재와 "
            "문단 순서가 달라진 짧은 글에서 중심 생각을 다시 찾고, 답을 결정한 문장을 학생의 말로 설명하게 합니다. 가정에서는 모르는 단어를 즉시 알려 주기보다 "
            "앞뒤 문장으로 뜻을 추론한 흔적과 질문이 필요했던 위치를 보존해 다음 수업의 출발 자료로 사용합니다."
        ),
    }.get(slug, "")
    specific_html = f"<p>{escape(specific_note)}</p>" if specific_note else ""
    return f'<section class="elementary-english-block elementary-english-closing"><h2>{escape(heading)}</h2><p>{escape(paragraph)}</p><p>{escape(evidence_note)}</p><p>{escape(transfer_note)}</p>{specific_html}</section>'


def _individualize_diction(body: str, slug: str) -> str:
    focus = _focus_from_body(body)
    escaped_focus = escape(focus)
    placeholder = "EDUNEXT_ELEMENTARY_ENGLISH_FOCUS_PLACEHOLDER"
    body = body.replace(escaped_focus, placeholder)
    variants: dict[str, tuple[str, ...]] = {
        "첫 시도를": ("처음 남긴 시도를", "도움 전 시도를", "초기 영어 기록을", "첫 번째 사용을", "시작 표현을", "최초 반응을"),
        "첫 시도로": ("처음 남긴 시도로", "도움 전 시도로", "초기 영어 기록으로", "첫 번째 사용으로", "시작 표현으로", "최초 반응으로"),
        "첫 시도와": ("처음 남긴 시도와", "도움 전 시도와", "초기 영어 기록과", "첫 번째 사용과", "시작 표현과", "최초 반응과"),
        "단어 수를": ("어휘 개수를", "외운 낱말 수를", "학습 어휘량을", "단어 분량을", "기억한 어휘의 양을", "회상한 낱말 개수를"),
        "단어 수나": ("어휘 개수나", "외운 낱말 수나", "학습 어휘량이나", "단어 분량이나", "기억한 어휘의 양이나", "회상한 낱말 개수나"),
        "학교 학습과": ("교실에서 배운 내용과", "학교 영어 시간과", "정규 영어 학습과", "당일 교과 영어와", "학교 진도 활동과", "교과 시간의 영어와"),
        "첫 시도": ("처음 남긴 시도", "도움 전 시도", "초기 영어 기록", "첫 번째 사용", "시작 표현", "최초 반응"),
        "다음 영어 행동": ("후속 영어 활동", "이어 할 언어 행동", "다음번 표현 활동", "뒤이을 영어 과제", "이후의 언어 사용", "다음 학습 동작"),
        "학교 학습": ("교실에서 배운 내용", "학교 영어 시간", "정규 영어 학습", "당일 교과 영어", "학교 진도 활동", "교과 시간의 영어"),
        "집 복습": ("가정 복습", "집에서의 영어 활동", "귀가 후 영어", "가정 내 재사용", "집에서 이어 하는 학습", "생활 속 영어 복습"),
        "간격 뒤 재사용": ("시간을 둔 재사용", "며칠 뒤 표현 복원", "간격을 둔 영어 재시도", "다음 날의 독립 사용", "시간차 표현 재현", "도움 없는 후속 사용"),
        "단어 수": ("어휘 개수", "외운 낱말 수", "학습 어휘량", "단어 분량", "기억한 어휘의 양", "회상한 낱말 개수"),
        "기록합니다": ("기록으로 남깁니다", "적어 둡니다", "학습지에 남깁니다", "관찰표에 씁니다", "구체적으로 남깁니다", "별도 칸에 적습니다"),
        "확인합니다": ("점검합니다", "살펴봅니다", "대조합니다", "검토합니다", "확인해 봅니다", "점검해 봅니다"),
        "확인할": ("점검할", "살펴볼", "대조할", "판단할", "다시 볼", "기록으로 볼"),
        "확인하는": ("점검하는", "살펴보는", "대조하는", "판단하는", "다시 보는", "기록으로 읽는"),
        "설명합니다": ("말로 풀어냅니다", "근거와 함께 말합니다", "자기 말로 정리합니다", "과정을 밝혀 말합니다", "문장으로 나타냅니다", "이유까지 표현합니다"),
        "다시 연결": ("재연결", "다음 영어에 연결", "교과 표현에 재적용", "현재 활동에 이어 붙이기", "배운 표현과 연결", "후속 언어 활동에 연결"),
        "구분합니다": ("나누어 봅니다", "서로 가려냅니다", "별도로 분류합니다", "차이를 표시합니다", "다른 항목으로 봅니다", "각각 판별합니다"),
        " 정합니다": (" 결정합니다", " 선택합니다", " 구체화합니다", " 확정합니다", " 조정합니다", " 한 가지로 좁힙니다"),
    }
    for source in sorted(variants, key=len, reverse=True):
        occurrence = 0

        def replace_match(_: re.Match[str]) -> str:
            nonlocal occurrence
            replacement = _pick(variants[source], slug, f"diction-{source}-{occurrence}")
            occurrence += 1
            return replacement

        body = re.sub(re.escape(source), replace_match, body)
    return body.replace(placeholder, escaped_focus)


def build_local_elementary_english_body(slug: str, focus: str) -> str:
    location, city, _ = _parts(slug)
    pack = ENGLISH_PACKS[_kind_for_focus(focus)]
    sections = {
        "grade": _grade_plan(slug, location, focus, pack),
        "skills": _four_skills(slug, location, focus, pack),
        "diagnosis": _diagnosis(slug, location, focus, pack),
        "weekly": _weekly_plan(slug, location, focus, pack),
        "school": _school_section(slug, location, focus),
        "case": _student_case(slug, location, focus, pack),
        "error": _error_map(slug, location, focus, pack),
        "protocol": _focus_protocol(slug, location, focus, pack),
        "parent": _parent_coaching(slug, location, focus, pack),
        "transfer": _transfer(slug, location, focus, pack),
    }
    orders = (
        ("grade", "skills", "diagnosis", "protocol", "error", "weekly", "school", "case", "parent", "transfer"),
        ("diagnosis", "grade", "school", "skills", "error", "protocol", "weekly", "parent", "case", "transfer"),
        ("grade", "school", "skills", "case", "diagnosis", "protocol", "error", "weekly", "transfer", "parent"),
        ("skills", "diagnosis", "grade", "weekly", "error", "case", "protocol", "school", "parent", "transfer"),
        ("school", "grade", "diagnosis", "skills", "parent", "error", "weekly", "protocol", "case", "transfer"),
        ("grade", "skills", "weekly", "parent", "protocol", "diagnosis", "school", "error", "transfer", "case"),
    )
    order = _pick(orders, slug, "section-order")
    body = _opening(slug, location, focus, pack) + _search_intent(slug, location, focus, pack)
    body += "".join(sections[key] for key in order)
    body += _context_links(slug, location, city, focus)
    body += _faq(slug, location, focus, pack)
    body += _closing(slug, location, focus, pack)
    return _individualize_diction(body, slug)


def individualize_local_elementary_english_body(body: str, slug: str) -> str:
    if not is_local_elementary_english_slug(slug):
        return body
    return build_local_elementary_english_body(slug, _focus_from_body(body))
