# -*- coding: utf-8 -*-
"""앱 아이콘 + 링크 공유용 OG 이미지 생성 (Pillow).

    python make_assets.py

정체성: 운영 브랜드 네이처델리(하림FS)의 따뜻한 톤(갈색·크림·초록 잎)에
장소 '판교세븐벤처밸리 · 식단표' 정보를 얹은 오리지널 마크. 로고 복제 아님.
아이콘·OG는 자주 안 바뀌므로 이 스크립트는 개발용이다(주간 갱신과 무관).
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "icons")

BROWN = (0x53, 0x36, 0x26)     # 제목 갈색
BROWN2 = (0x8A, 0x6E, 0x57)    # 보조 텍스트(크림 위에서 읽히게)
CREAM = (0xF5, 0xF1, 0xE8)     # 바탕
WHITE = (0xFF, 0xFF, 0xFF)
LEAF = (0x74, 0xA5, 0x3C)      # 잎(네이처델리 그린 계열)
LEAF_D = (0x5E, 0x8C, 0x30)
FAINT = (0xB0, 0xA0, 0x8C)
LINE = (0xE2, 0xDD, 0xD0)
MEAL = [(0x54, 0x74, 0x94), (0xC1, 0x66, 0x2C), (0x63, 0x50, 0x7C)]  # 조·중·석

MALGUN = "C:/Windows/Fonts/malgun.ttf"
MALGUN_B = "C:/Windows/Fonts/malgunbd.ttf"


def font(bold, size):
    return ImageFont.truetype(MALGUN_B if bold else MALGUN, size)


def leaf(size, angle=35):
    """두 원의 교집합으로 만든 아몬드형 잎 (RGBA, 중앙에 잎맥)."""
    up = 4
    L = size * up
    a = Image.new("L", (L, L), 0)
    b = Image.new("L", (L, L), 0)
    r = int(L * 0.72)
    off = int(L * 0.42)
    cx = L // 2
    ImageDraw.Draw(a).ellipse([cx - off - r, cx - r, cx - off + r, cx + r], fill=255)
    ImageDraw.Draw(b).ellipse([cx + off - r, cx - r, cx + off + r, cx + r], fill=255)
    mask = ImageChops.darker(a, b)
    col = Image.new("RGBA", (L, L), LEAF + (255,))
    col.putalpha(mask)
    d = ImageDraw.Draw(col)
    d.line([(cx - r + off + int(L * 0.28), cx), (cx + r - off - int(L * 0.28), cx)],
           fill=LEAF_D + (255,), width=int(L * 0.022))
    col = col.rotate(angle, resample=Image.BICUBIC, expand=True)
    return col.resize((col.width // up, col.height // up), Image.LANCZOS)


def tile(size, bg):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, size, size], size * 0.225, fill=bg)
    return img


def fit_font(d, text, bold, max_w, start):
    """max_w에 들어갈 때까지 폰트 크기를 줄인다."""
    s = start
    while s > 8 and d.textlength(text, font=font(bold, s)) > max_w:
        s -= 2
    return font(bold, s)


def make_icon(size, ss=4):
    """maskable 안전영역(가운데 80% 원) 안에만 내용을 둔다.
    배경은 전체를 꽉 채워(둥근 모서리 없이) OS 마스크가 모양을 잡게 한다.
    긴 장소명은 잘리고 홈 라벨과 중복이라 넣지 않는다."""
    S = size * ss
    img = Image.new("RGBA", (S, S), BROWN)   # 전체 채움(마스킹 대비)
    # 잎: 상단 중앙
    lf = leaf(int(S * 0.24), angle=32)
    img.alpha_composite(lf, (int(S / 2 - lf.width / 2), int(S * 0.24)))
    d = ImageDraw.Draw(img)
    # 식단표: 중앙, 폭 62% 안에 들어오게
    f = fit_font(d, "식단표", True, S * 0.62, int(S * 0.30))
    d.text((S / 2, S * 0.585), "식단표", font=f, fill=CREAM, anchor="mm")
    # 초록 밑줄 (안전영역 안)
    d.rounded_rectangle([S * 0.35, S * 0.71, S * 0.65, S * 0.745], S * 0.017, fill=LEAF)
    return img.resize((size, size), Image.LANCZOS)


def draw_card(img, cx, cy, cw, ch, ss):
    """오른쪽 주간 표 카드: 요일 헤더 + 끼니 색 행 (식단표임을 바로 전달)."""
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx, cy, cx + cw, cy + ch], 34 * ss, fill=WHITE)
    fday = font(False, 30 * ss)
    hx, hy = cx + 34 * ss, cy + 40 * ss
    cellw = (cw - 68 * ss) / 5
    for i, wd in enumerate("월화수목금"):
        d.text((hx + cellw * i + cellw / 2, hy), wd, font=fday, fill=BROWN2, anchor="ma")
    d.line([(hx, hy + 52 * ss), (cx + cw - 34 * ss, hy + 52 * ss)], fill=LINE, width=2 * ss)
    # 끼니 행 3개
    rx, rw = cx + 34 * ss, cw - 68 * ss
    ry = hy + 82 * ss
    rowh = (ch - 200 * ss) / 3
    gap = rowh * 0.34
    rh = rowh - gap
    for i in range(3):
        y = ry + i * rowh
        d.rounded_rectangle([rx, y, rx + rw, y + rh], rh * 0.28, fill=CREAM)
        pad = rh * 0.22
        tag = rh - 2 * pad
        d.rounded_rectangle([rx + pad, y + pad, rx + pad + tag, y + pad + tag],
                            tag * 0.28, fill=MEAL[i])
        tx = rx + pad + tag + pad
        bh = rh * 0.15
        d.rounded_rectangle([tx, y + rh * 0.32, rx + rw - pad, y + rh * 0.32 + bh],
                            bh / 2, fill=(0xD9, 0xD2, 0xC4))


def make_og(path):
    W, H = 1200, 630
    ss = 2
    img = Image.new("RGBA", (W * ss, H * ss), CREAM)
    # 오른쪽 카드 + 부드러운 그림자
    cw = ch = 384 * ss
    cx = W * ss - 88 * ss - cw
    cy = (H * ss - ch) // 2
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([cx, cy + 10 * ss, cx + cw, cy + ch + 10 * ss],
                                         34 * ss, fill=(60, 45, 30, 60))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(14 * ss)))
    draw_card(img, cx, cy, cw, ch, ss)

    d = ImageDraw.Draw(img)
    P = 96 * ss
    x, y = P, 118 * ss
    d.text((x, y), "판교세븐벤처밸리점", font=font(False, 34 * ss), fill=BROWN2)
    y += 54 * ss
    big = font(True, 118 * ss)
    d.text((x, y), "주간", font=big, fill=BROWN); y += 126 * ss
    d.text((x, y), "식단표", font=big, fill=BROWN)
    # 제목 옆 잎
    lf = leaf(84 * ss, angle=32)
    img.alpha_composite(lf, (x + int(d.textlength("식단표", font=big)) + 20 * ss, y + 12 * ss))
    d = ImageDraw.Draw(img)
    d.text((P, H * ss - 62 * ss - 34 * ss), "pvv-menu.sumi.kr  ·  매주 자동 업데이트",
           font=font(False, 34 * ss), fill=FAINT)

    img.convert("RGB").resize((W, H), Image.LANCZOS).save(path, "PNG")
    return path


def main():
    if not os.path.isdir(ICONS):
        os.makedirs(ICONS)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512),
                       ("apple-touch-icon.png", 180)]:
        make_icon(size).save(os.path.join(ICONS, name), "PNG")
        print("icons/" + name)
    make_og(os.path.join(HERE, "og-image.png"))
    print("og-image.png")


if __name__ == "__main__":
    main()
