from pathlib import Path

SITE_NAME = "EduNext"
SITE_URL = "https://edunext.co.kr"
SITE_DESCRIPTION = "부산, 양산, 구미 지역별 과외 학습 정보를 정리한 교육 허브"
NAVER_SITE_VERIFICATION = "5e86d1c886813bddb33f5314c98324fac8b42484"

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CONTENT_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_content_fixed"
SCHOOL_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_school_fixed"
TITLE_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_title_fixed"
STRUCTURE_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_structure_fixed"
IMAGE_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_image_fixed"
HOME_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_home_fixed"
HOME_FIXED_V2_OUTPUT_DIR = PROJECT_ROOT / "output_home_fixed_v2"
MOBILE_FIXED_OUTPUT_DIR = PROJECT_ROOT / "output_mobile_fixed"
HOME_REDESIGN_OUTPUT_DIR = PROJECT_ROOT / "output_home_redesign"
MENU_CONTENT_REDESIGN_OUTPUT_DIR = PROJECT_ROOT / "output_menu_content_redesign"
NAV_CLEAN_OUTPUT_DIR = PROJECT_ROOT / "output_nav_clean"
PREDEPLOY_FINAL_OUTPUT_DIR = PROJECT_ROOT / "output_predeploy_final"
ASSETS_DIR = PROJECT_ROOT / "assets"
AUDIT_DIR = PROJECT_ROOT / "audit"

SOURCE_DATA_DIR = Path(r"C:\gptwp\자료")
REGION_EXCEL = SOURCE_DATA_DIR / "부산 구미 양산 포항 경산 (메인 키워드).xlsx"
CONTENT_EXCEL = SOURCE_DATA_DIR / "부산_구미_양산 메인허브키워드 학교 포함.xlsx"

TARGET_CITIES = {"부산", "양산", "구미"}
CITY_PROVINCE = {
    "부산": "부산",
    "양산": "경남",
    "구미": "경북",
}

CATEGORIES = [
    "과외",
    "영어과외",
    "수학과외",
    "초등과외",
    "중등과외",
    "고등과외",
    "초등영어과외",
    "중등영어과외",
    "고등영어과외",
    "초등수학과외",
    "중등수학과외",
    "고등수학과외",
]

SUBJECT_CATEGORIES = {"영어과외", "수학과외"}
GRADE_CATEGORIES = {"초등과외", "중등과외", "고등과외"}
SUBJECT_GRADE_CATEGORIES = {
    "초등영어과외",
    "중등영어과외",
    "고등영어과외",
    "초등수학과외",
    "중등수학과외",
    "고등수학과외",
}

SCHOOL_SHEETS = {
    "고등과외\u3000내신\u3000수능\u3000전문",
    "고등\u3000수학과외\u3000내신\u3000맞춤\u3000수업",
    "고등\u3000영어과외\u3000내신\u3000수행평가\u3000입시\u3000전문과외",
}
