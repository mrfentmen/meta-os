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

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
TOKENS = ISO / "contracts" / "tokens.json"
WALL_DIR = ISO / "theme" / "wallpaper"
GREETER = WALL_DIR / "greeter-wallpaper.png"
ACTIVE = WALL_DIR / "greeter-active.png"
MANIFEST = WALL_DIR / "MANIFEST.json"
GREETER_SIZES = {
    "greeter-wallpaper.png": (1920, 1080),
    "greeter-wallpaper-2560x1440.png": (2560, 1440),
    "greeter-wallpaper-3840x2160.png": (3840, 2160),
    "greeter-wallpaper-1366x768.png": (1366, 768),
}
GRUB = ISO / "boot" / "grub" / "themes" / "metaos" / "meta-grub.png"

BOTTOM = (3, 5, 10)

# The default keeps the name every existing reference uses. The pack adds the
# two other panels this desktop actually meets.
SIZES = {
    "meta-wallpaper.png": (1920, 1080),
    "meta-wallpaper-2560x1440.png": (2560, 1440),
    "meta-wallpaper-3840x2160.png": (3840, 2160),
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
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


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

    # Outside this band every pixel in a row is the same colour, so that part
    # is one bytes multiply. Only the ring gets a per-pixel loop, which is what
    # makes a 4K check take seconds instead of minutes.
    band = radius + glow + 2
    left = max(0, int(cx - band))
    right = min(width, int(cx + band) + 1)

    rows = []
    for y in range(height):
        dy = y - cy
        bg = blend(top, floor, y / (height - 1))
        unit = bytes(bg) + b"\xff"
        row = bytearray(unit * left)
        for x in range(left, right):
            dx = x - cx
            off = abs((dx * dx + dy * dy) ** 0.5 - radius)
            if off <= thickness:
                alpha = 1.0 - (off / thickness) ** 2
            elif off <= glow:
                alpha = 0.20 * (1.0 - (off - thickness) / (glow - thickness))
            else:
                alpha = 0.0
            row += bytes(blend(bg, ring, alpha)) + b"\xff"
        row += unit * (width - right)
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
        base = None
        for name, (width, height) in GREETER_SIZES.items():
            image = build(tokens, variant="greeter", width=width, height=height)
            out.append((WALL_DIR / name, image, width, height))
            if name == "greeter-wallpaper.png":
                base = image
        # LightDM points at this name, so it always exists, before the picker
        # has run and after it: no missing-backdrop window on the first boot.
        out.append((ACTIVE, base, 1920, 1080))
        out.append((GRUB, build(tokens, variant="grub"), 1920, 1080))
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(tokens) -> int:
    """Fast path: hash what is on disk, do not redraw 32 million pixels."""
    if not MANIFEST.is_file():
        print("wallpaper: MANIFEST.json is missing (run make_wallpaper.py)")
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    want = hashlib.sha256(TOKENS.read_bytes()).hexdigest()
    if data.get("tokens_sha256") != want:
        print("wallpaper: tokens changed since the pack was drawn (run make_wallpaper.py)")
        return 1
    files = data.get("files", {})
    if not files:
        print("wallpaper: MANIFEST.json lists no files")
        return 1
    stale = 0
    for rel, info in sorted(files.items()):
        path = ISO / rel
        if not path.is_file():
            print("wallpaper: %s is missing" % rel)
            stale = 1
        elif digest(path) != info.get("sha256"):
            print("wallpaper: %s is stale (run make_wallpaper.py)" % rel)
            stale = 1
        else:
            print("wallpaper: %s is current (%dx%d)"
                  % (rel, info.get("width", 0), info.get("height", 0)))
    if not stale:
        print("wallpaper pack: %d file(s) current" % len(files))
    return stale


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

    if "--check" in argv and only is None:
        return check_manifest(tokens)

    produced = targets(tokens, only)
    stale = 0
    if "--check" in argv:
        for path, image, width, height in produced:
            if not path.is_file():
                print("wallpaper: %s is missing" % path.relative_to(ISO))
                stale = 1
            elif path.read_bytes() != image:
                print("wallpaper: %s is stale (run make_wallpaper.py)" % path.relative_to(ISO))
                stale = 1
            else:
                print("wallpaper: %s is current (%dx%d)"
                      % (path.relative_to(ISO), width, height))
        return stale

    for path, image, width, height in produced:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)
        print("wallpaper: wrote %s (%d bytes, %dx%d)"
              % (path.relative_to(ISO), len(image), width, height))

    # The manifest records the tokens and the bytes that produced them, so a
    # later check is ten hashes instead of ten renders.
    MANIFEST.write_text(json.dumps({
        "tokens_sha256": hashlib.sha256(TOKENS.read_bytes()).hexdigest(),
        "files": {
            str(path.relative_to(ISO)): {
                "sha256": digest(path), "width": width, "height": height,
            }
            for path, _image, width, height in produced
        },
    }, indent=2) + "\n", encoding="utf-8")
    print("wallpaper: wrote %s (%d file(s))"
          % (MANIFEST.relative_to(ISO), len(produced)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
