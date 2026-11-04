#!/usr/bin/env python3
"""Every dock app gets a glyph — 27 of them, in the three languages.

style-candidates.py proved the language on six apps. This file draws the other
twenty-one and renders the whole dock three times, once per language, so the
choice is made against the real thing instead of a sample.

Glyphs are described in a 0..1 box and mapped to the same canvas and stroke
weight as style-candidates.py, which is imported rather than copied — one
geometry, one place to change it.

Usage: app-icons.py [outdir]
Writes <outdir>/dock-A|B|C.png strips and <outdir>/app-icons-A|B|C/<name>-256.png
"""
import importlib.util
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("styles", os.path.join(HERE, "style-candidates.py"))

C = S.C
W = S._stroke()

B0, B1 = 0.155, 0.845          # glyph box inside the icon


def u(x):
    return int((B0 + x * (B1 - B0)) * C)


def v(y):
    return int((B0 + y * (B1 - B0)) * C)


def r(z, base=None):
    """A length in glyph-box units to pixels."""
    return int(z * (B1 - B0) * C)


class Pen:
    """Monoline pen on an L mask, 0..1 coordinates inside a configurable box.

    App icons use the plate's inner box (0.155..0.845). Settings symbols use the
    full 24 px grid (0.06..0.94) with a lighter stroke, so both sets come out of
    one geometry rather than two that drift.
    """

    def __init__(self, box=None, weight=1.0):
        self.b0, self.b1 = box or (B0, B1)
        self.weight = weight
        self.img = Image.new("L", (C, C), 0)
        self.d = ImageDraw.Draw(self.img)

    def _u(self, x):
        return int((self.b0 + x * (self.b1 - self.b0)) * C)

    def _r(self, z):
        return int(z * (self.b1 - self.b0) * C)

    def _w(self, w):
        return max(1, int(W * w * self.weight))

    def line(self, pts, w=1.0):
        self.d.line([(self._u(x), self._u(y)) for x, y in pts], fill=255,
                    width=self._w(w), joint="curve")

    def poly(self, pts, close=True, w=1.0):
        p = [(self._u(x), self._u(y)) for x, y in pts]
        if close:
            self.d.polygon(p, outline=255, width=self._w(w))
        else:
            self.d.line(p, fill=255, width=self._w(w), joint="curve")

    def fill(self, pts):
        self.d.polygon([(self._u(x), self._u(y)) for x, y in pts], fill=255)

    def circ(self, cx, cy, rad, fill=False, w=1.0):
        box = (self._u(cx) - self._r(rad), self._u(cy) - self._r(rad),
               self._u(cx) + self._r(rad), self._u(cy) + self._r(rad))
        if fill:
            self.d.ellipse(box, fill=255)
        else:
            self.d.ellipse(box, outline=255, width=self._w(w))

    def rect(self, x1, y1, x2, y2, rad=0.0, fill=False, w=1.0):
        box = (self._u(x1), self._u(y1), self._u(x2), self._u(y2))
        rr = self._r(rad)
        if fill:
            if rr:
                self.d.rounded_rectangle(box, radius=rr, fill=255)
            else:
                self.d.rectangle(box, fill=255)
        elif rr:
            self.d.rounded_rectangle(box, radius=rr, outline=255,
                                     width=self._w(w))
        else:
            self.d.rectangle(box, outline=255, width=self._w(w))

    def dot(self, cx, cy, rad):
        self.circ(cx, cy, rad, fill=True)

    def arc(self, x1, y1, x2, y2, a1, a2, w=1.0):
        self.d.arc((self._u(x1), self._u(y1), self._u(x2), self._u(y2)),
                   a1, a2, fill=255, width=self._w(w))

    def gear(self, cx, cy, ro, teeth=8):
        import math
        outer, inner = ro, ro * 0.74
        pts = []
        for i in range(teeth * 2):
            a = (math.pi * 2) * i / (teeth * 2) - math.pi / 2
            rad = outer if i % 2 == 0 else inner
            pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
        self.fill(pts)
        # hole, punched back to transparent so the plate shows through
        hx, hy, hr = self._u(cx), self._u(cy), self._r(ro * 0.30)
        self.d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=0)


def glyph(name):
    p = Pen()
    if name == "web":
        p.circ(0.5, 0.5, 0.44)
        p.line([(0.06, 0.5), (0.94, 0.5)])
        p.d.arc((u(0.26), v(0.06), u(0.74), v(0.94)), 0, 360, fill=None)
        p.arc(0.3, 0.06, 0.7, 0.94, 90, 270)
        p.arc(0.3, 0.06, 0.7, 0.94, 270, 90)
    elif name in ("editor",):
        p.line([(0.34, 0.16), (0.08, 0.5), (0.34, 0.84)])
        p.line([(0.66, 0.16), (0.92, 0.5), (0.66, 0.84)])
        p.line([(0.56, 0.1), (0.44, 0.9)], w=0.85)
    elif name == "agents":
        p.dot(0.5, 0.5, 0.085)
        nodes = [(0.24, 0.2), (0.82, 0.34), (0.42, 0.88)]
        for n in nodes:
            p.line([(0.5, 0.5), n], w=0.62)
            p.circ(n[0], n[1], 0.13, w=0.85)
    elif name == "custos":
        p.poly([(0.5, 0.08), (0.92, 0.26), (0.84, 0.66), (0.5, 0.94),
                (0.16, 0.66), (0.08, 0.26)])
        p.circ(0.5, 0.42, 0.11)
        p.line([(0.5, 0.53), (0.5, 0.70)])
    elif name == "board":
        p.rect(0.14, 0.18, 0.86, 0.92, rad=0.08)
        p.rect(0.34, 0.08, 0.66, 0.24, rad=0.05)
        for i in range(3):
            y = 0.46 + i * 0.14
            p.line([(0.28, y), (0.72, y)], w=0.8)
    elif name == "boards":
        # three stacked cards, offset — reads at 44 px where columns did not
        for i in range(3):
            x = 0.10 + i * 0.06
            y = 0.10 + i * 0.10
            p.rect(x, y, x + 0.72, y + 0.60, rad=0.06, w=0.85)
            if i == 2:
                for k in range(2):
                    yy = y + 0.20 + k * 0.16
                    p.line([(x + 0.14, yy), (x + 0.56, yy)], w=0.6)
    elif name == "messages":
        p.rect(0.08, 0.16, 0.92, 0.74, rad=0.14)
        p.fill([(0.30, 0.72), (0.24, 0.94), (0.52, 0.74)])
        for i in range(2):
            p.dot(0.34 + i * 0.32, 0.45, 0.062)
    elif name == "logo":
        p.poly([(0.5, 0.06), (0.94, 0.5), (0.5, 0.94), (0.06, 0.5)])
        p.poly([(0.5, 0.28), (0.72, 0.5), (0.5, 0.72), (0.28, 0.5)])
        p.dot(0.5, 0.5, 0.055)
    elif name == "music3d":
        p.circ(0.34, 0.76, 0.15, fill=True)
        p.line([(0.49, 0.74), (0.49, 0.16)])
        p.line([(0.49, 0.16), (0.78, 0.28), (0.78, 0.46)])
        p.poly([(0.20, 0.30), (0.34, 0.22), (0.34, 0.38), (0.20, 0.46)],
               close=False, w=0.6)
    elif name == "notes":
        p.poly([(0.16, 0.06), (0.84, 0.06), (0.84, 0.94), (0.16, 0.94)])
        for i in range(4):
            y = 0.28 + i * 0.16
            p.line([(0.30, y), (0.70, y)], w=0.72)
    elif name == "notes3d":
        p.poly([(0.10, 0.20), (0.62, 0.20), (0.62, 0.90), (0.10, 0.90)])
        for i in range(3):
            y = 0.40 + i * 0.16
            p.line([(0.22, y), (0.50, y)], w=0.72)
        p.poly([(0.62, 0.34), (0.90, 0.20), (0.90, 0.74), (0.62, 0.90)],
               close=False, w=0.6)
        p.line([(0.62, 0.34), (0.62, 0.20)])
    elif name == "budget":
        p.arc(0.08, 0.24, 0.92, 0.96, 180, 360)
        p.line([(0.5, 0.6), (0.74, 0.34)])
        p.dot(0.5, 0.6, 0.09)
        for x in (0.14, 0.5, 0.86):
            p.line([(x, 0.54), (x, 0.62)], w=0.7)
    elif name == "controls":
        for i, (y, x) in enumerate(((0.22, 0.66), (0.5, 0.34), (0.78, 0.58))):
            p.line([(0.08, y), (0.92, y)], w=0.8)
            p.dot(x, y, 0.10)
    elif name == "about":
        p.circ(0.5, 0.5, 0.44)
        p.dot(0.5, 0.30, 0.06)
        p.line([(0.5, 0.44), (0.5, 0.72)])
    elif name == "aegis":
        p.arc(0.05, 0.30, 0.95, 0.74, 190, 350)
        p.arc(0.05, 0.26, 0.95, 0.70, 10, 170)
        p.dot(0.5, 0.5, 0.15)
    elif name == "science":
        p.dot(0.5, 0.5, 0.09)
        for a in ((0.16, 0.78), (0.84, 0.36), (0.24, 0.20)):
            p.line([(0.5, 0.5), a], w=0.62)
            p.circ(a[0], a[1], 0.135, w=0.85)
    elif name == "terminal":
        p.line([(0.10, 0.24), (0.36, 0.5), (0.10, 0.76)])
        p.line([(0.50, 0.76), (0.90, 0.76)])
    elif name == "trash":
        p.line([(0.06, 0.22), (0.94, 0.22)], w=0.9)
        p.rect(0.26, 0.10, 0.74, 0.22, rad=0.04, w=0.8)
        p.poly([(0.16, 0.22), (0.84, 0.22), (0.76, 0.94), (0.24, 0.94)])
        p.line([(0.40, 0.40), (0.42, 0.76)], w=0.65)
        p.line([(0.60, 0.40), (0.58, 0.76)], w=0.65)
    elif name == "files":
        p.poly([(0.06, 0.84), (0.06, 0.20), (0.40, 0.20), (0.50, 0.34),
                (0.94, 0.34), (0.94, 0.84)])
        p.line([(0.06, 0.46), (0.94, 0.46)], w=0.7)
    elif name == "imperium":
        p.line([(0.06, 0.22), (0.5, 0.06), (0.94, 0.22)])
        p.rect(0.06, 0.22, 0.94, 0.32, rad=0.02, w=0.8)
        for x in (0.22, 0.5, 0.78):
            p.line([(x, 0.34), (x, 0.80)], w=0.9)
        p.line([(0.06, 0.82), (0.94, 0.82)])
    elif name == "dashboard":
        p.rect(0.06, 0.06, 0.46, 0.46, rad=0.05)
        p.rect(0.54, 0.06, 0.94, 0.46, rad=0.05)
        p.rect(0.06, 0.54, 0.46, 0.94, rad=0.05)
        p.d.rectangle((u(0.56), v(0.56), u(0.92), v(0.92)), fill=255)
    elif name == "calculator":
        p.rect(0.10, 0.06, 0.90, 0.94, rad=0.08)
        p.line([(0.24, 0.24), (0.76, 0.24)], w=0.75)
        for row in range(2):
            for col in range(3):
                p.dot(0.28 + col * 0.22, 0.48 + row * 0.24, 0.062)
    elif name == "calendar":
        p.rect(0.06, 0.16, 0.94, 0.94, rad=0.08)
        p.line([(0.06, 0.38), (0.94, 0.38)], w=0.8)
        for x in (0.30, 0.70):
            p.line([(x, 0.06), (x, 0.24)], w=0.9)
        for col in range(3):
            p.dot(0.26 + col * 0.24, 0.56, 0.055)
            p.dot(0.26 + col * 0.24, 0.74, 0.055)
    elif name == "musica":
        p.circ(0.30, 0.78, 0.17, fill=True)
        p.line([(0.47, 0.76), (0.47, 0.10)])
        p.line([(0.47, 0.10), (0.90, 0.24), (0.90, 0.44)])
    elif name == "nervus":
        p.line([(0.06, 0.5), (0.94, 0.5)], w=0.9)
        for i, x in enumerate((0.24, 0.5, 0.76)):
            p.line([(x, 0.5), (x, 0.86 if i % 2 else 0.14)], w=0.62)
            p.dot(x, 0.86 if i % 2 else 0.14, 0.10)
    elif name == "officina":
        # open-ended spanner
        p.line([(0.78, 0.22), (0.34, 0.68)], w=1.25)
        p.arc(0.52, 0.04, 0.96, 0.48, 130, 320, w=1.05)
        p.poly([(0.14, 0.74), (0.30, 0.90), (0.44, 0.76), (0.26, 0.60)],
               close=True, w=0.7)
    elif name == "settings":
        p.gear(0.5, 0.5, 0.46, teeth=8)
        p.circ(0.5, 0.5, 0.16)
    elif name == "trio":
        p.poly([(0.5, 0.06), (0.94, 0.24), (0.88, 0.62), (0.5, 0.94),
                (0.12, 0.62), (0.06, 0.24)])
        for i in range(3):
            y = 0.38 + i * 0.13
            p.line([(0.32, y), (0.68, y)], w=0.7)
    else:
        raise SystemExit("no glyph for %s" % name)
    return p.img


ORDER = ["terminal", "files", "editor", "web", "messages", "boards", "board",
         "agents", "aegis", "custos", "imperium", "trio", "science", "musica",
         "music3d", "notes", "notes3d", "officina", "nervus", "budget",
         "dashboard", "calendar", "calculator", "logo", "controls", "settings",
         "trash"]
LABEL = {"terminal": "Terminal", "files": "Files", "editor": "Editor",
         "web": "Web", "messages": "Messages", "boards": "Boards",
         "board": "Boards", "agents": "Agents", "aegis": "Aegis",
         "custos": "Custos", "imperium": "Imperium", "trio": "Trio",
         "science": "Science", "musica": "Musica", "music3d": "Music 3D",
         "notes": "Notes", "notes3d": "Notes 3D", "officina": "Officina",
         "nervus": "Nervus", "budget": "Budget", "dashboard": "Dashboard",
         "calendar": "Calendar", "calculator": "Calculator", "logo": "Logo",
         "controls": "Controls", "settings": "Settings", "trash": "Trash"}


def font(sz, bold=False):
    for p in ("/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz, index=1 if bold else 0)
            except Exception:
                try:
                    return ImageFont.truetype(p, sz)
                except Exception:
                    pass
    return ImageFont.load_default()


def dock_strip(drawn, lang, dark=True, icon=48, gap=10):
    w = 27 * (icon + gap) + gap
    h = icon + 26
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bar)
    d.rounded_rectangle((0, 4, w - 1, h - 5), radius=18,
                        fill=(14, 20, 36, 230) if dark else (250, 251, 253, 235),
                        outline=(46, 62, 96, 200) if dark else (198, 206, 220, 220),
                        width=2)
    x = gap
    for name in ORDER:
        ic = drawn[(lang, name)].resize((icon, icon), Image.LANCZOS)
        bar.paste(ic, (x, (h - icon) // 2), ic)
        x += icon + gap
    return bar


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "..", "..", "..", "captures")
    outdir = os.path.abspath(outdir)

    masks = {}
    for name in ORDER:
        masks[name] = glyph(name)

    drawn = {}
    for lang, fn in (("A", S.style_a), ("B", S.style_b), ("C", S.style_c)):
        d = os.path.join(outdir, "app-icons-" + lang)
        os.makedirs(d, exist_ok=True)
        for name in ORDER:
            icon = fn(masks[name]).resize((S.S, S.S), Image.LANCZOS)
            icon.save(os.path.join(d, "%s-256.png" % name))
            drawn[(lang, name)] = icon
    print("wrote %d icons x 3 languages" % len(ORDER))

    # one sheet: each language as a real dock, on ink, then on paper
    strip_w = 27 * 58 + 10
    pad, head = 26, 118
    row_h = 84
    sheet_h = head + 3 * row_h + 3 * row_h + 34 + pad
    sheet = Image.new("RGB", (strip_w + 2 * pad, sheet_h), (7, 11, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 26), "Meta OS — the whole dock, three languages",
           font=font(30, True), fill=(232, 236, 244))
    d.text((pad, 62), "27 tiles. A monoline / B knockout / C dot-matrix.",
           font=font(16), fill=(140, 152, 176))

    names = {"A": "A — ink plate, monoline", "B": "B — ink to blue, knockout",
             "C": "C — bracket frame, dot-matrix"}
    for i, lang in enumerate(("A", "B", "C")):
        y = head + i * row_h
        d.text((pad, y - 20), names[lang], font=font(15), fill=(120, 186, 255))
        st = dock_strip(drawn, lang, dark=True, icon=44, gap=13)
        sheet.paste(st, (pad, y + 4), st)

    y2 = head + 3 * row_h + 8
    d.text((pad, y2), "on a light desktop", font=font(15), fill=(140, 152, 176))
    for i, lang in enumerate(("A", "B", "C")):
        st = dock_strip(drawn, lang, dark=False, icon=40, gap=14)
        y = y2 + 24 + i * 62
        sheet.paste(st, (pad, y), st)

    p = os.path.join(outdir, "dock-three-languages.png")
    sheet.save(p)
    print("wrote", p, os.path.getsize(p), "bytes")


if __name__ == "__main__":
    main()
