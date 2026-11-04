#!/usr/bin/env python3
"""Check the generated window-button art: both formats, every state, correct.

Usage: python3 check_buttons.py <theme-dir>   (e.g. os-build/iso/payload-theme)

Prints one problem per line and exits 1 if any. Kept out of test_tokens.sh as a
real file rather than an inline heredoc, because a nested heredoc quoting a
Python heredoc is how you lose an afternoon.

Why both formats are checked: xfwm4 resolves a button to an image and draws
NOTHING when the lookup fails. An SVG-only theme on an image without the rsvg
GdkPixbuf loader therefore has no buttons at all — the bug this art exists to
fix. The PNG twins must exist and must be real.
"""
import glob
import os
import sys
import xml.dom.minidom

NAMES = ("close", "maximize", "hide")
STATES = ("active", "inactive", "prelight", "pressed", "toggled")
SIZE = 22


def main(argv):
    theme = argv[0] if argv else os.path.join("os-build", "iso", "payload-theme")
    art = os.path.join(theme, "xfwm4")
    problems = []

    for name in NAMES:
        for state in STATES:
            svg = os.path.join(art, "%s-%s.svg" % (name, state))
            png = os.path.join(art, "%s-%s.png" % (name, state))
            if not os.path.exists(svg) or os.path.getsize(svg) == 0:
                problems.append("%s-%s.svg missing" % (name, state))
            else:
                try:
                    doc = xml.dom.minidom.parse(svg)
                except Exception:
                    problems.append("%s-%s.svg is not XML" % (name, state))
                else:
                    root = doc.documentElement
                    if root.getAttribute("width") != root.getAttribute("height"):
                        problems.append("%s-%s.svg is not square" % (name, state))
                    if not root.getElementsByTagName("circle"):
                        problems.append("%s-%s.svg has no disc" % (name, state))
                    if not root.getElementsByTagName("path"):
                        problems.append("%s-%s.svg has no glyph" % (name, state))
            if not os.path.exists(png):
                problems.append("%s-%s.png missing" % (name, state))

    try:
        from PIL import Image
    except ImportError:
        problems.append("PIL not installed: cannot check the PNG twins at all")
        Image = None

    if Image is not None:
        for path in sorted(glob.glob(os.path.join(art, "*.png"))):
            name = os.path.basename(path)
            im = Image.open(path)
            if im.size != (SIZE, SIZE):
                problems.append("%s is %dx%d not %dx%d" % (name, im.size[0], im.size[1], SIZE, SIZE))
            elif im.mode != "RGBA":
                problems.append("%s is %s not RGBA" % (name, im.mode))
            elif im.getpixel((0, 0))[3] != 0:
                problems.append("%s corner is opaque (the disc is not round)" % name)
            elif im.getpixel((SIZE // 2, SIZE // 2))[3] == 0:
                problems.append("%s centre is transparent (nothing was drawn)" % name)

    # The two formats are drawn from one set of coordinates; if the SVG names a
    # glyph the PNG does not contain, the pair has drifted.
    n_svg = len(glob.glob(os.path.join(art, "*-*.svg")))
    n_png = len(glob.glob(os.path.join(art, "*-*.png")))
    if n_svg != n_png:
        problems.append("%d svgs but %d pngs" % (n_svg, n_png))
    if n_svg != len(NAMES) * len(STATES):
        problems.append("want %d buttons, have %d" % (len(NAMES) * len(STATES), n_svg))

    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
