# EduNext

부산, 양산, 구미 지역 과외 정적 사이트 생성 프로젝트입니다. 대표 도메인은 `https://edunext.co.kr`이며 canonical, sitemap, robots, JSON-LD 모두 non-www 기준으로 생성합니다.

## 실행

```powershell
& "C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" generator.py
& "C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" scripts\audit_site.py
& "C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" -m http.server 8000 --directory output
```

일반 Python 경로가 잡힌 환경에서는 아래처럼 실행할 수 있습니다.

```powershell
python generator.py
python scripts\audit_site.py
python -m http.server 8000 --directory output
```

## 데이터

- 지역 데이터: `C:\gptwp\자료\부산 구미 양산 포항 경산 (메인 키워드).xlsx`
- 콘텐츠 데이터: `C:\gptwp\자료\부산_구미_양산 메인허브키워드 학교 포함.xlsx`
- 1차 생성 대상: 부산, 양산, 구미
- 학교 페이지: 콘텐츠 엑셀의 학교 시트에 실제 본문이 있는 키워드만 생성

## 검증 산출물

`python scripts\audit_site.py` 실행 후 `audit/`에 다음 파일이 생성됩니다.

- `summary.md`
- `broken-links.csv`
- `orphan-pages.csv`
- `crawl-depth.csv`
- `duplicate-titles.csv`
- `duplicate-descriptions.csv`
- `canonical-errors.csv`
- `domain-errors.csv`
- `sitemap-errors.csv`
- `content-similarity.csv`

## 배포 전 확인

```powershell
& "C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" scripts\pre_deploy_check.py
```

실제 Git push, Vercel 배포, DNS 변경은 이 프로젝트에서 자동으로 수행하지 않습니다.
