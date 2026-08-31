from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from config import ASSETS_DIR, AUDIT_DIR, CONTENT_FIXED_OUTPUT_DIR, HOME_FIXED_OUTPUT_DIR, HOME_FIXED_V2_OUTPUT_DIR, HOME_REDESIGN_OUTPUT_DIR, IMAGE_FIXED_OUTPUT_DIR, MENU_CONTENT_REDESIGN_OUTPUT_DIR, MOBILE_FIXED_OUTPUT_DIR, NAV_CLEAN_OUTPUT_DIR, OUTPUT_DIR, PREDEPLOY_FINAL_OUTPUT_DIR, PROJECT_ROOT, SCHOOL_FIXED_OUTPUT_DIR, STRUCTURE_FIXED_OUTPUT_DIR, TITLE_FIXED_OUTPUT_DIR
from sitegen.models import Page
from sitegen.render import render_not_found, render_page
from sitegen.sitemap import render_robots, render_sitemap


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def active_output_dir() -> Path:
    import os

    explicit_output = os.environ.get("EDUNEXT_OUTPUT_DIR")
    if explicit_output:
        return PROJECT_ROOT / explicit_output

    if os.environ.get("EDUNEXT_OUTPUT") == "content_fixed":
        return CONTENT_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "school_fixed":
        return SCHOOL_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "title_fixed":
        return TITLE_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "structure_fixed":
        return STRUCTURE_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "image_fixed":
        return IMAGE_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "home_fixed":
        return HOME_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "home_fixed_v2":
        return HOME_FIXED_V2_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "mobile_fixed":
        return MOBILE_FIXED_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "home_redesign":
        return HOME_REDESIGN_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "menu_content_redesign":
        return MENU_CONTENT_REDESIGN_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "nav_clean":
        return NAV_CLEAN_OUTPUT_DIR
    if os.environ.get("EDUNEXT_OUTPUT") == "predeploy_final":
        return PREDEPLOY_FINAL_OUTPUT_DIR
    return OUTPUT_DIR


def prepare_output(output_dir: Path) -> Path:
    tmp = output_dir.parent / f"_{output_dir.name}_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    return tmp


def publish(tmp: Path, output_dir: Path) -> None:
    if output_dir.exists():
        backup = output_dir.parent / f"{output_dir.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(str(output_dir), str(backup))
    shutil.move(str(tmp), str(output_dir))


def write_assets(root: Path) -> None:
    write_text(root / "assets" / "css" / "style.css", (ASSETS_DIR / "css" / "style.css").read_text(encoding="utf-8"))
    write_text(root / "assets" / "js" / "main.js", (ASSETS_DIR / "js" / "main.js").read_text(encoding="utf-8"))
    write_text(root / "assets" / "images" / "edunext-og.svg", (ASSETS_DIR / "images" / "edunext-og.svg").read_text(encoding="utf-8"))
    for folder in ["fixed", "search-thumbnails"]:
        source = ASSETS_DIR / "images" / folder
        if source.exists():
            shutil.copytree(source, root / "assets" / "images" / folder)
    home_images = ASSETS_DIR / "images" / "home"
    if home_images.exists():
        shutil.copytree(home_images, root / "assets" / "images" / "home")


def write_search_thumbnail_map(pages: list[Page], output_dir: Path) -> None:
    rows = []
    for page in pages:
        rows.append(
            {
                "keyword": page.title,
                "slug": page.slug,
                "page_type": page.page_type,
                "selected_thumbnail": page.search_thumbnail,
                "thumbnail_absolute_url": page.search_thumbnail_url,
                "selection_hash": page.search_thumbnail_hash,
                "output_path": str((output_dir / "index.html") if page.slug == "index" else (output_dir / page.slug / "index.html")),
            }
        )
    (PROJECT_ROOT / "data" / "search_thumbnail_map.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT_DIR.mkdir(exist_ok=True)
    with (AUDIT_DIR / "search-thumbnail-map.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["keyword", "slug", "page_type", "selected_thumbnail", "thumbnail_absolute_url", "selection_hash", "output_path"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_site(pages: list[Page]) -> None:
    page_map = {page.slug: page for page in pages}
    output_dir = active_output_dir()
    tmp = prepare_output(output_dir)
    for page in pages:
        if page.slug == "index":
            target = tmp / "index.html"
        else:
            target = tmp / page.slug / "index.html"
        write_text(target, render_page(page, page_map))
    write_text(tmp / "sitemap.xml", render_sitemap(pages))
    write_text(tmp / "robots.txt", render_robots())
    write_text(tmp / "404.html", render_not_found())
    write_assets(tmp)
    publish(tmp, output_dir)
    write_search_thumbnail_map(pages, output_dir)
