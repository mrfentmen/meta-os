#!/usr/bin/env python3
"""MetaOS boot/installer brand assets — generated, original, reproducible.

Every pixel here is drawn by this file. No Apple artwork, fonts, icons or
layouts are used or traced: the mark is a ring plus a dot, the wordmark is
built from 5x7 block glyphs drawn as rectangles, so there is no font file
and no font licence in the shipped theme.

Outputs
  plymouth/metaos/logo.png            512x512  transparent ring mark
  plymouth/metaos/wordmark.png        480x120  transparent block "METAOS"
  plymouth/metaos/dot.png              24x24   copied, see PROVENANCE below
  calamares/branding/metaos/productLogo.png     256x256
  calamares/branding/metaos/productIcon.png     128x128
  calamares/branding/metaos/productWelcome.png  640x400
  docs/theme-mock.png                1280x720   MOCK render, not a boot capture
  assets/MANIFEST.json               sha256 + size + provenance per file

PROVENANCE: dot.png is copied verbatim from
os-build/face/plymouth/metaos/ring-dot.png (OC1's lane, already on main)
so the splash spinner and the face spinner share one dot instead of
forking the brand. Its sha256 is recorded in MANIFEST.json.

Run: python3 os-build/iso/assets/make_assets.py
Needs: Pillow (only build-time; nothing Python ships in the ISO).
"""

import hashlib
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ISO, "..", ".."))

PLYMOUTH = os.path.join(ISO, "plymouth", "metaos")
BRANDING = os.path.join(ISO, "calamares", "branding", "metaos")
DOCS = os.path.join(ISO, "docs")

INK = (11, 18, 32)
INK_DEEP = (5, 9, 18)
MID = (27, 43, 69)
BLUE = (63, 169, 245)
BLUE_DIM = (33, 94, 138)
WHITE = (255, 255, 255)

GLYPHS = {
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
}


def ensure_dirs():
    for d in (PLYMOUTH, BRANDING, DOCS):
        os.makedirs(d, exist_ok=True)


def ring_mark(size, stroke, dot_radius, with_inner=True):
    """Ring + dot on an upper-right diagonal. Drawn at 4x then downsampled."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = stroke * 4
    d.ellipse((pad, pad, s - pad, s - pad), outline=BLUE, width=stroke * 4)
    if with_inner:
        inner_pad = pad + stroke * 6
        d.ellipse(
            (inner_pad, inner_pad, s - inner_pad, s - inner_pad),
            outline=BLUE_DIM,
            width=max(1, stroke),
        )
    cx = cy = s // 2
    off = (s // 2 - pad) * 0.7071
    dx, dy = cx + off, cy - off
    r = dot_radius * 4
    d.ellipse((dx - r, dy - r, dx + r, dy + r), fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def glyph_block(text, cell=14, gap=10, colour=WHITE):
    cols = len(text) * 5 + (len(text) - 1)
    w = cols * cell + gap * (len(text) - 1) * 0
    width = len(text) * 5 * cell + (len(text) - 1) * gap
    height = 7 * cell
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for ch in text:
        rows = GLYPHS[ch]
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    d.rectangle(
                        (x + rx * cell, ry * cell, x + rx * cell + cell - 1, ry * cell + cell - 1),
                        fill=colour,
                    )
        x += 5 * cell + gap
    return img


def gradient(size, top, bottom):
    img = Image.new("RGB", size, top)
    d = ImageDraw.Draw(img)
    h = size[1]
    for y in range(h):
        t = y / max(1, h - 1)
        d.line(
            (0, y, size[0], y),
            fill=(
                round(top[0] + (bottom[0] - top[0]) * t),
                round(top[1] + (bottom[1] - top[1]) * t),
                round(top[2] + (bottom[2] - top[2]) * t),
            ),
        )
    return img


def write_logo():
    ring_mark(512, stroke=16, dot_radius=30).save(os.path.join(PLYMOUTH, "logo.png"))


def write_wordmark():
    glyph = glyph_block("METAOS", cell=14, gap=10)
    canvas = Image.new("RGBA", (glyph.width + 40, glyph.height + 40), (0, 0, 0, 0))
    canvas.alpha_composite(glyph, (20, 20))
    canvas.save(os.path.join(PLYMOUTH, "wordmark.png"))


def write_dot():
    src = os.path.join(REPO, "os-build", "face", "plymouth", "metaos", "ring-dot.png")
    dst = os.path.join(PLYMOUTH, "dot.png")
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        return "copied from os-build/face/plymouth/metaos/ring-dot.png (OC1 lane, on main)"
    # Fallback only if the face lane's dot disappears: draw the same shape.
    img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((6, 6, 18, 18), fill=WHITE)
    img.save(dst)
    return "generated fallback (face dot missing)"


def write_branding_images():
    logo = ring_mark(256, stroke=9, dot_radius=15)
    logo.save(os.path.join(BRANDING, "productLogo.png"))

    icon = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    d.rounded_rectangle((0, 0, 127, 127), radius=28, fill=INK)
    mark = ring_mark(88, stroke=5, dot_radius=7)
    icon.alpha_composite(mark, (20, 20))
    icon.save(os.path.join(BRANDING, "productIcon.png"))

    welcome = gradient((640, 400), INK, INK_DEEP).convert("RGBA")
    big = ring_mark(180, stroke=7, dot_radius=12)
    welcome.alpha_composite(big, (320 - 90, 78))
    word = glyph_block("METAOS", cell=9, gap=8)
    welcome.alpha_composite(word, (320 - word.width // 2, 282))
    dd = ImageDraw.Draw(welcome)
    # Underline sits below the block wordmark (which ends at y=345); at 340
    # it cut through the glyphs -- caught in the first visual check.
    dd.rectangle((320 - 120, 356, 320 + 120, 358), fill=BLUE)
    welcome.save(os.path.join(BRANDING, "productWelcome.png"))


def write_mock():
    """MOCK: same assets on the theme background. NOT a boot capture."""
    canvas = gradient((1280, 720), INK, INK_DEEP).convert("RGBA")
    logo = ring_mark(260, stroke=9, dot_radius=15)
    cx, cy = 640, 300
    canvas.alpha_composite(logo, (cx - 130, cy - 130))
    word = glyph_block("METAOS", cell=10, gap=9)
    canvas.alpha_composite(word, (cx - word.width // 2, cy + 150))
    d = ImageDraw.Draw(canvas)
    # 12-dot progress ring, 4 lit: the layout metaos.script paints at runtime.
    import math

    for i in range(12):
        a = math.radians(-90 + i * 30)
        x = cx + math.cos(a) * 190
        y = cy + math.sin(a) * 190
        lit = i < 4
        r = 7 if lit else 4
        d.ellipse((x - r, y - r, x + r, y + r), fill=BLUE if lit else MID)
    canvas.convert("RGB").save(os.path.join(DOCS, "theme-mock.png"))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(dot_origin):
    rows = []
    targets = [
        (os.path.join(PLYMOUTH, "logo.png"), "plymouth splash mark"),
        (os.path.join(PLYMOUTH, "wordmark.png"), "plymouth wordmark, block glyphs"),
        (os.path.join(PLYMOUTH, "dot.png"), dot_origin),
        (os.path.join(BRANDING, "productLogo.png"), "calamares branding logo"),
        (os.path.join(BRANDING, "productIcon.png"), "calamares branding icon"),
        (os.path.join(BRANDING, "productWelcome.png"), "calamares welcome page"),
        (os.path.join(DOCS, "theme-mock.png"), "MOCK render, not a boot capture"),
    ]
    for path, note in targets:
        with Image.open(path) as im:
            w, h = im.size
            mode = im.mode
        rows.append(
            {
                "path": os.path.relpath(path, ISO),
                "width": w,
                "height": h,
                "mode": mode,
                "sha256": sha256(path),
                "source": note,
            }
        )
    data = {
        "generator": "os-build/iso/assets/make_assets.py",
        "licence": "original work for MetaOS; no third-party artwork, fonts or icons",
        "font_note": "wordmark is 5x7 block glyphs drawn as rectangles; no font file is shipped",
        "assets": rows,
    }
    with open(os.path.join(HERE, "MANIFEST.json"), "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def main():
    try:
        from PIL import __version__ as pillow_version
    except ImportError:
        sys.exit("make_assets: Pillow is required (pip install pillow)")
    ensure_dirs()
    write_logo()
    write_wordmark()
    origin = write_dot()
    write_branding_images()
    write_mock()
    manifest(origin)
    print(f"make_assets: ok (Pillow {pillow_version}) -> {os.path.relpath(ISO, REPO)}")


if __name__ == "__main__":
    main()
