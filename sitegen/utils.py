from __future__ import annotations

import html
import re


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\u3000", " ").strip()


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def excerpt(value: str, limit: int = 115) -> str:
    text = strip_tags(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalize_slug(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().replace("\u3000", ""))


def page_slug(region_slug: str | None, category: str) -> str:
    if not region_slug:
        return "전국과외" if category == "과외" else category
    return f"{region_slug}{category}"
