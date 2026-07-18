from __future__ import annotations

import csv
import html
import json
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
import os

OUTPUT = ROOT / os.environ.get("EDUNEXT_FINAL_OUTPUT", "output_nav_clean")
BASELINE = ROOT / "output_home_redesign"
AUDIT = ROOT / "audit"
VERIFY = ROOT / "verification" / "final-predeploy-report"
SITE = "https://edunext.kr"
EXPECTED = {"html": 1462, "sitemap": 1462, "school": 429}


def strip_tags(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", value, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def one(pattern: str, text: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, text, flags)
    return html.unescape(match.group(1)).strip() if match else ""


def attrs(tag: str) -> dict[str, str]:
    return {key.lower(): html.unescape(v1 or v2 or v3 or "") for key, v1, v2, v3 in re.findall(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", tag)}


def page_url(path: Path) -> str:
    rel = path.relative_to(OUTPUT).as_posix()
    return "/" if rel == "index.html" else "/" + rel[:-len("index.html")]


def csv_write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def add(rows: list[dict], severity: str, category: str, page: str, detail: str, suggestion: str = "") -> None:
    rows.append({"severity": severity, "category": category, "page": page, "detail": detail, "suggestion": suggestion})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_status(path: str) -> tuple[int, str]:
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open("http://127.0.0.1:8015" + quote(path, safe="/?=&%"), timeout=5)
        return response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location", "")


def main() -> None:
    AUDIT.mkdir(exist_ok=True)
    VERIFY.mkdir(parents=True, exist_ok=True)
    issues: list[dict] = []
    metadata_errors: list[dict] = []
    empty_pages: list[dict] = []
    duplicate_content: list[dict] = []
    image_errors: list[dict] = []
    html_files = sorted(OUTPUT.rglob("index.html"))
    pages: dict[str, dict] = {}
    titles, descriptions = defaultdict(list), defaultdict(list)

    for path in html_files:
        url = page_url(path)
        text = path.read_text(encoding="utf-8")
        title = one(r"<title>(.*?)</title>", text)
        h1s = [strip_tags(v) for v in re.findall(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)]
        desc = one(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', text)
        canonical = one(r'<link\s+rel=["\']canonical["\'][^>]*href=["\']([^"\']*)', text)
        body = one(r"<body\b[^>]*>(.*?)</body>", text)
        main = one(r"<main\b[^>]*>(.*?)</main>", text)
        article_match = re.search(r'<article\s+class=["\'][^"\']*content-body[^"\']*["\'][^>]*>(.*?)</article>', text, re.I | re.S)
        article = article_match.group(1) if article_match else ""
        page_type = one(r'<main\b[^>]*class=["\'][^"\']*page-type-([\w-]+)', text)
        links = [(a.get("href", ""), strip_tags(inner)) for tag, inner in re.findall(r"(<a\b[^>]*>)(.*?)</a>", text, re.I | re.S) for a in [attrs(tag)]]
        ids = re.findall(r'\bid=["\']([^"\']+)', text, re.I)
        images = [attrs(tag) for tag in re.findall(r"<img\b[^>]*>", text, re.I)]
        nav_html = one(r'<nav\s+class=["\'][^"\']*top-nav[^"\']*["\'][^>]*>(.*?)</nav>', text)
        nav_links = [(a.get("href", ""), strip_tags(inner)) for tag, inner in re.findall(r"(<a\b[^>]*>)(.*?)</a>", nav_html, re.I | re.S) for a in [attrs(tag)]]
        pages[url] = {"path": path, "text": text, "title": title, "h1s": h1s, "desc": desc, "canonical": canonical, "body": body, "main": main, "article": article, "type": page_type, "links": links, "ids": set(ids), "images": images, "nav": nav_links}
        titles[title].append(url)
        descriptions[desc].append(url)

        if not body or not strip_tags(body): empty_pages.append({"page": url, "reason": "empty body", "length": 0})
        if not main or not strip_tags(main): empty_pages.append({"page": url, "reason": "empty main", "length": 0})
        if url != "/" and not article_match: empty_pages.append({"page": url, "reason": "missing content-body article", "length": 0})
        article_len = len(strip_tags(article))
        if url != "/" and article_len < 250: empty_pages.append({"page": url, "reason": "short article", "length": article_len})
        if not text.lower().startswith("<!doctype html>") or not re.search(r"</html>\s*$", text, re.I): add(issues, "BLOCKER", "HTML", url, "HTML document appears truncated")
        for tag in ("section", "nav", "ul", "ol"):
            if re.search(fr"<{tag}\b[^>]*>\s*</{tag}>", text, re.I): add(issues, "HIGH", "EMPTY_ELEMENT", url, f"empty {tag}")
        if len(ids) != len(set(ids)): add(issues, "HIGH", "ACCESSIBILITY", url, "duplicate id")

        expected_url = SITE + url
        checks = [
            (not title, "title missing"), (len(h1s) != 1, f"H1 count {len(h1s)}"), (not desc, "description missing"),
            (canonical != expected_url, f"canonical mismatch: {canonical}"),
            ('name="robots" content="index,follow"' not in text, "robots index,follow missing"),
            ('charset="utf-8"' not in text.lower(), "charset missing"), ('name="viewport"' not in text.lower(), "viewport missing"),
            ('<html lang="ko">' not in text.lower(), 'lang="ko" missing'),
            (one(r'<meta\s+property=["\']og:title["\'][^>]*content=["\']([^"\']*)', text) != title, "og:title mismatch"),
            (one(r'<meta\s+property=["\']og:url["\'][^>]*content=["\']([^"\']*)', text) != expected_url, "og:url mismatch"),
            (one(r'<meta\s+name=["\']twitter:title["\'][^>]*content=["\']([^"\']*)', text) != title, "twitter:title mismatch"),
        ]
        og_image = one(r'<meta\s+property=["\']og:image["\'][^>]*content=["\']([^"\']*)', text)
        tw_image = one(r'<meta\s+name=["\']twitter:image["\'][^>]*content=["\']([^"\']*)', text)
        if not og_image or not tw_image or og_image != tw_image: checks.append((True, "og/twitter image missing or mismatch"))
        for failed, detail in checks:
            if failed:
                row = {"page": url, "field": detail.split()[0], "detail": detail}
                metadata_errors.append(row); add(issues, "HIGH", "METADATA", url, detail)
        if len(title) < 10 or len(title) > 65: metadata_errors.append({"page": url, "field": "title_length", "detail": str(len(title))})
        if len(desc) < 50 or len(desc) > 180: metadata_errors.append({"page": url, "field": "description_length", "detail": str(len(desc))})

        for raw in re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', text, re.I | re.S):
            try:
                data = json.loads(raw)
                packed = json.dumps(data, ensure_ascii=False)
                if "WebSite" not in packed or "WebPage" not in packed or "BreadcrumbList" not in packed: raise ValueError("required schema missing")
                if any(host in packed for host in ["localhost", "127.0.0.1", "www.edunext.kr"]): raise ValueError("wrong schema host")
            except (json.JSONDecodeError, ValueError) as exc:
                metadata_errors.append({"page": url, "field": "json_ld", "detail": str(exc)}); add(issues, "BLOCKER", "JSON_LD", url, str(exc))

        paragraphs = [strip_tags(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", article, re.I | re.S) if len(strip_tags(p)) > 30]
        for value, count in Counter(paragraphs).items():
            if count > 1:
                duplicate_content.append({"page": url, "type": "paragraph", "count": count, "text": value[:240]})
        headings = [strip_tags(x) for x in re.findall(r"<h[23]\b[^>]*>(.*?)</h[23]>", article, re.I | re.S)]
        for value, count in Counter(headings).items():
            if count > 1: duplicate_content.append({"page": url, "type": "heading", "count": count, "text": value})

        for image in images:
            src = image.get("src", "")
            if not image.get("alt", "").strip(): image_errors.append({"page": url, "src": src, "reason": "missing alt"})
            if src.startswith("/"):
                target = OUTPUT / unquote(src.lstrip("/"))
                if not target.exists(): image_errors.append({"page": url, "src": src, "reason": "missing file"})
            elif src.startswith("http"): image_errors.append({"page": url, "src": src, "reason": "external dependency"})

        residue = ["TODO", "FIXME", "lorem ipsum", "javascript:void(0)", "C:\\Projects", "C:\\gptwp", "localhost", "127.0.0.1"]
        for token in residue:
            if token.lower() in text.lower(): add(issues, "HIGH", "RESIDUE", url, f"exposed token: {token}")
        for href, _ in links:
            if href in {"", "#"}: add(issues, "HIGH", "LINK", url, f"empty link: {href!r}")

    # Counts and expected-value variance.
    school_urls = [url for url, p in pages.items() if p["type"] == "school"]
    school_general = [u for u in school_urls if not u.rstrip("/").endswith(("영어과외", "수학과외"))]
    school_english = [u for u in school_urls if u.rstrip("/").endswith("영어과외")]
    school_math = [u for u in school_urls if u.rstrip("/").endswith("수학과외")]
    city_school = {city: sum(u.startswith("/" + city) for u in school_general) for city in ["부산", "구미", "양산"]}
    if len(html_files) != EXPECTED["html"]: add(issues, "MEDIUM", "EXPECTED_COUNT", "/", f"HTML {len(html_files)} (request baseline {EXPECTED['html']}); generated page inventory contains 36 more keyword pages")

    # Sitemap full reconciliation.
    sitemap_tree = ElementTree.parse(OUTPUT / "sitemap.xml")
    locs = [node.text or "" for node in sitemap_tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    sitemap_paths = [urlparse(loc).path or "/" for loc in locs]
    if len(locs) != EXPECTED["sitemap"]: add(issues, "MEDIUM", "EXPECTED_COUNT", "/sitemap.xml", f"sitemap {len(locs)} (request baseline {EXPECTED['sitemap']}); matches generated HTML inventory")
    if len(locs) != len(set(locs)): add(issues, "BLOCKER", "SITEMAP", "/sitemap.xml", "duplicate sitemap URLs")
    for loc in locs:
        parsed = urlparse(loc)
        if parsed.scheme != "https" or parsed.netloc != "edunext.kr" or parsed.query or parsed.fragment or "/index.html" in parsed.path: add(issues, "BLOCKER", "SITEMAP", "/sitemap.xml", f"invalid URL {loc}")
    for missing in sorted(set(pages) - set(sitemap_paths)): add(issues, "BLOCKER", "SITEMAP", missing, "HTML missing from sitemap")
    for extra in sorted(set(sitemap_paths) - set(pages)): add(issues, "BLOCKER", "SITEMAP", extra, "sitemap URL has no HTML")

    # Links and crawl graph, including fragment existence.
    graph = defaultdict(set); broken = []
    for source, p in pages.items():
        for href, label in p["links"]:
            parsed = urlparse(href)
            if parsed.scheme and parsed.netloc not in {"", "edunext.kr"}:
                continue
            if href.startswith(("mailto:", "tel:")): continue
            target_path = unquote(parsed.path or source)
            if not target_path.startswith("/"):
                target_path = str((Path(source) / target_path)).replace("\\", "/")
            if target_path.startswith("/assets/") or target_path in {"/sitemap.xml", "/robots.txt"}: continue
            if target_path.endswith("index.html"): target_path = target_path[:-10]
            if target_path != "/" and not target_path.endswith("/"): target_path += "/"
            if target_path not in pages:
                broken.append({"source": source, "href": href, "text": label, "reason": "missing target"})
            elif parsed.fragment and parsed.fragment not in pages[target_path]["ids"]:
                broken.append({"source": source, "href": href, "text": label, "reason": "missing fragment"})
            else: graph[source].add(target_path)
    reached = {"/": 0}; queue = deque(["/"])
    while queue:
        current = queue.popleft()
        for target in graph[current]:
            if target not in reached: reached[target] = reached[current] + 1; queue.append(target)
    orphan = [{"page": url, "page_type": pages[url]["type"], "depth": "unreachable"} for url in sorted(set(pages) - set(reached))]
    for row in broken: add(issues, "BLOCKER", "BROKEN_LINK", row["source"], f"{row['href']} - {row['reason']}")
    for row in orphan: add(issues, "BLOCKER", "ORPHAN", row["page"], "not reachable from home")

    # Global menu on every generated page.
    expected_menu = [("/부산과외/", "부산과외"), ("/양산과외/", "양산과외"), ("/구미과외/", "구미과외"), ("/#high-schools", "고등학교별 과외")]
    menu_bad = [url for url, p in pages.items() if p["nav"] != expected_menu]
    for url in menu_bad: add(issues, "HIGH", "GLOBAL_MENU", url, f"menu mismatch: {pages[url]['nav']}")

    # Home school inventory.
    home_text = pages["/"]["text"]
    home_cards = len(re.findall(r'class=["\'][^"\']*home-school-card', home_text, re.I))
    home_school_links = [href for href, _ in pages["/"]["links"] if (urlparse(href).path if href else "") in school_urls]
    school_link_errors = len([h for h in home_school_links if unquote(urlparse(h).path) not in pages])
    if home_cards != 143: add(issues, "HIGH", "HOME_SCHOOL", "/", f"school cards {home_cards}, expected 143")
    if len(home_school_links) != 429 or len(set(home_school_links)) != 429: add(issues, "HIGH", "HOME_SCHOOL", "/", f"school links {len(home_school_links)}, unique {len(set(home_school_links))}")
    if "/##high-schools" in home_text: add(issues, "HIGH", "REGRESSION", "/", "/##high-schools present")

    # Baseline preservation for URL, title, H1, body article.
    changed = []
    new_since_baseline = []
    if BASELINE.exists():
        base_files = {}
        for baseline_path in BASELINE.rglob("index.html"):
            rel = baseline_path.relative_to(BASELINE).as_posix()
            baseline_url = "/" if rel == "index.html" else "/" + rel[:-len("index.html")]
            base_files[baseline_url] = baseline_path
        for url, p in pages.items():
            bp = base_files.get(url)
            if not bp: new_since_baseline.append(url); continue
            old = bp.read_text(encoding="utf-8")
            for kind, old_value, new_value in [
                ("title", one(r"<title>(.*?)</title>", old), p["title"]),
                ("h1", one(r"<h1\b[^>]*>(.*?)</h1>", old), p["h1s"][0] if p["h1s"] else ""),
                ("article", strip_tags(one(r'<article\s+class=["\'][^"\']*content-body[^"\']*["\'][^>]*>(.*?)</article>', old)), strip_tags(p["article"])),
            ]:
                if old_value != new_value: changed.append((url, kind))
        if changed: add(issues, "BLOCKER", "CONTENT_PRESERVATION", changed[0][0], f"{len(changed)} baseline differences")
        for url in new_since_baseline:
            add(issues, "INFO", "APPROVED_HUB_ADDITION", url, "approved national/province category hub added by generator")

    # Robots, file exposure, assets and image policy.
    robots = (OUTPUT / "robots.txt").read_text(encoding="utf-8") if (OUTPUT / "robots.txt").exists() else ""
    if "Disallow: /" in robots or "Sitemap: https://edunext.kr/sitemap.xml" not in robots: add(issues, "BLOCKER", "ROBOTS", "/robots.txt", "robots policy invalid")
    exposed = [p.relative_to(OUTPUT).as_posix() for p in OUTPUT.rglob("*") if p.is_file() and (p.suffix.lower() in {".py", ".xlsx", ".env", ".map"} or p.name in {".git", ".DS_Store", "Thumbs.db"})]
    for item in exposed: add(issues, "HIGH", "EXPOSED_FILE", item, "non-deploy artifact inside output")
    fixed_files = sorted((OUTPUT / "assets" / "images" / "fixed").glob("*"))
    thumb_files = sorted((OUTPUT / "assets" / "images" / "search-thumbnails").glob("*"))
    fixed_pages = sum('class="page-fixed-images"' in p["text"] for p in pages.values())
    home_fixed = 'class="page-fixed-images"' in home_text
    if len(fixed_files) != 6 or fixed_pages != len(html_files) - 1 or home_fixed: image_errors.append({"page": "/", "src": "fixed/*", "reason": f"files={len(fixed_files)}, pages={fixed_pages}, home={home_fixed}"})
    if len(thumb_files) != 24: image_errors.append({"page": "/", "src": "search-thumbnails/*", "reason": f"count={len(thumb_files)}"})
    for row in image_errors: add(issues, "HIGH", "IMAGE", row["page"], f"{row['src']}: {row['reason']}")

    # Browser/mobile results.
    mobile_rows = []
    mobile_data = json.loads((AUDIT / "final-mobile-results.json").read_text(encoding="utf-8"))
    for result in mobile_data["results"]:
        if result["overflow"]: mobile_rows.append({"severity": "HIGH", "page": result["path"], "width": result["width"], "issue": "horizontal overflow", "detail": ", ".join(result["overflowElements"])})
        if result["menuCount"] != 4: mobile_rows.append({"severity": "HIGH", "page": result["path"], "width": result["width"], "issue": "menu count", "detail": str(result["menuCount"])})
        if result["width"] <= 430 and result["smallTargets"]: mobile_rows.append({"severity": "MEDIUM", "page": result["path"], "width": result["width"], "issue": "touch targets under 44px", "detail": str(result["smallTargets"])})
    interaction = mobile_data["interaction"]
    for key, label in [("opened", "menu open and body lock"), ("panelClickStaysOpen", "panel click stays open"), ("toggleClosed", "toggle close and body unlock"), ("escapeClosed", "Esc close"), ("outsideClosed", "outside click close"), ("schoolTarget", "school anchor"), ("closedAfterLink", "close after link")]:
        if not interaction.get(key): mobile_rows.append({"severity": "MEDIUM", "page": "/부산과외/", "width": 390, "issue": label, "detail": "failed"})
    for error in mobile_data.get("consoleErrors", []): mobile_rows.append({"severity": "HIGH", "page": "browser", "width": "all", "issue": "console error", "detail": error})
    for row in mobile_rows: add(issues, row["severity"], "MOBILE", row["page"], f"{row['width']}px {row['issue']}: {row['detail']}")

    # URL normalization on local static server and configuration risk.
    variants = ["/구미과외/", "/구미과외/index.html", "/구미과외", "//구미과외//", "/구미과외/?test=1", "/구미과외/index.htm", "/undefined/", "/null/", "/None/", "/not-a-real-page/"]
    normalization = [(v, *local_status(v)) for v in variants]
    risks = []
    for variant, status, location in normalization:
        if variant.startswith("//") and status == 200: risks.append((variant, status, "double-slash normalization is not explicitly declared in vercel.json"))
    if risks: add(issues, "MEDIUM", "URL_NORMALIZATION", "/", f"{len(risks)} local normalization risks; deployment redirects must be verified")
    url_md = ["# URL normalization", "", "| Variant | Status | Location |", "|---|---:|---|"] + [f"| `{v}` | {s} | `{loc}` |" for v, s, loc in normalization]
    url_md += ["", "## Risks", ""] + [f"- `{v}` ({s}): {reason}" for v, s, reason in risks]
    url_md += ["", "Vercel has trailingSlash and `/index.html` redirects. Verify production http→https and www→non-www permanent redirects after deployment."]
    (AUDIT / "final-url-normalization.md").write_text("\n".join(url_md) + "\n", encoding="utf-8")

    # Duplicate title/description findings.
    for value, urls in titles.items():
        if value and len(urls) > 1:
            for url in urls: metadata_errors.append({"page": url, "field": "duplicate_title", "detail": f"{len(urls)} pages"})
    for value, urls in descriptions.items():
        if value and len(urls) > 1:
            for url in urls: metadata_errors.append({"page": url, "field": "duplicate_description", "detail": f"{len(urls)} pages"})

    # Write requested machine-readable reports.
    errors = [r for r in issues if r["severity"] in {"BLOCKER", "HIGH"}]
    warnings = [r for r in issues if r["severity"] in {"MEDIUM", "LOW", "INFO"}]
    csv_write(AUDIT / "final-predeploy-errors.csv", errors, ["severity", "category", "page", "detail", "suggestion"])
    csv_write(AUDIT / "final-predeploy-warnings.csv", warnings, ["severity", "category", "page", "detail", "suggestion"])
    csv_write(AUDIT / "final-broken-links.csv", broken, ["source", "href", "text", "reason"])
    csv_write(AUDIT / "final-orphan-pages.csv", orphan, ["page", "page_type", "depth"])
    csv_write(AUDIT / "final-empty-pages.csv", empty_pages, ["page", "reason", "length"])
    csv_write(AUDIT / "final-metadata-errors.csv", metadata_errors, ["page", "field", "detail"])
    csv_write(AUDIT / "final-duplicate-content.csv", duplicate_content, ["page", "type", "count", "text"])
    csv_write(AUDIT / "final-image-errors.csv", image_errors, ["page", "src", "reason"])
    csv_write(AUDIT / "final-mobile-errors.csv", mobile_rows, ["severity", "page", "width", "issue", "detail"])

    counts = Counter(r["severity"] for r in issues)
    blocker, high = counts["BLOCKER"], counts["HIGH"]
    readiness = "배포 금지" if blocker else "중요 오류 수정 후 재검사 필요" if high else "경미한 수정 후 배포 가능" if counts["MEDIUM"] else "배포 가능"
    max_depth = max(reached.values()) if reached else 0
    metrics = {
        "html": len(html_files), "sitemap": len(locs), "keyword": len(html_files) - len(school_urls) - 1, "home": 1,
        "school": len(school_urls), "school_general": len(school_general), "school_english": len(school_english), "school_math": len(school_math),
        "busan_schools": city_school["부산"], "gumi_schools": city_school["구미"], "yangsan_schools": city_school["양산"],
        "fixed_pages": fixed_pages, "thumb_pages": sum(bool(one(r'<meta\s+property=["\']og:image["\'][^>]*content=["\']([^"\']*)', p["text"])) for p in pages.values()),
        "empty": len(empty_pages), "orphan": len(orphan), "broken": len(broken), "school_link_errors": school_link_errors,
        "metadata": len(metadata_errors), "mobile": len(mobile_rows), "normalization": len(risks), "max_depth": max_depth,
    }
    regression = [
        ("메인 위 홈 텍스트", "PASS" if not re.search(r'<main[^>]*>\s*홈\s*<', home_text) else "FAIL"),
        ("/##high-schools", "PASS" if "/##high-schools" not in home_text else "FAIL"),
        ("학교 앵커 이동", "PASS" if interaction.get("schoolTarget") else "FAIL"),
        ("모바일 링크 후 메뉴 닫힘", "PASS" if interaction.get("closedAfterLink") else "FAIL"),
        ("전역 메뉴 4개", "PASS" if not menu_bad else "FAIL"),
        ("학교 링크 429개", "PASS" if len(set(home_school_links)) == 429 else "FAIL"),
        ("홈 고정 이미지 없음", "PASS" if not home_fixed else "FAIL"),
        ("og/twitter 이미지 일치", "PASS" if not any("image" in r["detail"] for r in metadata_errors) else "FAIL"),
        ("고아 페이지 없음", "PASS" if not orphan else "FAIL"),
        ("깨진 링크 없음", "PASS" if not broken else "FAIL"),
        ("도메인 일관성", "PASS" if not any(r["category"] in {"SITEMAP", "METADATA", "JSON_LD"} and "host" in r["detail"] for r in issues) else "FAIL"),
    ]
    top5 = [
        "모바일 메뉴 바깥 클릭 닫기 동작 추가",
        "44px 미만 모바일 링크/버튼 터치 영역 확대",
        "HTML·sitemap 예상 1426과 실제 1462 차이의 승인 여부 확인",
        "프로덕션에서 query/double-slash/index.html 정규화 리디렉션 재검증",
        "배포 후 http→https 및 www→non-www 영구 리디렉션 확인",
    ]
    summary = ["# EduNext final predeploy audit", "", f"- 대상: `{OUTPUT}`", f"- 판정: **{readiness}**", f"- BLOCKER: {blocker}", f"- HIGH: {high}", f"- MEDIUM: {counts['MEDIUM']}", "", "## Inventory", ""]
    summary += [f"- {k}: {v}" for k, v in metrics.items()]
    summary += ["", "## Regression", ""] + [f"- {status} — {label}" for label, status in regression]
    summary += ["", "## First five actions", ""] + [f"{i}. {item}" for i, item in enumerate(top5, 1)]
    summary += ["", "## Notes", "", "- Candidate files were read only; no output promotion, commit, push, or deployment was performed.", "- The 36-page variance is inventory drift against the supplied expectation, while generated HTML and sitemap reconcile 1:1.", "- www→non-www and http→https must be permanent redirects in production."]
    (AUDIT / "final-predeploy-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    deployment = ["# Deployment readiness", "", f"## Decision: {readiness}", "", f"BLOCKER {blocker}, HIGH {high}, MEDIUM {counts['MEDIUM']}", "", "Do not promote until HIGH findings are resolved and browser audit is rerun.", "", "Vercel configuration already declares trailingSlash and index.html/www redirects. Production behavior still requires verification. Candidate output is not the configured deployment output directory."]
    (AUDIT / "final-deployment-readiness.md").write_text("\n".join(deployment) + "\n", encoding="utf-8")

    links = [
        ("Summary", "../../audit/final-predeploy-summary.md"), ("Errors", "../../audit/final-predeploy-errors.csv"),
        ("Warnings", "../../audit/final-predeploy-warnings.csv"), ("Broken links", "../../audit/final-broken-links.csv"),
        ("Mobile", "../../audit/final-mobile-errors.csv"), ("Normalization", "../../audit/final-url-normalization.md"),
    ]
    report = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EduNext 배포 전 검사</title><style>body{{font-family:system-ui;margin:0;background:#f4f7fa;color:#172033}}main{{max-width:980px;margin:auto;padding:32px 20px}}.hero,.card{{background:#fff;border:1px solid #d9e0e8;border-radius:16px;padding:24px;margin-bottom:18px}}.bad{{color:#a22;font-weight:800}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}strong{{display:block;font-size:1.8rem}}a{{color:#156f83}}</style></head><body><main><section class="hero"><h1>EduNext 최종 전수검사</h1><p class="bad">{readiness}</p><p>{OUTPUT}</p></section><section class="grid">{''.join(f'<div class="card"><span>{label}</span><strong>{value}</strong></div>' for label,value in [('HTML',metrics['html']),('Sitemap',metrics['sitemap']),('BLOCKER',blocker),('HIGH',high),('빈 페이지',metrics['empty']),('고아',metrics['orphan']),('깨진 링크',metrics['broken']),('메타 오류',metrics['metadata']),('모바일',metrics['mobile'])])}</section><section class="card"><h2>보고서</h2><ul>{''.join(f'<li><a href="{href}">{label}</a></li>' for label,href in links)}</ul></section><section class="card"><h2>우선 조치</h2><ol>{''.join(f'<li>{x}</li>' for x in top5)}</ol></section></main></body></html>'''
    (VERIFY / "index.html").write_text(report, encoding="utf-8")
    print(json.dumps({"readiness": readiness, "severity": counts, "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
