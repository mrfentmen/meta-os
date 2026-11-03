#!/usr/bin/env python3
"""make_wallpaper.py — draw the MetaOS wallpaper and login backdrop.

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
GREETER = ISO / "theme" / "wallpaper" / "greeter-wallpaper.png"

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


def build(tokens, greeter=False):
    top = rgb(tokens["black"])
    ring = rgb(tokens["blue"])
    if greeter:
        # Dimmer field and a smaller ring, so the user name, the password box
        # and the session buttons sit on something calm.
        top = tuple(int(c * 0.55) for c in top)
        cx, cy = W / 2.0, H * 0.40
        radius = H * 0.26
        thickness = 8.0
        glow = 54.0
        floor = (2, 3, 6)
    else:
        cx, cy = W / 2.0, H * 0.46
        radius = H * 0.30
        thickness = 9.0
        glow = 46.0
        floor = BOTTOM

    rows = []
    for y in range(H):
        dy = y - cy
        bg = blend(top, floor, y / (H - 1))
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
    targets = ((OUT, build(tokens)), (GREETER, build(tokens, greeter=True)))

    stale = 0
    for path, image in targets:
        if "--check" in argv:
            if not path.is_file():
                print("wallpaper: %s is missing" % path.relative_to(ISO))
                stale = 1
            elif path.read_bytes() != image:
                print("wallpaper: %s is stale (run make_wallpaper.py)" % path.relative_to(ISO))
                stale = 1
            else:
                print("wallpaper: %s is current" % path.relative_to(ISO))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            print("wallpaper: wrote %s (%d bytes, %dx%d)"
                  % (path.relative_to(ISO), len(image), W, H))
    return stale


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
