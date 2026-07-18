from __future__ import annotations

from datetime import date

from config import SITE_URL
from sitegen.models import Page


def render_sitemap(pages: list[Page]) -> str:
    items = []
    for page in sorted(pages, key=lambda item: item.url):
        if page.slug == "index":
            loc = SITE_URL + "/"
        else:
            loc = SITE_URL + page.url
        items.append(f"  <url><loc>{loc}</loc><lastmod>{date.today().isoformat()}</lastmod></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(items) + "\n</urlset>\n"


def render_robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
