from __future__ import annotations

from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
REPORT_PATH = ROOT / "audit" / "numeric-content-audit.json"


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.text_parts: list[str] = []
        self.heading_tag: str | None = None
        self.heading_parts: list[str] = []
        self.headings: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if not self.skip_depth and tag in {"h1", "h2", "h3"}:
            self.heading_tag = tag
            self.heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if not self.skip_depth and tag == self.heading_tag:
            heading = " ".join("".join(self.heading_parts).split())
            if heading:
                self.headings.append((tag, heading))
            self.heading_tag = None
            self.heading_parts = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.text_parts.append(data)
        if self.heading_tag:
            self.heading_parts.append(data)


def family_for(html: str, slug: str) -> str:
    markers = [
        ("middle-school-english", "middle-school-english-guide"),
        ("middle-school-math", "middle-school-math-guide"),
        ("school-english", "school-english-guide"),
        ("school-math", "school-math-guide"),
        ("school-general", "school-general-guide"),
        ("local-elementary-english", "elementary-english-content"),
        ("local-elementary-math", "elementary-math-content"),
        ("local-elementary-general", "elementary-general-content"),
        ("local-middle-english", "middle-english-content"),
        ("local-middle-math", "middle-math-content"),
        ("local-middle-general", "middle-general-content"),
        ("local-high-english", "high-english-content"),
        ("local-high-math", "high-math-content"),
        ("local-high-general", "high-general-content"),
        ("priority-region", "priority-region-content"),
        ("secondary-region", "secondary-region-content"),
    ]
    for family, marker in markers:
        if marker in html:
            return family
    for suffix, family in [
        ("초등영어과외", "local-elementary-english"),
        ("초등수학과외", "local-elementary-math"),
        ("초등과외", "local-elementary-general"),
        ("중등영어과외", "local-middle-english"),
        ("중등수학과외", "local-middle-math"),
        ("중등과외", "local-middle-general"),
        ("고등영어과외", "local-high-english"),
        ("고등수학과외", "local-high-math"),
        ("고등과외", "local-high-general"),
        ("영어과외", "region-english"),
        ("수학과외", "region-math"),
        ("과외", "region-general"),
    ]:
        if slug.endswith(suffix):
            return family
    return "other"


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def audit_page(path: Path) -> dict[str, object]:
    html = path.read_text(encoding="utf-8")
    slug = path.parent.name
    parser = VisibleTextParser()
    parser.feed(html)
    visible = " ".join(" ".join(parser.text_parts).split())
    compact = re.sub(r"\s+", "", visible)
    digit_count = len(re.findall(r"\d", visible))
    numeric_headings = [text for _, text in parser.headings if re.search(r"\d", text)]
    long_questions = [
        text for tag, text in parser.headings
        if tag == "h3" and text.endswith("?") and len(text) >= 55
    ]
    return {
        "slug": slug,
        "family": family_for(html, slug),
        "visible_characters": len(compact),
        "digit_count": digit_count,
        "digits_per_1000_characters": round(digit_count * 1000 / max(1, len(compact)), 2),
        "heading_count": len(parser.headings),
        "numeric_heading_count": len(numeric_headings),
        "numeric_headings": numeric_headings,
        "long_question_count": len(long_questions),
        "long_questions": long_questions,
        "mentions_24_72": len(re.findall(r"24\s*[·~ㆍ]\s*72|24시간|72시간", visible)),
        "mentions_28_day": len(re.findall(r"28일", visible)),
        "mentions_3_day": len(re.findall(r"3일|사흘|셋째 날", visible)),
        "has_28_daily_rows": all(f"{day}일" in visible for day in (1, 7, 14, 21, 28)),
    }


def summarize(pages: list[dict[str, object]]) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for page in pages:
        groups[str(page["family"])].append(page)
    summaries: dict[str, object] = {}
    for family, items in sorted(groups.items()):
        ratios = [float(item["digits_per_1000_characters"]) for item in items]
        visible_characters = [int(item["visible_characters"]) for item in items]
        numeric_headings = [int(item["numeric_heading_count"]) for item in items]
        summaries[family] = {
            "pages": len(items),
            "visible_characters_min": min(visible_characters),
            "visible_characters_median": round(statistics.median(visible_characters)),
            "visible_characters_max": max(visible_characters),
            "digits_per_1000_median": round(statistics.median(ratios), 2),
            "digits_per_1000_p95": round(percentile(ratios, 0.95), 2),
            "numeric_headings_median": statistics.median(numeric_headings),
            "pages_with_numeric_headings": sum(bool(value) for value in numeric_headings),
            "pages_with_long_questions": sum(bool(item["long_question_count"]) for item in items),
            "pages_with_24_72": sum(bool(item["mentions_24_72"]) for item in items),
            "pages_with_28_day": sum(bool(item["mentions_28_day"]) for item in items),
            "pages_with_28_daily_rows": sum(bool(item["has_28_daily_rows"]) for item in items),
        }
    return summaries


def main() -> None:
    paths = sorted(OUTPUT.glob("*/index.html"))
    pages = [audit_page(path) for path in paths]
    report = {
        "page_count": len(pages),
        "families": summarize(pages),
        "highest_numeric_density": sorted(
            pages,
            key=lambda page: float(page["digits_per_1000_characters"]),
            reverse=True,
        )[:30],
        "pages_with_24_72": [
            page for page in pages if int(page["mentions_24_72"]) > 0
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"page_count": report["page_count"], "families": report["families"]}, ensure_ascii=False, indent=2))
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
