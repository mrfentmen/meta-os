#!/usr/bin/env python3
"""Composite the studio's captured frames into the Meta OS wallpaper loop.

Input : the PNGs written by loop_from_studio.mjs (studio canvas, transparent
        background, 2176x1236 at 2x device scale).
Output: loop-NN.jpg at 1920x1080 — the frame set meta-live.py plays as the
        desktop wallpaper — plus a wrap-around check.

Why a compositor at all: the studio draws glyphs on transparency at its own
canvas size; the wallpaper needs the ink field behind them at the screen size,
and a soft bloom of the same glyphs so the art reads at a distance instead of
looking like small text. Nothing here invents pixels: every glyph comes from
the studio's own render.

Usage: loop_frames_to_wallpaper.py [src-dir] [out-dir] [--frames N] [--fps 30]
"""
import glob
import os
import sys

from PIL import Image, ImageFilter

SRC = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/studio-frames"
OUT = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "/tmp/loop-wall"
W, H = 1920, 1080
INK = (7, 11, 22)
# The ribbon fills ~94% of the width and never touches the panel or the dock.
FILL = 0.94
BLOOM_RADIUS = 26
BLOOM_ALPHA = 0.34


def compose(frame: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (W, H), INK)
    w, h = frame.size
    scale = min(W * FILL / w, H * 0.86 / h)
    art = frame.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    x = (W - art.width) // 2
    y = (H - art.height) // 2
    # Bloom first, so the sharp glyphs sit on top of their own glow.
    if BLOOM_ALPHA > 0:
        glow = art.filter(ImageFilter.GaussianBlur(BLOOM_RADIUS))
        alpha = glow.getchannel("A").point(lambda v: int(v * BLOOM_ALPHA))
        glow.putalpha(alpha)
        canvas.paste(glow, (x, y), glow)
    canvas.paste(art, (x, y), art)
    return canvas


def main() -> int:
    files = sorted(glob.glob(os.path.join(SRC, "frame-*.png")))
    if len(files) < 8:
        print(f"composite: need at least 8 frames in {SRC}, found {len(files)}", file=sys.stderr)
        return 1
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, "loop-*.jpg")):
        os.remove(old)
    total = 0
    for i, f in enumerate(files):
        out = os.path.join(OUT, f"loop-{i:03d}.jpg")
        compose(Image.open(f).convert("RGBA")).save(out, quality=90, subsampling=1)
        total += os.path.getsize(out)
    print(f"composite: {len(files)} frames {W}x{H} -> {OUT} ({total // 1024} KiB)")

    # Wrap check: the step from the last frame back to the first must look like
    # any other step. A seam shows up as a much larger mean difference.
    first = Image.open(os.path.join(OUT, "loop-000.jpg")).convert("L").resize((160, 90))
    last = Image.open(os.path.join(OUT, f"loop-{len(files) - 1:03d}.jpg")).convert("L").resize((160, 90))
    second = Image.open(os.path.join(OUT, "loop-001.jpg")).convert("L").resize((160, 90))

    def mean_abs(a, b):
        pa, pb = a.tobytes(), b.tobytes()
        return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)

    seam = mean_abs(last, first)
    normal = mean_abs(first, second)
    print(f"wrap: last->first {seam:.2f} vs first->second {normal:.2f} (per-pixel mean abs)")
    if normal and seam > normal * 3:
        print("wrap: SEAM — the loop will visibly jump", file=sys.stderr)
        return 1
    print("wrap: OK — no jump at the loop point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
