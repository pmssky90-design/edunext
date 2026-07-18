from __future__ import annotations

import csv
import hashlib
import json
import shutil
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"C:\Projects\studymap-deploy")
SOURCE_THUMBS = SOURCE_ROOT / "images" / "thumbs"
SOURCE_FIXED = SOURCE_THUMBS / "fixed"
TARGET_FIXED = ROOT / "assets" / "images" / "fixed"
TARGET_SEARCH = ROOT / "assets" / "images" / "search-thumbnails"
AUDIT = ROOT / "audit"
DATA = ROOT / "data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        header = fh.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    return struct.unpack(">II", header[16:24])


def copy_unique(files: list[Path], target_dir: Path, purpose: str) -> tuple[list[dict[str, object]], list[str]]:
    target_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    manifest: list[str] = []
    seen_hashes: set[str] = set()
    for order, source in enumerate(sorted(files, key=lambda item: item.name), start=1):
        digest = sha256(source)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        target = target_dir / source.name
        shutil.copy2(source, target)
        width, height = png_size(target)
        rows.append(
            {
                "source_path": str(source),
                "target_path": str(target),
                "file_name": source.name,
                "size_bytes": target.stat().st_size,
                "sha256": digest,
                "purpose": purpose,
                "output_order": order,
                "width": width,
                "height": height,
            }
        )
        manifest.append(f"/assets/images/{target_dir.name}/{source.name}")
    return rows, manifest


def main() -> None:
    AUDIT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    if not SOURCE_FIXED.exists():
        raise FileNotFoundError(SOURCE_FIXED)
    fixed_files = list(SOURCE_FIXED.glob("*.png"))
    search_files = [path for path in SOURCE_THUMBS.glob("*.png") if path.parent == SOURCE_THUMBS]
    fixed_rows, fixed_manifest = copy_unique(fixed_files, TARGET_FIXED, "fixed")
    search_rows, search_manifest = copy_unique(search_files, TARGET_SEARCH, "search-thumbnail")

    fixed_images = []
    for row, src in zip(fixed_rows, fixed_manifest):
        fixed_images.append(
            {
                "src": src,
                "alt": "",
                "width": row["width"],
                "height": row["height"],
            }
        )
    (DATA / "fixed_images.json").write_text(json.dumps({"images": fixed_images}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA / "search_thumbnails.json").write_text(json.dumps({"images": search_manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (AUDIT / "copied-image-inventory.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["source_path", "target_path", "file_name", "size_bytes", "sha256", "purpose", "output_order", "width", "height"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(fixed_rows + search_rows)

    analysis = [
        "# StudyNavi Image Analysis",
        "",
        f"- selected_project_path: {SOURCE_ROOT}",
        "- evidence: generated HTML uses `studynavi-flow`, `fixed-image-stack`, `representative-image`, `flow-image`, and `studymap.co.kr` image meta URLs.",
        f"- fixed_image_source: {SOURCE_FIXED}",
        f"- fixed_image_count: {len(fixed_rows)}",
        "- fixed_image_order: file name ascending, 001.png to 006.png",
        "- fixed_image_html: `figure.representative-image` for the first image, `figure.flow-image` for the rest",
        "- fixed_image_loading: StudyNavi uses lazy/async; EduNext uses eager/high for the first above-article image and lazy/async for the rest.",
        f"- search_thumbnail_source: {SOURCE_THUMBS}",
        f"- search_thumbnail_count: {len(search_rows)}",
        "- search_thumbnail_usage: metadata only in EduNext; no body img is rendered for search thumbnails.",
        "- search_thumbnail_selection: stable SHA-256 of page slug modulo thumbnail count.",
        "- metadata_targets: og:image, twitter:image, WebPage JSON-LD image.",
        "",
        "## Copied Fixed Images",
    ]
    analysis.extend(f"- {row['file_name']}: {row['width']}x{row['height']}, sha256={row['sha256']}" for row in fixed_rows)
    analysis.append("")
    analysis.append("## Copied Search Thumbnails")
    analysis.extend(f"- {row['file_name']}: {row['width']}x{row['height']}, sha256={row['sha256']}" for row in search_rows)
    (AUDIT / "studynavi-image-analysis.md").write_text("\n".join(analysis) + "\n", encoding="utf-8")
    print({"fixed": len(fixed_rows), "search_thumbnails": len(search_rows), "project": str(SOURCE_ROOT)})


if __name__ == "__main__":
    main()
