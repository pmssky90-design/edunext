from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import quote

from config import NAVER_SITE_VERIFICATION, SITE_DESCRIPTION, SITE_NAME, SITE_URL
from sitegen.models import Page
from sitegen.secondary_region_content import individualize_secondary_region_body
from sitegen.local_middle_english import (
    build_local_middle_english_meta,
    individualize_local_middle_english_body,
    is_local_middle_english_slug,
)
from sitegen.utils import escape

ROOT = Path(__file__).resolve().parents[1]
FIXED_IMAGE_MANIFEST = ROOT / "data" / "fixed_images.json"
SEARCH_THUMBNAIL_MANIFEST = ROOT / "data" / "search_thumbnails.json"

SUBJECTS = {"영어과외", "수학과외"}
GRADES = {"초등과외", "중등과외", "고등과외"}
SUBJECT_GRADES = {"초등영어과외", "중등영어과외", "고등영어과외", "초등수학과외", "중등수학과외", "고등수학과외"}
CITIES = ("부산", "구미", "양산")
SPECIAL_REGION_HUBS = {"경남과외", "경북과외"}
PRIORITY_REGION_SLUGS = {
    "구미옥계동과외",
    "부산하단동과외",
    "부산우동과외",
    "부산화명동과외",
}
PRIORITY_MATH_EXCLUSIONS = {"수학과외", "경남수학과외", "경북수학과외"}


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def is_priority_region_math_page(page: Page) -> bool:
    """Select city and smaller regional math pages, excluding grade and collection hubs."""
    return (
        page.page_type == "subject"
        and page.category == "수학과외"
        and page.slug.endswith("수학과외")
        and page.slug not in PRIORITY_MATH_EXCLUSIONS
        and not re.search(r"(초등|중등|고등)수학과외$", page.slug)
    )


def structure_priority_math_body(body: str) -> str:
    """Give regional math guides a readable H2 structure while keeping FAQ questions at H3."""
    body = body.replace("수학학습", "수학 학습")
    headings = list(re.finditer(r"<h2\b[^>]*>.*?</h2>", body, flags=re.I | re.S))
    if len(headings) < 2:
        return body
    faq_start = headings[-1].start()
    guide, faq = body[:faq_start], body[faq_start:]
    guide = re.sub(r"<h3(\b[^>]*)>", r"<h2\1>", guide, flags=re.I)
    guide = re.sub(r"</h3>", "</h2>", guide, flags=re.I)
    return guide + faq


def polish_priority_region_math_body(body: str, page: Page) -> str:
    if not is_priority_region_math_page(page):
        return body
    return structure_priority_math_body(body)


def faq_section_bounds(body: str) -> tuple[int, int, int] | None:
    """Return the FAQ heading start, section end, and heading end for a visible FAQ block."""
    headings = list(re.finditer(r"<h2\b[^>]*>(.*?)</h2>", body, flags=re.I | re.S))
    for index, heading in enumerate(headings):
        label = plain_text(heading.group(1))
        if "FAQ" not in label.upper() and not ("자주" in label and "질문" in label):
            continue
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        section = body[heading.end() : section_end]
        if len(re.findall(r"<h3\b[^>]*>.*?</h3>\s*<p\b[^>]*>.*?</p>", section, flags=re.I | re.S)) >= 2:
            return heading.start(), section_end, heading.end()
    return None


def deduplicate_faq_pairs(body: str) -> str:
    """Remove only repeated FAQ question/answer pairs with identical visible text."""
    bounds = faq_section_bounds(body)
    if not bounds:
        return body
    _, section_end, section_start = bounds
    section = body[section_start:section_end]
    seen: set[tuple[str, str]] = set()

    def keep_first(match: re.Match[str]) -> str:
        key = (plain_text(match.group(1)), plain_text(match.group(2)))
        if key in seen:
            return ""
        seen.add(key)
        return match.group(0)

    cleaned = re.sub(
        r"<h3\b[^>]*>(.*?)</h3>\s*<p\b[^>]*>(.*?)</p>",
        keep_first,
        section,
        flags=re.I | re.S,
    )
    return body[:section_start] + cleaned + body[section_end:]


SCENARIO_NOTICE = (
    "아래 내용은 실제 학생의 상담·수업 결과가 아니라, 지역 생활 흐름에 맞춘 학습 방법을 "
    "설명하기 위해 구성한 가상 시나리오입니다."
)


def individualize_priority_region_body(body: str, page: Page) -> str:
    """Replace the four highest-similarity region articles with locally structured guides."""
    if page.slug not in PRIORITY_REGION_SLUGS:
        return body

    notice = f'<strong class="scenario-notice">{escape(SCENARIO_NOTICE)}</strong>'
    articles = {
        "구미옥계동과외": f"""
<section class="priority-region-content priority-region-okgye" data-content-version="region-individual-v1">
<h2>구미옥계동과외를 찾기 전에 이름과 생활권부터 구분하세요</h2>
<p>옥계동이라는 검색어 하나만으로 학생의 학습 조건을 단정할 수는 없습니다. 구미시 공식 안내에서는 옥계동을 양포동의 법정동 가운데 하나로 소개하므로, 행정 공지나 지역 정보를 확인할 때는 <a href="https://www.gumi.go.kr/yangpo/contents.do?mid=0103000000">구미시 양포동 공식 안내</a>도 함께 보는 편이 정확합니다. 과외 계획에서는 행정명보다 학교에서 집까지 걸리는 시간, 저녁 식사 시각, 보호자가 확인할 수 있는 요일을 따로 적어야 합니다.</p>
<ol>
<li><strong>검색 범위:</strong> 옥계동 안에서 찾는지, 구미 전체까지 넓힐지 먼저 정합니다.</li>
<li><strong>생활 범위:</strong> 학교·집·학습 장소가 이어지는 실제 평일 경로를 그립니다.</li>
<li><strong>학습 범위:</strong> 영어와 수학 가운데 먼저 바꿀 한 과정을 고릅니다.</li>
</ol>

<h2>가상 학습 시나리오: 귀가 시각이 다른 날을 두 종류로 나눈 예시</h2>
<p>{notice} 한 학생이 월·수에는 비교적 일찍 귀가하고 화·목에는 일정이 늦게 끝난다고 가정해 보겠습니다. 처음에는 매일 같은 분량을 적어 두어 늦은 날마다 계획이 밀렸습니다. 이후 이른 날은 새 개념과 긴 독해, 늦은 날은 단어 회상과 수학 오답 한 문제처럼 목적을 나누었습니다. 주말에는 밀린 분량을 한꺼번에 채우지 않고, 완료하지 못한 이유를 시간 부족·이해 부족·시작 지연으로 분류했습니다. 이 예시는 실제 수업 결과가 아니라 변동 시간표를 학습 행동으로 바꾸는 방법을 보여 주기 위한 구성입니다.</p>

<h2>옥계동 학생의 한 주는 ‘두 개의 저녁표’로 설계합니다</h2>
<p>매일 똑같은 계획표보다 정상 귀가일과 늦은 귀가일을 분리한 표가 실용적입니다. 다음 네 칸만 일주일 동안 기록하면 수업 시간보다 먼저 조정할 항목이 보입니다.</p>
<table>
<thead><tr><th>기록 칸</th><th>확인할 내용</th><th>계획에 반영하는 방법</th></tr></thead>
<tbody>
<tr><td>집 도착</td><td>요일별 실제 시각</td><td>시작 가능한 시간대를 두 종류로 나눕니다.</td></tr>
<tr><td>첫 행동</td><td>식사·휴식·휴대전화 중 무엇이 먼저인지</td><td>공부 시작 신호를 한 가지로 고정합니다.</td></tr>
<tr><td>멈춘 지점</td><td>어떤 문제나 문장에서 오래 멈췄는지</td><td>다음 수업의 질문 목록으로 옮깁니다.</td></tr>
<tr><td>종료 상태</td><td>완료·부분 완료·미시작</td><td>분량이 아니라 중단 이유를 기록합니다.</td></tr>
</tbody>
</table>

<h2>초등은 시작 신호, 중등은 수정 기록을 먼저 봅니다</h2>
<p>초등 단계에서는 오래 앉아 있는 시간보다 가방을 정리하고 오늘 할 한 가지를 꺼내는 순서를 반복하는 것이 중요합니다. 보호자는 정답을 바로 알려주기보다 “어디까지 혼자 했는가”를 표시하게 해 독립적으로 시작하는 구간을 늘릴 수 있습니다.</p>
<p>중학생은 계획을 지켰는지만 확인하면 실패 기록이 쌓이기 쉽습니다. 시험일과 제출일을 달력에 옮긴 뒤, 하루가 어긋났을 때 무엇을 다음 날로 넘기고 무엇을 축소할지 학생이 직접 선택하게 해야 합니다. 영어는 틀린 문장의 근거를 다시 찾고, 수학은 풀이가 끊긴 줄을 표시하면 과목별 조정 지점도 달라집니다.</p>

<h2>고등 학습은 주간 마감 순서와 질문의 질로 점검합니다</h2>
<p>고등학생은 과목 수와 일정이 늘어나므로 “많이 공부하기”보다 마감 충돌을 먼저 풀어야 합니다. 수행평가 준비, 학교 과제, 시험 복습을 한 목록에 섞지 말고 제출 시각과 예상 소요시간을 함께 적습니다. 과외 시간에는 이미 아는 문제를 반복하기보다 혼자 해결하지 못한 개념, 풀이를 바꾼 이유, 다음 시험 전 다시 볼 오류를 설명하게 하는 편이 좋습니다.</p>
<ul>
<li>영어: 단어 수보다 문장 안에서 뜻을 회상할 수 있는지 확인합니다.</li>
<li>수학: 정답보다 첫 풀이 선택과 막힌 단계가 설명되는지 확인합니다.</li>
<li>주간 계획: 미완료 항목을 삭제하지 않고 원인과 다음 시도를 한 줄로 남깁니다.</li>
</ul>

<h2>직접 연결된 학교 페이지가 없을 때 확인하는 순서</h2>
<p>현재 옥계동 페이지에는 특정 학교를 지역 안에 있다고 임의로 연결하지 않았습니다. 먼저 <a href="/#high-schools">고등학교별 과외 목록</a>에서 실제 학교명을 찾고, 학교별 페이지에 연결된 공식 홈페이지에서 학사일정과 학교 명칭을 다시 확인하세요. 지역 전체 기준은 <a href="/구미과외/">구미과외</a>, 과목 기준은 <a href="/구미옥계동영어과외/">구미옥계동영어과외</a>와 <a href="/구미옥계동수학과외/">구미옥계동수학과외</a>로 나누면 탐색 목적이 섞이지 않습니다.</p>

<h2>2주 동안 수업보다 먼저 검증할 세 가지 가설</h2>
<p>첫 상담에서 “집중력이 부족하다”처럼 큰 결론을 내리기보다 확인 가능한 가설로 바꾸는 것이 좋습니다. 첫째, 시작이 늦는 원인이 귀가 후 회복시간인지 준비 순서인지 구분합니다. 둘째, 과제를 끝내지 못하는 원인이 분량인지 이해인지 살펴봅니다. 셋째, 설명을 들은 뒤 혼자 풀 수 있는 간격이 하루인지 이틀인지 기록합니다. 같은 문제처럼 보여도 가설에 따라 필요한 과외 방식은 달라집니다.</p>
<div class="planning-example">
<p><strong>1주 차:</strong> 기존 생활을 크게 바꾸지 않고 도착·시작·중단 시각을 기록합니다. 학생이 도움을 요청한 문장이나 문제도 그대로 남깁니다.</p>
<p><strong>2주 차:</strong> 시작 신호 하나와 최소 학습 하나만 바꿉니다. 예를 들어 가방 정리 뒤 수학 예제 한 문제를 설명하거나, 영어 본문에서 근거 문장 하나를 찾게 합니다.</p>
<p><strong>판단일:</strong> 완료량보다 시작까지 걸린 시간, 같은 오류의 재발, 질문의 구체성이 달라졌는지 비교합니다. 변화가 없다면 의지 문제로 단정하지 말고 가설을 바꿉니다.</p>
</div>

<h2>옥계동과외 선생님을 비교할 때 답을 들어야 할 질문</h2>
<p>수업 소개만 듣기보다 학생의 기록을 어떻게 해석할지 물어보세요. “늦은 귀가일의 과제를 어떻게 줄일 것인가”, “영어 독해에서 답만 틀린 경우와 근거를 못 찾은 경우를 어떻게 구분하는가”, “수학 오답을 다시 틀렸을 때 어느 풀이 단계로 돌아가는가”처럼 구체적인 질문이 좋습니다. 답변에는 학생이 해야 할 행동, 선생님이 확인할 증거, 보호자에게 전달할 주기가 함께 있어야 합니다.</p>
<p>교재 수나 숙제량이 많다는 사실만으로 적합성을 판단하기는 어렵습니다. 현재 학교 학습과 겹치는 부분, 혼자 복습할 수 있는 범위, 다음 수업까지 남길 짧은 과제가 분리되는지 확인하세요. 온라인 수업을 고려한다면 화면 공유만 가능한지보다 학생의 필기와 풀이 과정을 어떤 방식으로 확인하는지도 점검할 필요가 있습니다.</p>

<h2>옥계동에서 대면과 온라인을 결정하는 실험</h2>
<p>이동시간만으로 수업 방식을 결정하지 말고 같은 과제를 두 환경에서 한 번씩 수행해 보세요. 대면에서는 학생이 질문을 미루지 않는지, 수업 뒤 혼자 복습할 자료가 남는지를 봅니다. 온라인에서는 접속 전에 교재와 필기를 준비하는지, 화면으로 풀이 전 과정을 보여 줄 수 있는지, 연결이 끝난 뒤 과제를 스스로 찾는지를 확인합니다.</p>
<p>학생이 말로 풀이를 설명하고 자료를 스스로 정리한다면 온라인에서도 과정 확인이 가능합니다. 반대로 준비 단계에서 계속 도움이 필요하거나 필기 일부만 보여 주어 오류 위치를 찾기 어렵다면 초기에는 대면 점검이 나을 수 있습니다. 어느 방식이든 두 번의 수업 뒤 시작 준비, 질문 횟수, 수업 후 독립 복습을 같은 기준으로 비교해야 합니다.</p>

<h2>주간 피드백은 완료율이 아니라 다음 행동으로 끝냅니다</h2>
<p>옥계동 학생의 주간 기록에는 잘한 점 하나, 반복해서 막힌 점 하나, 다음 주에 시험할 행동 하나면 충분합니다. “과제를 80% 했다”에서 끝내지 말고 “늦은 화요일에는 긴 독해를 옮기고 단어를 문장으로 회상한다”처럼 다음 일정에 들어갈 문장으로 바꿉니다. 보호자는 결과를 대신 해석하기보다 학생이 선택한 변경을 일주일 뒤 다시 물어보는 역할을 맡을 수 있습니다.</p>
<p>상담 자료에는 정확한 집 주소나 불필요한 개인정보를 적지 않아도 됩니다. 학교명·학년·대략적인 귀가 시각과 학습 행동만으로 먼저 비교하고, 자료를 전달해야 할 때는 사용 목적과 보관 방법을 확인하세요. 지역을 좁히기 위한 정보와 수업 설계에 꼭 필요한 정보를 구분하면 탐색 단계에서 과도한 정보를 공유하지 않을 수 있습니다.</p>

<h2>옥계동과외 상담 전에 작성할 6줄 메모</h2>
<p>학교명과 학년, 요일별 귀가 시각, 최근 반복된 미완료 과제, 영어에서 막히는 과정, 수학에서 막히는 과정, 학생이 혼자 공부할 수 있다고 느끼는 시간을 한 줄씩 적어 보세요. 성적 전체나 정확한 주소부터 제공할 필요는 없습니다. 이 메모가 있으면 수업 횟수를 정하기 전에 생활시간 조정이 필요한지, 과목 설명이 필요한지, 과제 관리가 필요한지를 구분할 수 있습니다.</p>
</section>
""",
        "부산하단동과외": f"""
<section class="priority-region-content priority-region-hadan" data-content-version="region-individual-v1">
<h2>부산하단동과외는 하단1·2동과 학교 동선을 한 번 더 나눠 봅니다</h2>
<p>사하구 공식 자료에는 하단동이 1992년 하단1동과 하단2동으로 나뉜 이력이 나오며, <a href="https://www.saha.go.kr/hadan2/contents.do?mId=0100000000">하단2동 공식 소개</a>에는 부산여고·건국중고·하단중·동아대학교 승학캠퍼스가 함께 언급됩니다. 이 정보는 지역을 이해하는 출발점일 뿐, 모든 학생의 통학 조건이 같다는 뜻은 아닙니다. 과외를 비교할 때는 어느 행정동인지와 별개로 학교 종료 후 집에 도착하는 경로를 직접 확인해야 합니다.</p>

<h2>먼저 찾을 것은 수업 시간이 아니라 평일의 반환점입니다</h2>
<p>하교 뒤 곧바로 집으로 오는지, 다른 일정이나 식사를 거치는지에 따라 같은 저녁 90분의 쓰임이 달라집니다. 일주일 동안 ‘학교 종료 → 첫 이동 → 집 도착 → 책상에 앉은 시각’을 적고 다음 세 유형 가운데 어디에 가까운지 판단해 보세요.</p>
<dl>
<dt><strong>직행형</strong></dt><dd>귀가 시각은 일정하지만 시작이 늦다면 휴식 종료 신호부터 정합니다.</dd>
<dt><strong>경유형</strong></dt><dd>중간 일정이 있다면 이동 중 가능한 회상 과제와 집에서 할 집중 과제를 분리합니다.</dd>
<dt><strong>변동형</strong></dt><dd>요일마다 경로가 다르면 긴 과제의 배치일을 먼저 고정하고 나머지를 채웁니다.</dd>
</dl>

<h2>가상 학습 시나리오: 세 개의 마감을 한 장에서 분리한 예시</h2>
<p>{notice} 한 중학생이 학교 과제, 영어 단어 확인, 수학 오답을 모두 “오늘 공부”라고 적는 상황을 가정합니다. 처음에는 쉬운 항목부터 하다 제출이 있는 학교 과제를 늦게 발견했습니다. 계획표를 제출 마감·수업 전 준비·개인 복습의 세 줄로 나눈 뒤에는 우선순위를 정하는 질문이 달라집니다. 끝내지 못한 날에도 총공부시간 대신 어떤 마감을 잘못 판단했는지 남깁니다. 이는 하단동 학생의 실제 성과를 소개하는 내용이 아니라, 여러 일정이 겹칠 때 분류 기준을 설명하는 가상 예시입니다.</p>

<h2>하단동 중학생은 ‘내용’과 ‘마감’을 따로 회상해야 합니다</h2>
<p>중학교에서는 과목이 늘어나는 만큼 무엇을 배웠는지와 언제 끝내야 하는지가 동시에 흐려질 수 있습니다. 학교에서 나온 직후 3분 동안 과목별 핵심어를 적고, 집에서는 그 메모를 보지 않은 채 다시 설명해 보게 합니다. 설명하지 못한 내용은 복습 목록, 날짜를 놓친 항목은 일정 목록으로 분리합니다. 두 문제를 같은 과제량 증가로 해결하지 않는 것이 핵심입니다.</p>
<ul>
<li>설명은 되지만 문제를 틀린 경우: 풀이 절차나 적용 조건을 확인합니다.</li>
<li>배운 내용 자체가 떠오르지 않는 경우: 당일 회상 간격을 짧게 잡습니다.</li>
<li>알고도 제출을 놓친 경우: 마감 알림과 확인 시간을 고정합니다.</li>
</ul>

<h2>학교별 정보는 실제 연결된 두 페이지에서 확인합니다</h2>
<p>하단동에서 학교명을 기준으로 찾는 경우에는 <a href="/부산건국고과외/">부산건국고과외</a>와 <a href="/부산여고과외/">부산여고과외</a> 페이지로 이동할 수 있습니다. 각 학교 페이지는 학교 이름에 맞춘 학습 탐색 경로이며 재학 여부나 배정, 과외 효과를 뜻하지 않습니다. 시험일·행사일·교육과정처럼 바뀔 수 있는 내용은 해당 페이지의 학교 공식 홈페이지 링크에서 다시 확인해야 합니다.</p>

<h2>영어와 수학은 같은 시간표라도 기록 방식이 달라야 합니다</h2>
<p><a href="/부산하단동영어과외/">하단동 영어 학습</a>은 어휘를 외운 횟수보다 문장 속 의미를 회상하고 독해 근거를 찾는 과정을 남기는 편이 좋습니다. <a href="/부산하단동수학과외/">하단동 수학 학습</a>은 오답 수보다 처음 선택한 개념과 풀이가 끊긴 위치를 표시해야 합니다. 두 과목 모두 필요하다면 같은 날 분량을 늘리기보다 집중이 필요한 과목과 유지할 과목을 주간 단위로 교대할 수 있습니다.</p>

<h2>보호자는 주 1회 세 질문만 확인합니다</h2>
<ol>
<li>이번 주에 가장 자주 밀린 마감은 무엇이었나요?</li>
<li>혼자 해결하지 못해 질문으로 남긴 지점은 어디였나요?</li>
<li>다음 주에 없애거나 줄여야 할 계획은 무엇인가요?</li>
</ol>
<p>매일 완료 여부를 대신 확인하면 학생이 계획을 수정할 기회가 줄 수 있습니다. 주간 점검에서는 지적보다 학생의 근거를 듣고, 다음 일주일에 시험할 한 가지 변경만 합의하는 편이 좋습니다.</p>

<h2>시험 14일 전부터 하단동 시간표를 운영하는 방식</h2>
<p>시험 대비는 날짜별 분량을 촘촘히 채우는 것보다 과목마다 첫 회상일과 두 번째 확인일을 정하는 방식이 안정적입니다. 14일 전에는 학교에서 배운 범위와 빠진 자료를 확인하고, 10일 전에는 책을 덮고 핵심 개념을 설명합니다. 7일 전에는 틀린 이유가 다른 문제를 골라 다시 풀고, 3일 전에는 새 문제를 늘리기보다 아직 설명되지 않는 부분을 질문 목록으로 좁힙니다.</p>
<table>
<thead><tr><th>시점</th><th>학생이 남길 증거</th><th>과외에서 확인할 것</th></tr></thead>
<tbody>
<tr><td>14일 전</td><td>시험 범위와 빠진 자료 목록</td><td>학습 순서를 정할 정보가 충분한지</td></tr>
<tr><td>10일 전</td><td>과목별 핵심어를 보지 않고 쓴 메모</td><td>기억 공백인지 이해 공백인지</td></tr>
<tr><td>7일 전</td><td>오답을 원인별로 나눈 표</td><td>같은 오류가 다른 문제에서도 반복되는지</td></tr>
<tr><td>3일 전</td><td>혼자 설명하지 못한 질문</td><td>남은 시간에 해결할 우선순위</td></tr>
</tbody>
</table>

<h2>수행평가와 지필시험을 같은 공부로 묶지 않습니다</h2>
<p>수행평가는 제출 형식, 준비물, 발표 또는 작성 과정처럼 마감 관리가 중요하고, 지필시험은 기억을 다시 꺼내고 문제에 적용하는 간격이 중요합니다. 두 항목을 모두 “시험 준비”라고 쓰면 당장 보이는 수행평가에 시간이 몰릴 수 있습니다. 계획표에서 제출물은 산출물 칸, 지필시험은 회상 칸으로 나누고 서로 다른 완료 기준을 둡니다.</p>
<p>산출물 칸에는 초안·검토·제출 세 상태를 표시하고, 회상 칸에는 설명 가능·부분 설명·질문 필요를 표시합니다. 이 방식이면 시간이 부족한 날에도 제출만 했다고 시험 준비까지 끝났다고 착각하지 않고, 반대로 문제를 오래 풀었다고 수행평가 준비가 된 것으로 보지 않게 됩니다.</p>

<h2>계획이 무너진 다음 날 사용하는 복구 규칙</h2>
<p>밀린 항목을 다음 날 계획 아래에 그대로 붙이면 과부하가 반복됩니다. 먼저 마감이 지나면 의미가 사라지는 일, 다음 수업 전에 필요한 일, 이번 주 안에 다시 연결하면 되는 일로 나눕니다. 첫 번째는 즉시 확인하고, 두 번째는 분량을 줄여 핵심만 남기며, 세 번째는 비어 있는 날로 옮깁니다. 학생은 옮긴 이유를 한 문장으로 적어 다음 주 같은 충돌을 예방할 수 있습니다.</p>
<aside class="content-note"><p><strong>복구의 기준:</strong> 밀린 분량을 모두 되살리는 것이 아니라 다음 학습과 연결되는 핵심을 보존하는 것입니다. 반복해서 밀리는 항목은 의지보다 예상 소요시간과 시작 조건을 다시 측정해야 합니다.</p></aside>

<h2>첫 상담에 가져갈 자료는 많기보다 서로 연결되어야 합니다</h2>
<p>최근 시험지 전체를 준비하기 어렵다면 영어 지문 한 개, 수학 오답 두 문제, 최근 수행평가 안내 한 장, 평일 시간표만으로도 시작할 수 있습니다. 영어 자료에는 답을 고른 이유를, 수학 자료에는 처음 막힌 줄을 학생이 표시하게 합니다. 수행평가 안내에서는 제출일과 필요한 산출물을, 시간표에서는 실제 집 도착 시각을 확인합니다.</p>
<p>네 자료를 함께 보면 성적 결과만으로는 드러나지 않는 연결이 보입니다. 내용을 이해했지만 마감을 놓치는지, 시간이 충분해도 첫 과제를 고르지 못하는지, 설명을 들을 때는 알지만 하루 뒤 복원하지 못하는지 구분할 수 있습니다. 상담에서 이 자료를 어떻게 수업 목표와 주간 과제로 바꿀지 설명해 주는지 확인하세요.</p>

<h2>하단동과외 비교를 마치는 기준</h2>
<p>상담 뒤에는 수업 횟수보다 학생의 귀가 경로가 반영되었는지, 학교 일정 확인 방법이 정해졌는지, 영어와 수학의 점검 기준이 구분되었는지를 보세요. <a href="/부산사하구과외/">부산사하구과외</a>는 더 넓은 생활권을 비교할 때, 하단동 페이지는 실제 하루의 순서를 좁혀 볼 때 사용하면 역할이 분명해집니다.</p>
<p>후보를 비교하는 표에는 거리·시간·수업형태뿐 아니라 피드백 주기, 결석이나 학교 일정 변경 시 조정 방법, 학생이 질문을 준비하는 방식도 넣으세요. 가까운 수업이어도 마감 충돌을 다루지 못하면 현재 문제와 맞지 않을 수 있고, 설명이 자세해도 학생의 독립 복습으로 이어지지 않으면 재검토가 필요합니다. 대면과 온라인 후보가 함께 있다면 이동 편의가 아니라 풀이 과정 확인과 수업 후 기록 전달 방식을 같은 항목으로 비교하세요. 첫 한 달의 확인 날짜를 미리 정해 두면 막연한 만족도 대신 실제 기록으로 계속 여부를 판단할 수 있습니다.</p>
</section>
""",
        "부산우동과외": f"""
<section class="priority-region-content priority-region-udong" data-content-version="region-individual-v1">
<h2>부산우동과외 계획은 넓은 지명보다 이번 주의 충돌부터 찾습니다</h2>
<p>‘우동’은 검색에 쓰는 지역명이고 학생의 실제 평일은 학교 위치, 귀가 경로, 방과 후 일정에 따라 더 잘게 나뉩니다. 해운대구의 <a href="https://www.haeundae.go.kr/index.do?menuCd=DOM_000000101006002001">우2동 행정복지센터 공식 소개</a>처럼 행정 정보가 필요한 경우에는 정확한 동을 다시 확인하고, 학습 계획에서는 집 주소 대신 요일별 도착 시각과 마감의 겹침을 기준으로 삼으세요.</p>

<h2>한 주를 네 칸의 충돌 지도에 옮겨 보세요</h2>
<div class="decision-grid" role="list" aria-label="우동 학생의 주간 충돌 점검">
<p role="listitem"><strong>고정 일정</strong><br>학교 종료와 이미 정해진 이동 시간을 적습니다.</p>
<p role="listitem"><strong>바뀌는 마감</strong><br>수행평가·과제·시험 준비의 날짜를 적습니다.</p>
<p role="listitem"><strong>집중 과업</strong><br>새 개념, 긴 독해처럼 방해 없이 해야 할 일을 고릅니다.</p>
<p role="listitem"><strong>회복 과업</strong><br>단어 회상, 오답 한 문제처럼 늦은 날에도 남길 일을 정합니다.</p>
</div>
<p>충돌 지도는 모든 칸을 채우는 계획표가 아닙니다. 고정 일정과 마감이 겹치는 날을 먼저 찾고, 집중 과업을 다른 날로 이동시키기 위한 도구입니다. 비어 있는 시간보다 사용할 수 있는 에너지의 차이를 표시하면 무리한 분량을 줄일 수 있습니다.</p>

<h2>가상 학습 시나리오: 세 과목을 번갈아 살린 일주일</h2>
<p>{notice} 수행평가가 겹친 고등학생이 영어·수학·탐구를 매일 같은 비율로 공부하려 했다고 가정합니다. 처음에는 시작 과목을 고르느라 시간이 길어지고 세 과목 모두 끝내지 못했습니다. 이후 월요일은 영어 독해 근거 정리, 화요일은 수학 풀이 복원, 수요일은 탐구 개념 회상처럼 하루의 중심 과업을 하나로 정했습니다. 나머지 과목은 10분 확인만 남겨 연결을 끊지 않았습니다. 이 내용은 실제 우동 학생의 결과나 점수 변화를 말하는 사례가 아니라, 마감 충돌을 해소하는 선택 방식을 보여 주는 가상 시나리오입니다.</p>

<h2>과목 선택은 ‘어려운 과목’ 대신 막힌 과정으로 결정합니다</h2>
<table>
<thead><tr><th>관찰된 문제</th><th>먼저 볼 페이지</th><th>수업 전에 남길 자료</th></tr></thead>
<tbody>
<tr><td>읽었지만 근거 문장을 찾지 못함</td><td><a href="/부산우동영어과외/">부산우동영어과외</a></td><td>틀린 선택지와 선택한 이유</td></tr>
<tr><td>개념은 아는데 풀이가 중간에 끊김</td><td><a href="/부산우동수학과외/">부산우동수학과외</a></td><td>마지막으로 확신한 계산 줄</td></tr>
<tr><td>두 과목 모두 마감을 반복해서 놓침</td><td>현재 우동과외 페이지</td><td>일주일 귀가·시작 시각 기록</td></tr>
</tbody>
</table>

<h2>학교명 검색은 일정 확인 통로로 사용합니다</h2>
<p>현재 우동 페이지에서는 <a href="/부산문화여고과외/">부산문화여고과외</a>, <a href="/부산센텀여고과외/">부산센텀여고과외</a>, <a href="/부산해강고과외/">부산해강고과외</a>로 이어집니다. 학교별 페이지에서 공식 홈페이지 이동 경로를 확인할 수 있지만, 연결 자체가 재학·배정·성적 향상을 의미하지는 않습니다. 학사일정은 변경될 수 있으므로 학생이 실제로 다니는 학교의 공식 공지를 기준으로 계획표를 갱신해야 합니다.</p>

<h2>초등·중등·고등은 충돌을 푸는 단위가 다릅니다</h2>
<p><strong>초등학생</strong>은 하루 전체보다 시작 전 10분을 봅니다. 준비물을 꺼내고 첫 과제를 고르는 과정에서 도움이 얼마나 필요한지 기록하면 과외가 설명 중심인지 습관 연결 중심인지 판단하기 쉽습니다. 긴 숙제 대신 수업에서 배운 내용을 말로 한 번 설명하고 스스로 완료 표시를 하게 하는 방식으로 독립 구간을 늘릴 수 있습니다.</p>
<p><strong>중학생</strong>은 과목별 마감과 복습 간격을 한 주 단위로 봅니다. 일정이 겹친 날에는 모든 과목을 조금씩 처리하기보다 제출이 있는 과목, 기억 연결이 끊기면 안 되는 과목, 다음 날로 옮길 과목을 분류합니다. 옮긴 과목에는 새 날짜만 적지 말고 이동 이유를 함께 기록해야 같은 충돌을 찾을 수 있습니다.</p>
<p><strong>고등학생</strong>은 선택과목과 학교 평가를 월간 지도에서 먼저 확인합니다. 한 주의 중심 과업을 정할 때 시험 비중만 보지 말고 현재 이해 공백, 필요한 회상 횟수, 혼자 해결 가능한 정도를 함께 봅니다. 과외 시간은 문제 수를 늘리는 시간보다 질문의 원인을 찾아 다음 독립학습을 설계하는 시간으로 사용할 수 있습니다.</p>

<h2>세 번의 수업 뒤에는 수업 방식도 다시 선택합니다</h2>
<p>첫 수업에서는 진단 결과보다 학생이 풀이와 생각을 얼마나 설명할 수 있는지 확인합니다. 두 번째 수업에서는 이전 피드백이 가정학습에 남았는지 보고, 세 번째 수업에서는 같은 유형의 도움을 계속 요청하는지 점검합니다. 세 번의 기록이 모이면 설명 비중을 늘릴지, 혼자 푸는 시간을 늘릴지, 과제량을 줄이고 회상 간격을 짧게 할지 결정할 근거가 생깁니다.</p>
<ol>
<li>학생이 수업 목표를 자기 말로 말할 수 있었는가</li>
<li>수업 중 표시한 오류를 다음 학습에서 다시 찾았는가</li>
<li>숙제를 못 했을 때 이유와 수정 방법을 설명했는가</li>
<li>선생님의 피드백이 보호자 없이도 학생 기록에 남았는가</li>
</ol>

<h2>체험 수업에서는 네 장면을 순서대로 관찰합니다</h2>
<p><strong>시작 장면</strong>에서는 선생님이 정답을 설명하기 전에 학생의 기존 풀이와 생각을 묻는지 봅니다. 학생이 말이 없을 때 바로 대신 설명하는지, 작은 질문으로 알고 있는 범위를 찾아가는지도 확인할 수 있습니다.</p>
<p><strong>오류 장면</strong>에서는 틀린 문제를 고쳐 주는 데서 멈추지 않고 오류의 출발점을 표시하는지 봅니다. 영어라면 근거 없는 선택, 어휘 오해, 문장 구조 해석을 구분하고, 수학이라면 개념 선택, 식 세우기, 계산을 분리해야 다음 과제가 구체적입니다.</p>
<p><strong>연습 장면</strong>에서는 비슷한 문제를 바로 반복하는지, 자료를 가린 뒤 학생이 과정을 복원하게 하는지 살펴봅니다. 학생이 설명한 문장을 선생님이 다시 정리해 주더라도 최종 요약은 학생의 말이나 필기로 남아야 합니다.</p>
<p><strong>마무리 장면</strong>에서는 다음 수업 전 할 일이 분량만 제시되는지, 시작 조건과 완료 기준까지 정해지는지 확인합니다. “10문제 풀기”보다 “오답 두 문제의 첫 풀이를 가리고 과정 복원하기”가 점검 가능한 과제입니다.</p>

<h2>한 달 뒤에는 점수 대신 계획의 이동을 비교합니다</h2>
<p>첫 주와 넷째 주의 도착 시각은 같더라도 시작까지 걸린 시간, 질문으로 가져온 문제의 구체성, 밀린 과제를 옮기는 방식은 달라질 수 있습니다. 이 세 가지가 그대로라면 숙제량을 늘리기 전에 수업 피드백이 가정학습까지 이어졌는지 다시 봅니다. 달라졌다면 효과를 단정하기보다 다음 달에도 유지할 행동 하나와 새로 검증할 문제 하나를 정합니다.</p>

<h2>우동에서 대면·온라인 방식을 고르는 관찰 기준</h2>
<p>방식은 지역의 편의성만으로 정하지 말고 학생이 자료를 보여 주고 질문하는 과정으로 판단합니다. 온라인에서도 풀이 화면과 노트를 즉시 공유하고 학생이 말로 설명할 수 있다면 이동시간을 줄이는 장점이 있습니다. 반대로 준비물을 자주 빠뜨리거나 화면 밖에서 풀이 과정이 사라진다면 대면 수업 또는 초기 대면 점검이 더 적합할 수 있습니다.</p>
<p>어느 방식을 택하든 수업 전 제출할 자료, 수업 중 학생이 설명할 시간, 수업 후 남길 기록이 정해져 있어야 합니다. 단순히 접속이 편하거나 가까운지만 비교하면 학습 과정의 차이를 놓치기 쉽습니다.</p>

<h2>우동과외 상담에서는 네 가지 선택이 남아야 합니다</h2>
<ul>
<li>일찍 끝나는 날과 늦게 끝나는 날에 각각 무엇을 할지</li>
<li>이번 달 영어와 수학 중 어느 과정을 먼저 바꿀지</li>
<li>수업에서 설명받을 문제와 혼자 반복할 문제를 어떻게 나눌지</li>
<li>학교 일정이 바뀔 때 계획을 다시 보는 요일을 언제로 할지</li>
</ul>
<p>상담을 마친 뒤에도 “열심히 하자”만 남는다면 실행 기준이 부족합니다. 반대로 학생이 다음 주에 줄일 분량과 질문으로 가져갈 문제를 말할 수 있다면 계획을 검토할 근거가 생긴 것입니다. 더 넓은 범위는 <a href="/부산해운대구과외/">부산해운대구과외</a>, 인접 생활권 비교는 <a href="/부산반여동과외/">부산반여동과외</a>와 <a href="/부산반송동과외/">부산반송동과외</a>에서 이어서 확인할 수 있습니다.</p>
<p>우동처럼 학교명과 세부 생활권을 함께 검색하는 경우에는 지명만 보고 학생의 학교를 추정하지 않아야 합니다. 상담 단계에서 실제 학교의 공식 일정과 학생이 제공한 시간표를 대조하고, 일정이 바뀌면 누가 언제 계획을 갱신할지 정하세요. 검색 결과에 나온 학교명과 실제 재학 학교가 일치하는지도 학생 또는 보호자가 먼저 확인해야 잘못된 달력을 옮기지 않습니다. 선생님은 학습 우선순위를 제안하고, 학생은 수행한 과정과 질문을 남기며, 보호자는 주간 확인 시점만 지키는 식으로 역할을 나누면 같은 정보를 여러 사람이 반복 확인하는 부담을 줄일 수 있습니다. 이 역할 분담은 상담 뒤에도 기록이 끊기지 않는지 판단하는 기준이 됩니다.</p>
</section>
""",
        "부산화명동과외": f"""
<section class="priority-region-content priority-region-hwamyeong" data-content-version="region-individual-v1">
<h2>부산화명동과외에서는 고정 일정과 변동 일정을 따로 적습니다</h2>
<p>화명동 학생의 학습 계획을 만들 때 지역에 대한 일반적인 인상보다 반복되는 시간과 매주 바뀌는 시간을 구분하는 것이 먼저입니다. 학교 종료, 정기 수업, 식사처럼 거의 같은 일정은 ‘고정 칸’에 두고 수행평가, 행사, 보충 일정처럼 달라지는 항목은 ‘변동 칸’에 둡니다. 두 달력을 한 표에 섞으면 계획이 어긋난 원인을 찾기 어렵습니다.</p>

<h2>7일 관찰로 시작 가능한 시간을 찾는 방법</h2>
<p>첫 주에는 공부량을 늘리지 말고 아래 다섯 시각만 기록해 보세요. 기록의 목적은 학생을 감시하는 것이 아니라 과외와 가정학습이 실제로 들어갈 자리를 찾는 것입니다.</p>
<ol>
<li>학교나 마지막 일정이 끝난 시각</li>
<li>집에 도착한 시각</li>
<li>휴식이 끝난 시각</li>
<li>첫 학습 행동을 시작한 시각</li>
<li>집중이 크게 떨어진 시각</li>
</ol>
<p>도착과 시작 사이가 길다면 과목을 추가하기 전에 시작 신호를 정합니다. 시작은 빠르지만 금방 멈춘다면 첫 과제의 난이도와 길이를 조정합니다. 늦게 귀가한 날에는 고정 분량을 강요하지 않고 다음 날 다시 연결할 최소 행동을 남깁니다.</p>

<h2>가상 학습 시나리오: ‘책상에 앉기’와 ‘공부 시작’을 구분한 예시</h2>
<p>{notice} 한 초등학생이 저녁마다 책상에는 앉지만 준비물을 찾고 오늘 할 일을 고르느라 시간을 보내는 상황을 가정합니다. 보호자가 문제집 페이지를 매번 지정하는 대신, 학생이 가방 정리 → 오늘 과제 한 줄 쓰기 → 15분 타이머 시작의 순서를 직접 반복하도록 했습니다. 끝난 뒤에는 맞힌 개수보다 혼자 시작한 단계와 도움을 요청한 지점을 표시합니다. 이는 실제 화명동 학생의 변화나 성과를 소개하는 것이 아니라, 시작 행동을 관찰하는 방법을 설명하기 위한 가상 시나리오입니다.</p>

<h2>학년이 바뀌면 보호자가 넘겨줄 결정도 달라집니다</h2>
<dl>
<dt><strong>초등 단계</strong></dt><dd>과제의 시작 순서를 함께 만들되, 준비물과 완료 표시는 학생이 하게 합니다.</dd>
<dt><strong>중등 단계</strong></dt><dd>시험일까지 남은 날을 알려주기보다 과목별 첫 복습일을 학생이 선택하게 합니다.</dd>
<dt><strong>고등 단계</strong></dt><dd>주간 총시간을 묻기보다 선택과목·수행평가·시험 복습이 충돌할 때 무엇을 미룰지 근거를 듣습니다.</dd>
</dl>
<p>자기주도학습은 혼자 두는 것이 아니라 결정의 일부를 단계적으로 넘기는 과정입니다. 학생이 선택한 계획이 어긋나면 대신 고쳐 주기보다 다음 주에 바꿀 한 가지를 말하게 해야 수정 능력을 확인할 수 있습니다.</p>

<h2>영어는 회상 간격, 수학은 풀이 복원으로 나눕니다</h2>
<p><a href="/부산화명동영어과외/">부산화명동영어과외</a>를 볼 때는 단어를 몇 번 썼는지보다 하루 뒤 문장 속에서 뜻을 떠올리는지, 독해 답의 근거를 다시 찾는지를 확인하세요. <a href="/부산화명동수학과외/">부산화명동수학과외</a>에서는 틀린 문제를 다시 푸는 데서 끝내지 않고 처음 풀이를 가리고 과정을 복원하게 합니다. 풀이가 다시 끊긴 위치가 다음 설명의 출발점입니다.</p>

<h2>학교 페이지는 서로 다른 달력을 확인하는 장치입니다</h2>
<p>화명동에서 학교명을 기준으로 탐색할 때는 <a href="/부산금명여고과외/">부산금명여고과외</a>와 <a href="/부산화명고과외/">부산화명고과외</a> 페이지가 연결되어 있습니다. 학교별 페이지의 공식 홈페이지 링크에서 실제 학사일정을 확인한 뒤 학생의 변동 달력에 옮기세요. 해당 링크는 학교 정보 탐색을 위한 것이며 재학 여부, 배정 또는 과외 성과를 뜻하지 않습니다.</p>

<h2>일요일 15분으로 두 달력을 다시 맞춥니다</h2>
<p>고정 달력에는 정해진 수업과 반복되는 귀가시간을, 변동 달력에는 이번 주에만 있는 시험·행사·제출을 적습니다. 일요일에는 변동 달력을 먼저 보고 집중이 필요한 과제를 빈 고정 칸으로 옮깁니다. 이때 모든 빈칸을 채우지 말고 일정이 길어진 날을 위한 회복 칸을 적어도 하나 남겨 둡니다.</p>
<div class="planning-example">
<p><strong>월·화:</strong> 새 개념과 긴 과제를 배치하되 학교에서 나온 새 마감이 있는지 확인합니다.</p>
<p><strong>수·목:</strong> 앞서 배운 내용을 자료 없이 회상하고, 설명되지 않는 부분을 질문으로 바꿉니다.</p>
<p><strong>금:</strong> 미완료 분량을 모두 옮기지 않고 다음 학습에 꼭 필요한 연결만 복구합니다.</p>
<p><strong>주말:</strong> 총공부시간 대신 시작 지연, 이해 공백, 일정 충돌 가운데 무엇이 반복됐는지 분류합니다.</p>
</div>

<h2>수업 피드백은 학생용과 보호자용을 다르게 남깁니다</h2>
<p>학생에게는 다음에 혼자 할 행동이 보여야 합니다. 예를 들어 “독해가 약함” 대신 “틀린 선택지를 지우기 전에 근거 문장에 밑줄을 긋는다”, “계산 실수” 대신 “부호가 바뀐 줄부터 가리고 다시 복원한다”처럼 씁니다. 학생용 피드백은 다음 학습을 시작할 때 바로 꺼내 볼 수 있을 만큼 짧아야 합니다.</p>
<p>보호자용 피드백에는 점수 예상보다 관찰된 과정이 적합합니다. 학생이 도움 없이 시작한 범위, 반복한 오류, 다음 주에 바꿀 한 가지, 보호자가 확인하지 않아도 되는 항목을 구분하면 과도한 개입을 줄일 수 있습니다. 개인정보나 전체 성적표를 상시 공유하기보다 학습 조정에 필요한 자료만 목적에 맞게 전달하세요.</p>

<h2>연속으로 실패한 계획은 난이도보다 연결 지점을 고칩니다</h2>
<p>같은 계획이 두 번 이상 밀렸다면 의욕을 강조하기 전에 앞 단계가 있는지 확인합니다. 영어 본문을 읽기 전에 필요한 어휘가 준비되지 않았는지, 수학 문제를 풀기 전에 예제의 핵심 조건을 설명할 수 있는지, 책상에 앉기 전에 준비물을 찾느라 흐름이 끊기는지 살펴봅니다. 연결 지점을 찾으면 과제를 더 쉽게 만드는 대신 시작 직전에 필요한 한 단계를 추가할 수 있습니다.</p>
<p>그래도 실행되지 않는다면 분량을 절반으로 줄여 시작 시각과 완료 여부를 다시 측정합니다. 작은 계획이 안정된 뒤에 난이도나 양을 올려야 무엇이 실제로 달라졌는지 판단할 수 있습니다. 계획 변경은 실패를 숨기는 작업이 아니라 다음 시도의 조건을 더 정확하게 만드는 과정입니다.</p>

<h2>4주 점검에서는 유지·교체·중단을 구분합니다</h2>
<p>한 달 동안 사용한 학습 방법을 모두 계속 가져갈 필요는 없습니다. 학생이 도움 없이 반복할 수 있고 다음 과제로 이어지는 행동은 유지합니다. 실행은 되지만 오류가 줄지 않는 행동은 방법을 교체합니다. 시간만 오래 걸리고 학습 목표와 연결되지 않는 행동은 중단합니다. 세 칸으로 나누면 새로운 과제를 추가하기 전에 불필요한 부담을 정리할 수 있습니다.</p>
<ul>
<li><strong>유지:</strong> 준비 순서, 질문 표시, 짧은 회상처럼 혼자 반복되는 행동</li>
<li><strong>교체:</strong> 반복은 했지만 이해나 복원으로 이어지지 않은 방법</li>
<li><strong>중단:</strong> 목표를 설명할 수 없고 다른 중요한 마감을 밀어내는 활동</li>
</ul>
<p>점검 결과는 학생·선생님·보호자가 각각 한 문장씩 말해 보는 것이 좋습니다. 서로의 판단이 다르면 누가 맞는지 정하기보다 다음 주에 관찰할 증거를 합의합니다. 예를 들어 “집중이 좋아졌다” 대신 시작 뒤 20분 동안 자리 이탈 횟수를 확인하는 식으로 바꾸면 다음 결정이 쉬워집니다.</p>

<h2>화명동과외 선택 전 마지막으로 확인할 진단표</h2>
<table>
<thead><tr><th>질문</th><th>‘예’라면 먼저 할 일</th></tr></thead>
<tbody>
<tr><td>요일마다 귀가 시각 차이가 큰가요?</td><td>정상일과 변동일의 과제를 두 종류로 만듭니다.</td></tr>
<tr><td>시작은 하지만 무엇을 배웠는지 설명하지 못하나요?</td><td>수업 직후 3분 회상 기록을 남깁니다.</td></tr>
<tr><td>시험 직전에 모든 과목이 한꺼번에 밀리나요?</td><td>시험일이 아니라 첫 복습일을 달력에 적습니다.</td></tr>
<tr><td>보호자 확인이 없으면 계획이 멈추나요?</td><td>완료 확인 한 단계를 학생에게 넘깁니다.</td></tr>
</tbody>
</table>
<p>네 질문 가운데 반복되는 항목 하나만 이번 달의 우선 목표로 정하세요. 지역 범위를 넓혀 비교할 때는 <a href="/부산북구과외/">부산북구과외</a>, 가까운 생활권을 함께 볼 때는 <a href="/부산구포동과외/">부산구포동과외</a>와 <a href="/부산덕천동과외/">부산덕천동과외</a>를 사용할 수 있습니다. 페이지 수를 많이 보는 것보다 같은 학년·귀가 시각·과목 문제를 기준으로 비교해야 차이가 분명해집니다.</p>
<p>마지막 선택 전에는 후보마다 같은 자료를 보여 주고 답변을 비교하세요. 한쪽에는 시험지를, 다른 쪽에는 시간표만 보여 주면 판단 기준이 달라집니다. 동일한 오답 두 문제와 7일 생활 기록을 바탕으로 첫 달 목표, 수업 밖 과제, 피드백 방식, 일정 변경 시 대안을 물어보면 설명의 구체성을 비교할 수 있습니다. 선택 뒤에는 4주 점검 날짜를 정하고 유지·교체·중단 항목을 학생과 함께 기록하세요.</p>
</section>
""",
    }
    return articles[page.slug].strip()


def clarify_hypothetical_scenarios(body: str) -> str:
    """Label constructed student narratives so they cannot be mistaken for testimonials."""

    def clarify_section(match: re.Match[str]) -> str:
        section = match.group(0)
        is_scenario = "이 변화는 점수 보장이 아니라" in section or 'class="scenario-notice"' in section
        if "처음에는" not in section or not is_scenario:
            return section

        def label_heading(heading_match: re.Match[str]) -> str:
            inner = re.sub(r"^\s*가상 학습 시나리오:\s*", "", heading_match.group(2))
            inner = inner.replace("학생의 변화", "학습 조정 예시").replace("사례", "예시")
            return f"{heading_match.group(1)}가상 학습 시나리오: {inner}{heading_match.group(3)}"

        section = re.sub(
            r"(<h2\b[^>]*>)(.*?)(</h2>)",
            label_heading,
            section,
            count=1,
            flags=re.I | re.S,
        )
        if 'class="scenario-notice"' not in section:
            section = re.sub(
                r"(<p\b[^>]*>)",
                rf'\1<strong class="scenario-notice">{escape(SCENARIO_NOTICE)}</strong> ',
                section,
                count=1,
                flags=re.I,
            )
        section = section.replace(
            "학생 사례입니다.",
            "학생의 학습 상황을 설명하기 위한 가상 시나리오입니다.",
        )
        section = section.replace(
            "이 사례의 관찰 기준은",
            "이 가상 시나리오에서 살펴볼 기준은",
        )
        section = section.replace(
            "이 변화는 점수 보장이 아니라 학생이 자신의 하루를 이해하고 수정하는 힘이 자랐다는 데 의미가 있습니다.",
            "이 구성은 점수 향상이나 실제 결과를 보장하는 사례가 아니라, 학생이 자신의 하루를 이해하고 수정하는 과정을 설명하기 위한 예시입니다.",
        )
        return section

    return re.sub(
        r"<h2\b[^>]*>.*?</h2>.*?(?=<h2\b|$)",
        clarify_section,
        body,
        flags=re.I | re.S,
    )


def _contextual_link(page: Page) -> str:
    return f'<a href="{escape(page.url)}">{escape(page.title)}</a>'


def _natural_link_list(pages: list[Page]) -> str:
    links = [_contextual_link(page) for page in pages]
    if len(links) <= 1:
        return "".join(links)
    if len(links) == 2:
        return f"{links[0]}와 {links[1]}"
    return f"{', '.join(links[:-1])}, {links[-1]}"


def _is_general_school_page(page: Page) -> bool:
    return (
        page.page_type == "school"
        and not page.slug.endswith("영어과외")
        and not page.slug.endswith("수학과외")
    )


CITY_REGION_HUBS = {"부산과외", "구미과외", "양산과외"}


def _is_pure_region_tutoring_slug(slug: str) -> bool:
    return slug.endswith("과외") and not any(
        slug.endswith(suffix)
        for suffix in ("영어과외", "수학과외", "초등과외", "중등과외", "고등과외")
    )


def _navigation_school_slugs(page: Page, page_map: dict[str, Page]) -> list[str]:
    """Keep city hubs focused on schools that have no narrower region page.

    Schools assigned to a district or neighborhood remain discoverable from that
    more relevant page, instead of being repeated in a city-wide list containing
    hundreds of links.
    """
    slugs = list(dict.fromkeys(page.school_slugs))
    if page.slug not in CITY_REGION_HUBS:
        return slugs

    narrower: set[str] = set()
    city = page.slug[: -len("과외")]
    for candidate in page_map.values():
        if (
            candidate.page_type != "region"
            or candidate.slug == page.slug
            or not candidate.slug.startswith(city)
            or not _is_pure_region_tutoring_slug(candidate.slug)
        ):
            continue
        narrower.update(candidate.school_slugs)
    return [slug for slug in slugs if slug not in narrower]


def render_contextual_region_section(page: Page, page_map: dict[str, Page]) -> str:
    """Build a short, in-article navigation section for a pure regional tutoring page."""
    if page.page_type != "region" or page.category != "과외" or page.slug in SPECIAL_REGION_HUBS:
        return ""

    base = page.slug[: -len("과외")] if page.slug.endswith("과외") else page.slug
    parent = page_map.get(page.parent_slug or "")
    if parent and parent.slug == page.slug:
        parent = None
    english = page_map.get(f"{base}영어과외")
    math = page_map.get(f"{base}수학과외")

    schools: list[Page] = []
    seen: set[str] = set()
    for slug in _navigation_school_slugs(page, page_map):
        item = page_map.get(slug)
        if not item or item.slug in seen or not _is_general_school_page(item):
            continue
        seen.add(item.slug)
        schools.append(item)
        if len(schools) == 3:
            break

    nearby: list[Page] = []
    if not schools:
        for slug in [*page.child_slugs, *page.sibling_slugs]:
            item = page_map.get(slug)
            if (
                not item
                or item.slug in seen
                or item.slug == page.slug
                or item.slug == (parent.slug if parent else "")
                or item.page_type != "region"
                or item.category != "과외"
                or item.slug in SPECIAL_REGION_HUBS
            ):
                continue
            seen.add(item.slug)
            nearby.append(item)
            if len(nearby) == 2:
                break

    paragraphs: list[str] = []
    if parent:
        paragraphs.append(
            f"생활권을 더 넓게 비교하려면 {_contextual_link(parent)}에서 상위 지역의 학년별 학습 흐름과 "
            "연결된 세부 지역을 먼저 확인할 수 있습니다."
        )
    if english and math:
        paragraphs.append(
            f"과목별 원인이 분명하다면 {_contextual_link(english)}에서 어휘·독해 학습 기준을, "
            f"{_contextual_link(math)}에서 개념·오답 관리 기준을 이어서 살펴보세요."
        )
    elif english or math:
        subject = english or math
        paragraphs.append(f"과목별 학습 기준은 {_contextual_link(subject)}에서 이어서 확인할 수 있습니다.")
    if schools:
        paragraphs.append(
            f"학교 일정과 학습 흐름을 함께 살펴보려면 {_natural_link_list(schools)} 등 실제로 연결된 "
            "학교별 과외 페이지를 참고할 수 있습니다."
        )
    elif nearby:
        paragraphs.append(
            f"가까운 생활권과 비교가 필요할 때는 {_natural_link_list(nearby)}도 함께 확인하면 지역별 "
            "학습 계획의 차이를 살펴보기 쉽습니다."
        )

    if not paragraphs:
        return ""
    content = "\n".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    return (
        '<section class="contextual-links" aria-labelledby="related-learning-pages">\n'
        f'<h2 id="related-learning-pages">{escape(base)} 관련 학습 페이지 함께 보기</h2>\n'
        f"{content}\n"
        "</section>"
    )


def add_contextual_region_links(body: str, page: Page, page_map: dict[str, Page]) -> str:
    """Insert or replace the contextual region links immediately before the FAQ section."""
    cleaned = re.sub(
        r'\s*<section\s+class=["\']contextual-links["\'][^>]*>.*?</section>\s*',
        "\n",
        body,
        flags=re.I | re.S,
    ).strip()
    section = render_contextual_region_section(page, page_map)
    if not section:
        return cleaned
    faq_wrapper = re.search(r'<section\s+class=["\']regional-faq["\'][^>]*>', cleaned, flags=re.I)
    bounds = faq_section_bounds(cleaned)
    insert_at = faq_wrapper.start() if faq_wrapper else bounds[0] if bounds else None
    if insert_at is not None:
        return f"{cleaned[:insert_at].rstrip()}\n{section}\n{cleaned[insert_at:].lstrip()}"
    return f"{cleaned}\n{section}"


def _normalized_internal_href(href: str) -> str:
    value = unescape(href).strip()
    if not value.startswith("/") or value.startswith("//"):
        return ""
    path, _, fragment = value.partition("#")
    path = path.split("?", 1)[0]
    return f"{path}#{fragment}" if fragment else path


def internal_link_slugs(fragment: str) -> set[str]:
    """Return root-relative page slugs linked from an HTML fragment."""
    slugs: set[str] = set()
    for href in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', fragment, flags=re.I):
        normalized = _normalized_internal_href(href)
        if not normalized:
            continue
        path = normalized.split("#", 1)[0]
        slug = path.strip("/")
        if slug:
            slugs.add(slug)
    return slugs


def deduplicate_region_body_links(body: str, page: Page) -> str:
    """Keep one useful in-article link per target on pure regional tutoring pages.

    Links in the dedicated contextual section take priority over earlier keyword
    mentions. Repeated links in FAQ answers become ordinary text, while external
    references and fragment-only links remain untouched.
    """
    if page.page_type != "region" or page.category != "과외" or page.slug in SPECIAL_REGION_HUBS:
        return body

    contextual = re.search(
        r'<section\s+class=["\']contextual-links["\'][^>]*>.*?</section>',
        body,
        flags=re.I | re.S,
    )
    contextual_hrefs: set[str] = set()
    contextual_bounds: tuple[int, int] | None = None
    if contextual:
        contextual_bounds = (contextual.start(), contextual.end())
        contextual_hrefs = {
            normalized
            for href in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', contextual.group(0), flags=re.I)
            if (normalized := _normalized_internal_href(href))
        }

    faq = re.search(
        r'<section\s+class=["\']regional-faq["\'][^>]*>.*?</section>',
        body,
        flags=re.I | re.S,
    )
    faq_bounds = (faq.start(), faq.end()) if faq else None
    faq_keeps_directory = bool(faq and re.search(r'href\s*=\s*["\']/#high-schools["\']', faq.group(0), flags=re.I))

    seen: set[str] = set()
    anchor_pattern = re.compile(
        r'<a\b(?P<attrs>[^>]*\bhref\s*=\s*(?P<quote>["\'])(?P<href>[^"\']+)(?P=quote)[^>]*)>'
        r'(?P<inner>.*?)</a>',
        flags=re.I | re.S,
    )

    def keep_one(match: re.Match[str]) -> str:
        normalized = _normalized_internal_href(match.group("href"))
        if not normalized:
            return match.group(0)
        inside_contextual = bool(
            contextual_bounds
            and contextual_bounds[0] <= match.start() < contextual_bounds[1]
        )
        inside_faq = bool(faq_bounds and faq_bounds[0] <= match.start() < faq_bounds[1])
        if normalized == "/#high-schools" and faq_keeps_directory:
            if inside_faq and normalized not in seen:
                seen.add(normalized)
                return match.group(0)
            return match.group("inner")
        if inside_faq:
            return match.group("inner")
        if normalized in contextual_hrefs:
            if inside_contextual and normalized not in seen:
                seen.add(normalized)
                return match.group(0)
            return match.group("inner")
        if normalized in seen:
            return match.group("inner")
        seen.add(normalized)
        return match.group(0)

    return anchor_pattern.sub(keep_one, body)


def _region_kind(base: str) -> str:
    local = base
    for city in CITIES:
        if local.startswith(city):
            local = local[len(city) :]
            if not local:
                return "city"
            break
    if local.endswith(("구", "군")):
        return "district"
    if local.endswith(("읍", "면")):
        return "town"
    return "neighborhood"


def _regional_pages(page: Page, page_map: dict[str, Page], limit: int = 2) -> list[Page]:
    pages: list[Page] = []
    seen: set[str] = set()
    for slug in [*page.child_slugs, *page.sibling_slugs]:
        item = page_map.get(slug)
        if (
            not item
            or item.slug in seen
            or item.slug == page.slug
            or item.slug == page.parent_slug
            or item.page_type != "region"
            or item.category != "과외"
            or item.slug in SPECIAL_REGION_HUBS
        ):
            continue
        seen.add(item.slug)
        pages.append(item)
        if len(pages) == limit:
            break
    return pages


def _regional_school_pages(page: Page, page_map: dict[str, Page], limit: int = 3) -> list[Page]:
    pages: list[Page] = []
    seen: set[str] = set()
    for slug in _navigation_school_slugs(page, page_map):
        item = page_map.get(slug)
        if not item or item.slug in seen or not _is_general_school_page(item):
            continue
        seen.add(item.slug)
        pages.append(item)
        if len(pages) == limit:
            break
    return pages


def render_regional_faq(page: Page, page_map: dict[str, Page]) -> str:
    """Create five page-specific navigation and preparation questions for a region."""
    if page.page_type != "region" or page.category != "과외" or page.slug in SPECIAL_REGION_HUBS:
        return ""

    location = page.slug[: -len("과외")] if page.slug.endswith("과외") else page.slug
    kind = _region_kind(location)
    parent = page_map.get(page.parent_slug or "")
    if parent and parent.slug == page.slug:
        parent = None
    nearby = _regional_pages(page, page_map)
    schools = _regional_school_pages(page, page_map)
    english = page_map.get(f"{location}영어과외")
    math = page_map.get(f"{location}수학과외")

    if kind == "city":
        heading = f"{location} 지역·과목 페이지를 찾을 때 자주 묻는 질문"
        question_1 = f"{location} 전체에서 내 생활권에 맞는 과외 페이지는 어떻게 찾나요?"
        if nearby:
            answer_1 = (
                f"{location}과외는 도시 전체의 탐색 출발점으로 보고, 실제 통학·귀가 생활권이 정해졌다면 "
                f"{_natural_link_list(nearby)}처럼 연결된 하위 지역 페이지로 범위를 좁혀 보세요. "
                "행정구역 이름보다 학생이 평일에 이동하는 학교·집·학습 장소의 순서를 기준으로 선택하는 편이 정확합니다."
            )
        else:
            answer_1 = f"{location}과외에서는 학생의 학교·집·학습 장소가 이어지는 실제 평일 동선을 기준으로 생활권을 정리하는 것이 좋습니다."
    elif kind == "district":
        heading = f"{location} 생활권과 학교 페이지에 관한 자주 묻는 질문"
        question_1 = f"{location}과외와 상위 지역 페이지는 어떻게 나눠서 봐야 하나요?"
        parent_link = _contextual_link(parent) if parent else "상위 지역 페이지"
        answer_1 = (
            f"{parent_link}는 더 넓은 지역의 과목·학년 흐름을 비교할 때 사용하고, {location}과외에서는 구·군 안의 "
            "통학시간과 귀가 이후 학습 순서를 확인하세요."
        )
        if nearby:
            answer_1 += f" 세부 생활권은 {_natural_link_list(nearby)}에서 한 단계 더 좁혀 볼 수 있습니다."
    elif kind == "town":
        heading = f"{location} 통학권과 학습 페이지 활용 FAQ"
        question_1 = f"{location}과외 페이지에서 읍·면 통학권은 어떤 기준으로 살펴보나요?"
        parent_link = _contextual_link(parent) if parent else "상위 지역 페이지"
        answer_1 = (
            f"먼저 {parent_link}에서 넓은 지역 흐름을 확인한 뒤, {location}에서는 학교까지의 이동 방법과 귀가 시각, "
            "저녁 식사 이후 실제로 확보되는 학습시간을 함께 기록하세요. 같은 읍·면 안에서도 이동 조건에 따라 계획은 달라질 수 있습니다."
        )
    else:
        heading = f"{location} 인접 생활권과 과목 페이지 FAQ"
        question_1 = f"{location}과외와 상위 생활권 페이지는 무엇이 다른가요?"
        parent_link = _contextual_link(parent) if parent else "상위 생활권 페이지"
        answer_1 = (
            f"{parent_link}는 여러 세부 지역을 비교하는 용도이고, {location}과외는 학생의 실제 귀가 시각과 가정학습 순서를 "
            "더 좁은 생활권에서 점검하는 페이지입니다. 두 페이지의 설명을 평균 정보로 보지 말고 학생의 한 주 기록과 대조해 사용하세요."
        )

    question_2 = f"{location}영어과외와 {location}수학과외 페이지는 언제 따로 확인하나요?"
    if english and math:
        answer_2 = (
            f"어휘·독해·문장 회상처럼 영어 학습 과정이 궁금하면 {_contextual_link(english)}를, 개념 이해·풀이 과정·오답 재확인이 "
            f"필요하면 {_contextual_link(math)}를 확인하세요. {location}과외는 두 과목을 포함한 전체 생활계획을 비교하는 용도로 구분하면 됩니다."
        )
    else:
        answer_2 = f"{location}의 과목별 페이지가 생성되어 있는지 먼저 확인하고, 현재 페이지에서는 학년과 생활시간을 함께 비교하세요."

    if schools:
        question_3 = f"{location}에서 학교별 과외 페이지는 어떤 용도로 확인해야 하나요?"
        answer_3 = (
            f"현재 연결된 {_natural_link_list(schools)}에서 학교명별 학습 페이지와 공식 홈페이지 이동 경로를 확인할 수 있습니다. "
            "학교 페이지는 탐색을 돕는 정보이며 재학·배정·성적 또는 과외 효과를 의미하지 않으므로, 실제 학사일정은 학교 공식 홈페이지에서 다시 확인하세요."
        )
    else:
        question_3 = f"{location}에 직접 연결된 학교 페이지가 없으면 어디에서 찾아야 하나요?"
        answer_3 = (
            f"현재 {location}과외에 학교 페이지가 직접 연결되지 않았다면 <a href=\"/#high-schools\">고등학교별 과외 목록</a>에서 "
            "도시와 학교명을 기준으로 찾으세요. 학교가 이 생활권에 속한다고 임의로 추정하지 않고, 학교 페이지의 공식 홈페이지 링크로 명칭과 일정을 확인하는 것이 안전합니다."
        )

    if nearby:
        question_4 = f"{location} 주변의 다른 지역을 비교할 때 무엇을 같게 맞춰야 하나요?"
        answer_4 = (
            f"함께 살펴볼 수 있는 페이지는 {_natural_link_list(nearby)}입니다. 비교할 때는 일반적인 지역 설명보다 학년, 학교 종료 시각, 이동시간, "
            f"저녁 학습 시작 시각을 같은 기준으로 놓고 보세요. 그래야 {location}에서 가능한 계획과 다른 생활권의 계획을 과장 없이 구분할 수 있습니다."
        )
    else:
        question_4 = f"{location}에서 다른 생활권까지 함께 살펴봐야 하는 경우는 언제인가요?"
        answer_4 = (
            f"학교와 집, 학습 장소가 서로 다른 행정구역에 있거나 요일마다 귀가 경로가 달라진다면 {location}만 보지 말고 "
            f"{_contextual_link(parent) if parent else '상위 지역 페이지'}에서 연결된 지역을 함께 확인하세요."
        )

    preparation = {
        "city": "희망 생활권, 학교명, 학년, 과목별 어려움, 평일 귀가 시각",
        "district": "구·군 안의 실제 생활 동, 학교명, 학년, 이동시간, 영어·수학의 현재 과제",
        "town": "학교까지의 이동 방법, 요일별 귀가 시각, 학년, 수행평가 일정, 가정에서 가능한 학습시간",
        "neighborhood": "학교명, 학년, 요일별 귀가 시각, 현재 과제, 영어·수학 가운데 먼저 조정할 항목",
    }[kind]
    question_5 = f"{page.slug} 정보를 비교하기 전에 어떤 내용을 정리하면 좋나요?"
    answer_5 = (
        f"{location} 페이지를 볼 때는 {preparation} 등을 한 주 기준으로 적어 두세요. 정확한 집 주소나 성적 전체를 먼저 제공할 필요는 없으며, "
        "실제로 반복되는 시간표와 최근 학습 행동을 중심으로 정리해야 페이지의 학습 기준을 개인 상황에 맞게 판단할 수 있습니다."
    )

    pairs = [
        (question_1, answer_1),
        (question_2, answer_2),
        (question_3, answer_3),
        (question_4, answer_4),
        (question_5, answer_5),
    ]
    items = "\n".join(
        f'<h3 id="regional-faq-{index}">{escape(question)}</h3>\n<p>{answer}</p>'
        for index, (question, answer) in enumerate(pairs, start=1)
    )
    return (
        '<section class="regional-faq" aria-labelledby="regional-faq-heading">\n'
        f'<h2 id="regional-faq-heading">{escape(heading)}</h2>\n{items}\n</section>'
    )


def replace_regional_faq(body: str, page: Page, page_map: dict[str, Page]) -> str:
    """Replace an existing regional FAQ block while preserving surrounding original content."""
    replacement = render_regional_faq(page, page_map)
    if not replacement:
        return body
    wrapper = re.search(
        r'\s*<section\s+class=["\']regional-faq["\'][^>]*>.*?</section>\s*',
        body,
        flags=re.I | re.S,
    )
    if wrapper:
        return f"{body[:wrapper.start()].rstrip()}\n{replacement}\n{body[wrapper.end():].lstrip()}"
    bounds = faq_section_bounds(body)
    if not bounds:
        return f"{body.rstrip()}\n{replacement}"
    section_start, section_end, _ = bounds
    return f"{body[:section_start].rstrip()}\n{replacement}\n{body[section_end:].lstrip()}"


def enhance_content_body(body: str, *, clarify_scenarios: bool = False) -> tuple[str, str]:
    """Add stable heading anchors and a compact table of contents without changing text."""
    if clarify_scenarios:
        body = clarify_hypothetical_scenarios(body)
    body = deduplicate_faq_pairs(body)
    entries: list[tuple[int, str, str]] = []
    index = 0

    def add_anchor(match: re.Match[str]) -> str:
        nonlocal index
        level, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        if re.search(r"\bid\s*=", attrs, flags=re.I):
            anchor_match = re.search(r'\bid\s*=\s*["\']([^"\']+)', attrs, flags=re.I)
            anchor = anchor_match.group(1) if anchor_match else f"content-section-{index + 1}"
        else:
            index += 1
            anchor = f"content-section-{index}"
            attrs += f' id="{anchor}"'
        entries.append((int(level), anchor, plain_text(inner)))
        return f"<h{level}{attrs}>{inner}</h{level}>"

    enhanced = re.sub(r"<h([23])(\s[^>]*)?>(.*?)</h\1>", add_anchor, body, flags=re.I | re.S)
    visible = [entry for entry in entries if entry[2]][:24]
    if len(visible) < 2:
        return enhanced, ""
    links = "".join(
        f'<li class="toc-level-{level}"><a href="#{escape(anchor)}">{escape(label)}</a></li>'
        for level, anchor, label in visible
    )
    toc = (
        '<nav class="page-toc" aria-label="이 페이지의 목차">'
        '<details><summary>이 페이지의 내용</summary>'
        f'<ol>{links}</ol></details></nav>'
    )
    return enhanced, toc


def faq_schema(body: str) -> dict[str, object] | None:
    bounds = faq_section_bounds(body)
    if not bounds:
        return None
    _, section_end, section_start = bounds
    section = body[section_start:section_end]
    pairs = re.findall(r"<h3\b[^>]*>(.*?)</h3>\s*<p\b[^>]*>(.*?)</p>", section, flags=re.I | re.S)
    entities = []
    seen_questions: set[str] = set()
    for question, answer in pairs:
        question_text, answer_text = plain_text(question), plain_text(answer)
        if question_text and answer_text and question_text not in seen_questions:
            seen_questions.add(question_text)
            entities.append({"@type": "Question", "name": question_text, "acceptedAnswer": {"@type": "Answer", "text": answer_text}})
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities} if entities else None


def absolute_url(path: str) -> str:
    return SITE_URL + (path if path.startswith("/") else f"/{path}")


def load_fixed_image_manifest() -> list[dict[str, str]]:
    if not FIXED_IMAGE_MANIFEST.exists():
        return []
    data = json.loads(FIXED_IMAGE_MANIFEST.read_text(encoding="utf-8"))
    return list(data.get("images", []))


def load_search_thumbnail_manifest() -> list[str]:
    if not SEARCH_THUMBNAIL_MANIFEST.exists():
        return []
    data = json.loads(SEARCH_THUMBNAIL_MANIFEST.read_text(encoding="utf-8"))
    return list(data.get("images", []))


def build_search_thumbnail_url(src: str) -> str:
    return SITE_URL + "/" + "/".join(quote(part) for part in src.lstrip("/").split("/"))


def select_stable_search_thumbnail(page: Page) -> tuple[str, str, str]:
    thumbnails = load_search_thumbnail_manifest()
    if not thumbnails:
        fallback = "/assets/images/edunext-og.svg"
        return fallback, SITE_URL + fallback, ""
    digest = hashlib.sha256(page.slug.encode("utf-8")).hexdigest()
    src = thumbnails[int(digest, 16) % len(thumbnails)]
    return src, build_search_thumbnail_url(src), digest


def page_city(page: Page | None) -> str:
    if not page:
        return ""
    for city in CITIES:
        if page.slug.startswith(city):
            return city
    return ""


def compact_label(current: Page, target: Page, context: str = "") -> str:
    label = target.title
    if context == "parent":
        return label
    current_city = page_city(current)
    target_city = page_city(target)
    if context == "school-action":
        school = target.school_display_name or target.title
        if target.slug.endswith("수학과외"):
            return f"{school} 수학과외"
        if target.slug.endswith("영어과외"):
            return f"{school} 영어과외"
        return f"{school} 종합과외"
    if current_city and current_city == target_city and target.page_type != "school":
        label = label[len(target_city) :] if label.startswith(target_city) else label
    if target.page_type == "school":
        base = target.school_display_name or label
        if target.slug.endswith("수학과외"):
            return f"{base} 수학과외"
        if target.slug.endswith("영어과외"):
            return f"{base} 영어과외"
        return f"{base} 종합과외"
    return label or target.title


def unique_pages(slugs: list[str], page_map: dict[str, Page], current: Page, seen: set[str] | None = None) -> list[Page]:
    seen = seen if seen is not None else set()
    pages = []
    for slug in slugs:
        if slug in seen or slug not in page_map or slug == current.slug:
            continue
        seen.add(slug)
        pages.append(page_map[slug])
    return pages


def render_page_cards(title: str, pages: list[Page], current: Page, context: str = "") -> str:
    if not pages:
        return ""
    links = "".join(
        f'<li><a class="related-link-card" href="{escape(item.url)}">'
        f'<span>{escape(compact_label(current, item, context))}</span></a></li>'
        for item in pages
    )
    return f'<section class="related-section"><h2>{escape(title)}</h2><ul class="related-card-grid">{"".join(links)}</ul></section>'


def category_family_sections(page: Page, page_map: dict[str, Page], candidates: list[str], seen: set[str]) -> str:
    english = unique_pages([slug for slug in candidates if slug in page_map and page_map[slug].page_type != "school" and "영어" in page_map[slug].category], page_map, page, seen)
    math = unique_pages([slug for slug in candidates if slug in page_map and page_map[slug].page_type != "school" and "수학" in page_map[slug].category], page_map, page, seen)
    chunks = []
    if english:
        chunks.append(render_page_cards("영어 과목·학년별 과외", english, page))
    if math:
        chunks.append(render_page_cards("수학 과목·학년별 과외", math, page))
    return "".join(chunks)


def school_section(page: Page, page_map: dict[str, Page], seen: set[str] | None = None) -> str:
    school_slugs = _navigation_school_slugs(page, page_map)
    if not school_slugs:
        return ""
    seen = seen if seen is not None else set()
    title = "고등학교별 과외 찾기" if page.page_type == "home" else "관련 고등학교 학습 페이지"
    groups: dict[str, list[Page]] = {}
    for slug in school_slugs:
        item = page_map.get(slug)
        if not item:
            continue
        base = item.slug
        for suffix in ["수학과외", "영어과외", "과외"]:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        groups.setdefault(base, []).append(item)
    cards = []
    for base, items in sorted(groups.items()):
        items = sorted(items, key=lambda p: {"school": 0}.get(p.page_type, 1))
        items = [item for item in items if item.slug not in seen and item.slug != page.slug]
        if not items:
            continue
        seen.update(item.slug for item in items)
        links = "".join(f'<a href="{escape(item.url)}">{escape(compact_label(page, item, "school-action"))}</a>' for item in items)
        display = items[0].school_display_name or base
        official = items[0].official_school_name
        meta = f"<small>{escape(official)}</small>" if official else ""
        cards.append(f'<li class="school-card"><strong>{escape(display)}</strong>{meta}<div>{links}</div></li>')
    if not cards:
        return ""
    return f'<section class="link-section school-section" id="high-schools"><h2>{escape(title)}</h2><ul class="school-grid">{"".join(cards)}</ul></section>'


def render_related_navigation(page: Page, page_map: dict[str, Page], linked_content: str = "") -> str:
    used: set[str] = set()
    if page.page_type == "region" and page.category == "과외" and page.slug not in SPECIAL_REGION_HUBS:
        used.update(internal_link_slugs(linked_content))
    chunks = ['<nav class="related-navigation" aria-label="관련 페이지">']
    if page.slug in {"초등영어과외", "중등영어과외", "고등영어과외"}:
        grade = page.slug.removesuffix("영어과외")
        regional_grade = unique_pages(
            [f"{region}{grade}영어과외" for region in ("부산", "경남", "경북", "양산", "구미")],
            page_map,
            page,
            used,
        )
        chunks.append(render_page_cards(f"지역별 {grade}영어과외", regional_grade, page))
        grade_hubs = unique_pages(["영어과외", f"{grade}과외", f"{grade}수학과외"], page_map, page, used)
        chunks.append(render_page_cards("과목·학년 허브", grade_hubs, page))
        adjacent_by_grade = {
            "초등": ["중등영어과외"],
            "중등": ["초등영어과외", "고등영어과외"],
            "고등": ["중등영어과외"],
        }
        adjacent = unique_pages(adjacent_by_grade[grade], page_map, page, used)
        chunks.append(render_page_cards("이어지는 영어 학습 단계", adjacent, page))
    elif page.slug == "영어과외":
        regional_english = unique_pages(
            ["부산영어과외", "경남영어과외", "경북영어과외", "양산영어과외", "구미영어과외"],
            page_map,
            page,
            used,
        )
        chunks.append(render_page_cards("지역별 영어과외", regional_english, page))
        grade_english = unique_pages(
            ["초등영어과외", "중등영어과외", "고등영어과외"],
            page_map,
            page,
            used,
        )
        chunks.append(render_page_cards("학년별 영어과외", grade_english, page))
        overview = unique_pages(["전국과외", "수학과외"], page_map, page, used)
        chunks.append(render_page_cards("다른 학습 허브", overview, page))
    elif page.slug == "경남영어과외":
        overview = unique_pages(["경남과외", "영어과외", "양산영어과외"], page_map, page, used)
        chunks.append(render_page_cards("경남권 영어과외 둘러보기", overview, page))
        local_english = unique_pages(
            [
                "양산교동영어과외",
                "양산남부동영어과외",
                "양산동면영어과외",
                "양산물금읍영어과외",
                "양산중부동영어과외",
            ],
            page_map,
            page,
            used,
        )
        chunks.append(render_page_cards("양산 생활권별 영어과외", local_english, page))
    elif page.slug == "경북영어과외":
        overview = unique_pages(["경북과외", "영어과외", "구미영어과외"], page_map, page, used)
        chunks.append(render_page_cards("경북권 영어과외 둘러보기", overview, page))
        local_english = unique_pages(
            [
                "구미고아읍영어과외",
                "구미남통동영어과외",
                "구미사곡동영어과외",
                "구미산동읍영어과외",
                "구미송정동영어과외",
                "구미옥계동영어과외",
                "구미원평동영어과외",
                "구미형곡동영어과외",
            ],
            page_map,
            page,
            used,
        )
        chunks.append(render_page_cards("구미 생활권별 영어과외", local_english, page))
    parent = unique_pages([page.parent_slug or ""], page_map, page, used)
    if parent:
        chunks.append(render_page_cards("지역 둘러보기", parent, page, "parent"))
    child_regions = unique_pages([slug for slug in page.child_slugs if slug in page_map and page_map[slug].page_type == "region"], page_map, page, used)
    chunks.append(render_page_cards("하위 지역별 과외", child_regions, page))
    subject_links = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in SUBJECTS], page_map, page, used)
    chunks.append(render_page_cards("과목별 과외", subject_links, page))
    grade_links = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in GRADES], page_map, page, used)
    chunks.append(render_page_cards("학년별 과외", grade_links, page))
    sg_links = [slug for slug in page.related_slugs if slug in page_map and page_map[slug].category in SUBJECT_GRADES]
    chunks.append(category_family_sections(page, page_map, sg_links, used))
    school_related = unique_pages([slug for slug in page.related_slugs if slug in page_map and page_map[slug].page_type == "school"], page_map, page, used)
    chunks.append(render_page_cards("같은 학교·관련 학교", school_related, page))
    chunks.append(school_section(page, page_map, used))
    siblings = unique_pages([slug for slug in page.sibling_slugs if slug in page_map and page_map[slug].page_type == "region"], page_map, page, used)
    chunks.append(render_page_cards("같은 단계의 인접·형제 지역", siblings[:18], page))
    chunks.append("</nav>")
    body = "".join(chunks)
    return body if 'related-section' in body or 'school-section' in body else ""


def render_page_hero_image(page: Page) -> str:
    if page.page_type == "home" or not page.hero_image:
        return ""
    alt = page.hero_image_alt or page.title
    return f'<figure class="page-hero-image"><img src="{escape(page.hero_image)}" alt="{escape(alt)}"></figure>'


def render_fixed_images(page: Page) -> str:
    if page.page_type == "home":
        return ""
    figures = []
    for index, image in enumerate(load_fixed_image_manifest(), start=1):
        src = image.get("src", "")
        if not src:
            continue
        css_class = "representative-image" if index == 1 else "flow-image"
        alt = image.get("alt") or f"{page.title} 맞춤 과외 안내 이미지 {index:03d}"
        loading = "eager" if index == 1 else "lazy"
        priority = ' fetchpriority="high"' if index == 1 else ""
        width = f' width="{escape(str(image.get("width", "")))}"' if image.get("width") else ""
        height = f' height="{escape(str(image.get("height", "")))}"' if image.get("height") else ""
        figures.append(
            f'<figure class="{css_class}"><img src="{escape(src)}" alt="{escape(alt)}"{width}{height} loading="{loading}" decoding="async"{priority}></figure>'
        )
    if not figures:
        return ""
    return '<section class="page-fixed-images" aria-label="학습 안내 이미지">' + "".join(figures) + "</section>"


def breadcrumbs(page: Page) -> str:
    items = []
    crumbs = [("홈", "/")] + [item for item in page.breadcrumbs if item[1] != "/"]
    seen = set()
    filtered = []
    for name, url in crumbs:
        if url in seen:
            continue
        seen.add(url)
        filtered.append((name, url))
    for index, (name, url) in enumerate(filtered):
        if index == len(filtered) - 1:
            items.append(f'<li><span aria-current="page">{escape(name)}</span></li>')
        else:
            items.append(f'<li><a href="{escape(url)}">{escape(name)}</a></li>')
    return '<nav class="breadcrumb" aria-label="breadcrumb"><ol>' + "".join(items) + "</ol></nav>"


def schema(
    page: Page,
    body: str | None = None,
    *,
    page_name: str | None = None,
    page_description: str | None = None,
) -> str:
    crumbs = [("홈", "/")] + [item for item in page.breadcrumbs if item[1] != "/"]
    data = [
        {"@context": "https://schema.org", "@type": "Organization", "@id": f"{SITE_URL}/#organization", "name": SITE_NAME, "url": SITE_URL + "/"},
        {"@context": "https://schema.org", "@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": SITE_URL + "/", "name": SITE_NAME, "description": SITE_DESCRIPTION},
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": absolute_url(page.url) + "#webpage",
            "url": absolute_url(page.url),
            "name": page_name or page.title,
            "description": page_description or page.meta_description,
            "image": page.search_thumbnail_url,
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "inLanguage": "ko-KR",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name, "item": absolute_url(url)}
                for i, (name, url) in enumerate(crumbs)
            ],
        },
    ]
    faq = faq_schema(page.body if body is None else body)
    if faq:
        data.append(faq)
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def home_nav(page_map: dict[str, Page]) -> str:
    labels = [
        ("부산과외", "부산"),
        ("구미과외", "구미"),
        ("양산과외", "양산"),
        ("영어과외", "영어"),
        ("수학과외", "수학"),
        ("초등과외", "초등"),
        ("중등과외", "중등"),
        ("고등과외", "고등"),
    ]
    links = []
    for slug, label in labels:
        item = page_map.get(slug)
        if item:
            links.append(f'<a href="{escape(item.url)}">{escape(label)}</a>')
    links.append('<a href="/#high-schools">고등학교별 과외</a>')
    return "".join(links)


def home_link_list(items: list[tuple[str, str]], page_map: dict[str, Page]) -> str:
    links = []
    for slug, label in items:
        item = page_map.get(slug)
        if item:
            links.append(f'<li><a class="home-link-card" href="{escape(item.url)}">{escape(label)}</a></li>')
    return '<ul class="home-link-grid">' + "".join(links) + "</ul>" if links else ""


def primary_nav(page_map: dict[str, Page]) -> str:
    """Render the same compact global navigation on every page."""
    links = []
    for slug, label in [
        ("부산과외", "부산과외"),
        ("양산과외", "양산과외"),
        ("구미과외", "구미과외"),
    ]:
        item = page_map.get(slug)
        if item:
            links.append(f'<a href="{escape(item.url)}">{escape(label)}</a>')
    links.append('<a href="/#high-schools">고등학교별 과외</a>')
    return "".join(links)


def home_cta_grid(items: list[tuple[str, str, str]], page_map: dict[str, Page]) -> str:
    cards = []
    for slug, label, desc in items:
        href = f"/{slug}" if slug.startswith("#") else (page_map[slug].url if slug in page_map else "")
        if href:
            cards.append(f'<a class="home-cta-card" href="{escape(href)}"><strong>{escape(label)}</strong><span>{escape(desc)}</span></a>')
    return '<div class="home-cta-grid">' + "".join(cards) + "</div>"


def home_intro(title: str, body: str) -> str:
    return f'<div class="home-section-intro"><h2>{escape(title)}</h2><p>{escape(body)}</p></div>'


def home_school_groups(page_map: dict[str, Page]) -> dict[str, dict[str, list[Page]]]:
    groups: dict[str, dict[str, list[Page]]] = {"busan": {}, "gumi": {}, "yangsan": {}}
    city_keys = {CITIES[0]: "busan", CITIES[1]: "gumi", CITIES[2]: "yangsan"}
    for item in page_map.values():
        if item.page_type != "school":
            continue
        city = page_city(item)
        city_key = city_keys.get(city)
        if not city_key:
            continue
        base = item.school_display_name or item.official_school_name or item.title
        groups[city_key].setdefault(base, []).append(item)
    return groups


def render_home_school_card(name: str, items: list[Page]) -> str:
    ordered = sorted(items, key=lambda p: (0 if "怨쇱쇅" in p.slug and "?섑븰" not in p.slug and "?곸뼱" not in p.slug else 1 if "?섑븰" in p.slug else 2, p.slug))
    links = "".join(f'<a href="{escape(item.url)}">{escape(compact_label(item, item, "school-action"))}</a>' for item in ordered)
    official = next((item.official_school_name for item in ordered if item.official_school_name), "")
    meta = f"<small>{escape(official)}</small>" if official else ""
    return f'<li class="home-school-card"><strong>{escape(name)}</strong>{meta}<div>{links}</div></li>'


def render_home_school_section(section_id: str, title: str, groups: dict[str, list[Page]], visible_count: int) -> str:
    ordered = sorted(groups.items())
    visible = ordered[:visible_count]
    hidden = ordered[visible_count:]
    visible_cards = "".join(render_home_school_card(name, items) for name, items in visible)
    hidden_cards = "".join(render_home_school_card(name, items) for name, items in hidden)
    details = ""
    if hidden_cards:
        city = title.split()[0]
        details = (
            f'<details class="home-school-details"><summary>▼ {escape(city)} 고등학교 전체 보기</summary>'
            f'<ul class="home-school-grid home-school-grid-details">{hidden_cards}</ul></details>'
        )
    return (
        f'<section class="home-section home-school-section" id="{section_id}" data-visible-schools="{len(visible)}" data-hidden-schools="{len(hidden)}">'
        f'<h2>{escape(title)}</h2><p>대표 학교를 먼저 확인하고, 전체 보기를 열어 나머지 학교 페이지까지 이어서 탐색할 수 있습니다.</p>'
        f'<ul class="home-school-grid">{visible_cards}</ul>{details}</section>'
    )


def render_home_region_detail(page_map: dict[str, Page]) -> str:
    city_items = [("부산과외", "부산과외"), ("구미과외", "구미과외"), ("양산과외", "양산과외")]
    district_items = []
    for item in page_map.values():
        if item.page_type == "region" and item.parent_slug in {"부산과외", "구미과외", "양산과외"}:
            district_items.append((item.slug, item.title))
    district_items = sorted(district_items, key=lambda row: row[1])[:36]
    return (
        '<section class="home-section" id="region-detail">'
        + home_intro("지역별 과외 둘러보기", "도시별 대표 페이지와 하위 지역 페이지를 나누어 확인할 수 있습니다. 더 세부적인 동·읍·면 페이지는 각 지역 허브에서 이어서 탐색할 수 있습니다.")
        + home_link_list(city_items + district_items, page_map)
        + "</section>"
    )


def render_home(page: Page, page_map: dict[str, Page]) -> str:
    canonical = absolute_url(page.url)
    search_title = page.seo_title or page.title
    meta_description = page.meta_description
    if not page.search_thumbnail_url:
        page.search_thumbnail, page.search_thumbnail_url, page.search_thumbnail_hash = select_stable_search_thumbnail(page)
    city_cards = [
        ("부산", [("부산과외", "부산과외"), ("부산영어과외", "영어과외"), ("부산수학과외", "수학과외"), ("부산초등과외", "초등과외"), ("부산중등과외", "중등과외"), ("부산고등과외", "고등과외")], "busan-high-schools"),
        ("구미", [("구미과외", "구미과외"), ("구미영어과외", "영어과외"), ("구미수학과외", "수학과외"), ("구미초등과외", "초등과외"), ("구미중등과외", "중등과외"), ("구미고등과외", "고등과외")], "gumi-high-schools"),
        ("양산", [("양산과외", "양산과외"), ("양산영어과외", "영어과외"), ("양산수학과외", "수학과외"), ("양산초등과외", "초등과외"), ("양산중등과외", "중등과외"), ("양산고등과외", "고등과외")], "yangsan-high-schools"),
    ]
    city_html = []
    for city, links, anchor in city_cards:
        city_html.append(
            f'<article class="home-feature-card home-city-card"><span class="home-card-icon" aria-hidden="true">⌁</span><h3>{escape(city)}</h3><p>{escape(city)} 지역 대표 과외 페이지에서 과목과 학년별 정보를 이어서 확인할 수 있습니다.</p>'
            + home_link_list(links, page_map)
            + f'<a class="home-anchor-link" href="/#{anchor}">{escape(city)} 고등학교 보기</a></article>'
        )
    subject_html = (
        '<article class="home-feature-card home-subject-card"><span class="home-card-icon" aria-hidden="true">A</span><h3>영어과외</h3><p>지역별 영어와 학년별 영어 페이지를 한 번에 좁혀 볼 수 있습니다.</p>'
        + home_link_list([("부산영어과외", "부산영어과외"), ("구미영어과외", "구미영어과외"), ("양산영어과외", "양산영어과외"), ("초등영어과외", "초등영어과외"), ("중등영어과외", "중등영어과외"), ("고등영어과외", "고등영어과외")], page_map)
        + '</article><article class="home-feature-card home-subject-card"><span class="home-card-icon" aria-hidden="true">∑</span><h3>수학과외</h3><p>수학 과목 페이지와 초등·중등·고등 수학 흐름을 분리해 탐색합니다.</p>'
        + home_link_list([("부산수학과외", "부산수학과외"), ("구미수학과외", "구미수학과외"), ("양산수학과외", "양산수학과외"), ("초등수학과외", "초등수학과외"), ("중등수학과외", "중등수학과외"), ("고등수학과외", "고등수학과외")], page_map)
        + "</article>"
    )
    grade_html = (
        '<article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">01</span><h3>초등</h3><p>기초 학습과 과목별 준비 흐름을 함께 확인합니다.</p>'
        + home_link_list([("부산초등과외", "부산초등과외"), ("구미초등과외", "구미초등과외"), ("양산초등과외", "양산초등과외"), ("초등영어과외", "초등영어과외"), ("초등수학과외", "초등수학과외")], page_map)
        + '</article><article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">02</span><h3>중등</h3><p>내신과 고등 준비 사이의 연결 지점을 살펴봅니다.</p>'
        + home_link_list([("부산중등과외", "부산중등과외"), ("구미중등과외", "구미중등과외"), ("양산중등과외", "양산중등과외"), ("중등영어과외", "중등영어과외"), ("중등수학과외", "중등수학과외")], page_map)
        + '</article><article class="home-feature-card home-grade-card"><span class="home-card-icon" aria-hidden="true">03</span><h3>고등</h3><p>학교별 내신과 과목별 학습 페이지로 바로 이어집니다.</p>'
        + home_link_list([("부산고등과외", "부산고등과외"), ("구미고등과외", "구미고등과외"), ("양산고등과외", "양산고등과외"), ("고등영어과외", "고등영어과외"), ("고등수학과외", "고등수학과외")], page_map)
        + '<a class="home-anchor-link" href="/#high-schools">고등학교별 과외</a></article>'
    )
    school_groups = home_school_groups(page_map)
    body = f"""
    <section class="home-hero">
      <figure class="home-hero-image"><img src="/assets/images/home/home-hero.png" alt="함께 공부하는 학생과 선생님" loading="eager" decoding="async" fetchpriority="high"></figure>
      <div class="home-hero-copy">
        <p class="eyebrow">부산 · 양산 · 구미 프리미엄 과외 정보</p>
        <h1>{escape(page.title)}</h1>
        <p class="home-hero-lead">지역별 과외, 학교별 과외, 영어·수학, 학년별 과외를 한곳에서 찾을 수 있습니다.</p>
        {home_cta_grid([("부산과외", "부산과외", "지역별 대표 허브"), ("구미과외", "구미과외", "구미 학습 페이지"), ("양산과외", "양산과외", "양산 지역 탐색"), ("#high-schools", "학교별과외", "고등학교별 이동")], page_map)}
      </div>
    </section>
    <section class="home-section" id="city-tutoring">
      {home_intro("부산·구미·양산 지역별 과외", "도시별 대표 페이지에서 과목과 학년 페이지로 이어집니다. 먼저 지역을 고른 뒤 영어·수학, 초등·중등·고등 흐름을 좁혀 볼 수 있습니다.")}
      <div class="home-card-grid">{"".join(city_html)}</div>
    </section>
    <section class="home-section" id="subjects">
      {home_intro("과목별 과외 찾기", "영어와 수학 페이지를 분리해 배치했습니다. 지역별 과목 페이지와 학년 결합 페이지를 함께 확인할 수 있습니다.")}
      <div class="home-card-grid two-columns">{subject_html}</div>
    </section>
    <section class="home-section" id="grades">
      {home_intro("학년별 과외 찾기", "초등·중등·고등 단계별로 대표 지역 페이지와 과목 결합 페이지를 이어서 볼 수 있습니다.")}
      <div class="home-card-grid three-columns">{grade_html}</div>
    </section>
    <section class="home-section home-school-hub" id="high-schools">
      <h2>고등학교별 과외 찾기</h2>
      <p>부산·구미·양산의 고등학교별 종합과외, 수학과외, 영어과외 페이지를 지역별로 확인할 수 있습니다.</p>
      <nav class="home-school-jump" aria-label="도시별 고등학교 바로가기"><a href="/#busan-high-schools">부산 고등학교</a><a href="/#gumi-high-schools">구미 고등학교</a><a href="/#yangsan-high-schools">양산 고등학교</a></nav>
    </section>
    {render_home_school_section("busan-high-schools", "부산 고등학교별 과외", school_groups["busan"], 24)}
    {render_home_school_section("gumi-high-schools", "구미 고등학교별 과외", school_groups["gumi"], 12)}
    {render_home_school_section("yangsan-high-schools", "양산 고등학교별 과외", school_groups["yangsan"], 8)}
    {render_home_region_detail(page_map)}
    <section class="home-section" id="site-guide">
      <h2>사이트 이용 안내</h2>
      <p>각 링크는 실제 생성된 정적 HTML 페이지로 연결됩니다. 상담 정보, 전화번호, 가격, 평점처럼 확인되지 않은 정보는 임의로 표시하지 않습니다.</p>
    </section>
    """
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="naver-site-verification" content="{escape(NAVER_SITE_VERIFICATION)}" />
  <title>{escape(search_title)}</title>
  <meta name="description" content="{escape(meta_description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{escape(search_title)}">
  <meta property="og:description" content="{escape(meta_description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(page.search_thumbnail_url)}">
  <meta property="og:image:alt" content="{escape(page.title)} 대표 이미지">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(search_title)}">
  <meta name="twitter:description" content="{escape(meta_description)}">
  <meta name="twitter:image" content="{escape(page.search_thumbnail_url)}">
  <link rel="stylesheet" href="/assets/css/style.css?v=20260901-link-quality">
  {schema(page)}
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header">
    <span class="brand" aria-current="page">EduNext</span>
    <button class="menu-toggle" type="button" aria-label="메뉴 열기">☰</button>
    <nav class="top-nav">{primary_nav(page_map)}</nav>
  </header>
  <main id="main" class="home-main">
    {body}
  </main>
  <footer class="site-footer">
    <p>© {date.today().year} EduNext. 실제 상담 정보, 전화번호, 평점은 임의로 표시하지 않습니다.</p>
    <a href="/sitemap.xml">Sitemap</a>
  </footer>
  <script src="/assets/js/main.js" defer></script>
</body>
</html>
"""


def render_page(page: Page, page_map: dict[str, Page]) -> str:
    if page.page_type == "home":
        return render_home(page, page_map)
    canonical = absolute_url(page.url)
    search_title = page.seo_title or page.title
    meta_description = page.meta_description
    if is_local_middle_english_slug(page.slug):
        search_title, meta_description = build_local_middle_english_meta(page.slug)
    if not page.search_thumbnail_url:
        page.search_thumbnail, page.search_thumbnail_url, page.search_thumbnail_hash = select_stable_search_thumbnail(page)
    body = individualize_local_middle_english_body(page.body, page.slug)
    body = individualize_secondary_region_body(body, page)
    body = individualize_priority_region_body(body, page)
    body = polish_priority_region_math_body(body, page)
    body = add_contextual_region_links(body, page, page_map)
    body = replace_regional_faq(body, page, page_map)
    body = deduplicate_region_body_links(body, page)
    enhanced_body, toc = enhance_content_body(
        body,
        clarify_scenarios=page.page_type == "region" and page.category == "과외",
    )
    sections = render_related_navigation(page, page_map, enhanced_body)
    nav = "".join(
        f'<a href="{escape(page_map[slug].url)}">{escape(page_map[slug].title)}</a>'
        for slug in ["부산과외", "양산과외", "구미과외", "영어과외", "수학과외", "초등과외", "중등과외", "고등과외"]
        if slug in page_map and page_map[slug].url != page.url
    )
    if page.page_type != "home":
        nav += '<a href="/#high-schools">고등학교별 과외</a>'
    nav = primary_nav(page_map)
    brand = '<span class="brand" aria-current="page">EduNext</span>' if page.url == "/" else '<a class="brand" href="/">EduNext</a>'
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(search_title)}</title>
  <meta name="description" content="{escape(meta_description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{escape(search_title)}">
  <meta property="og:description" content="{escape(meta_description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(page.search_thumbnail_url)}">
  <meta property="og:image:alt" content="{escape(page.title)} 대표 이미지">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(search_title)}">
  <meta name="twitter:description" content="{escape(meta_description)}">
  <meta name="twitter:image" content="{escape(page.search_thumbnail_url)}">
  <link rel="stylesheet" href="/assets/css/style.css?v=20260901-link-quality">
  {schema(page, body, page_name=search_title, page_description=meta_description)}
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header">
    {brand}
    <button class="menu-toggle" type="button" aria-label="메뉴 열기">☰</button>
    <nav class="top-nav">{nav}</nav>
  </header>
  <main id="main" class="page-main page-type-{escape(page.page_type)}">
    {breadcrumbs(page)}
    <section class="page-hero">
      <p class="eyebrow">부산·양산·구미 과외 정보</p>
      <h1>{escape(page.title)}</h1>
      <p>{escape(meta_description)}</p>
    </section>
    {render_page_hero_image(page)}
    {render_fixed_images(page)}
    {toc}
    <article class="content-body">{enhanced_body}</article>
    {sections}
  </main>
  <footer class="site-footer">
    <p>© {date.today().year} EduNext. 실제 상담 정보, 전화번호, 평점은 임의로 표시하지 않습니다.</p>
    <a href="/sitemap.xml">Sitemap</a>
  </footer>
  <script src="/assets/js/main.js" defer></script>
</body>
</html>
"""


def render_not_found() -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>페이지를 찾을 수 없습니다 | {SITE_NAME}</title>
  <meta name="robots" content="noindex,follow">
  <link rel="stylesheet" href="/assets/css/style.css?v=20260901-link-quality">
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header"><a class="brand" href="/">{SITE_NAME}</a></header>
  <main id="main" class="page-main">
    <section class="page-hero">
      <p class="eyebrow">404 · Page not found</p>
      <h1>페이지를 찾을 수 없습니다</h1>
      <p>주소가 변경되었거나 존재하지 않는 페이지입니다. 홈페이지에서 지역·과목·학교별 과외 정보를 다시 찾아보세요.</p>
      <p><a class="home-anchor-link" href="/">EduNext 홈으로 이동</a></p>
    </section>
  </main>
</body>
</html>
"""
