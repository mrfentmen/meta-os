#!/usr/bin/env python3
"""Contact sheet builder (NC-174): N frames in, one labeled grid out.
usage: python3 sheet.py <out.png> <frame1> [frame2 ...] [--cols 4]
File name under each frame, label bar included in the tile.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

try:
    FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
except Exception:  # noqa: BLE001 - headless fallback
    FONT = ImageFont.load_default()


def main(argv):
    cols = 4
    if "--cols" in argv:
        cols = int(argv[argv.index("--cols") + 1])
        argv = [a for a in argv if a != "--cols" and a != str(cols)]
    out, files = argv[0], argv[1:]
    thumbs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im.thumbnail((320, 240))
        thumbs.append((os.path.basename(f), im))
    tw, th = 320, 240 + 22
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (6, 9, 15))
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im, (x + (tw - im.width) // 2, y))
        d.text((x + 6, y + 246), name[:40], fill=(215, 229, 242), font=FONT)
    sheet.save(out)
    print("sheet %s: %d frames in %dx%d" % (out, len(thumbs), cols, rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
