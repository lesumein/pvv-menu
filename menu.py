# -*- coding: utf-8 -*-
"""판교세븐벤처밸리점 주간 식단표 - 최신 PDF 자동 다운로드 + 표 파싱.

AI 없이 전부 규칙 기반으로 동작한다.
  1) 게시판 목록에서 id가 가장 큰 글의 첨부 PDF를 최신으로 보고 내려받는다.
  2) PDF 안에 실제로 그려진 표 테두리(rect)를 기준으로 셀을 잘라낸다.
     좌표/공백 추측이 아니라 표 격자 그 자체를 쓰므로 레이아웃이 흔들려도 안전하다.

사용법:
    python menu.py              # 오늘 식단
    python menu.py --week       # 이번 주 전체
    python menu.py 09-04        # 특정 날짜(월-일)
    python menu.py --json       # 구조화 데이터
    python menu.py --html       # 아티팩트용 menu.html 생성
    python menu.py --site       # GitHub Pages용 index.html 생성
"""
import datetime as dt
import json
import os
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

import pdfplumber

BASE = "http://pvv.co.kr/bbs/"
LIST_URL = BASE + "index.php?code=bbs_menu01"
UA = {"User-Agent": "Mozilla/5.0"}
DATE_RE = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")
TIME_RE = re.compile(r"(\d{1,2}:\d{2})\D+(\d{1,2}:\d{2})")
MEALS = ("조식", "중식", "석식")
HERE = os.path.dirname(os.path.abspath(__file__))


def _get(url):
    return urlopen(Request(url, headers=UA), timeout=30).read()


def download_latest(outdir=HERE):
    """최신 첨부 PDF를 받아 경로를 돌려준다. 이미 있으면 재사용."""
    html = _get(LIST_URL)  # 페이지가 EUC-KR이라 bytes 그대로 다룬다
    items = re.findall(
        rb"download\.php\?bbsMode=fileDown&code=bbs_menu01&id=(\d+)&filename=([^\"']+)",
        html,
    )
    if not items:
        sys.exit("첨부파일 링크를 찾지 못했습니다.")
    post_id, raw_name = max(items, key=lambda x: int(x[0]))
    path = os.path.join(outdir, raw_name.decode("cp949", "replace"))
    if not os.path.exists(path):
        url = "%sdownload.php?bbsMode=fileDown&code=bbs_menu01&id=%s&filename=%s" % (
            BASE, post_id.decode(), quote(raw_name, safe=""))
        data = _get(url)
        if not data.startswith(b"%PDF"):
            sys.exit("PDF가 아닌 응답: %r" % data[:80])
        with open(path, "wb") as f:
            f.write(data)
    return path


def _resolve_year(month, day, today):
    """식단표에는 연도가 없다. 오늘 기준 가장 가까운 해로 맞춘다(연말 걸침 대비)."""
    best = None
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            cand = dt.date(year, month, day)
        except ValueError:
            continue
        if best is None or abs((cand - today).days) < abs((best - today).days):
            best = cand
    return best


def parse(pdf_path, today=None):
    """PDF 한 장을 주간 식단 구조체로 바꾼다."""
    today = today or dt.date.today()
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        headings = [x for x in page.extract_text().split("\n") if x.strip()]
        rows = page.extract_table(
            {"vertical_strategy": "lines", "horizontal_strategy": "lines"})
    if not rows:
        sys.exit("표를 찾지 못했습니다.")

    days = {}  # 열 인덱스 -> date
    for col, cell in enumerate(rows[0]):
        m = DATE_RE.search(cell or "")
        if m:
            days[col] = _resolve_year(int(m.group(1)), int(m.group(2)), today)
    if not days:
        sys.exit("날짜 헤더를 찾지 못했습니다.")

    # date -> [(끼니, 시간, 코너, [메뉴...])], 표에 나온 순서를 유지한다
    table = {d: [] for d in days.values()}
    times, takeout, origin = {}, "", []
    meal = None
    for row in rows[1:]:
        raw = row[0] or ""
        label = raw.replace(" ", "").replace("\n", "")
        if label:
            # 라벨이 있는 행에서 구간이 바뀐다. 끼니명이 아니면 표 본문이 끝난 것.
            meal = next((n for n in MEALS if label.startswith(n)), None)
            if meal:
                t = TIME_RE.search(label)
                times[meal] = "%s~%s" % t.groups() if t else ""
            elif label.startswith("TakeOut"):
                takeout = " ".join(x.strip() for x in row[1:] if x)
            elif "원산지" in label or "국내산" in label:
                origin = [x.strip() for x in raw.split("\n") if x.strip()]
        if meal is None or not any(row[c] for c in days):
            continue
        corner = (row[1] or "").strip() or None
        for col, date in days.items():
            items = [x.strip() for x in (row[col] or "").split("\n") if x.strip()]
            if items:
                table[date].append((meal, times.get(meal, ""), corner, items))

    return {
        "title": headings[0] if headings else "",
        "site": headings[1] if len(headings) > 1 else "",
        "source": os.path.basename(pdf_path),
        "fetched": today.isoformat(),
        "takeout": takeout,
        "origin": origin,
        "days": [_pack_day(d, table[d]) for d in sorted(table)],
    }


def _pack_day(date, entries):
    meals = []
    for name, time, corner, items in entries:
        if not meals or meals[-1]["name"] != name:
            meals.append({"name": name, "time": time, "corners": []})
        meals[-1]["corners"].append({"name": corner, "items": items})
    return {
        "date": date.isoformat(),
        "label": date.strftime("%m월 %d일").lstrip("0"),
        "weekday": "월화수목금토일"[date.weekday()],
        "meals": meals,
    }


def render(week, dates):
    out = []
    by_date = {d["date"]: d for d in week["days"]}
    for date in dates:
        day = by_date.get(date.isoformat())
        out.append("[ %s (%s) ]" % (date.strftime("%m월 %d일"), "월화수목금토일"[date.weekday()]))
        if not day:
            out.append("  식단 없음")
            continue
        for meal in day["meals"]:
            out.append("  %s %s" % (meal["name"], meal["time"]))
            for corner in meal["corners"]:
                prefix = "    %s: " % corner["name"] if corner["name"] else "    "
                out.append(prefix + " · ".join(corner["items"]))
        out.append("")
    if week["takeout"]:
        out.append("Take Out: %s" % week["takeout"])
    return "\n".join(out)


"""GitHub Pages용 껍데기. 아티팩트는 claude.ai가 head를 붙여주지만
여기서는 직접 붙여야 하고, PWA 설치에 필요한 manifest/서비스워커도 여기서 건다."""
SHELL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#F2F3EF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141714" media="(prefers-color-scheme: dark)">
<meta name="description" content="판교세븐벤처밸리점 주간 식단표. 지금 배식중인 끼니를 바로 확인하세요.">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="식단표">
<meta property="og:type" content="website">
<meta property="og:site_name" content="판교세븐벤처밸리 식단표">
<meta property="og:title" content="판교세븐벤처밸리 주간 식단표">
<meta property="og:description" content="지금 배식중인 끼니를 바로 확인하세요. 조·중·석식, 매주 자동 업데이트.">
<meta property="og:url" content="https://pvv-menu.sumi.kr/">
<meta property="og:image" content="https://pvv-menu.sumi.kr/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="판교세븐벤처밸리 주간 식단표">
<meta name="twitter:description" content="지금 배식중인 끼니를 바로 확인하세요. 조·중·석식, 매주 자동 업데이트.">
<meta name="twitter:image" content="https://pvv-menu.sumi.kr/og-image.png">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" href="icons/icon-192.png">
<style>html{color-scheme:light dark}body{margin:0}img{max-width:100%%}[hidden]{display:none!important}</style>
%s
</head>
<body>
%s
<script>
if ("serviceWorker" in navigator) {
  addEventListener("load", function () { navigator.serviceWorker.register("sw.js"); });
}
</script>
</body>
</html>
"""


def _fill(week):
    with open(os.path.join(HERE, "menu_template.html"), encoding="utf-8") as f:
        html = f.read()
    if "/*__MENU_DATA__*/null" not in html:
        sys.exit("템플릿에서 /*__MENU_DATA__*/null 자리를 찾지 못했습니다.")
    return html.replace("/*__MENU_DATA__*/null",
                        json.dumps(week, ensure_ascii=False, separators=(",", ":")))


def _save(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def write_html(week, out_path=os.path.join(HERE, "menu.html")):
    """아티팩트용 단일 HTML(head 없음)."""
    return _save(out_path, _fill(week))


HEAD_TAG = re.compile(r"\A(?:<title>.*?</title>|<link\b[^>]*>)\s*", re.S)


def write_site(week, out_path=os.path.join(HERE, "index.html")):
    """GitHub Pages용 설치 가능한 페이지. 템플릿 앞머리의 title/link는 head로 올린다."""
    body = _fill(week)
    head = []
    while True:
        m = HEAD_TAG.match(body)
        if not m:
            break
        head.append(m.group(0).strip())
        body = body[m.end():]
    return _save(out_path, SHELL % ("\n".join(head), body))


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    week = parse(download_latest())
    today = dt.date.today()

    if "--json" in argv:
        print(json.dumps(week, ensure_ascii=False, indent=2))
        return
    if "--html" in argv:
        print("생성: %s (%s)" % (write_html(week), week["title"]))
        return
    if "--site" in argv:
        print("생성: %s (%s)" % (write_site(week), week["title"]))
        return

    known = [dt.date.fromisoformat(d["date"]) for d in week["days"]]
    if "--week" in argv:
        dates = known
    elif [a for a in argv if "-" in a and not a.startswith("--")]:
        mm, dd = (int(x) for x in [a for a in argv if "-" in a][0].split("-")[-2:])
        dates = [d for d in known if (d.month, d.day) == (mm, dd)]
    elif today in known:
        dates = [today]
    else:
        print("오늘(%s) 식단이 이 표에 없습니다. 전체를 표시합니다.\n" % today)
        dates = known

    print("%s · %s" % (week["title"], week["site"]))
    print(render(week, dates))


if __name__ == "__main__":
    main(sys.argv[1:])
