from __future__ import annotations

import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output"
REPORT = ROOT / "audit" / "text-anomaly-audit.json"


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


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sentence_then_particle", re.compile(r"(?:다|요|죠|니다|세요|십시오)\.(?:을|를|이|가|은|는)(?=\s|[^가-힣]|$)")),
    ("wrong_state_particle", re.compile(r"상태을")),
    ("wrong_table_particle", re.compile(r"(?:조건표|판단표|변환표|강도표|역할표|전환표|연결표|점검표|준비표|뼈대 표)을")),
    ("word_corruption", re.compile(r"뼈대표|계획 가설")),
    ("unfinished_placeholder", re.compile(r"TODO|FIXME|undefined|\{\{[^}]+\}\}|\{[a-zA-Z_][^}]*\}")),
    ("artificial_review_number", re.compile(r"24\s*[·/]\s*72|24시간|72시간|28일")),
)


def visible_text(path: Path) -> str:
    parser = VisibleTextParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def main() -> int:
    hits: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    pages = sorted(OUTPUT.glob("*/index.html"))
    for path in pages:
        text = visible_text(path)
        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 70)
                end = min(len(text), match.end() + 70)
                hits.append({"slug": path.parent.name, "rule": name, "match": match.group(0), "context": text[start:end]})
                counts[name] += 1
    payload = {"page_count": len(pages), "hit_count": len(hits), "counts": dict(counts), "hits": hits}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "hits"}, ensure_ascii=False, indent=2))
    if hits:
        for hit in hits[:30]:
            print(f"{hit['slug']} [{hit['rule']}] {hit['context']}")
    print(f"report={REPORT}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
