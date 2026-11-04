#!/usr/bin/env python3
"""Generate plymouth-sized ribbon frames from the settled 32-frame smooth loop.

Source (DO NOT MODIFY): ../wallpapers/studio-loop-smooth/loop-*.jpg
  32 frames, 1920x1088, played by meta-live.py image mode at 16 fps.
Output: frames/frame-0.png .. frame-31.png at 480x272 (plymouth-appropriate:
  small enough for the initramfs, large enough that the ribbon reads after
  the script scales it to screen).
Palette: untouched source pixels (meta blues on ink); no recolor, no logo add.
Also writes the D3 contact sheet next to the lane report on demand (--contact).
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "wallpapers", "studio-loop-smooth")
DST = os.path.join(HERE, "frames")
W, H = 480, 272
EXPECT = 32


def main():
    import glob
    files = sorted(glob.glob(os.path.join(SRC, "loop-*.jpg")))
    if len(files) != EXPECT:
        print(f"frames: want {EXPECT} source frames, found {len(files)} in {SRC}",
              file=sys.stderr)
        return 1
    os.makedirs(DST, exist_ok=True)
    total = 0
    for i, f in enumerate(files):
        img = Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS)
        out = os.path.join(DST, f"frame-{i}.png")
        img.save(out, optimize=True)
        total += os.path.getsize(out)
    wrote = sorted(os.listdir(DST))
    assert len(wrote) == EXPECT, f"wrote {len(wrote)} frames, want {EXPECT}"
    print(f"frames: {EXPECT} PNGs {W}x{H} in {DST} ({total} bytes total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
