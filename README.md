# 판교세븐벤처밸리 식단

[pvv.co.kr 식단 게시판](http://pvv.co.kr/bbs/index.php?code=bbs_menu01)의 최신 주간 식단표 PDF를
자동으로 받아 폰에서 보기 좋게 보여주는 페이지. 매주 월요일 아침 GitHub Actions가 알아서 갱신한다.

**https://lesumein.github.io/pvv-menu/** — 홈 화면에 추가하면 앱처럼 설치된다.

## 어떻게 읽어오나

AI를 쓰지 않는다. 전부 규칙 기반이다.

1. 게시판 목록에서 `download.php` 링크를 긁어 **id가 가장 큰 글**을 최신으로 본다.
   게시판이 EUC-KR이라 파일명은 원본 바이트 그대로 percent-encoding 해야 내려받아진다.
2. PDF 안에 **실제로 그려진 표 테두리**(pdfplumber `lines` 전략)를 격자로 써서 셀을 잘라낸다.
   공백 정렬 텍스트를 열 위치로 추측하면 목요일 열이 줄마다 흔들리고, 병합된 끼니 라벨이
   세로 중앙 정렬이라 구간 경계를 잡을 수 없다. 표 격자를 쓰면 그런 추측이 필요 없다.
3. 0행에서 날짜, 0열에서 끼니(조식/중식/석식)와 배식 시간, 1열에서 코너를 읽는다.
   식단표에 연도가 없으므로 오늘 기준 가장 가까운 해로 보정한다(연말 걸침 대비).

## 쓰기

```
pip install -r requirements.txt

python menu.py            # 오늘 식단
python menu.py --week     # 이번 주 전체
python menu.py 09-04      # 특정 날짜
python menu.py --json     # 구조화 데이터
python menu.py --site     # index.html 생성 (Pages 배포본)
python menu.py --html     # menu.html 생성 (Claude 아티팩트용, head 없음)
```

디자인은 `menu_template.html` 하나에만 있다. `/*__MENU_DATA__*/null` 자리에 주간 데이터가 주입된다.
아이콘을 다시 만들려면 `python make_icons.py`.

## 구성

| 파일 | 역할 |
|---|---|
| `menu.py` | 다운로드 · 파싱 · 렌더 |
| `menu_template.html` | 페이지 디자인 (단일 소스) |
| `index.html` | 생성물. Pages가 서빙 |
| `sw.js`, `manifest.webmanifest`, `icons/` | PWA 설치 · 오프라인 |
| `.github/workflows/update-menu.yml` | 매주 월요일 07:00 KST 자동 갱신 |

## 한계

- 식단표가 **스캔 이미지**로 올라오면 표 격자가 없어 실패한다(`표를 찾지 못했습니다`).
  그때는 OCR이 필요하다.
- Actions 크론은 저장소에 60일간 활동이 없으면 자동 중지된다. 갱신 때마다 `index.html`의
  `fetched` 날짜가 바뀌어 커밋이 남으므로 실제로는 걸리지 않는다.
