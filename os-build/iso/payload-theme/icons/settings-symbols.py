#!/usr/bin/env python3
"""System and settings symbols — the chrome that is not an app tile.

App tiles live on a plate. Everything else (Settings rows, the top bar, menus,
dialogs) is a bare monoline symbol on whatever background it lands on, so the
same geometry has to work at 24 px on ink and on paper, in one weight.

Geometry comes from app-icons.Pen with the 24 px grid box and a lighter stroke,
so a settings gear and the Settings app tile share an outline instead of being
drawn twice.

Usage: settings-symbols.py [outdir]      → <outdir>/settings-symbols.png
"""
import importlib.util
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = _load("appicons", os.path.join(HERE, "app-icons.py"))
S = A.S

PAPER = (232, 236, 244, 255)
INK = (9, 14, 28, 255)
BLUE = (24, 119, 242, 255)
MUTED = (140, 152, 176)

SYMBOLS = ["display", "sound", "network", "wifi", "bluetooth", "battery",
           "power", "theme", "wallpaper", "lock", "keyboard", "pointer",
           "bell", "update", "info", "clock", "users", "storage", "search",
           "chevron-down"]


def symbol(name):
    p = A.Pen(box=(0.055, 0.945), weight=1.12)
    if name == "display":
        p.rect(0.06, 0.14, 0.94, 0.70, rad=0.06)
        p.line([(0.5, 0.70), (0.5, 0.86)])
        p.line([(0.30, 0.86), (0.70, 0.86)])
    elif name == "sound":
        p.poly([(0.10, 0.38), (0.26, 0.38), (0.48, 0.16), (0.48, 0.84),
                (0.26, 0.62), (0.10, 0.62)])
        p.arc(0.40, 0.26, 0.78, 0.74, -60, 60, w=0.9)
        p.arc(0.40, 0.10, 0.98, 0.90, -55, 55, w=0.9)
    elif name == "network":
        p.dot(0.24, 0.26, 0.10)
        p.dot(0.76, 0.26, 0.10)
        p.dot(0.50, 0.78, 0.10)
        p.line([(0.24, 0.26), (0.50, 0.78)], w=0.75)
        p.line([(0.76, 0.26), (0.50, 0.78)], w=0.75)
        p.line([(0.24, 0.26), (0.76, 0.26)], w=0.75)
    elif name == "wifi":
        p.arc(0.02, 0.10, 0.98, 0.92, 215, 325)
        p.arc(0.20, 0.32, 0.80, 1.02, 215, 325)
        p.dot(0.5, 0.84, 0.075)
    elif name == "bluetooth":
        p.line([(0.30, 0.22), (0.70, 0.62), (0.50, 0.82), (0.50, 0.10),
                (0.70, 0.30), (0.30, 0.70)], w=0.95)
    elif name == "battery":
        p.rect(0.04, 0.30, 0.82, 0.70, rad=0.08)
        p.rect(0.84, 0.42, 0.94, 0.58, rad=0.03, fill=True)
        p.rect(0.16, 0.42, 0.38, 0.58, rad=0.02, fill=True)
        p.rect(0.44, 0.42, 0.66, 0.58, rad=0.02, fill=True)
    elif name == "power":
        p.arc(0.12, 0.14, 0.88, 0.90, 300, 240)
        p.line([(0.5, 0.06), (0.5, 0.46)])
    elif name == "theme":
        # crescent: a filled disc with a shifted disc punched out
        d = p.d
        cx, cy, rad = p._u(0.5), p._u(0.5), p._r(0.44)
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=255)
        ox, oy, orad = p._u(0.62), p._u(0.34), p._r(0.40)
        d.ellipse((ox - orad, oy - orad, ox + orad, oy + orad), fill=0)
    elif name == "wallpaper":
        p.rect(0.04, 0.14, 0.96, 0.86, rad=0.07)
        p.poly([(0.12, 0.78), (0.38, 0.44), (0.56, 0.64), (0.68, 0.52),
                (0.90, 0.78)], close=False, w=0.85)
        p.dot(0.72, 0.30, 0.065)
    elif name == "lock":
        p.rect(0.18, 0.44, 0.82, 0.92, rad=0.08)
        p.arc(0.28, 0.10, 0.72, 0.62, 180, 360)
        p.line([(0.28, 0.36), (0.28, 0.46)], w=0.9)
        p.line([(0.72, 0.36), (0.72, 0.46)], w=0.9)
        p.dot(0.5, 0.66, 0.065)
    elif name == "keyboard":
        p.rect(0.02, 0.24, 0.98, 0.76, rad=0.07)
        for row in range(2):
            for col in range(5):
                p.dot(0.16 + col * 0.17, 0.40 + row * 0.16, 0.045)
        p.line([(0.30, 0.68), (0.70, 0.68)], w=0.85)
    elif name == "pointer":
        p.poly([(0.30, 0.06), (0.30, 0.80), (0.46, 0.62), (0.58, 0.92),
                (0.70, 0.86), (0.58, 0.56), (0.80, 0.54)], close=True, w=0.85)
    elif name == "bell":
        p.poly([(0.5, 0.08), (0.78, 0.28), (0.78, 0.62), (0.92, 0.74),
                (0.08, 0.74), (0.22, 0.62), (0.22, 0.28)], close=True, w=0.85)
        p.arc(0.38, 0.70, 0.62, 0.94, 0, 180)
    elif name == "update":
        p.arc(0.08, 0.08, 0.92, 0.92, 20, 160, w=0.9)
        p.arc(0.08, 0.08, 0.92, 0.92, 200, 340, w=0.9)
        p.poly([(0.86, 0.30), (0.94, 0.16), (0.76, 0.20)], close=False, w=0.85)
        p.poly([(0.14, 0.70), (0.06, 0.84), (0.24, 0.80)], close=False, w=0.85)
    elif name == "info":
        p.circ(0.5, 0.5, 0.44)
        p.dot(0.5, 0.28, 0.062)
        p.line([(0.5, 0.42), (0.5, 0.74)])
    elif name == "clock":
        p.circ(0.5, 0.5, 0.44)
        p.line([(0.5, 0.24), (0.5, 0.52)])
        p.line([(0.5, 0.52), (0.70, 0.64)], w=0.85)
    elif name == "users":
        p.circ(0.36, 0.30, 0.16)
        p.arc(0.10, 0.50, 0.62, 0.98, 180, 360)
        p.line([(0.10, 0.78), (0.10, 0.92)], w=0.85)
        p.line([(0.62, 0.78), (0.62, 0.92)], w=0.85)
        p.circ(0.68, 0.30, 0.13, w=0.85)
    elif name == "storage":
        for i in range(3):
            y = 0.22 + i * 0.24
            p.d.ellipse((p._u(0.10), p._u(y - 0.10), p._u(0.90), p._u(y + 0.10)),
                        outline=255, width=p._w(0.9))
            if i < 2:
                p.line([(0.10, y), (0.10, y + 0.24)], w=0.75)
                p.line([(0.90, y), (0.90, y + 0.24)], w=0.75)
    elif name == "search":
        p.circ(0.42, 0.42, 0.32)
        p.line([(0.66, 0.66), (0.92, 0.92)], w=1.0)
    elif name == "chevron-down":
        p.line([(0.26, 0.40), (0.5, 0.64), (0.74, 0.40)], w=1.0)
    else:
        raise SystemExit("no symbol for %s" % name)
    return p.img


def tint(mask, colour):
    img = Image.new("RGBA", (S.C, S.C), colour)
    img.putalpha(mask)
    return img


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "..", "..", "..", "captures")
    outdir = os.path.abspath(outdir)

    masks = {n: symbol(n) for n in SYMBOLS}
    at = {}
    for n, m in masks.items():
        at[(n, "paper")] = tint(m, PAPER).resize((96, 96), Image.LANCZOS)
        at[(n, "ink")] = tint(m, INK).resize((96, 96), Image.LANCZOS)
        at[(n, "blue")] = tint(m, BLUE).resize((96, 96), Image.LANCZOS)

    W, H = 1180, 1200
    sheet = Image.new("RGB", (W, H), (7, 11, 22))
    d = ImageDraw.Draw(sheet)
    f = A.font
    d.text((28, 24), "Meta OS — settings and system symbols", font=f(30, True),
           fill=(232, 236, 244))
    d.text((28, 60), "one monoline geometry, 24 px grid, works on ink and on paper",
           font=f(16), fill=MUTED)

    # grid, 6 across, 48 px, with names
    cell_w, cell_h = 186, 132
    for i, n in enumerate(SYMBOLS):
        col, row = i % 6, i // 6
        x = 28 + col * cell_w
        y = 100 + row * cell_h
        ic = at[(n, "paper")].resize((48, 48), Image.LANCZOS)
        sheet.paste(ic, (x + 8, y + 10), ic)
        d.text((x + 8, y + 68), n, font=f(15), fill=(196, 204, 220))
        # 24 px proof: ink on a paper chip (what Settings draws), accent on ink
        chip = Image.new("RGB", (30, 30), (232, 236, 244))
        sm = at[(n, "ink")].resize((24, 24), Image.LANCZOS)
        chip.paste(sm, (3, 3), sm)
        sheet.paste(chip, (x + 8, y + 88))
        sm2 = at[(n, "blue")].resize((24, 24), Image.LANCZOS)
        sheet.paste(sm2, (x + 48, y + 91), sm2)

    # mock: the Settings window, dark
    top = 100 + 4 * cell_h + 10
    d.text((28, top), "in place — Settings rows at 24 px", font=f(15), fill=MUTED)
    card = Image.new("RGB", (556, 300), (14, 20, 36))
    cd = ImageDraw.Draw(card)
    rows = ["display", "wallpaper", "sound", "network", "theme", "lock",
            "storage", "update"]
    names = {"display": "Displays", "wallpaper": "Wallpaper", "sound": "Sound",
             "network": "Network", "theme": "Appearance", "lock": "Privacy",
             "storage": "Storage", "update": "Updates"}
    for i, n in enumerate(rows):
        y = 12 + i * 35
        if i == 2:
            cd.rounded_rectangle((6, y - 6, 550, y + 28), radius=8,
                                 fill=(24, 36, 60))
        ic = at[(n, "paper")].resize((22, 22), Image.LANCZOS)
        card.paste(ic, (22, y), ic)
        cd.text((58, y + 1), names[n], font=f(15), fill=(226, 232, 242))
        chev = at[("chevron-down", "paper")].resize((16, 16), Image.LANCZOS)
        card.paste(chev, (522, y + 4), chev)
    cd.rounded_rectangle((0, 0, 555, 299), radius=12, outline=(46, 62, 96), width=2)
    sheet.paste(card, (28, top + 26))

    # mock: top bar at 28 px, the bar height the theme uses
    bar_x, bar_y, bar_w = 28, top + 26 + 300 + 24, W - 56
    d.text((28, bar_y - 22), "in place — top bar, 28 px", font=f(15), fill=MUTED)
    bar = Image.new("RGB", (bar_w, 28), (10, 15, 28))
    bd = ImageDraw.Draw(bar)
    bd.text((14, 6), "Meta OS", font=f(14), fill=(232, 236, 244))
    bd.text((bar_w // 2 - 40, 6), "21:04  Tue 4 Nov", font=f(14), fill=(196, 204, 220))
    x = bar_w - 20
    for n in ("battery", "wifi", "bell", "search"):
        ic = at[(n, "paper")].resize((16, 16), Image.LANCZOS)
        x -= 24
        bar.paste(ic, (x, 6), ic)
    bd.rounded_rectangle((0, 0, bar_w - 1, 27), radius=6, outline=(34, 48, 78), width=1)
    sheet.paste(bar, (bar_x, bar_y))

    # light strip: every symbol at 24 px on paper, in ink
    ly = bar_y + 46
    d.text((28, ly), "every symbol, 24 px, on paper", font=f(15), fill=MUTED)
    strip = Image.new("RGB", (W - 56, 56), (232, 236, 244))
    for i, n in enumerate(SYMBOLS):
        ic = at[(n, "ink")].resize((24, 24), Image.LANCZOS)
        strip.paste(ic, (12 + i * 54, 16), ic)
    sheet.paste(strip, (28, ly + 22))

    p = os.path.join(outdir, "settings-symbols.png")
    sheet.save(p)
    print("wrote", p, os.path.getsize(p), "bytes")
    print("symbols:", len(SYMBOLS))


if __name__ == "__main__":
    main()
