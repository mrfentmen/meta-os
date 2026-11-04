#!/usr/bin/env python3
"""Build the GRUB theme images from settled theme assets. No new art.

Inputs (read-only): ../splash/background.png (1920x1080), ../splash/meta-m.png
Outputs: background.png (verbatim copy, same pixels), mark.png (M mark
scaled to 256 px for the theme's branding icon).
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_BG = os.path.join(HERE, "..", "splash", "background.png")
SRC_MARK = os.path.join(HERE, "..", "splash", "meta-m.png")


def main():
    for p in (SRC_BG, SRC_MARK):
        if not os.path.exists(p):
            print(f"grub: missing source {p}", file=sys.stderr)
            return 1
    bg = Image.open(SRC_BG)
    assert bg.size == (1920, 1080), bg.size
    bg.save(os.path.join(HERE, "background.png"))
    mark = Image.open(SRC_MARK).convert("RGBA")
    mark.resize((256, 256), Image.LANCZOS).save(os.path.join(HERE, "mark.png"))
    print("grub: background.png 1920x1080, mark.png 256x256")
    return 0


if __name__ == "__main__":
    sys.exit(main())
