from __future__ import annotations

import re

HOME_SEO_TITLE = "부산 구미 양산 지역별 과외 정보"

TYPE_PREFIXES = [
    "초등수학과외",
    "중등수학과외",
    "고등수학과외",
    "초등영어과외",
    "중등영어과외",
    "고등영어과외",
    "고등 수학과외",
    "고등 영어과외",
    "수학과외",
    "영어과외",
    "초등과외",
    "중등과외",
    "고등과외",
    "과외",
]

GENERATED_HUB_KEYWORDS = {
    f"{region}{category}"
    for region in ("전국", "경남", "경북")
    for category in (
        "과외", "영어과외", "수학과외", "초등과외", "중등과외", "고등과외",
        "초등영어과외", "중등영어과외", "고등영어과외",
        "초등수학과외", "중등수학과외", "고등수학과외",
    )
}
GENERATED_HUB_KEYWORDS.update({
    "영어과외", "수학과외", "초등과외", "중등과외", "고등과외",
    "초등영어과외", "중등영어과외", "고등영어과외",
    "초등수학과외", "중등수학과외", "고등수학과외",
})


def normalize_spaces(value: str) -> str:
    value = value.replace("\u3000", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r",(?=\S)", ", ", value)
    value = re.sub(r"\s*([|_])\s*(EDUNEXT|CLASSNOVA)\s*$", "", value, flags=re.I)
    value = re.sub(r"\s*[-|_]\s*$", "", value)
    return value.strip()


def sheet_suffix(sheet_name: str) -> tuple[str, bool]:
    value = normalize_spaces(sheet_name)
    for prefix in TYPE_PREFIXES:
        if value == prefix:
            return "", True
        if value.startswith(prefix + " "):
            return normalize_spaces(value[len(prefix) + 1 :]), True
    return value, False


def build_page_title(keyword: str, source_sheet: str | None) -> tuple[str, bool]:
    if not source_sheet:
        if keyword in GENERATED_HUB_KEYWORDS:
            scope = "지역별" if keyword.startswith(("경남", "경북")) else "전국"
            return normalize_spaces(f"{keyword} {scope} 학습 정보"), False
        return normalize_spaces(keyword), False
    suffix, removed = sheet_suffix(source_sheet)
    title = normalize_spaces(f"{keyword} {suffix}" if suffix else keyword)
    return title, removed
