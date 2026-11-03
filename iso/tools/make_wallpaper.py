#!/usr/bin/env python3
"""make_wallpaper.py — draw the MetaOS wallpaper and login backdrop.

Original art, generated from `iso/contracts/tokens.json`: an ink field that
falls from the contract black to a deeper black, with one blue ring. Nothing
is copied, and no pixel is hand-placed in a binary file.

The desktop ships three sizes. Xfce can scale one image, but scaling a ring
up from 1366 to 2560 blurs the edge, and a ring is the one thing on this
desktop that has to stay crisp. First login picks the file that matches the
screen and falls back to 1080p.

    python3 iso/tools/make_wallpaper.py            write every PNG
    python3 iso/tools/make_wallpaper.py --check    exit 1 if any is stale
    python3 iso/tools/make_wallpaper.py --size 2560x1440   one size only

The image is deterministic: same tokens in, same bytes out for a given size.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
TOKENS = ISO / "contracts" / "tokens.json"
WALL_DIR = ISO / "theme" / "wallpaper"
GREETER = WALL_DIR / "greeter-wallpaper.png"
GRUB = ISO / "boot" / "grub" / "themes" / "metaos" / "meta-grub.png"

BOTTOM = (3, 5, 10)

# The default keeps the name every existing reference uses. The pack adds the
# two other panels this desktop actually meets.
SIZES = {
    "meta-wallpaper.png": (1920, 1080),
    "meta-wallpaper-2560x1440.png": (2560, 1440),
    "meta-wallpaper-1366x768.png": (1366, 768),
}


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


def build(tokens, variant="desktop", width=1920, height=1080):
    top = rgb(tokens["black"])
    ring = rgb(tokens["blue"])
    if variant == "greeter":
        # Dimmer field and a smaller ring, so the user name, the password box
        # and the session buttons sit on something calm.
        top = tuple(int(c * 0.55) for c in top)
        cx, cy = width / 2.0, height * 0.40
        radius = height * 0.26
        thickness = 8.0
        glow = 54.0
        floor = (2, 3, 6)
    elif variant == "grub":
        # The menu is drawn over the lower two thirds; keep that area quiet.
        top = tuple(int(c * 0.35) for c in top)
        cx, cy = width / 2.0, height * 0.30
        radius = height * 0.18
        thickness = 6.0
        glow = 40.0
        floor = (1, 2, 4)
    else:
        cx, cy = width / 2.0, height * 0.46
        radius = height * 0.30
        thickness = max(6.0, height * 0.0083)
        glow = max(32.0, height * 0.0426)
        floor = BOTTOM

    rows = []
    for y in range(height):
        dy = y - cy
        bg = blend(top, floor, y / (height - 1))
        row = bytearray()
        for x in range(width):
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
    return png(rows, width, height)


def targets(tokens, only=None):
    """Every PNG this tool owns, desktop pack first."""
    out = []
    for name, (width, height) in SIZES.items():
        if only and (width, height) != only:
            continue
        out.append((WALL_DIR / name, build(tokens, width=width, height=height), width, height))
    if not only:
        out.append((GREETER, build(tokens, variant="greeter"), 1920, 1080))
        out.append((GRUB, build(tokens, variant="grub"), 1920, 1080))
    return out


def main(argv):
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    only = None
    if "--size" in argv:
        try:
            width, height = argv[argv.index("--size") + 1].lower().split("x")
            only = (int(width), int(height))
        except (ValueError, IndexError):
            print("wallpaper: --size wants WxH, for example 2560x1440", file=sys.stderr)
            return 2
        if only not in SIZES.values():
            print("wallpaper: %dx%d is not one of the shipped sizes" % only, file=sys.stderr)
            return 2

    stale = 0
    for path, image, width, height in targets(tokens, only):
        if "--check" in argv:
            if not path.is_file():
                print("wallpaper: %s is missing" % path.relative_to(ISO))
                stale = 1
            elif path.read_bytes() != image:
                print("wallpaper: %s is stale (run make_wallpaper.py)" % path.relative_to(ISO))
                stale = 1
            else:
                print("wallpaper: %s is current (%dx%d)" % (path.relative_to(ISO), width, height))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            print("wallpaper: wrote %s (%d bytes, %dx%d)"
                  % (path.relative_to(ISO), len(image), width, height))
    return stale


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
