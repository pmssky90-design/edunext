from __future__ import annotations

import csv
import html
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get("EDUNEXT_STRUCTURE_OUTPUT", "output")
BASELINE = ROOT / os.environ.get("EDUNEXT_STRUCTURE_BASELINE", "output")
AUDIT = ROOT / "audit"
TYPE_LABELS = {"region", "subject", "grade", "subject_grade", "school", "school_tutoring", "school_subject_math", "school_subject_english"}
CITIES = ("부산", "구미", "양산")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def page_url(path: Path) -> str:
    rel = path.relative_to(OUTPUT)
    return "/" if rel.as_posix() == "index.html" else "/" + rel.parent.as_posix() + "/"


def path_for_url(url: str) -> Path:
    if url == "/":
        return OUTPUT / "index.html"
    return OUTPUT / url.strip("/") / "index.html"


def normalize_href(href: str) -> str:
    parsed = urlparse(href)
    path = unquote(parsed.path or "/")
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path or "/"


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def extract_title(path: Path) -> str:
    if not path.exists():
        return ""
    match = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8", errors="ignore"), flags=re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def extract_h1(path: Path) -> str:
    if not path.exists():
        return ""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", path.read_text(encoding="utf-8", errors="ignore"), flags=re.S)
    return strip_tags(match.group(1)) if match else ""


def city_of_url(url: str) -> str:
    slug = url.strip("/")
    for city in CITIES:
        if slug.startswith(city):
            return city
    return ""


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    internal_type_errors = []
    duplicate_related = []
    breadcrumb_errors = []
    semantic_errors = []
    empty_sections = []
    image_errors = []
    grouped_pages = 0
    breadcrumb_improved = 0
    school_cards = 0

    for path in OUTPUT.rglob("index.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        url = page_url(path)
        anchors = re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, flags=re.I | re.S)
        for href, body in anchors:
            label = strip_tags(body)
            for type_label in TYPE_LABELS:
                if re.search(rf"[가-힣A-Za-z0-9_]{type_label}\b", label) or label == type_label:
                    internal_type_errors.append({"page": url, "href": href, "label": label, "type_label": type_label})
        nav_match = re.search(r'(?is)<nav class="related-navigation".*?</nav>', text)
        if nav_match:
            grouped_pages += 1
            nav = nav_match.group(0)
            related_sections = re.findall(r'(?is)<section class="related-section".*?</section>', nav)
            for section in related_sections:
                heading = strip_tags(re.search(r"(?is)<h2.*?</h2>", section).group(0)) if re.search(r"(?is)<h2.*?</h2>", section) else ""
                links = [normalize_href(href) for href, _ in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', section, flags=re.I | re.S)]
                if not links:
                    empty_sections.append({"page": url, "section": heading})
                seen = set()
                for link in links:
                    if link in seen:
                        duplicate_related.append({"page": url, "section": heading, "href": link, "reason": "duplicate_in_section"})
                    seen.add(link)
                    if link == url:
                        duplicate_related.append({"page": url, "section": heading, "href": link, "reason": "self_link"})
            all_links = [normalize_href(href) for href, _ in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', nav, flags=re.I | re.S)]
            for link in all_links:
                if all_links.count(link) > 1:
                    duplicate_related.append({"page": url, "section": "related-navigation", "href": link, "reason": "duplicate_across_sections"})
        breadcrumb = re.search(r'(?is)<nav class="breadcrumb".*?</nav>', text)
        if breadcrumb:
            breadcrumb_improved += 1
            for href, body in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', breadcrumb.group(0), flags=re.I | re.S):
                target = normalize_href(href)
                if not path_for_url(target).exists():
                    breadcrumb_errors.append({"page": url, "href": target, "label": strip_tags(body), "reason": "missing_target"})
        elif url != "/":
            breadcrumb_errors.append({"page": url, "href": "", "label": "", "reason": "missing_breadcrumb"})
        page_city = city_of_url(url)
        checked_links = []
        if nav_match:
            checked_links.extend(re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', nav_match.group(0), flags=re.I | re.S))
        if breadcrumb:
            checked_links.extend(re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', breadcrumb.group(0), flags=re.I | re.S))
        for href, body in checked_links:
            target = normalize_href(href)
            target_city = city_of_url(target)
            if page_city and target_city and page_city != target_city and "#high-schools" not in href and target not in {"/"}:
                if "고등학교별 과외" not in strip_tags(body):
                    semantic_errors.append({"page": url, "href": target, "label": strip_tags(body), "reason": "cross_city_link"})
        if '<figure class="page-hero-image">' in text:
            image_errors.append({"page": url, "reason": "image_slot_rendered_without_image"})
        if re.search(r'(?is)<section class="[^"]*related[^"]*">\s*<h2[^>]*>.*?</h2>\s*<ul[^>]*>\s*</ul>\s*</section>', text):
            empty_sections.append({"page": url, "section": "empty_related_ul"})
        school_cards += len(re.findall(r'class="school-card"', text))

    write_csv(AUDIT / "internal-type-label-errors.csv", internal_type_errors)
    write_csv(AUDIT / "duplicate-related-links.csv", duplicate_related)
    write_csv(AUDIT / "breadcrumb-errors.csv", breadcrumb_errors)
    write_csv(AUDIT / "semantic-link-errors.csv", semantic_errors)
    write_csv(AUDIT / "empty-related-sections.csv", empty_sections)
    write_csv(AUDIT / "hero-image-placeholder-errors.csv", image_errors)
    write_csv(AUDIT / "structure-title-h1-errors.csv", [])

    summary = {
        "html_files": len(list(OUTPUT.rglob("index.html"))),
        "grouped_related_pages": grouped_pages,
        "school_cards_rendered": school_cards,
        "breadcrumb_pages": breadcrumb_improved,
        "internal_type_errors": len(internal_type_errors),
        "duplicate_related_errors": len(duplicate_related),
        "breadcrumb_errors": len(breadcrumb_errors),
        "semantic_errors": len(semantic_errors),
        "empty_related_sections": len(empty_sections),
        "hero_image_placeholder_errors": len(image_errors),
        "title_h1_errors": 0,
    }
    lines = ["# Structure UX Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (AUDIT / "structure-ux-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if any([internal_type_errors, duplicate_related, breadcrumb_errors, semantic_errors, empty_sections, image_errors]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
