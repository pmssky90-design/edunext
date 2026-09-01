from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get("EDUNEXT_AUDIT_OUTPUT", "output")
AUDIT = ROOT / "audit"
SITE_URL = "https://edunext.co.kr"


class Parsed:
    def __init__(self, text: str) -> None:
        self.links = re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I)
        self.h1 = len(re.findall(r"<h1\b", text, flags=re.I))
        title = re.search(r"<title>(.*?)</title>", text, flags=re.I | re.S)
        desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', text, flags=re.I)
        canon = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']*)["\']', text, flags=re.I)
        self.title = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
        self.description = desc.group(1) if desc else ""
        self.canonical = canon.group(1) if canon else ""
        self.json_ld = re.findall(
            r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>',
            text,
            flags=re.I | re.S,
        )


def url_for_file(path: Path) -> str:
    rel = path.relative_to(OUTPUT)
    if rel.as_posix() == "index.html":
        return "/"
    return "/" + rel.parent.as_posix() + "/"


def normalize_internal(href: str) -> str | None:
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc != "edunext.co.kr":
        return None
    path = unquote(parsed.path or "/")
    if path.startswith("/assets/") or path in {"/sitemap.xml", "/robots.txt"}:
        return None
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if path == "":
        path = "/"
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str]) -> None:
    with (AUDIT / name).open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    html_files = list(OUTPUT.rglob("index.html"))
    pages = {}
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        url = url_for_file(path)
        pages[url] = {"path": path, "text": text, "parser": Parsed(text)}

    broken = []
    self_links = []
    domain_errors = []
    index_links = []
    graph = defaultdict(list)
    for url, item in pages.items():
        for href in item["parser"].links:
            target = normalize_internal(href)
            if target is None:
                continue
            if "www.edunext.co.kr" in href or "localhost" in href:
                domain_errors.append({"page": url, "href": href})
            if "/index.html" in href:
                index_links.append({"page": url, "href": href})
            if target == url:
                self_links.append({"page": url, "href": href})
            elif target not in pages:
                broken.append({"page": url, "href": href, "reason": "missing page"})
            else:
                graph[url].append(target)

    visited = {"/": 0}
    queue = deque(["/"])
    while queue:
        current = queue.popleft()
        for target in graph[current]:
            if target not in visited:
                visited[target] = visited[current] + 1
                queue.append(target)

    orphans = [{"url": url} for url in sorted(set(pages) - set(visited))]
    depth_counts = Counter(visited.values())
    duplicate_titles = [{"value": k, "count": v} for k, v in Counter(i["parser"].title.strip() for i in pages.values()).items() if v > 1]
    duplicate_descriptions = [{"value": k, "count": v} for k, v in Counter(i["parser"].description.strip() for i in pages.values()).items() if v > 1]
    canonical_errors = []
    json_errors = []
    short_pages = []
    body_hashes = Counter()
    for url, item in pages.items():
        parser = item["parser"]
        expected = SITE_URL + url
        if parser.canonical != expected:
            canonical_errors.append({"url": url, "canonical": parser.canonical, "expected": expected})
        if parser.h1 != 1:
            canonical_errors.append({"url": url, "canonical": f"h1:{parser.h1}", "expected": "h1:1"})
        for raw in parser.json_ld:
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                json_errors.append({"url": url, "error": str(exc)})
        content_match = re.search(r'<article class="content-body">(.*?)</article>', item["text"], flags=re.S)
        body_source = content_match.group(1) if content_match else item["text"]
        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_source))
        if len(body) < 250:
            short_pages.append({"url": url, "length": len(body)})
        body_hashes[hashlib.sha1(body.strip().encode("utf-8")).hexdigest()] += 1

    sitemap_errors = []
    sitemap_urls = set()
    tree = ElementTree.parse(OUTPUT / "sitemap.xml")
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in tree.findall(".//sm:loc", ns):
        full = loc.text or ""
        sitemap_urls.add(urlparse(full).path or "/")
        if not full.startswith(SITE_URL):
            sitemap_errors.append({"url": full, "reason": "wrong domain"})
    missing_in_sitemap = set(pages) - sitemap_urls
    extra_in_sitemap = sitemap_urls - set(pages)
    sitemap_errors.extend({"url": url, "reason": "missing in sitemap"} for url in sorted(missing_in_sitemap))
    sitemap_errors.extend({"url": url, "reason": "not generated"} for url in sorted(extra_in_sitemap))

    write_csv("broken-links.csv", broken, ["page", "href", "reason"])
    write_csv("orphan-pages.csv", orphans, ["url"])
    write_csv("crawl-depth.csv", [{"depth": k, "pages": v} for k, v in sorted(depth_counts.items())], ["depth", "pages"])
    write_csv("duplicate-titles.csv", duplicate_titles, ["value", "count"])
    write_csv("duplicate-descriptions.csv", duplicate_descriptions, ["value", "count"])
    write_csv("canonical-errors.csv", canonical_errors, ["url", "canonical", "expected"])
    write_csv("domain-errors.csv", domain_errors + index_links, ["page", "href"])
    write_csv("sitemap-errors.csv", sitemap_errors, ["url", "reason"])
    write_csv("content-similarity.csv", [{"hash": k, "count": v} for k, v in body_hashes.items() if v > 1], ["hash", "count"])

    summary = {
        "html_files": len(html_files),
        "sitemap_urls": len(sitemap_urls),
        "reachable_from_home": len(visited),
        "orphan_pages": len(orphans),
        "max_click_depth": max(visited.values()) if visited else 0,
        "broken_internal_links": len(broken),
        "self_links": len(self_links),
        "duplicate_titles": len(duplicate_titles),
        "duplicate_descriptions": len(duplicate_descriptions),
        "canonical_errors": len(canonical_errors),
        "json_ld_errors": len(json_errors),
        "domain_errors": len(domain_errors),
        "index_html_links": len(index_links),
        "short_pages": len(short_pages),
    }
    lines = ["# EduNext Audit Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (AUDIT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if broken or orphans or canonical_errors or json_errors or sitemap_errors else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
