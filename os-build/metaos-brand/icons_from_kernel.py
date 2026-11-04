#!/usr/bin/env python3
"""Turn kernel/src/icons.rs ASCII bitmap glyphs into PNG icons.

The kernel draws its dock from 48x48 character grids (icons.rs). The
XFCE desktop cannot read those, so this renders the same grids to PNG
using the kernel's own palette from framebuffer.rs::icon_color, and
writes one file per icon into an output directory.

Usage: icons_from_kernel.py <icons.rs> <out-dir> [size]
"""
import os
import re
import sys

from PIL import Image

# kernel/src/framebuffer.rs::icon_color, kept in step by hand.
PALETTE = {
    "K": (0, 0, 0),
    "W": (255, 255, 255),
    "B": (24, 119, 242),
    "b": (0, 0, 170),
    "L": (85, 85, 255),
    "G": (140, 140, 140),
    "D": (70, 70, 70),
    "R": (205, 45, 45),
    "N": (35, 175, 70),
    "Y": (245, 197, 66),
    "O": (232, 140, 35),
    "C": (60, 190, 220),
}


def parse(src):
    text = open(src, encoding="utf-8").read()
    icons = []
    for m in re.finditer(r'label:\s*"([^"]+)",\s*rows:\s*\[(.*?)\]', text, re.S):
        label, block = m.group(1), m.group(2)
        rows = re.findall(r'"([^"]*)"', block)
        if len(rows) == 48:
            icons.append((label, rows))
    return icons


def render(rows, size):
    grid = 48
    im = Image.new("RGBA", (grid, grid), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row[:grid]):
            col = PALETTE.get(ch)
            if col:
                px[x, y] = (col[0], col[1], col[2], 255)
    return im.resize((size, size), Image.NEAREST)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "kernel/src/icons.rs"
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 128

    icons = parse(src)
    if not icons:
        print("no icons parsed — the rows must be 48 strings each")
        return 1
    os.makedirs(out, exist_ok=True)
    for label, rows in icons:
        name = label.lower()
        path = os.path.join(out, name + ".png")
        render(rows, size).save(path)
        filled = sum(1 for r in rows for c in r if c in PALETTE)
        print(f"{name:12s} {filled:4d} px  -> {path}")
    print(f"{len(icons)} icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
