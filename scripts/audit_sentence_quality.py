from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sitegen.text_quality import PARTICLE_NOUNS


OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "audit" / "sentence-quality-audit.json"


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = VisibleTextParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def visible_text_parts(value: str) -> list[str]:
    parser = VisibleTextParser()
    parser.feed(value)
    return [re.sub(r"\s+", " ", item).strip() for item in parser.parts if item.strip()]


def article_html(html: str) -> str:
    match = re.search(r'<article\b[^>]*class="[^"]*content-body[^"]*"[^>]*>(.*?)</article>', html, flags=re.I | re.S)
    return match.group(1) if match else html


def has_final(value: str) -> tuple[bool, bool]:
    for char in reversed(value):
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            final_index = code % 28
            return final_index != 0, final_index == 8
    return False, False


def expected_particle(noun: str, particle: str) -> str:
    final, rieul = has_final(noun)
    if particle in {"을", "를"}:
        return "을" if final else "를"
    if particle in {"은", "는"}:
        return "은" if final else "는"
    if particle in {"이", "가"}:
        return "이" if final else "가"
    if particle in {"과", "와"}:
        return "과" if final else "와"
    return "으로" if final and not rieul else "로"


NOUN_PATTERN = re.compile(
    rf"(?P<noun>{'|'.join(sorted((re.escape(item) for item in PARTICLE_NOUNS), key=len, reverse=True))})"
    r"(?P<particle>으로|로|을|를|은|는|이|가|과|와)(?=[^가-힣]|$)"
)
FINITE_PARTICLE = re.compile(r"[가-힣]+니다(?:을|를|은|는|이|가|과|와)(?=[^가-힣]|$)")
MISSING_BOUNDARY = re.compile(r"[가-힣]+니다\s+(?=[가-힣A-Z])")
MALFORMED = re.compile(r"조학생과|읽음할 때|만남할 때|뼈대표|계획 가설")
ADJACENT_REPEAT = re.compile(
    r"(?<![가-힣])(?P<word>[가-힣]{2,})\s+(?P=word)"
    r"(?P<particle>으로|에서|에게|부터|까지|로|을|를|은|는|이|가|과|와|의|도|만|에)?(?=[^가-힣]|$)"
)
MISSING_STUDENT_PARTICLE = re.compile(r"학습 (?:계획|관리|과정|기준|기록) 학생에게")
SPACED_COPULA = re.compile(r"(?<=[가-힣0-9”’)])\s+입니다(?=[.\s]|$)")
GRADE_PARTICLE_SPACE = re.compile(r"(?<![가-힣])(?:초|중|고)[1-6]\s+(?:은|는|이|가|을|를|과|와)")


def main() -> int:
    pages = sorted(OUTPUT.glob("*/index.html"))
    issue_counts: Counter[str] = Counter()
    issue_pages: Counter[str] = Counter()
    examples: list[dict[str, str]] = []
    chars: list[int] = []
    focus_counts: list[int] = []

    for path in pages:
        html = path.read_text(encoding="utf-8", errors="ignore")
        article = article_html(html)
        text_parts = visible_text_parts(article)
        text = " ".join(text_parts)
        chars.append(len(text))
        page_rules: set[str] = set()

        metadata_values = [
            unescape(value)
            for value in (
                re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S).group(1)
                if re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
                else "",
                *re.findall(
                    r'<meta\b[^>]*(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"[^>]*content="([^"]*)"',
                    html,
                    flags=re.I,
                ),
            )
            if value
        ]
        metadata_repeats = [match.group(0) for value in metadata_values for match in ADJACENT_REPEAT.finditer(value)]
        if metadata_repeats:
            issue_counts["metadata_adjacent_word_repeat"] += len(metadata_repeats)
            page_rules.add("metadata_adjacent_word_repeat")
            if len(examples) < 40:
                examples.append(
                    {"slug": path.parent.name, "rule": "metadata_adjacent_word_repeat", "match": metadata_repeats[0]}
                )

        wrong_particles = []
        for part in text_parts:
            wrong_particles.extend(
                match.group(0)
                for match in NOUN_PATTERN.finditer(part)
                if match.group("particle") != expected_particle(match.group("noun"), match.group("particle"))
            )
        checks = {
            "wrong_known_noun_particle": wrong_particles,
            "finite_sentence_particle": [match.group(0) for part in text_parts for match in FINITE_PARTICLE.finditer(part)],
            "missing_sentence_boundary": [match.group(0) for part in text_parts for match in MISSING_BOUNDARY.finditer(part)],
            "malformed_phrase": [match.group(0) for part in text_parts for match in MALFORMED.finditer(part)],
            "adjacent_word_repeat": [match.group(0) for part in text_parts for match in ADJACENT_REPEAT.finditer(part)],
            "missing_student_particle": [
                match.group(0) for part in text_parts for match in MISSING_STUDENT_PARTICLE.finditer(part)
            ],
            "spaced_copula": [match.group(0) for part in text_parts for match in SPACED_COPULA.finditer(part)],
            "grade_particle_space": [
                match.group(0) for part in text_parts for match in GRADE_PARTICLE_SPACE.finditer(part)
            ],
        }
        for rule, hits in checks.items():
            if not hits:
                continue
            issue_counts[rule] += len(hits)
            page_rules.add(rule)
            if len(examples) < 40:
                examples.append({"slug": path.parent.name, "rule": rule, "match": hits[0]})

        paragraphs = [
            plain_text(match.group(1))
            for match in re.finditer(r"<p\b[^>]*>(.*?)</p>", article, flags=re.I | re.S)
        ]
        paragraph_counts = Counter(item for item in paragraphs if len(item) >= 45)
        duplicate_paragraphs = sum(count - 1 for count in paragraph_counts.values() if count > 1)
        if duplicate_paragraphs:
            issue_counts["duplicate_paragraph"] += duplicate_paragraphs
            page_rules.add("duplicate_paragraph")

        headings = [
            plain_text(match.group(1))
            for match in re.finditer(r"<h[23]\b[^>]*>(.*?)</h[23]>", article, flags=re.I | re.S)
        ]
        heading_counts = Counter(item for item in headings if item)
        duplicate_headings = sum(count - 1 for count in heading_counts.values() if count > 1)
        if duplicate_headings:
            issue_counts["duplicate_heading"] += duplicate_headings
            page_rules.add("duplicate_heading")

        # The data-*-focus attributes contain a page-specific learning theme
        # (for example "요약하기"), not the search keyword. Repetition checks
        # therefore use the actual slug phrase instead of misclassifying normal
        # references to the lesson theme as keyword stuffing.
        focus = path.parent.name
        focus_count = text.count(focus)
        focus_counts.append(focus_count)
        if focus_count > 30:
            issue_counts["excessive_primary_keyword_repetition"] += focus_count - 30
            page_rules.add("excessive_primary_keyword_repetition")
            if len(examples) < 40:
                examples.append(
                    {
                        "slug": path.parent.name,
                        "rule": "excessive_primary_keyword_repetition",
                        "match": f"{focus}: {focus_count}회",
                    }
                )

        for rule in page_rules:
            issue_pages[rule] += 1

    summary = {
        "page_count": len(pages),
        "issue_count": sum(issue_counts.values()),
        "issue_counts": dict(issue_counts),
        "issue_pages": dict(issue_pages),
        "visible_chars": {
            "min": min(chars) if chars else 0,
            "median": round(statistics.median(chars), 1) if chars else 0,
            "max": max(chars) if chars else 0,
            "total": sum(chars),
        },
        "primary_keyword_repetition": {
            "page_count": len(focus_counts),
            "median": round(statistics.median(focus_counts), 1) if focus_counts else 0,
            "max": max(focus_counts) if focus_counts else 0,
        },
        "examples": examples,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "examples"}, ensure_ascii=False, indent=2))
    print(f"report={REPORT}")
    return 1 if summary["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
