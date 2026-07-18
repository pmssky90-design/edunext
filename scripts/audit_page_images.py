from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import SITE_URL

OUTPUT = ROOT / os.environ.get("EDUNEXT_IMAGE_AUDIT_OUTPUT", "output_image_fixed")
AUDIT = ROOT / "audit"
DATA = ROOT / "data"


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def page_slug(path: Path) -> str:
    rel = path.relative_to(OUTPUT)
    return "index" if rel.as_posix() == "index.html" else rel.parent.name


def meta(markup: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, markup, flags=re.I)
        if match:
            return match.group(1)
    return ""


def json_ld_images(markup: str) -> list[str]:
    values: list[str] = []
    for body in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', markup, flags=re.I | re.S):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "WebPage" and node.get("image"):
                values.append(str(node["image"]))
    return values


def local_asset_exists(url: str) -> bool:
    parsed = urlparse(url)
    path = unquote(parsed.path).lstrip("/")
    return (OUTPUT / path).exists()


def expected_thumbnail(slug: str, thumbnails: list[str]) -> tuple[str, str]:
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    src = thumbnails[int(digest, 16) % len(thumbnails)]
    return digest, SITE_URL + "/" + "/".join(__import__("urllib.parse").parse.quote(part) for part in src.lstrip("/").split("/"))


def main() -> int:
    AUDIT.mkdir(exist_ok=True)
    fixed = json.loads((DATA / "fixed_images.json").read_text(encoding="utf-8"))["images"]
    thumbnails = json.loads((DATA / "search_thumbnails.json").read_text(encoding="utf-8"))["images"]
    map_rows = json.loads((DATA / "search_thumbnail_map.json").read_text(encoding="utf-8"))

    fixed_errors: list[dict[str, object]] = []
    thumb_errors: list[dict[str, object]] = []
    thumb_counter: Counter[str] = Counter()
    fixed_pages = 0
    thumb_pages = 0
    visible_search_thumb_body = 0

    expected_fixed_srcs = [item["src"] for item in fixed]
    for html in OUTPUT.rglob("index.html"):
        markup = html.read_text(encoding="utf-8", errors="ignore")
        slug = page_slug(html)
        is_home = slug == "index"
        section_match = re.search(r'(?is)<section class="page-fixed-images".*?</section>', markup)
        if is_home and section_match:
            fixed_errors.append({"page": slug, "reason": "home_has_fixed_images"})
        if not is_home:
            if not section_match:
                fixed_errors.append({"page": slug, "reason": "missing_fixed_images"})
            else:
                fixed_pages += 1
                imgs = re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>', section_match.group(0), flags=re.I)
                if imgs != expected_fixed_srcs:
                    fixed_errors.append({"page": slug, "reason": "fixed_image_order_mismatch", "found": "|".join(imgs)})
                for src in imgs:
                    if not (OUTPUT / src.lstrip("/")).exists():
                        fixed_errors.append({"page": slug, "reason": "missing_fixed_file", "src": src})
        og = meta(markup, "og:image")
        tw = meta(markup, "twitter:image")
        if og:
            thumb_pages += 1
            thumb_counter[Path(unquote(urlparse(og).path)).name] += 1
        expected_hash, expected_url = expected_thumbnail(slug, thumbnails)
        if og != expected_url:
            thumb_errors.append({"page": slug, "reason": "og_image_mismatch", "found": og, "expected": expected_url})
        if tw != og:
            thumb_errors.append({"page": slug, "reason": "twitter_image_mismatch", "found": tw, "expected": og})
        if not og.startswith(SITE_URL + "/assets/images/search-thumbnails/"):
            thumb_errors.append({"page": slug, "reason": "bad_domain_or_path", "found": og})
        if "studymap.co.kr" in og or "localhost" in og or "127.0.0.1" in og or "file://" in og:
            thumb_errors.append({"page": slug, "reason": "forbidden_domain", "found": og})
        if not local_asset_exists(og):
            thumb_errors.append({"page": slug, "reason": "missing_thumbnail_file", "found": og})
        images = json_ld_images(markup)
        if expected_url not in images:
            thumb_errors.append({"page": slug, "reason": "jsonld_image_mismatch", "found": "|".join(images), "expected": expected_url})
        body = re.search(r"(?is)<body.*?</body>", markup)
        if body and "search-thumbnails" in body.group(0):
            visible_search_thumb_body += 1
            thumb_errors.append({"page": slug, "reason": "search_thumbnail_in_body"})

    stability_rows = []
    changed = 0
    for row in map_rows:
        digest, expected_url = expected_thumbnail(row["slug"], thumbnails)
        same = row["thumbnail_absolute_url"] == expected_url and row["selection_hash"] == digest
        changed += 0 if same else 1
        stability_rows.append({"slug": row["slug"], "stable": same, "expected": expected_url, "actual": row["thumbnail_absolute_url"]})

    write_csv(AUDIT / "fixed-image-errors.csv", fixed_errors)
    write_csv(AUDIT / "search-thumbnail-errors.csv", thumb_errors)
    write_csv(AUDIT / "search-thumbnail-stability.csv", stability_rows, ["slug", "stable", "expected", "actual"])
    distribution = [{"thumbnail": key, "pages": value} for key, value in sorted(thumb_counter.items())]
    write_csv(AUDIT / "search-thumbnail-distribution.csv", distribution, ["thumbnail", "pages"])

    summary = {
        "html_files": len(list(OUTPUT.rglob("index.html"))),
        "fixed_source_images": len(fixed),
        "search_thumbnail_source_images": len(thumbnails),
        "fixed_image_pages": fixed_pages,
        "missing_or_bad_fixed_pages": len(fixed_errors),
        "search_thumbnail_pages": thumb_pages,
        "search_thumbnail_errors": len(thumb_errors),
        "search_thumbnail_body_exposures": visible_search_thumb_body,
        "og_twitter_mismatches": len([row for row in thumb_errors if row["reason"] == "twitter_image_mismatch"]),
        "stability_changed_rows": changed,
        "used_thumbnails": len(thumb_counter),
        "max_thumbnail_pages": max(thumb_counter.values(), default=0),
    }
    lines = ["# Image Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (AUDIT / "image-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 1 if fixed_errors or thumb_errors or changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
