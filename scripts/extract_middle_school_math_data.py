from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import re
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"C:\자료\주요자료\2025년 유초중등 학교별 학년별 학생수 학급수 입학 졸업 교원 직원 면적_260206W.xlsx")
DEFAULT_OUTPUT = ROOT / "data" / "middle_school_math_pages.json"
TARGETS = {("부산", None): "부산", ("경남", "양산시"): "양산", ("경북", "구미시"): "구미"}
TOWN_PATTERN = re.compile(r"[가-힣0-9]+(?:동|읍|면)")


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def date_text(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    text = clean(value).split(" ", 1)[0].replace(".", "-")
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def number(value: object) -> int | float:
    if value in (None, ""):
        return 0
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else round(parsed, 2)


def display_name(official: str) -> str:
    if official.endswith("여자중학교"):
        return official[: -len("여자중학교")] + "여중"
    if official.endswith("중학교"):
        return official[: -len("중학교")] + "중"
    return official


def city_for(province: str, district: str) -> str:
    if province == "부산":
        return "부산"
    return TARGETS.get((province, district), "")


def school_rows(source: Path) -> list[dict[str, object]]:
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    worksheet = workbook["학교별 주요통계"]
    rows: list[dict[str, object]] = []
    for row_index, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
        if row_index <= 17:
            continue
        province = clean(row[1])
        district = clean(row[2])
        city = city_for(province, district)
        if not city or clean(row[4]) != "중학교" or clean(row[11]) != "본교":
            continue
        if "폐교" in clean(row[15]):
            continue
        official = clean(row[8])
        display = display_name(official)
        base = display if display.startswith(city) else f"{city}{display}"
        address = clean(row[19])
        towns = TOWN_PATTERN.findall(address)
        town = towns[-1] if towns else ""
        coeducation = clean(row[14]).replace("남여공학", "남녀공학")
        rows.append(
            {
                "slug": f"{base}수학과외",
                "city": city,
                "province": province,
                "district": district,
                "town": town,
                "official_name": official,
                "display_name": display,
                "english_name": clean(row[9]),
                "kedi_code": clean(row[10]),
                "school_detail": clean(row[6]),
                "establishment": clean(row[12]),
                "coeducation": coeducation,
                "status": clean(row[15]),
                "opened_on": date_text(row[17]),
                "postal_code": clean(row[18]),
                "address": address,
                "telephone": clean(row[20]),
                "homepage": clean(row[22]),
                "general_classes": number(row[24]),
                "general_students": number(row[25]),
                "special_classes": number(row[28]),
                "special_students": number(row[29]),
                "total_classes": number(row[32]),
                "grade1_classes": number(row[33]),
                "grade2_classes": number(row[34]),
                "grade3_classes": number(row[35]),
                "total_students": number(row[39]),
                "grade1_students": number(row[42]),
                "grade2_students": number(row[45]),
                "grade3_students": number(row[48]),
                "students_per_class": number(row[60]),
                "teachers": number(row[61]),
                "students_per_teacher": number(row[103]),
                "admissions": number(row[112]),
                "graduates": number(row[115]),
                "source_date": date_text(row[0]),
                "source_row": row_index,
            }
        )
    workbook.close()
    return sorted(rows, key=lambda item: str(item["slug"]))


def validate(rows: list[dict[str, object]]) -> None:
    slugs = [str(row["slug"]) for row in rows]
    errors: list[str] = []
    if len(rows) != 218:
        errors.append(f"expected 218 rows, found {len(rows)}")
    if len(slugs) != len(set(slugs)):
        errors.append("duplicate slugs found")
    for row in rows:
        missing = [key for key in ("slug", "city", "district", "town", "official_name", "homepage", "address") if not row.get(key)]
        if missing:
            errors.append(f"{row.get('slug')}: missing {', '.join(missing)}")
    if errors:
        raise ValueError("\n".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Busan, Yangsan and Gumi middle-school math page data.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = school_rows(args.source)
    validate(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    city_counts = {city: sum(1 for row in rows if row["city"] == city) for city in ("부산", "양산", "구미")}
    print(f"wrote {len(rows)} rows to {args.output}")
    print(city_counts)


if __name__ == "__main__":
    main()
