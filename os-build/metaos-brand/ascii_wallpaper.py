#!/usr/bin/env python3
"""Render the Meta OS ASCII wallpaper.

The desktop wallpaper is drawn entirely from characters: a faint full-screen
character field, the Meta infinity mark traced in a density ramp, and the
product name in monospace. Nothing is upscaled from a screenshot, so it is
crisp at any desktop resolution.

Usage:
    python3 ascii_wallpaper.py OUT.png [--w 2560] [--h 1440] [--cell 16]
"""
import argparse
import math
import random

from PIL import Image, ImageDraw, ImageFont

# Density ramp: dark -> bright. Index chosen from the intensity field.
RAMP = " .:-=+*#%@"
# Characters used for the background field. Short on purpose: it should read
# as texture, not as readable words.
FIELD = "metaos01/\\|_-."
# Vertical gradient, top to bottom (RGB).
TOP = (9, 13, 21)
BOTTOM = (17, 24, 39)
# Mark colours, centre of the stroke to the outer falloff.
HOT = (150, 225, 255)
COOL = (28, 110, 200)
FIELD_INK = (26, 42, 66)

MONO = "/System/Library/Fonts/Menlo.ttc"


def infinity_points(steps=2400):
    """Unit lemniscate: x = sin t, y = sin t * cos t. Horizontal figure 8."""
    pts = []
    for i in range(steps):
        t = 2.0 * math.pi * i / steps
        pts.append((math.sin(t), math.sin(t) * math.cos(t)))
    return pts


def build(out, w, h, cell):
    # Monospace cell: Menlo advance is ~0.6em, so pick a font size that makes
    # the grid land near square-ish cells.
    font = ImageFont.truetype(MONO, int(cell * 1.05))
    cols = w // cell
    rows = h // int(cell * 1.55)
    cw = w / cols
    ch = h / rows

    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line(
            [(0, y), (w, y)],
            fill=(
                int(TOP[0] + (BOTTOM[0] - TOP[0]) * t),
                int(TOP[1] + (BOTTOM[1] - TOP[1]) * t),
                int(TOP[2] + (BOTTOM[2] - TOP[2]) * t),
            ),
        )

    # ---- faint character field over the whole screen -------------------
    rng = random.Random(20261103)
    for r in range(rows):
        for c in range(cols):
            d.text(
                (c * cw, r * ch),
                rng.choice(FIELD),
                font=font,
                fill=FIELD_INK,
            )

    # ---- the mark, traced in characters ---------------------------------
    # Screen-space geometry of the mark.
    mx, my = w * 0.5, h * 0.47
    ax, ay = w * 0.235, h * 0.115          # mark half-extent
    sigma = ch * 0.62                       # stroke thickness in pixels
    pts = [(mx + px * ax, my + py * ay) for px, py in infinity_points()]

    # Bucket the curve into cells once, then only test nearby cells.
    near = {}
    for px, py in pts:
        near.setdefault((int(px / cw), int(py / ch)), []).append((px, py))

    for r in range(rows):
        for c in range(cols):
            best = None
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    for px, py in near.get((c + dc, r + dr), ()):
                        dx = px - (c * cw + cw * 0.5)
                        dy = py - (r * ch + ch * 0.5)
                        dd = dx * dx + dy * dy
                        if best is None or dd < best:
                            best = dd
            if best is None:
                continue
            dd = math.sqrt(best)
            if dd > sigma * 3.2:
                continue
            i = math.exp(-(dd * dd) / (2.0 * sigma * sigma))
            ch_ = RAMP[min(len(RAMP) - 1, int(i * (len(RAMP) - 1) + 0.5))]
            if ch_ == " ":
                continue
            # Bluer at the edge of the stroke, white-hot at the centre.
            col = tuple(
                int(COOL[k] + (HOT[k] - COOL[k]) * i) for k in range(3)
            )
            d.text((c * cw, r * ch), ch_, font=font, fill=col)

    # ---- product name ---------------------------------------------------
    big = ImageFont.truetype(MONO, int(cell * 2.6))
    d.text((w * 0.055, h * 0.84), "META OS 1.0", font=big, fill=(236, 242, 250))
    small = ImageFont.truetype(MONO, int(cell * 0.95))
    d.text(
        (w * 0.055, h * 0.90),
        "metaos console . ascii desktop . kernel alive",
        font=small,
        fill=(96, 130, 170),
    )

    img.save(out)
    return img.size, (cols, rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--w", type=int, default=2560)
    ap.add_argument("--h", type=int, default=1440)
    ap.add_argument("--cell", type=int, default=16)
    a = ap.parse_args()
    size, grid = build(a.out, a.w, a.h, a.cell)
    print(f"wrote {a.out} {size[0]}x{size[1]} grid {grid[0]}x{grid[1]}")


if __name__ == "__main__":
    main()
