#!/usr/bin/env python3
"""MetaOS wallpaper generator — procedural originals only.
Colors default to the ASCII-studio palette; override via env.
Writes 3840x2160 PNGs (downscalable for greeter/desktop)."""
import os
from PIL import Image, ImageDraw
import math

W, H = 3840, 2160
BLUE = os.environ.get("META_BLUE", "#1877F2")
BLACK = os.environ.get("META_BLACK", "#070B16")
WHITE = os.environ.get("META_WHITE", "#EDF5FF")

def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def mix(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def vertical(path, top, bottom):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        c = mix(hx(top), hx(bottom), y / H)
        for x in range(0, W, 4):
            px[x, y] = c
    img.save(path)

def diagonal_rays(path, base, ray, n=24):
    img = Image.new("RGB", (W, H), hx(base))
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W * 0.72, H * 0.42
    r = math.hypot(W, H)
    rc = hx(ray)
    for i in range(n):
        a0 = (i / n) * math.pi
        shade = 26 + int(30 * (i % 2))
        d.pieslice([cx-r, cy-r, cx+r, cy+r], math.degrees(a0)*2, math.degrees(a0)*2+180/n, fill=rc+(shade,))
    img.save(path)

vertical("metaos-theme/wallpapers/meta-dusk.png", BLACK, "#0d2247")
diagonal_rays("metaos-theme/wallpapers/meta-rays.png", BLACK, BLUE)
vertical("metaos-theme/wallpapers/meta-dawn.png", "#0d2247", BLUE)
print("wrote 3 wallpapers")
