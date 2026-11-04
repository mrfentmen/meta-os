"""Prove the wallpaper always covers the screen, without needing GTK.

meta-live paints its frame into a DrawingArea's own allocation, using
cover_metrics() for the geometry (scale + centred offset). That function is the
whole of the "wallpaper is small and stuck in the corner" fix, and it is a pure
function of four numbers — so it is checked here for every aspect ratio the
screen can take, with no display, no pixbuf, and no GTK.

What this does NOT prove is GTK drawing it (no display here); it proves the
numbers, which is the part that was wrong, plus the invariant the bug broke:
after the transform, the frame's painted rectangle must cover the whole screen.

The frame is the shipped size, 1920x1080. Every case asserts:
  * both painted edges reach or pass the screen edge (no gap, no letterbox);
  * the overflow is split evenly (dx == width - dx - pw*scale), i.e. the loop
    stays centred rather than being pushed to one corner;
  * a 1:1 screen returns scale 1.0 and zero offset — the shipped path costs
    nothing, and the pixel grid stays exact;
  * degenerate inputs (zero screen, zero frame) do not produce NaN or a crash.
"""
import sys

sys.path.insert(0, "os-build/iso/payload-theme/wallpapers/live")
import importlib

meta_live = importlib.import_module("meta-live")
cover_metrics = meta_live.cover_metrics

FW, FH = 1920, 1080
EPS = 1e-6

cases = [
    ((FW, FH), "shipped: frame is the screen size"),
    ((1600, 900), "smaller, same aspect"),
    ((2560, 1600), "larger, same aspect"),
    ((1920, 1200), "taller: width binds, crop top/bottom"),
    ((1280, 1024), "4:3: crop left/right"),
    ((3840, 1080), "ultrawide"),
    ((800, 1280), "portrait"),
    ((640, 360), "the boot window before the mode switch"),
    ((1764, 994), "a dragged cocoa window"),
    ((1, 1), "first allocation, before the window is placed"),
]

fails = 0


def check(cond, label, detail=""):
    global fails
    if not cond:
        fails += 1
        print("FAIL %-40s %s" % (label, detail))
    return cond


for (w, h), label in cases:
    scale, dx, dy = cover_metrics(FW, FH, w, h)
    problems = []

    if scale <= 0:
        problems.append("scale %r" % (scale,))
    painted_w = FW * scale
    painted_h = FH * scale
    # Cover: never a gap on any edge.
    if painted_w + EPS < w:
        problems.append("width %.2f < %d" % (painted_w, w))
    if painted_h + EPS < h:
        problems.append("height %.2f < %d" % (painted_h, h))
    # Centred: equal overflow on both sides of each axis.
    if abs(dx - (w - painted_w - dx)) > EPS:
        problems.append("x off-centre (dx %.2f)" % dx)
    if abs(dy - (h - painted_h - dy)) > EPS:
        problems.append("y off-centre (dy %.2f)" % dy)
    # No overflow kept off-screen on the near side (dx <= 0, dy <= 0).
    if dx > EPS or dy > EPS:
        problems.append("frame starts inside the screen (dx %.2f dy %.2f)" % (dx, dy))

    status = "PASS" if not problems else "FAIL"
    print("%s %-40s %4dx%-4d  scale %.4f  dx %8.2f  dy %8.2f  %s"
          % (status, label, w, h, scale, dx, dy, "; ".join(problems)))
    if problems:
        fails += 1

scale, dx, dy = cover_metrics(FW, FH, FW, FH)
if not check(scale == 1.0 and dx == 0.0 and dy == 0.0,
             "identical size is a 1:1 blit",
             "scale %r dx %r dy %r" % (scale, dx, dy)):
    pass
else:
    print("PASS identical size is a 1:1 blit (zero resample, exact pixels)")

# Degenerate inputs: the first draw happens before GTK has allocated a size.
for (pw, ph, w, h) in ((0, 0, 1920, 1080), (FW, FH, 0, 0), (-1, 20, 800, 600)):
    scale, dx, dy = cover_metrics(pw, ph, w, h)
    if check(scale == 1.0 and dx == 0.0 and dy == 0.0,
             "degenerate input is inert", "%d %d %d %d -> %r" % (pw, ph, w, h, scale)):
        print("PASS degenerate input is inert: frame %sx%s screen %sx%s"
              % (pw, ph, w, h))

print("covered: %d case(s) failed" % fails)
sys.exit(1 if fails else 0)
