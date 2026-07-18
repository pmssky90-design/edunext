from __future__ import annotations

import time

from sitegen.data_loader import load_content, load_regions, load_school_region_map
from sitegen.pages import build_pages
from sitegen.writer import write_site


def build_site() -> None:
    started = time.perf_counter()
    regions = load_regions()
    content, school_slugs = load_content()
    school_map = load_school_region_map()
    pages, stats = build_pages(regions, content, school_slugs, school_map)
    write_site(pages)
    elapsed = time.perf_counter() - started
    print(f"EduNext generation complete in {elapsed:.2f}s")
    print(f"regions: {len(regions)}")
    print(f"content rows: {len(content)}")
    print(f"pages: {len(pages)}")
    print(f"sitemap urls: {len(pages)}")
    print("stats:", dict(sorted(stats.items())))
