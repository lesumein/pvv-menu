# -*- coding: utf-8 -*-
"""앱 아이콘(식판 모양) 생성. 외부 라이브러리 없이 PNG를 직접 쓴다.

4배 크기로 그린 뒤 축소해 모서리를 매끄럽게 만든다.
    python make_icons.py
"""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")
SS = 4  # 슈퍼샘플링 배율

GROUND = (0x2F, 0x6B, 0x57)   # 청자 그린 - 페이지 강조색과 같은 값
TRAY = (0xF2, 0xF3, 0xEF)     # 식판 바탕
CELL = (0xD2, 0xDA, 0xD2)     # 반찬 칸

# 식판: 위 3칸(반찬) + 아래 2칸(밥/국). 0~1 정규 좌표
TRAY_BOX = (0.135, 0.200, 0.865, 0.800)
TRAY_R = 0.055
CELL_R = 0.022
INNER = (0.180, 0.248, 0.820, 0.752)
GAP = 0.026


def rounded_rect(buf, size, box, radius, color):
    x0, y0, x1, y1 = [v * size for v in box]
    r = radius * size
    for y in range(max(0, int(y0)), min(size, int(y1) + 1)):
        for x in range(max(0, int(x0)), min(size, int(x1) + 1)):
            # 모서리 원 안쪽인지 검사
            cx = min(max(x + .5, x0 + r), x1 - r)
            cy = min(max(y + .5, y0 + r), y1 - r)
            dx, dy = x + .5 - cx, y + .5 - cy
            if dx * dx + dy * dy > r * r:
                continue
            i = (y * size + x) * 3
            buf[i:i + 3] = bytes(color)


def cells():
    x0, y0, x1, y1 = INNER
    w = x1 - x0
    top_h = (y1 - y0) * .40
    bot_y = y0 + top_h + GAP
    cw = (w - 2 * GAP) / 3
    out = [(x0 + i * (cw + GAP), y0, x0 + i * (cw + GAP) + cw, y0 + top_h) for i in range(3)]
    bw = (w - GAP) / 2
    out += [(x0 + i * (bw + GAP), bot_y, x0 + i * (bw + GAP) + bw, y1) for i in range(2)]
    return out


def render(size):
    big = size * SS
    buf = bytearray(bytes(GROUND) * (big * big))
    rounded_rect(buf, big, TRAY_BOX, TRAY_R, TRAY)
    for box in cells():
        rounded_rect(buf, big, box, CELL_R, CELL)

    # 박스 필터로 축소하며 알파 채널을 붙인다
    out = bytearray(size * size * 4)
    n = SS * SS
    for y in range(size):
        for x in range(size):
            r = g = b = 0
            for sy in range(SS):
                row = ((y * SS + sy) * big + x * SS) * 3
                for sx in range(SS):
                    i = row + sx * 3
                    r += buf[i]
                    g += buf[i + 1]
                    b += buf[i + 2]
            o = (y * size + x) * 4
            out[o] = r // n
            out[o + 1] = g // n
            out[o + 2] = b // n
            out[o + 3] = 255
    return bytes(out)


def write_png(path, size, pixels):
    raw = b"".join(b"\x00" + pixels[y * size * 4:(y + 1) * size * 4] for y in range(size))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512),
                       ("apple-touch-icon.png", 180)]:
        n = write_png(os.path.join(OUT, name), size, render(size))
        print("%s  %d bytes" % (name, n))


if __name__ == "__main__":
    main()
