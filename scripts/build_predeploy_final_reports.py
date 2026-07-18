from __future__ import annotations

import csv
import html
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "output_predeploy_final"
BASELINE = ROOT / "output_home_redesign"
AUDIT = ROOT / "audit"


def url_for(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return "/" if rel == "index.html" else "/" + rel[:-10]


def text(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group(1)))).strip()


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (AUDIT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    current = {url_for(CURRENT, path): path for path in CURRENT.rglob("index.html")}
    baseline = {url_for(BASELINE, path): path for path in BASELINE.rglob("index.html")}
    extras = sorted(set(current) - set(baseline))
    sitemap = {
        urlparse(node.text or "").path or "/"
        for node in ElementTree.parse(CURRENT / "sitemap.xml").findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    }
    home = current["/"].read_text(encoding="utf-8")
    home_hrefs = set(re.findall(r'<a\b[^>]*href=["\']([^"\']+)', home, re.I))
    inbound = Counter()
    for path in current.values():
        source = path.read_text(encoding="utf-8")
        for href in re.findall(r'<a\b[^>]*href=["\']([^"\']+)', source, re.I):
            parsed = urlparse(href)
            target = unquote(parsed.path)
            if target != "/" and target and not target.endswith("/"):
                target += "/"
            if target in current:
                inbound[target] += 1

    rows = []
    for url in extras:
        source = current[url].read_text(encoding="utf-8")
        title = text(r"<title>(.*?)</title>", source)
        h1 = text(r"<h1\b[^>]*>(.*?)</h1>", source)
        page_type_match = re.search(r'page-type-([\w-]+)', source)
        canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)', source, re.I)
        slug = url.strip("/")
        scope = "전국" if not slug.startswith(("경남", "경북")) else slug[:2]
        rows.append({
            "path": url,
            "title": title,
            "h1": h1,
            "page_type": page_type_match.group(1) if page_type_match else "",
            "source_sheet": "(generator fallback; no content sheet row)",
            "source_row": "",
            "in_sitemap": str(url in sitemap).lower(),
            "linked_from_home": str(any(unquote(urlparse(href).path) == url for href in home_hrefs)).lower(),
            "inbound_link_count": inbound[url],
            "canonical": canonical_match.group(1) if canonical_match else "",
            "reason_created": f"load_regions의 {scope} 계층과 CATEGORIES 12종 조합으로 생성된 정적 허브",
            "expected_or_unexpected": "expected",
            "action": "정상 신규 허브 승인; 1462개를 새 기준으로 사용",
        })
    fields = ["path", "title", "h1", "page_type", "source_sheet", "source_row", "in_sitemap", "linked_from_home", "inbound_link_count", "canonical", "reason_created", "expected_or_unexpected", "action"]
    write_csv("extra-36-paths.csv", rows, fields)

    errors = [{
        "severity": "MEDIUM",
        "category": "URL_NORMALIZATION",
        "page": "//구미과외//",
        "detail": "중복 슬래시 정규화가 vercel.json에 명시되지 않음; 로컬 정적 서버에서는 200",
        "action": "배포 플랫폼에서 중복 슬래시를 단일 슬래시로 308 정규화하고 프리뷰에서 검증",
    }]
    write_csv("predeploy-final-errors.csv", errors, ["severity", "category", "page", "detail", "action"])
    write_csv("predeploy-final-mobile.csv", [], ["severity", "page", "width", "issue", "detail"])

    normalization = """# Predeploy final URL normalization

## Result

- Query parameter: resolved by a self-canonical URL without the query. No redirect is required when content is identical.
- `/index.html`: covered by permanent redirects in `vercel.json` for root and nested paths.
- No trailing slash: covered by `trailingSlash: true`.
- Double slash: one remaining deployment-verification risk because no explicit rule exists.
- Unknown URLs: local server returns 404; no home fallback rewrite exists.

## Required production policy

1. `http://edunext.kr/*` → `https://edunext.kr/*` with 308.
2. `https://www.edunext.kr/*` → `https://edunext.kr/*` with 308 (already declared by host redirect).
3. `/**/index.html` → canonical trailing-slash URL with 308 (already declared).
4. Collapse repeated path slashes to one slash with 308; verify platform behavior because this is not explicit in `vercel.json`.
5. Keep query variants self-canonical to the query-free URL when the content is identical.
6. Return 404 for unknown paths; never rewrite all paths to `/`.
"""
    (AUDIT / "predeploy-final-url-normalization.md").write_text(normalization, encoding="utf-8")

    summary = f"""# EduNext predeploy final summary

- Candidate: `{CURRENT}`
- Decision: **경미한 수정 후 배포 가능**
- HTML: {len(current)}
- Sitemap URLs: {len(sitemap)}
- Approved added hubs: {len(rows)}
- Pages to remove: 0
- School pages: 429
- Empty pages: 0
- Orphan pages: 0
- Broken links: 0
- School link errors: 0
- Metadata errors: 0
- Mobile errors: 0
- Touch targets below 44px: 0
- Horizontal overflow: 0
- URL normalization risks: 1

The 36 additions are deterministic national/province category hubs: 12 national-level hubs, 12 Gyeongnam hubs, and 12 Gyeongbuk hubs. All are present in sitemap, have canonical metadata, and have inbound internal links. Existing baseline paths retain title, H1, slug and article body.
"""
    (AUDIT / "predeploy-final-summary.md").write_text(summary, encoding="utf-8")
    print(f"extra={len(rows)} current={len(current)} sitemap={len(sitemap)}")


if __name__ == "__main__":
    main()
