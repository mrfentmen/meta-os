#!/usr/bin/env python3
"""The three division tiles, in every accent, at dock size.

The dock goes from 27 to 28 tiles when Trio and Imperium become Police, Fire
and EMS. Those three tiles have to survive the same conditions as the other 25:
a 44 px dock slot, eight accent sets, and a wallpaper that recolours the whole
dock. This sheet is how that gets checked by looking instead of by trusting the
generator.

Usage: division-sheet.py [outdir]
Writes <outdir>/division-icons.png.
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ACCENTS = os.path.join(HERE, "accents")
NAMES = [("police", "Police"), ("fire", "Fire"), ("ems", "EMS")]


def font(sz, bold=False):
    for p in ("/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz, index=1 if bold else 0)
            except Exception:
                try:
                    return ImageFont.truetype(p, sz)
                except Exception:
                    pass
    return ImageFont.load_default()


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "accents")
    outdir = os.path.abspath(outdir)
    sets = sorted(d for d in os.listdir(ACCENTS)
                  if os.path.isdir(os.path.join(ACCENTS, d))
                  and os.path.exists(os.path.join(ACCENTS, d, "set.conf")))
    # blue-B first, it is the default
    sets.sort(key=lambda s: (s != "blue-B", s))

    rows = len(sets)
    cell_w, cell_h = 150, 116
    pad, head = 28, 108
    title = "Police, Fire, EMS: the three division tiles"
    # The dock is 506 px wide at 150 px per cell; the title is wider than that
    # at 26 px, so the sheet takes whichever is larger instead of clipping.
    title_w = ImageDraw.Draw(Image.new("RGB", (8, 8))).textlength(title, font=font(26, True))
    w = int(max(pad * 2 + cell_w * 3, title_w + pad * 2))
    h = head + rows * cell_h + pad
    sheet = Image.new("RGB", (w, h), (7, 11, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 24), title, font=font(26, True), fill=(232, 236, 244))
    d.text((pad, 58), "128 px and 44 px, in every accent set the dock can switch to.",
           font=font(14), fill=(140, 152, 176))

    for i, name in enumerate([n for n, _ in NAMES]):
        d.text((pad + i * cell_w, head - 26), dict(NAMES)[name], font=font(15, True),
               fill=(120, 186, 255))

    for r, setname in enumerate(sets):
        y = head + r * cell_h
        d.text((pad, y + 6), setname, font=font(13), fill=(150, 162, 186))
        for i, (name, _) in enumerate(NAMES):
            big = os.path.join(ACCENTS, setname, "128x128", "apps", name + ".png")
            small = os.path.join(ACCENTS, setname, "48x48", "apps", name + ".png")
            x = pad + i * cell_w
            if os.path.exists(big):
                ic = Image.open(big).convert("RGBA").resize((96, 96), Image.LANCZOS)
                sheet.paste(ic, (x, y + 20), ic)
            if os.path.exists(small):
                ic = Image.open(small).convert("RGBA")
                sheet.paste(ic, (x + 104, y + 20), ic)
                sheet.paste(ic.resize((32, 32), Image.LANCZOS), (x + 104, y + 72))

    p = os.path.join(outdir, "division-icons.png")
    sheet.save(p)
    print("wrote", p, os.path.getsize(p), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
