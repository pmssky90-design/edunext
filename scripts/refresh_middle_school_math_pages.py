from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
REVIEW = ROOT / "review"
sys.path.insert(0, str(ROOT))

from sitegen.data_loader import load_content, load_regions, load_school_region_map
from sitegen.middle_school_math import middle_school_math_contexts
from sitegen.pages import build_pages
from sitegen.render import render_page
from sitegen.sitemap import render_sitemap


REPRESENTATIVE_PARENT = "부산하단동중등수학과외"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def snapshot_before() -> None:
    source = OUTPUT / REPRESENTATIVE_PARENT / "index.html"
    target = REVIEW / "middle-school-math-before" / REPRESENTATIVE_PARENT / "index.html"
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def update_thumbnail_map(target_pages: list[object]) -> None:
    path = ROOT / "data" / "search_thumbnail_map.json"
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    target_slugs = {page.slug for page in target_pages}
    rows = [row for row in current if row.get("slug") not in target_slugs]
    for page in sorted(target_pages, key=lambda item: item.slug):
        rows.append(
            {
                "keyword": page.title,
                "slug": page.slug,
                "page_type": page.page_type,
                "selected_thumbnail": page.search_thumbnail,
                "thumbnail_absolute_url": page.search_thumbnail_url,
                "selection_hash": page.search_thumbnail_hash,
                "output_path": str(OUTPUT / page.slug / "index.html"),
            }
        )
    write_text(path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    snapshot_before()
    regions = load_regions()
    content, school_slugs = load_content()
    pages, stats = build_pages(regions, content, school_slugs, load_school_region_map())
    page_map = {page.slug: page for page in pages}
    contexts = middle_school_math_contexts()
    target_pages = [page_map[slug] for slug in contexts]
    parent_slugs = sorted({context.parent_slug for context in contexts.values()})
    missing_parents = [slug for slug in parent_slugs if slug not in page_map]
    if missing_parents:
        raise ValueError(f"Missing parent pages: {missing_parents}")

    for page in target_pages:
        write_text(OUTPUT / page.slug / "index.html", render_page(page, page_map))
    for slug in parent_slugs:
        page = page_map[slug]
        write_text(OUTPUT / slug / "index.html", render_page(page, page_map))
    write_text(OUTPUT / "sitemap.xml", render_sitemap(pages))
    update_thumbnail_map(target_pages)

    print(f"generated middle-school math pages: {len(target_pages)}")
    print(f"refreshed regional parent pages: {len(parent_slugs)}")
    print(f"all site pages in sitemap: {len(pages)}")
    print(f"school pages total: {stats['school']}")
    print(f"representative: {OUTPUT / '부산하단중수학과외' / 'index.html'}")
    return 0 if len(target_pages) == 218 and len(pages) == 1680 else 1


if __name__ == "__main__":
    raise SystemExit(main())
