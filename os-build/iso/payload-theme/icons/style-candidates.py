#!/usr/bin/env python3
"""Draw three icon languages for the same six tiles, side by side.

The dock ships 27 icons. Before drawing 27 of anything, three languages are
drawn for six representative apps so one can be picked by looking, not by
arguing. Same glyph geometry in all three, so the comparison is about the
language and not about the drawing.

  A  ink plate, monoline glyph            (dark, calm, mac-adjacent)
  B  ink->blue plate, knockout glyph      (solid, shop-window, Big Sur)
  C  bracket frame, dot-matrix glyph      (matches the ASCII spinner identity)

Everything is drawn at 4x and downsampled, so edges are clean at 128 and 256.
PIL only, no fonts in the art, no randomness: byte-identical on re-run.

Usage: style-candidates.py [outdir]
Writes <outdir>/style-A|B|C/<app>-256.png and <outdir>/icon-styles.png (the sheet).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

S = 256          # final icon edge
SS = 4           # supersample
C = S * SS

INK = (9, 14, 28, 255)          # Meta ink
INK_EDGE = (34, 48, 78, 255)    # plate hairline
BLUE = (24, 119, 242, 255)      # Meta accent
BRIGHT = (120, 186, 255, 255)   # highlight
PAPER = (232, 236, 244, 255)
FRAME = (43, 58, 92, 255)

APPS = ["terminal", "trio", "musica", "aegis", "science", "agents"]
LABEL = {"terminal": "Terminal", "trio": "Trio", "musica": "Musica",
         "aegis": "Aegis", "science": "Science", "agents": "Agents"}


# ---------------------------------------------------------------- glyph masks
# One mask per app, drawn white on black at supersampled size. Strokes are
# monoline and share the same optical weight so the three languages line up.

def _stroke():
    return int(C * 0.055)      # ~14 px at 256


def glyph(name):
    m = Image.new("L", (C, C), 0)
    d = ImageDraw.Draw(m)
    w = _stroke()
    r = w // 2
    box = int(C * 0.17)        # glyph area starts here
    far = C - box

    def line(pts, width=None):
        d.line(pts, fill=255, width=width or w, joint="curve")

    def circle(cx, cy, rad, width=None, fill=False):
        ww = width or w
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad),
                  outline=None if fill else 255, fill=255 if fill else None,
                  width=0 if fill else ww)

    if name == "terminal":
        # >_  chevron and caret
        line([(box, box + int(C * 0.06)), (box + int(C * 0.20), C // 2),
              (box, far - int(C * 0.06))])
        line([(int(C * 0.46), far - int(C * 0.10)), (far, far - int(C * 0.10))])
    elif name == "trio":
        # shield with three division bars
        top = box - int(C * 0.02)
        mid = int(C * 0.46)
        line([(C // 2, top), (far, top + int(C * 0.08))])
        line([(far, top + int(C * 0.08)), (far - int(C * 0.02), mid)])
        line([(far - int(C * 0.02), mid), (C // 2, far)])
        line([(C // 2, far), (box + int(C * 0.02), mid)])
        line([(box + int(C * 0.02), mid), (box, top + int(C * 0.08))])
        line([(box, top + int(C * 0.08)), (C // 2, top)])
        for i in range(3):
            y = int(C * (0.38 + i * 0.11))
            line([(int(C * 0.36), y), (int(C * 0.64), y)], width=int(w * 0.72))
    elif name == "musica":
        # eighth note: head, stem, flag
        hx, hy, hr = int(C * 0.40), int(C * 0.74), int(C * 0.11)
        d.ellipse((hx - hr, hy - int(hr * 0.82), hx + hr, hy + int(hr * 0.82)),
                  fill=255)
        line([(hx + hr - r // 2, hy - int(hr * 0.4)), (hx + hr - r // 2, box)])
        line([(hx + hr - r // 2, box), (far - int(C * 0.02), box + int(C * 0.14))])
        line([(far - int(C * 0.02), box + int(C * 0.14)),
              (far - int(C * 0.02), box + int(C * 0.30))])
    elif name == "aegis":
        # eye: two lens arcs, a pupil, one glint — reads at 24 px
        upper = (int(C * 0.14), int(C * 0.30), int(C * 0.86), int(C * 0.78))
        lower = (int(C * 0.14), int(C * 0.22), int(C * 0.86), int(C * 0.70))
        d.arc(upper, 185, 355, fill=255, width=w)
        d.arc(lower, 5, 175, fill=255, width=w)
        circle(C // 2, C // 2, int(C * 0.135), fill=True)
        d.ellipse((C // 2 - int(C * 0.045), C // 2 - int(C * 0.085),
                   C // 2 + int(C * 0.005), C // 2 - int(C * 0.035)), fill=0)
    elif name == "science":
        # three-atom molecule: centre, two bonds, two terminals
        circle(C // 2, C // 2, int(C * 0.09), fill=True)
        a1 = (int(C * 0.30), int(C * 0.70))
        a2 = (int(C * 0.72), int(C * 0.36))
        a3 = (int(C * 0.30), int(C * 0.30))
        for a in (a1, a2, a3):
            line([(C // 2, C // 2), a], width=int(w * 0.8))
        for a in (a1, a2, a3):
            d.ellipse((a[0] - int(C * 0.075), a[1] - int(C * 0.075),
                       a[0] + int(C * 0.075), a[1] + int(C * 0.075)),
                      outline=255, width=int(w * 0.85))
    elif name == "agents":
        # hub and three nodes
        circle(C // 2, C // 2, int(C * 0.095), fill=True)
        nodes = [(int(C * 0.28), int(C * 0.24)), (int(C * 0.78), int(C * 0.34)),
                 (int(C * 0.44), int(C * 0.80))]
        for n in nodes:
            line([(C // 2, C // 2), n], width=int(w * 0.66))
            d.ellipse((n[0] - int(C * 0.075), n[1] - int(C * 0.075),
                       n[0] + int(C * 0.075), n[1] + int(C * 0.075)),
                      outline=255, width=int(w * 0.85))
    else:
        raise SystemExit("no glyph for %s" % name)
    return m


# -------------------------------------------------------------------- plates

def plate(radius=int(C * 0.225)):
    return Image.new("RGBA", (C, C), (0, 0, 0, 0)), radius


def rounded_mask(radius):
    m = Image.new("L", (C, C), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, C - 1, C - 1), radius=radius, fill=255)
    return m


def style_a(g):
    plate_img, rad = plate()
    pm = rounded_mask(rad)
    plate_img.paste(Image.new("RGBA", (C, C), INK), (0, 0), pm)
    # inner hairline
    d = ImageDraw.Draw(plate_img)
    d.rounded_rectangle((1, 1, C - 2, C - 2), radius=rad,
                        outline=INK_EDGE, width=max(2, int(C * 0.006)))
    # glyph: blue body, bright on the top-left third for a lit edge
    plate_img.paste(Image.new("RGBA", (C, C), BLUE), (0, 0), g)
    lit_full = Image.new("L", (C, C), 0)
    lit_full.paste(g)
    lit = lit_full.crop((0, 0, C, int(C * 0.52)))
    lit_mask = Image.new("L", (C, C), 0)
    lit_mask.paste(lit, (0, 0))
    plate_img.paste(Image.new("RGBA", (C, C), BRIGHT), (0, 0), lit_mask)
    return plate_img


def style_b(g):
    plate_img, rad = plate()
    pm = rounded_mask(rad)
    grad = Image.new("RGBA", (C, C))
    gd = ImageDraw.Draw(grad)
    top = (16, 26, 50)
    for y in range(C):
        t = y / float(C - 1)
        # navy at the top, accent at the bottom: one straight ramp, no gloss
        # wash, because a wash with a straight cut read as a dome in the sheet.
        r = int(top[0] + (BLUE[0] - top[0]) * t)
        gg = int(top[1] + (BLUE[1] - top[1]) * t)
        b = int(top[2] + (BLUE[2] - top[2]) * t)
        gd.line([(0, y), (C, y)], fill=(r, gg, b, 255))
    plate_img.paste(grad, (0, 0), pm)
    # a single hairline of light on the top edge, clipped to the plate
    hair = Image.new("RGBA", (C, C), (255, 255, 255, 0))
    ImageDraw.Draw(hair).rounded_rectangle(
        (1, 1, C - 2, C - 2), radius=rad,
        outline=(255, 255, 255, 46), width=max(2, int(C * 0.006)))
    from PIL import ImageChops
    plate_img.paste(hair, (0, 0), ImageChops.multiply(hair.split()[3], pm))
    # knockout glyph
    plate_img.paste(Image.new("RGBA", (C, C), PAPER), (0, 0), g)
    return plate_img


def style_c(g, cols=21):
    """Dot-matrix glyph in a bracket frame — the spinner's language."""
    plate_img, rad = plate()
    plate_img = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate_img)
    inset = int(C * 0.045)
    stroke = max(2, int(C * 0.008))
    # plate: very dark, only enough to hold the grid
    pm = rounded_mask(rad)
    plate_img.paste(Image.new("RGBA", (C, C), (7, 11, 22, 255)), (0, 0), pm)
    d.rounded_rectangle((inset, inset, C - 1 - inset, C - 1 - inset),
                        radius=int(rad * 0.8), outline=FRAME, width=stroke)
    # corner ticks
    t = int(C * 0.09)
    for (cx, cy, dx, dy) in ((inset, inset, 1, 1), (C - 1 - inset, inset, -1, 1),
                             (inset, C - 1 - inset, 1, -1),
                             (C - 1 - inset, C - 1 - inset, -1, -1)):
        d.line([(cx, cy + dy * t), (cx + dx * t, cy + dy * t)],
               fill=BLUE, width=stroke * 2)
    # sample the mask onto a cell grid
    pad = int(C * 0.20)
    span = C - 2 * pad
    cell = span / float(cols)
    pix = g.load()
    dot = max(2, int(cell * 0.62))
    for row in range(cols):
        for col in range(cols):
            cx = int(pad + (col + 0.5) * cell)
            cy = int(pad + (row + 0.5) * cell)
            hit = 0
            for oy in (-cell * 0.26, 0, cell * 0.26):
                for ox in (-cell * 0.26, 0, cell * 0.26):
                    x, y = int(cx + ox), int(cy + oy)
                    if 0 <= x < C and 0 <= y < C and pix[x, y] > 110:
                        hit += 1
            if hit < 2:
                continue
            col_rgb = BRIGHT if hit >= 6 else BLUE
            d.rounded_rectangle((cx - dot // 2, cy - dot // 2,
                                 cx + dot // 2, cy + dot // 2),
                                radius=max(1, dot // 4), fill=col_rgb)
    return plate_img


# ------------------------------------------------------------------- cursor
def cursor_px(edge):
    """White arrow, black outline, blue accent — the boss's call.

    Order matters: black silhouette first, white body inset from it, blue only
    along the two leading edges. Drawing the outline last would eat the accent.
    """
    k = SS
    n = 24 * k
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(2.0, 1.6), (2.0, 18.4), (6.4, 14.0), (9.2, 22.0),
           (12.3, 20.8), (9.5, 13.1), (15.4, 13.1)]
    poly = [(x / 24.0 * n, y / 24.0 * n) for x, y in pts]
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    # black silhouette, built as a stroke so the tip stays sharp
    d.polygon(poly, fill=(0, 0, 0, 255))
    d.line(poly + [poly[0]], fill=(0, 0, 0, 255), width=int(1.1 * k),
           joint="curve")
    # white body, 1.1 px inset
    inset = [(cx + (x - cx) * 0.80, cy + (y - cy) * 0.80) for x, y in poly]
    d.polygon(inset, fill=(255, 255, 255, 255))
    # blue accent along the leading edges of the inset body
    d.line([inset[0], inset[1]], fill=BLUE, width=int(0.95 * k))
    d.line([inset[0], inset[6]], fill=BLUE, width=int(0.95 * k))
    if edge:
        return img
    return img.resize((24, 24), Image.LANCZOS)


# -------------------------------------------------------------------- sheet
def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
        "captures")
    outdir = os.path.abspath(outdir)
    for lang in ("A", "B", "C"):
        os.makedirs(os.path.join(outdir, "style-" + lang), exist_ok=True)

    masks = {a: glyph(a) for a in APPS}
    drawn = {}
    for a in APPS:
        for lang, fn in (("A", style_a), ("B", style_b), ("C", style_c)):
            big = fn(masks[a])
            icon = big.resize((S, S), Image.LANCZOS)
            icon.save(os.path.join(outdir, "style-" + lang, "%s-256.png" % a))
            drawn[(lang, a)] = icon

    # contact sheet — dark desktop background, both sizes, plus a light strip
    pad, cell_w, cell_h = 26, 196, 232
    head = 128
    sheet_w = pad + cell_w * 6 + pad
    strip_h = 3 * 46 + 16
    sheet_h = head + cell_h * 3 + 34 + strip_h + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (7, 11, 22))

    def font(sz, bold=False):
        for p in ("/System/Library/Fonts/Helvetica.ttc",
                  "/System/Library/Fonts/Supplemental/Arial.ttf",
                  "/Library/Fonts/Arial.ttf"):
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, sz, index=1 if bold else 0)
                except Exception:
                    try:
                        return ImageFont.truetype(p, sz)
                    except Exception:
                        pass
        return ImageFont.load_default()

    f_title, f_small, f_label = font(34, True), font(17), font(19)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 30), "Meta OS — icon languages", font=f_title, fill=PAPER)
    d.text((pad, 74), "same glyphs, three languages. pick one, then all 27.",
           font=f_small, fill=(140, 152, 176))

    names = {"A": "A — ink plate, monoline glyph",
             "B": "B — ink to blue plate, knockout glyph",
             "C": "C — bracket frame, dot-matrix glyph"}
    for row, lang in enumerate(("A", "B", "C")):
        y = head + row * cell_h
        d.text((pad, y + 6), names[lang], font=f_small, fill=(120, 186, 255))
        for col, a in enumerate(APPS):
            x = pad + col * cell_w + (cell_w - 160) // 2
            icon = drawn[(lang, a)].resize((160, 160), Image.LANCZOS)
            sheet.paste(icon, (x, y + 30), icon)
            w = d.textlength(LABEL[a], font=f_label) if hasattr(d, "textlength") else 60
            d.text((pad + col * cell_w + (cell_w - w) / 2, y + 196),
                   LABEL[a], font=f_label, fill=(196, 204, 220))

    # light strip: the same three languages on a light desktop
    ly = head + 3 * cell_h + 8
    d.text((pad, ly), "on a light background (Settings, Files, dialogs)",
           font=f_small, fill=(140, 152, 176))
    lstrip = Image.new("RGB", (sheet_w - 2 * pad, strip_h), (232, 236, 244))
    for row, lang in enumerate(("A", "B", "C")):
        for col, a in enumerate(APPS):
            icon = drawn[(lang, a)].resize((40, 40), Image.LANCZOS)
            x = col * cell_w + (cell_w - 40) // 2
            y = 10 + row * 46
            lstrip.paste(icon, (x, y), icon)
    sheet.paste(lstrip, (pad, ly + 26))

    sheet_path = os.path.join(outdir, "icon-styles.png")
    sheet.save(sheet_path)
    print("wrote", sheet_path, os.path.getsize(sheet_path), "bytes")

    # cursor sheet
    cur = Image.new("RGB", (520, 200), (232, 236, 244))
    cd = ImageDraw.Draw(cur)
    cd.text((24, 16), "cursor — white arrow, black outline, blue accent",
            font=f_small, fill=(40, 50, 70))
    big = cursor_px(True).resize((120, 120), Image.LANCZOS)
    cur.paste(big, (24, 52), big)
    for i, sz in enumerate((24, 32, 48)):
        small = big.resize((sz, sz), Image.LANCZOS)
        cur.paste(small, (200 + i * 90, 90), small)
    cpath = os.path.join(outdir, "cursor-candidates.png")
    cur.save(cpath)
    print("wrote", cpath, os.path.getsize(cpath), "bytes")


if __name__ == "__main__":
    main()
