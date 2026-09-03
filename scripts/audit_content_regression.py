from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "audit" / "content-regression-audit.json"


def visible_characters(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    match = re.search(r'<article\b[^>]*class=["\'][^"\']*content-body[^"\']*["\'][^>]*>(.*?)</article>', source, re.I | re.S)
    if not match:
        match = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.I | re.S)
    fragment = match.group(1) if match else source
    fragment = re.sub(r"<(?:script|style|noscript)\b.*?</(?:script|style|noscript)>", " ", fragment, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return len(" ".join(text.split()))


def page_paths(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("index.html")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare visible content length with a pre-change site snapshot.")
    parser.add_argument("current", type=Path)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()

    current = page_paths(args.current)
    baseline = page_paths(args.baseline)
    missing = sorted(set(baseline) - set(current))
    added = sorted(set(current) - set(baseline))
    comparisons: list[dict[str, object]] = []
    for relative in sorted(set(current) & set(baseline)):
        before = visible_characters(baseline[relative])
        after = visible_characters(current[relative])
        comparisons.append(
            {
                "page": relative.removesuffix("index.html") or "/",
                "before": before,
                "after": after,
                "delta": after - before,
            }
        )

    decreased = [item for item in comparisons if int(item["delta"]) < 0]
    increased = [item for item in comparisons if int(item["delta"]) > 0]
    unchanged = [item for item in comparisons if int(item["delta"]) == 0]
    deltas = [int(item["delta"]) for item in comparisons]
    report = {
        "current_pages": len(current),
        "baseline_pages": len(baseline),
        "common_pages": len(comparisons),
        "missing_pages": missing,
        "added_pages": added,
        "decreased_page_count": len(decreased),
        "increased_page_count": len(increased),
        "unchanged_page_count": len(unchanged),
        "total_character_delta": sum(deltas),
        "minimum_delta": min(deltas) if deltas else 0,
        "maximum_delta": max(deltas) if deltas else 0,
        "average_delta": round(sum(deltas) / len(deltas), 1) if deltas else 0,
        "decreased_pages": sorted(decreased, key=lambda item: int(item["delta"])),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "decreased_pages"}, ensure_ascii=False, indent=2))
    if decreased:
        print("largest decreases:")
        for item in report["decreased_pages"][:20]:
            print(f"  {item['page']}: {item['before']} -> {item['after']} ({item['delta']:+d})")
    print(f"report={REPORT_PATH}")
    return 1 if missing or decreased else 0


if __name__ == "__main__":
    raise SystemExit(main())
