#!/usr/bin/env python3
"""MetaOS plymouth splash asset generator - procedural originals only.

Reuses ../wallpapers/meta-rays.png (downscaled to 1920x1080) as the splash
background, and draws two original assets from the frozen studio palette
(blue #1877F2, white #EDF5FF, black #070B16):
  background.png  1920x1080 splash backdrop (wallpaper pixels, LANCZOS downscale)
  meta-m.png      512x512 transparent geometric "M" mark (white stems + blue chevron)
  progress.png    560x28 Meta-blue progress bar (matches gtk.css meta_blue_light edge)

No external art: every pixel is emitted by this file (PIL only).
Fallback: if the wallpaper is missing, render the same ink vertical gradient
recipe used by wallpapers/gen.py so the theme dir stays complete.
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
WALLPAPER = os.path.join(HERE, "..", "wallpapers", "meta-rays.png")

BLUE = "#1877F2"
BLUE_LIGHT = "#78BAFF"
INK = "#070B16"
PAPER = "#EDF5FF"


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_background():
    try:
        img = Image.open(WALLPAPER).convert("RGB")
        return img.resize((1920, 1080), Image.LANCZOS)
    except FileNotFoundError:
        print("wallpaper not found, rendering fallback gradient", file=sys.stderr)
        top, bottom = hx(INK), hx("#0d2247")
        img = Image.new("RGB", (1920, 1080))
        px = img.load()
        for y in range(1080):
            t = y / 1080
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            for x in range(0, 1920, 4):
                px[x, y] = c
        return img


def draw_mark(size=512):
    """Original geometric M: white outer stems, Meta-blue inner chevron."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = hx(PAPER) + (255,)
    blue = hx(BLUE) + (255,)
    u = size / 512.0
    left = (int(104 * u), int(96 * u), int(168 * u), int(416 * u))
    right = (int(344 * u), int(96 * u), int(408 * u), int(416 * u))
    d.rectangle(left, fill=white)
    d.rectangle(right, fill=white)
    chevron = [
        (168 * u, 96 * u), (256 * u, 296 * u), (344 * u, 96 * u),
        (344 * u, 168 * u), (256 * u, 368 * u), (168 * u, 168 * u),
    ]
    d.polygon(chevron, fill=blue)
    return img


def draw_progress(w=560, h=28):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=hx(BLUE) + (255,))
    d.line([h // 2, 2, w - h // 2, 2], fill=hx(BLUE_LIGHT) + (255,), width=2)
    return img


def main():
    bg = load_background()
    bg.save(os.path.join(HERE, "background.png"))
    mark = draw_mark()
    mark.save(os.path.join(HERE, "meta-m.png"))
    bar = draw_progress()
    bar.save(os.path.join(HERE, "progress.png"))
    print("wrote background.png %s, meta-m.png %s, progress.png %s"
          % (bg.size, mark.size, bar.size))


if __name__ == "__main__":
    main()
