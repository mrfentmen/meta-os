#!/usr/bin/env python3
"""make_wallpaper.py — draw the MetaOS wallpaper from the frozen tokens.

Original art, generated from `iso/contracts/tokens.json`: an ink field that
falls from the contract black to a deeper black, with one blue ring. Nothing
is copied, and no pixel is hand-placed in a binary file.

    python3 iso/tools/make_wallpaper.py            write the PNG
    python3 iso/tools/make_wallpaper.py --check    exit 1 if the file is stale

The image is deterministic: same tokens in, same bytes out.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
TOKENS = ISO / "contracts" / "tokens.json"
OUT = ISO / "theme" / "wallpaper" / "meta-wallpaper.png"

W, H = 1920, 1080
BOTTOM = (3, 5, 10)


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def blend(base, over, alpha):
    if alpha <= 0.0:
        return base
    return tuple(int(round(b + (o - b) * alpha)) for b, o in zip(base, over))


def png(rows, width, height):
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def build(tokens):
    top = rgb(tokens["black"])
    ring = rgb(tokens["blue"])
    cx, cy = W / 2.0, H * 0.46
    radius = H * 0.30
    thickness = 9.0
    glow = 46.0

    rows = []
    for y in range(H):
        dy = y - cy
        bg = blend(top, BOTTOM, y / (H - 1))
        row = bytearray()
        for x in range(W):
            dx = x - cx
            off = abs((dx * dx + dy * dy) ** 0.5 - radius)
            if off <= thickness:
                alpha = 1.0 - (off / thickness) ** 2
            elif off <= glow:
                alpha = 0.20 * (1.0 - (off - thickness) / (glow - thickness))
            else:
                alpha = 0.0
            row += bytes(blend(bg, ring, alpha)) + b"\xff"
        rows.append(bytes(row))
    return png(rows, W, H)


def main(argv):
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    image = build(tokens)

    if "--check" in argv:
        if not OUT.is_file():
            print("wallpaper: %s is missing" % OUT.relative_to(ISO))
            return 1
        if OUT.read_bytes() != image:
            print("wallpaper: %s is stale (run make_wallpaper.py)" % OUT.relative_to(ISO))
            return 1
        print("wallpaper: %s is current" % OUT.relative_to(ISO))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(image)
    print("wallpaper: wrote %s (%d bytes, %dx%d)"
          % (OUT.relative_to(ISO), len(image), W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
