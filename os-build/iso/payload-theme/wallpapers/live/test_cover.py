"""Prove meta-live._cover fills the screen, without needing GTK.

fake gi.GdkPixbuf is a thin wrapper over PIL, so the crop arithmetic in
_cover() is exercised exactly as written: same scale ratio, same centred
sub-pixbuf offsets. What this does NOT prove is GTK drawing it (no display
here) — it proves the geometry, which is the part that was wrong.

The test frame is deliberate: a red ramp across x, a green ramp down y, and a
white block in the middle. Ramp symmetry is what proves the crop is CENTRED
(left edge R + right edge R must stay ≈ 255 for any cover crop), and the white
block is what proves the loop's centre survived the scale.
"""
import sys
import types

from PIL import Image

W, H = 1920, 1080


class FakePixbuf:
    def __init__(self, img):
        self.img = img

    def get_width(self):
        return self.img.width

    def get_height(self):
        return self.img.height

    def scale_simple(self, w, h, interp):
        return FakePixbuf(self.img.resize((w, h), Image.BILINEAR))

    def new_subpixbuf(self, x, y, w, h):
        return FakePixbuf(self.img.crop((x, y, x + w, y + h)))


class FakeGdkPixbuf:
    class InterpType:
        BILINEAR = 2

    class Pixbuf:
        @staticmethod
        def new_from_file(path):
            return FakePixbuf(Image.open(path))


gi = types.ModuleType("gi")
gi.repository = types.ModuleType("gi.repository")
gi.repository.GdkPixbuf = FakeGdkPixbuf
sys.modules["gi"] = gi
sys.modules["gi.repository"] = gi.repository

sys.path.insert(0, "os-build/iso/payload-theme/wallpapers/live")
import importlib

meta_live = importlib.import_module("meta-live")
_cover = meta_live._cover

frame = Image.new("RGB", (W, H))
px = frame.load()
for y in range(H):
    g = int(round(255 * y / (H - 1)))
    for x in range(W):
        px[x, y] = (int(round(255 * x / (W - 1))), g, 40)
frame.paste((255, 255, 255), (W // 2 - 200, H // 2 - 200, W // 2 + 200, H // 2 + 200))

TOL = 14  # bilinear resampling plus 8-bit rounding

cases = [
    ((W, H), "shipped: frame is the screen size"),
    ((1600, 900), "smaller, same aspect"),
    ((2560, 1600), "larger, same aspect"),
    ((1920, 1200), "taller: width binds, crop top/bottom"),
    ((1280, 1024), "4:3: crop left/right"),
    ((3840, 1080), "ultrawide"),
    ((800, 1280), "portrait"),
]

fails = 0
for (w, h), label in cases:
    out = _cover(FakePixbuf(frame), w, h).img
    problems = []
    if (out.width, out.height) != (w, h):
        problems.append("size %dx%d" % (out.width, out.height))
    left = out.getpixel((0, h // 2))[0]
    right = out.getpixel((w - 1, h // 2))[0]
    top = out.getpixel((w // 2, 0))[1]
    bottom = out.getpixel((w // 2, h - 1))[1]
    if abs((left + right) - 255) > TOL:
        problems.append("x crop off-centre (R %d+%d)" % (left, right))
    if abs((top + bottom) - 255) > TOL:
        problems.append("y crop off-centre (G %d+%d)" % (top, bottom))
    if abs(left - right) > 255:
        problems.append("x edges swapped")
    if out.getpixel((w // 2, h // 2)) != (255, 255, 255):
        problems.append("centre marker lost")
    status = "PASS" if not problems else "FAIL"
    if problems:
        fails += 1
    print("%s %-38s %4dx%-4d  R %3d/%3d  G %3d/%3d  %s"
          % (status, label, w, h, left, right, top, bottom, "; ".join(problems)))

same = FakePixbuf(frame)
if _cover(same, W, H) is same:
    print("PASS identical size returns the original pixbuf (zero cost)")
else:
    print("FAIL identical size re-scaled; the shipped path is not free")
    fails += 1

z = _cover(FakePixbuf(frame), 0, 0)
if (z.get_width(), z.get_height()) == (W, H):
    print("PASS zero screen keeps the frame instead of crashing")
else:
    print("FAIL zero screen produced a %dx%d pixbuf" % (z.get_width(), z.get_height()))
    fails += 1

print("covered: %d case(s) failed" % fails)
sys.exit(1 if fails else 0)
