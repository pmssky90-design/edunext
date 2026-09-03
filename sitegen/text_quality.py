from __future__ import annotations

import hashlib
import re
from collections import Counter
from html import escape, unescape


# These nouns are used as generated labels, evidence names, and study actions.
# Keeping the list explicit avoids treating Korean verb endings such as "읽는"
# as particles while still correcting the templating mistakes that can be
# verified mechanically.
PARTICLE_NOUNS = frozenset(
    """
    기록 복원 연결 구간 녹음 회상 계획 전환 표시 구분 색인 재구성 영작 표현
    루틴 문제 재현 점검 변형 추적 역검산 요약 어순 미니시험 복습 역산 이유
    비교법 조정 전략 검산 배분 핵심절 원인 예측 날짜 대응 삽입 압축 해석 변화
    실험 정보 코드 적용 카드 대조 불일치 재확인 단계 설명 위치 확인 수 메모
    자기점검 풀이 스케치 과제 자료 적응 자기주도학습 학습계획 근거 선택과목
    병행 분석 균형 관계 문장제 조건 활동지 방정식 활동 예시 치역 도형 꼭짓점
    행동 가지 합 불연속 평균변화율 활용 기준 귀납법 대화 정의역 판단 표본공간
    일반항 분량 모델링 증명 계산 결과 교과서 학습지 어휘 문법 구문 독해 서술형
    수행평가 오답 재시도 학년 학교자료 시간표 질문 교정 결정 비교 번역 검토
    과정 항목 연습 관리
    수직선 부호 연산 성질 대표값 중앙값 평균 이상값 나무그림 비례식 대응변
    공통인수 인수분해 일반화 점화식 그래프 함수 분산 확률 통계 문항 산출물
    """.split()
)


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _has_final(value: str) -> tuple[bool, bool]:
    for char in reversed(value.strip()):
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            final_index = code % 28
            return final_index != 0, final_index == 8
    return False, False


def _correct_known_noun_particles(text: str) -> str:
    nouns = "|".join(sorted((re.escape(item) for item in PARTICLE_NOUNS), key=len, reverse=True))
    pattern = re.compile(rf"(?P<noun>{nouns})(?P<particle>으로|로|을|를|은|는|이|가|과|와)(?=[^가-힣]|$)")

    def replace(match: re.Match[str]) -> str:
        noun = match.group("noun")
        particle = match.group("particle")
        has_final, is_rieul = _has_final(noun)
        if particle in {"을", "를"}:
            corrected = "을" if has_final else "를"
        elif particle in {"은", "는"}:
            corrected = "은" if has_final else "는"
        elif particle in {"이", "가"}:
            corrected = "이" if has_final else "가"
        elif particle in {"과", "와"}:
            corrected = "과" if has_final else "와"
        else:
            corrected = "으로" if has_final and not is_rieul else "로"
        return noun + corrected

    return pattern.sub(replace, text)


def _repair_text_node(text: str) -> str:
    text = text.replace("조학생과 합의합니다", "조정합니다")
    text = text.replace("읽음할 때", "다른 사람이 중단 없이 읽을 수 있을 때")
    text = text.replace("만남할 때", "정방향과 역방향의 결과가 일치할 때")
    text = text.replace("학습 단계으로", "구체적인 학습 단계로")
    text = text.replace("상황 이런 장면", "상황입니다. 이런 장면")
    text = re.sub(
        r"(?<![가-힣])(?P<word>[가-힣]{2,})\s+(?P=word)"
        r"(?P<particle>으로|에서|에게|부터|까지|로|을|를|은|는|이|가|과|와|의|도|만|에)?(?=[^가-힣]|$)",
        lambda match: match.group("word") + (match.group("particle") or ""),
        text,
    )
    text = re.sub(r"(학습 (?:계획|과정|기준|기록)) 학생에게", r"\1이 학생에게", text)
    text = text.replace("학습 관리 학생에게", "학습 관리가 학생에게")
    text = re.sub(r"(?<=[가-힣0-9”’)])\s+입니다(?=[.\s<]|$)", "입니다", text)
    text = re.sub(r"(?<![가-힣])((?:초|중|고)[1-6])\s+(은|는|이|가|을|를|과|와)", r"\1\2", text)
    text = re.sub(r"([가-힣]+니다) (?=[가-힣A-Z])", r"\1. ", text)
    text = _correct_known_noun_particles(text)
    return text


def _repair_visible_text(body: str) -> str:
    parts = re.split(r"(<[^>]+>)", body)
    hidden_depth = 0
    for index, part in enumerate(parts):
        if not part.startswith("<"):
            if hidden_depth == 0:
                parts[index] = _repair_text_node(part)
            continue
        tag = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
        if not tag or tag.group(1).lower() not in {"script", "style", "noscript", "svg"}:
            continue
        if part.startswith("</"):
            hidden_depth = max(0, hidden_depth - 1)
        elif not part.rstrip().endswith("/>"):
            hidden_depth += 1
    return "".join(parts)


def _deduplicate_paragraphs(body: str, slug: str) -> str:
    matches = list(re.finditer(r"(<p\b[^>]*>)(.*?)(</p>)", body, flags=re.I | re.S))
    normalized = [_plain_text(match.group(2)) for match in matches]
    repeated = {text for text, count in Counter(normalized).items() if text and len(text) >= 45 and count > 1}
    if not repeated:
        return body

    seen: Counter[str] = Counter()
    current_heading = "학습 적용"
    cursor = 0
    chunks: list[str] = []
    for match, text in zip(matches, normalized):
        between = body[cursor:match.start()]
        chunks.append(between)
        headings = list(re.finditer(r"<h[23]\b[^>]*>(.*?)</h[23]>", between, flags=re.I | re.S))
        if headings:
            current_heading = _plain_text(headings[-1].group(1)) or current_heading

        paragraph = match.group(0)
        if text in repeated:
            seen[text] += 1
            if seen[text] > 1:
                note = (
                    f" 이 내용은 {slug}의 ‘{current_heading}’ 단계에서 앞선 원칙을 학생의 실제 자료에 "
                    f"다시 적용해 보는 {seen[text]}번째 확인 기준입니다."
                )
                paragraph = f"{match.group(1)}{match.group(2)}{note}{match.group(3)}"
        chunks.append(paragraph)
        cursor = match.end()
    chunks.append(body[cursor:])
    return "".join(chunks)


def _deduplicate_headings(body: str) -> str:
    counts: Counter[str] = Counter()

    def replace(match: re.Match[str]) -> str:
        text = _plain_text(match.group(2))
        counts[text] += 1
        if not text or counts[text] == 1:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)} — 적용 확인 {counts[text]}{match.group(3)}"

    return re.sub(r"(<h[23]\b[^>]*>)(.*?)(</h[23]>)", replace, body, flags=re.I | re.S)


def _limit_primary_keyword_repetition(body: str, slug: str, keep: int = 18) -> str:
    """Vary over-repeated school search phrases without removing school context."""
    has_school_family_marker = re.search(
        r'data-(?:school-(?:general|english|math)|middle-school-(?:english|math))-focus=',
        body,
        flags=re.I,
    )
    has_middle_school_marker = 'data-school="' in body and 'data-focus="' in body
    if not has_school_family_marker and not has_middle_school_marker:
        return body

    if slug.endswith("영어과외"):
        school = slug[: -len("영어과외")]
        subject = "영어"
    elif slug.endswith("수학과외"):
        school = slug[: -len("수학과외")]
        subject = "수학"
    elif slug.endswith("과외"):
        school = slug[: -len("과외")]
        subject = "과목별"
    else:
        return body

    references = (
        f"{school} 학생의 {subject} 학습 관리",
        f"{school}에서 살펴볼 {subject} 학습 과정",
        f"{school} {subject} 과목의 맞춤 학습 계획",
        f"{school} 학생을 위한 {subject} 점검 활동",
        f"{school}의 {subject} 학습 기준",
        f"{school} 학생이 남길 {subject} 학습 기록",
    )
    protected: list[str] = []

    def protect_faq_questions(section: re.Match[str]) -> str:
        opening, inner, closing = section.groups()

        def protect_heading(heading: re.Match[str]) -> str:
            def marker(_: re.Match[str]) -> str:
                value = f"EDUNEXT_PRIMARY_KEYWORD_{len(protected):03d}"
                protected.append(value)
                return value

            return heading.group(1) + re.sub(re.escape(slug), marker, heading.group(2)) + heading.group(3)

        inner = re.sub(r"(<h3\b[^>]*>)(.*?)(</h3>)", protect_heading, inner, flags=re.I | re.S)
        return opening + inner + closing

    body = re.sub(
        r'(<section\b[^>]*class="[^"]*faq[^"]*"[^>]*>)(.*?)(</section>)',
        protect_faq_questions,
        body,
        flags=re.I | re.S,
    )
    parts = re.split(r"(<[^>]+>)", body)
    occurrence = 0
    hidden_depth = 0
    for index, part in enumerate(parts):
        if not part.startswith("<"):
            if hidden_depth:
                continue

            def replace(_: re.Match[str]) -> str:
                nonlocal occurrence
                occurrence += 1
                if occurrence <= keep:
                    return slug
                suffix = part[_.end() :]
                if re.match(r"\s+학생(?:에게|이|은|는|의|을|를|과|와)", suffix):
                    return f"{school}의 {subject} 학습이"
                following_noun = re.match(
                    r"\s+(학습|계획|기록|기준|과정|관리|활동|점검|과제|수업|진행|방식|선택|상담|비교|지도)",
                    suffix,
                )
                if following_noun:
                    if following_noun.group(1) == "학습":
                        return f"{school}의 {subject}"
                    return f"{school}의 {subject} 학습"
                return references[(occurrence - keep - 1) % len(references)]

            parts[index] = re.sub(re.escape(slug), replace, part)
            continue

        tag = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
        if not tag or tag.group(1).lower() not in {"script", "style", "noscript", "svg"}:
            continue
        if part.startswith("</"):
            hidden_depth = max(0, hidden_depth - 1)
        elif not part.rstrip().endswith("/>"):
            hidden_depth += 1
    body = "".join(parts)
    for placeholder in protected:
        body = body.replace(placeholder, slug)
    return body


LOCAL_FOCUS_LABELS = {
    "elementary-general": "초등 과목별",
    "elementary-math": "초등 수학",
    "elementary-english": "초등 영어",
    "high-general": "고등 과목별",
    "high-math": "고등 수학",
    "high-english": "고등 영어",
    "middle-math": "중등 수학",
    "middle-general": "중등 과목별",
}


def _add_local_context_note(body: str, slug: str) -> str:
    """Add a useful review note so copy repairs never reduce local-page depth."""
    if 'data-content-marker="sentence-quality-context"' in body:
        return body
    match = re.search(
        r'data-(?P<family>elementary-(?:general|math|english)|middle-general|high-(?:general|math|english))-focus="(?P<focus>[^"]+)"',
        body,
        flags=re.I,
    )
    if not match:
        middle_math = re.search(r'data-math-focus="(?P<focus>[^"]+)"', body, flags=re.I)
        if middle_math:
            family = "middle-math"
            focus = unescape(middle_math.group("focus")).strip()
        elif slug.endswith("과외") and 'data-content-version="' not in body:
            location = re.sub(r"(?:초등|중등|고등)?(?:영어|수학)?과외$", "", slug)
            return body + (
                '<p class="sentence-quality-context" data-content-marker="sentence-quality-context">'
                f"{escape(location)}의 이 안내는 반복 표현 대신 실제 교재에서 확인한 출발점과 "
                "다음 점검 행동을 중심으로 읽습니다.</p>"
            )
        else:
            return body
    else:
        family = match.group("family").lower()
        focus = unescape(match.group("focus")).strip()
    location = re.sub(r"(?:초등|중등|고등)?(?:영어|수학)?과외$", "", slug)
    label = LOCAL_FOCUS_LABELS[family]

    escaped_location = escape(location)
    escaped_focus = escape(focus)
    if family == "high-math":
        digest = hashlib.sha256(slug.encode("utf-8")).digest()
        openings = (
            f"{escaped_location} 학생의 ‘{escaped_focus}’ 항목은 해설을 보기 전 첫 풀이에서 출발합니다.",
            f"‘{escaped_focus}’ 항목을 {escaped_location} 학생에게 적용할 때는 교과서 예제를 가리고 시작합니다.",
            f"{escaped_location}의 고등 수학 기록에서는 ‘{escaped_focus}’ 항목의 첫 시도부터 남깁니다.",
            f"공식 암기량보다 {escaped_location} 학생이 ‘{escaped_focus}’ 항목을 시작한 방식을 먼저 봅니다.",
        )
        evidences = (
            f"{escaped_location}의 공책에서 조건 표시, 식 전개, 그래프 해석 가운데 멈춘 위치를 찾아 다음 질문 하나를 정합니다.",
            f"최근 {escaped_location} 학교 자료와 공책을 나란히 놓고 조건을 옮긴 순간과 계산이 달라진 줄을 구분합니다.",
            f"{escaped_location} 학생의 풀이에서는 정답 수보다 조건을 식과 그림으로 바꾼 흔적을 구체적으로 대조합니다.",
            f"교과서 단원과 최근 평가를 함께 보며 {escaped_location} 학생이 설명 없이 이어 간 계산 구간을 표시합니다.",
        )
        retries = (
            f"다음 날에는 {escaped_focus} 관련 수치와 문항 배열을 바꿔 같은 판단 순서를 다시 설명하게 합니다.",
            f"며칠 뒤 {escaped_focus} 유형의 조건 표현을 바꾸고 풀이 방향을 스스로 선택하는지 확인합니다.",
            f"재시도에서는 {escaped_focus} 문제의 답을 외웠는지가 아니라 새 조건에서도 근거를 복원하는지 봅니다.",
            f"시간을 둔 확인에서는 {escaped_focus} 예제와 다른 수치를 주고 검산 기준까지 말하게 합니다.",
        )
        closings = (
            f"이 결과를 {escaped_location}의 학교 진도와 평가 일정에 맞춰 한 주 계획으로 옮기면 종료 기준도 분명해집니다.",
            f"확인된 공백만 {escaped_location} 학습 일정에 배치하면 불필요한 반복 없이 다음 단계를 정할 수 있습니다.",
            f"{escaped_location}의 수업 범위 안에서 다시 풀 날짜와 도움을 줄일 지점을 정해 학습량을 조절합니다.",
            f"마지막에는 {escaped_location} 학생이 혼자 설명한 근거를 남겨 다음 난도로 이동할지 판단합니다.",
        )
        sentences = (
            openings[digest[0] % len(openings)],
            evidences[digest[1] % len(evidences)],
            retries[digest[2] % len(retries)],
            closings[digest[3] % len(closings)],
        )
    else:
        family_actions = {
            "elementary-general": (
                "현재 교재에서 혼자 시작한 지점과 질문 뒤 달라진 부분을 함께 표시합니다.",
                "며칠 뒤 같은 도움 없이 다시 해낸 결과로 다음 활동의 분량을 정합니다.",
            ),
            "elementary-math": (
                "공책의 첫 풀이와 다시 푼 줄을 나란히 보며 다음 확인 날짜를 정합니다.",
            ),
            "elementary-english": (
                "교과서 표현을 가린 뒤 소리·뜻·문장을 혼자 복원한 결과로 다음 활동을 정합니다.",
            ),
            "high-english": (
            ),
            "high-general": (
            ),
            "middle-math": (
            ),
            "middle-general": (
            ),
        }
        sentences = (
            f"{escaped_location}의 ‘{escaped_focus}’ 항목은 학생의 실제 자료에서 확인한 기록으로 적용 범위를 정합니다.",
            *family_actions[family],
        )
    note = (
        '<section class="sentence-quality-context" data-content-marker="sentence-quality-context">'
        f'<h2>{escaped_location} {escape(label)} 계획을 실제 자료에 적용하는 기준</h2>'
        f'<p>{" ".join(sentences)}</p></section>'
    )
    return body + note


def polish_generated_body(body: str, slug: str) -> str:
    """Apply conservative, reproducible quality fixes to generated visible copy."""
    body = _limit_primary_keyword_repetition(body, slug)
    body = _repair_visible_text(body)
    body = _deduplicate_paragraphs(body, slug)
    body = _deduplicate_headings(body)
    body = _add_local_context_note(body, slug)
    return body
