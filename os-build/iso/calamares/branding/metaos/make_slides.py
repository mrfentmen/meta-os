#!/usr/bin/env python3
"""MetaOS 1.0 Calamares install slideshow — generated, original, reproducible.

Three ambient slides shown while Calamares writes to disk. Same ground
rules as os-build/iso/assets/make_assets.py: every pixel is drawn by this
file, no font files, no third-party artwork. The METAOS wordmark reuses the
5x7 block-glyph technique (rectangles only); the ring mark is the same
ring-plus-dot idiom.

Palette is the installer spec: blue #1877F2, white #EDF5FF, black #070B16.

Outputs (referenced by branding.desc `slideshow:`, paths relative to the
branding component dir /etc/calamares/branding/metaos/):
  slideshow/slide-01.png   800x450  ring + wordmark, progress bar 1/3
  slideshow/slide-02.png   800x450  ring + wordmark, progress bar 2/3
  slideshow/slide-03.png   800x450  ring + wordmark, progress bar full

Run: python3 os-build/iso/calamares/branding/metaos/make_slides.py
Needs: Pillow (build-time only; nothing Python ships in the ISO).
"""

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "slideshow")

BLUE = (24, 119, 242)  # #1877F2
WHITE = (237, 245, 255)  # #EDF5FF
BLACK = (7, 11, 22)  # #070B16

GLYPHS = {
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
}


def ring_mark(size, stroke, dot_radius, colour=BLUE, dot=WHITE):
    """Ring + dot on an upper-right diagonal. Drawn at 4x then downsampled."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = stroke * 4
    d.ellipse((pad, pad, s - pad, s - pad), outline=colour, width=stroke * 4)
    cx = cy = s // 2
    off = (s // 2 - pad) * 0.7071
    dx, dy = cx + off, cy - off
    r = dot_radius * 4
    d.ellipse((dx - r, dy - r, dx + r, dy + r), fill=dot)
    return img.resize((size, size), Image.LANCZOS)


def glyph_block(text, cell=10, gap=8, colour=WHITE):
    width = len(text) * 5 * cell + (len(text) - 1) * gap
    height = 7 * cell
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for ch in text:
        for ry, row in enumerate(GLYPHS[ch]):
            for rx, bit in enumerate(row):
                if bit == "1":
                    d.rectangle(
                        (x + rx * cell, ry * cell,
                         x + rx * cell + cell - 1, ry * cell + cell - 1),
                        fill=colour,
                    )
        x += 5 * cell + gap
    return img


def slide(fraction, index):
    w, h = 800, 450
    img = Image.new("RGB", (w, h), BLACK)
    d = ImageDraw.Draw(img)
    ring = ring_mark(150, stroke=6, dot_radius=10)
    img.paste(ring, (w // 2 - 75, 62), ring)
    word = glyph_block("METAOS")
    img.paste(word, (w // 2 - word.width // 2, 248), word)
    # Progress bar: 320px track, filled to `fraction`.
    bx0, bx1, by = w // 2 - 160, w // 2 + 160, 348
    d.rounded_rectangle((bx0, by, bx1, by + 14), radius=7, outline=BLUE, width=2)
    fill = int((bx1 - bx0) * fraction)
    if fill > 8:
        track = Image.new("RGBA", (bx1 - bx0 - 8, 6), (0, 0, 0, 0))
        ImageDraw.Draw(track).rounded_rectangle(
            (0, 0, fill - 8, 6), radius=3, fill=BLUE
        )
        img.paste(track, (bx0 + 4, by + 4), track)
    # Step dots: index of the lit dot matches the slide number.
    for i in range(3):
        cx = w // 2 - 24 + i * 24
        cy = 392
        r = 6 if i == index else 4
        d.ellipse((cx - r, cy - r, cx + r, cy + r),
                  fill=BLUE if i <= index else WHITE)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, frac in enumerate((1 / 3, 2 / 3, 1.0)):
        path = os.path.join(OUT, "slide-%02d.png" % (i + 1))
        slide(frac, i).save(path)
        print("wrote %s" % path)


if __name__ == "__main__":
    main()
