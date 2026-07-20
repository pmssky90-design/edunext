from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import CONTENT_EXCEL, SITE_URL
from sitegen.data_loader import load_content, load_regions, load_school_region_map
from sitegen.pages import build_pages
from sitegen.utils import strip_tags

OUTPUT = ROOT / os.environ.get("EDUNEXT_SCHOOL_AUDIT_OUTPUT", "output")
AUDIT = ROOT / "audit"


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def html_text(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'(?is)<article class="content-body">(.*?)</article>', text)
    return strip_tags(match.group(1) if match else "")


def links_for(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    links = re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I)
    out = []
    for href in links:
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != "edunext.co.kr":
            out.append(href)
            continue
        p = unquote(parsed.path or "/")
        if p.startswith("/assets/") or p in {"/sitemap.xml", "/robots.txt"}:
            continue
        if p.endswith("/index.html"):
            p = p[: -len("index.html")]
        if p != "/" and not p.endswith("/"):
            p += "/"
        out.append(p or "/")
    return out


def page_url(keyword: str) -> str:
    return f"/{keyword}/"


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    os.environ["EDUNEXT_STRICT_SOURCE"] = "1"
    content, school_slugs = load_content()
    school_map = load_school_region_map()
    school_slugs = sorted(school_slugs)
    sitemap_text = (OUTPUT / "sitemap.xml").read_text(encoding="utf-8") if (OUTPUT / "sitemap.xml").exists() else ""

    inventory = []
    by_type = Counter()
    duplicates = Counter(school_slugs)
    for keyword in school_slugs:
        info = school_map.get(keyword, {})
        kind = info.get("page_type")
        if not kind:
            kind = "school_subject_math" if keyword.endswith("수학과외") else "school_subject_english" if keyword.endswith("영어과외") else "school_tutoring"
        by_type[kind] += 1
        inventory.append({
            "keyword": keyword,
            "page_type": kind,
            "school_display_name": info.get("school_display_name", ""),
            "official_school_name": info.get("official_school_name", ""),
            "city": info.get("city", ""),
            "district": info.get("district", ""),
            "town": info.get("town", ""),
            "source_row": info.get("source_row", ""),
            "duplicate_count": duplicates[keyword],
            "body_exists": bool(content.get(keyword)),
            "body_text_length": len(strip_tags(content.get(keyword, ""))),
        })
    write_csv(AUDIT / "school-source-inventory.csv", inventory)

    existence = []
    missing = []
    for row in inventory:
        keyword = str(row["keyword"])
        path = OUTPUT / keyword / "index.html"
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        canonical = f'<link rel="canonical" href="{SITE_URL}/{keyword}/">'
        h1 = f"<h1>{keyword}</h1>"
        article = html_text(path)
        rec = {
            **row,
            "expected_output_path": str(path),
            "html_exists": path.exists(),
            "sitemap_exists": f"{SITE_URL}/{keyword}/" in sitemap_text,
            "canonical_matches": canonical in text,
            "title_matches": f"<title>{keyword} | EduNext</title>" in text,
            "h1_matches": h1 in text,
            "content_exists": bool(article),
            "content_character_count": len(article),
        }
        existence.append(rec)
        if not path.exists():
            missing.append(rec)
    write_csv(AUDIT / "school-page-existence.csv", existence)

    unclassified = [row for row in inventory if not row["page_type"]]
    write_csv(AUDIT / "unclassified-school-keywords.csv", unclassified)

    mapping_rows = []
    unresolved = []
    for row in inventory:
        keyword = str(row["keyword"])
        info = school_map.get(keyword, {})
        candidates = []
        for slug in [info.get("town_slug"), info.get("district_slug"), info.get("city_slug")]:
            if slug:
                candidates.extend([f"{slug}과외", f"{slug}고등과외", f"{slug}수학과외", f"{slug}영어과외"])
        existing = []
        for target in candidates:
            if (OUTPUT / target / "index.html").exists() and target not in existing:
                existing.append(target)
        rec = {
            "keyword": keyword,
            "school_display_name": row["school_display_name"],
            "official_school_name": row["official_school_name"],
            "city": row["city"],
            "district": row["district"],
            "town": row["town"],
            "mapped_region_pages": "|".join(existing),
            "mapping_success": bool(existing),
        }
        mapping_rows.append(rec)
        if not existing:
            unresolved.append(rec)
    write_csv(AUDIT / "school-region-mapping.csv", mapping_rows)
    write_csv(AUDIT / "unresolved-school-mapping.csv", unresolved)
    (ROOT / "data" / "school_region_map.json").write_text(json.dumps(mapping_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    regions = load_regions()
    built_pages, _ = build_pages(regions, content, set(school_slugs), school_map)
    built = {page.slug: page for page in built_pages}
    page_urls = {page.url for page in built_pages}
    graph = defaultdict(list)
    broken = []
    for page in built_pages:
        targets = page.child_slugs + page.sibling_slugs + page.related_slugs + page.school_slugs
        if page.slug == "index":
            targets += ["부산과외", "구미과외", "양산과외"]
        for target_slug in targets:
            target = built.get(target_slug)
            if target and target.url in page_urls:
                graph[page.url].append(target.url)
            elif target_slug:
                broken.append({"page": page.url, "href": target_slug})
    visited = {"/": 0}
    queue = deque(["/"])
    while queue:
        current = queue.popleft()
        for target in graph[current]:
            if target not in visited:
                visited[target] = visited[current] + 1
                queue.append(target)
    school_urls = {page_url(k) for k in school_slugs}
    orphan_school = sorted(school_urls - set(visited))
    school_depths = [{"url": url, "depth": visited[url]} for url in sorted(school_urls & set(visited))]
    write_csv(AUDIT / "school-crawl-depth.csv", school_depths, ["url", "depth"])
    write_csv(AUDIT / "orphan-school-pages.csv", [{"url": url} for url in orphan_school], ["url"])

    semantic_errors = []
    for row in inventory:
        keyword = str(row["keyword"])
        city = str(row["city"])
        page = built.get(keyword)
        hrefs = []
        if page:
            hrefs = [built[item].url for item in (page.related_slugs + page.school_slugs + page.child_slugs) if item in built]
        for href in hrefs:
            if href.startswith("/부산") and city and city != "부산":
                semantic_errors.append({"keyword": keyword, "href": href, "reason": "wrong_city_busan"})
            if href.startswith("/구미") and city and city != "구미":
                semantic_errors.append({"keyword": keyword, "href": href, "reason": "wrong_city_gumi"})
            if href.startswith("/양산") and city and city != "양산":
                semantic_errors.append({"keyword": keyword, "href": href, "reason": "wrong_city_yangsan"})
    write_csv(AUDIT / "school-semantic-link-errors.csv", semantic_errors)

    extra_school_pages = []
    for path in OUTPUT.glob("*고*과외/index.html"):
        keyword = path.parent.name
        if keyword not in school_slugs and ("고과외" in keyword or "고수학과외" in keyword or "고영어과외" in keyword):
            extra_school_pages.append({"keyword": keyword, "path": str(path)})
    write_csv(AUDIT / "extra-school-pages.csv", extra_school_pages)

    summary = {
        "school_total": len(school_slugs),
        "school_tutoring": by_type["school_tutoring"],
        "school_math": by_type["school_subject_math"],
        "school_english": by_type["school_subject_english"],
        "generated_school_pages": sum(1 for row in existence if row["html_exists"]),
        "missing_school_pages": len(missing),
        "extra_school_pages": len(extra_school_pages),
        "mapping_success": sum(1 for row in mapping_rows if row["mapping_success"]),
        "mapping_failed": len(unresolved),
        "reachable_school_pages": len(school_urls & set(visited)),
        "orphan_school_pages": len(orphan_school),
        "avg_school_depth": round(sum(row["depth"] for row in school_depths) / len(school_depths), 2) if school_depths else 0,
        "max_school_depth": max([row["depth"] for row in school_depths] or [0]),
        "broken_links": len(broken),
        "semantic_errors": len(semantic_errors),
    }
    lines = ["# School Source Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (AUDIT / "school-source-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if missing or orphan_school or semantic_errors or broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
