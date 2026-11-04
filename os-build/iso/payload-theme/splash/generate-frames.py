#!/usr/bin/env python3
"""Generate the plymouth boot frames from the studio's 240-frame loop.

Why 240: the old splash shipped 32 frames, advanced one every 4 refresh ticks
at 60 Hz — 15 fps, 11.25 degrees per step, one turn every 2.1 s. That is the
"slow, laggy spinner" report, and no amount of scaling makes 32 frames read as
motion. This writes one frame per source frame and the script advances one per
refresh, so the boot art turns at 60 fps.

Source (DO NOT MODIFY): ../wallpapers/studio-loop/loop-*.jpg
  240 frames, 1920x1080, produced by loop_from_studio.mjs +
  loop_frames_to_wallpaper.py from the logo studio itself. Same set the
  desktop wallpaper plays, so boot and desktop show the same object.
Output: frames/frame-000.png .. frame-239.png at 480x272.

480x272 is deliberate: plymouth scales to the screen, and the initramfs holds
every frame. A palette-quantised PNG at that size is ~9 KiB, so 240 frames cost
about 2 MB instead of the 4.6 MB thirty-two true-colour frames used to.

Also rewrites, in this directory:
  frames.inc      the `ribbon.f[i] = ...` block, inlined into metaos.script
  metaos.script   between the FRAMES-BEGIN / FRAMES-END markers, plus ribbon.n

    python3 generate-frames.py            # regenerate frames + script block
    python3 generate-frames.py --contact  # also write the contact sheet
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "wallpapers", "studio-loop")
DST = os.path.join(HERE, "frames")
SCRIPT = os.path.join(HERE, "metaos.script")
INC = os.path.join(HERE, "frames.inc")
W, H = 480, 272
MIN_FRAMES = 120  # a floor, not an exact count: fewer than this is choppy again
PALETTE = 96      # ink + two blues + antialias; 96 is comfortably enough


def frame_names(n):
    return ["frames/frame-%03d.png" % i for i in range(n)]


def write_inc(n):
    lines = ["ribbon.f = NULL;"]
    for i, name in enumerate(frame_names(n)):
        lines.append('ribbon.f[%d] = Image ("%s");' % (i, name))
        lines.append("ribbon.f[%d] = ribbon.f[%d].Scale (ribbon.w, ribbon.h);"
                     % (i, i))
    with open(INC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return "\n".join(lines)


def patch_script(n):
    with open(SCRIPT, "r", encoding="utf-8") as fh:
        text = fh.read()
    begin = "// FRAMES-BEGIN"
    end = "// FRAMES-END"
    if begin not in text or end not in text:
        raise SystemExit("generate-frames: metaos.script has no %s/%s markers"
                         % (begin, end))
    head, rest = text.split(begin, 1)
    _old, tail = rest.split(end, 1)
    block = "\n%s\n%s\n%s\n" % (begin, write_inc(n), end)
    text = head + block + tail
    # ribbon.n is read by on_refresh; keep it in step with the file count.
    import re
    text = re.sub(r"ribbon\.n = \d+;", "ribbon.n = %d;" % n, text, count=1)
    with open(SCRIPT, "w", encoding="utf-8") as fh:
        fh.write(text)
    return n


def main(argv):
    from PIL import Image

    files = sorted(glob.glob(os.path.join(SRC, "loop-*.jpg")))
    if len(files) < MIN_FRAMES:
        print("frames: need at least %d source frames in %s, found %d"
              % (MIN_FRAMES, SRC, len(files)), file=sys.stderr)
        return 1
    os.makedirs(DST, exist_ok=True)
    for old in glob.glob(os.path.join(DST, "frame-*.png")):
        os.remove(old)
    total = 0
    for i, f in enumerate(files):
        img = Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS)
        # Palette, not truecolour: these frames live in the initramfs.
        img = img.quantize(colors=PALETTE, method=Image.MEDIANCUT)
        out = os.path.join(DST, "frame-%03d.png" % i)
        img.save(out, optimize=True)
        total += os.path.getsize(out)
    wrote = sorted(glob.glob(os.path.join(DST, "frame-*.png")))
    if len(wrote) != len(files):
        print("frames: wrote %d, expected %d" % (len(wrote), len(files)),
              file=sys.stderr)
        return 1
    patch_script(len(wrote))
    print("frames: %d PNGs %dx%d in %s (%.1f MiB total, %.1f KiB each)"
          % (len(wrote), W, H, DST, total / 1048576.0, total / 1024.0 / len(wrote)))

    if "--contact" in argv:
        cols, rows = 12, 4
        sheet = Image.new("RGB", (cols * 160, rows * 90), (7, 11, 22))
        for n, p in enumerate(wrote[:cols * rows]):
            im = Image.open(p).convert("RGB").resize((160, 90))
            sheet.paste(im, ((n % cols) * 160, (n // cols) * 90))
        cs = os.path.join(HERE, "frames-contact.png")
        sheet.save(cs)
        print("frames: contact sheet %s" % cs)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
