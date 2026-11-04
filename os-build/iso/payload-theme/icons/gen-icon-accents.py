#!/usr/bin/env python3
"""Build the icon accent sets that the desktop switches between.

The dock has to follow the wallpaper. Runtime image work in the guest is a bad
trade (Pillow is not guaranteed on the image, and a login must not wait on 27
renders), so every accent is rendered here, at build time, and the runtime picks
a directory.

Sets written to <out>/<set>/128x128/apps/*.png plus index.theme:

  blue-B   default, Meta blue, solid plate      (the shipped default)
  blue-A   Meta blue, monoline plate
  blue-C   Meta blue, dot matrix in a bracket
  ice-B    cyan accent      <- meta-rays wallpaper
  amber-B  amber accent     <- meta-dawn wallpaper
  violet-B violet accent    <- meta-dusk wallpaper
  teal-B   teal accent      (cooled, never Ubuntu green)
  mono-B   paper glyph on ink, no hue at all

accents.conf maps a wallpaper's basename to a set name, so the runtime script
needs no image decoding at all. A wallpaper it does not recognise falls back to
blue-B and says so in its log.

Usage: gen-icon-accents.py [outdir] [--sync-default]

  --sync-default  also copy the blue-B set over icons/metaos/, so the system
                  theme the greeter and every launcher already point at ships
                  the new art with no runtime script involved.
"""
import importlib.util
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("styles", os.path.join(HERE, "style-candidates.py"))
A = _load("appicons", os.path.join(HERE, "app-icons.py"))

PAPER = (232, 236, 244, 255)
BRIGHT = (120, 186, 255, 255)

# set name, human label, accent, glyph/knockout colour, language
SETS = [
    ("blue-B", "Meta Blue — solid", (24, 119, 242), PAPER, "B"),
    ("blue-A", "Meta Blue — monoline", (24, 119, 242), BRIGHT, "A"),
    ("blue-C", "Meta Blue — dot matrix", (24, 119, 242), BRIGHT, "C"),
    ("ice-B", "Ice — cyan", (56, 189, 248), PAPER, "B"),
    ("amber-B", "Amber — dawn", (245, 158, 11), PAPER, "B"),
    ("violet-B", "Violet — dusk", (139, 92, 246), PAPER, "B"),
    ("teal-B", "Teal — pine", (20, 184, 166), PAPER, "B"),
    ("mono-B", "Mono — no hue", (72, 82, 104), PAPER, "B"),
]

# wallpaper basename -> set. Order matters only for readability.
WALLPAPERS = [
    ("meta-ascii.png", "blue-B"),
    ("meta-wallpaper.png", "blue-B"),  # generated live art, in the image only
    ("meta-rays.png", "ice-B"),
    ("meta-dawn.png", "amber-B"),
    ("meta-dusk.png", "violet-B"),
]

STYLE = {"A": S.style_a, "B": S.style_b, "C": S.style_c}


def render(mask, name, accent, bright, lang):
    fn = STYLE[lang]
    if lang == "C":
        return fn(mask, accent=accent, bright=bright)
    return fn(mask, accent=accent, bright=bright)


def write_set(outdir, setname, label, accent, bright, lang, masks):
    d = os.path.join(outdir, setname)
    apps = os.path.join(d, "128x128", "apps")
    os.makedirs(apps, exist_ok=True)
    for name in A.ORDER:
        icon = render(masks[name], name, accent, bright, lang).resize(
            (128, 128), Image.LANCZOS)
        icon.save(os.path.join(apps, name + ".png"))
    # 48 px copies: panel and menus ask for small sizes and the theme declares
    # 128x128 only, so a small-size row keeps GTK from scaling badly.
    small = os.path.join(d, "48x48", "apps")
    os.makedirs(small, exist_ok=True)
    for name in A.ORDER:
        icon = render(masks[name], name, accent, bright, lang).resize(
            (48, 48), Image.LANCZOS)
        icon.save(os.path.join(small, name + ".png"))
    with open(os.path.join(d, "index.theme"), "w") as f:
        f.write("[Icon Theme]\n"
                "Name=%s\n"
                "Comment=%s\n"
                "Inherits=Papirus,elementary-xfce,hicolor\n"
                "Directories=128x128/apps,48x48/apps\n\n"
                "[128x128/apps]\nSize=128\nType=Fixed\nContext=Applications\n\n"
                "[48x48/apps]\nSize=48\nType=Fixed\nContext=Applications\n"
                % (setname, label))
    with open(os.path.join(d, "set.conf"), "w") as f:
        f.write("# accent for this icon set (RGB)\naccent=%d,%d,%d\nlanguage=%s\n"
                % (accent[0], accent[1], accent[2], lang))
    return d


def proof(outdir, masks):
    """Four wallpapers, four docks: the same tiles following the art."""
    wdir = os.path.join(HERE, "..", "wallpapers")
    rows = [("meta-ascii.png", "blue-B"), ("meta-rays.png", "ice-B"),
            ("meta-dawn.png", "amber-B"), ("meta-dusk.png", "violet-B")]
    strips = []
    for wp, setname in rows:
        path = os.path.join(wdir, wp)
        if not os.path.exists(path):
            print("proof: missing wallpaper %s" % path, file=sys.stderr)
            continue
        accent = [s for s in SETS if s[0] == setname][0][2]
        icons = []
        for name in A.ORDER:
            icons.append(render(masks[name], name, accent, PAPER, "B").resize(
                (40, 40), Image.LANCZOS))
        strips.append((wp, setname, icons))

    if not strips:
        return None
    icon, gap, bar_h = 40, 12, 64
    w = len(A.ORDER) * (icon + gap) + gap
    h = 84
    sheet = Image.new("RGB", (w + 32, len(strips) * (bar_h + h) + 96),
                      (7, 11, 22))
    d = ImageDraw.Draw(sheet)
    d.text((16, 16), "Meta OS — the dock follows the wallpaper",
           font=A.font(26, True), fill=(232, 236, 244))
    d.text((16, 48), "same 27 icons, recoloured to the accent each wallpaper "
                     "declares", font=A.font(15), fill=(140, 152, 176))
    y = 84
    for wp, setname, icons in strips:
        bg = Image.open(os.path.join(wdir, wp)).convert("RGB")
        # crop a horizontal band out of the middle of the art, not a squashed
        # full frame, so the wallpaper reads as a wallpaper behind the dock
        bw, bh = sheet.width - 32, bar_h + h - 14
        scale = max(bw / float(bg.width), bh / float(bg.height))
        bg = bg.resize((int(bg.width * scale), int(bg.height * scale)),
                       Image.LANCZOS)
        left = (bg.width - bw) // 2
        top = max(0, (bg.height - bh) // 2)
        bg = bg.crop((left, top, left + bw, top + bh))
        sheet.paste(bg, (16, y - 8))
        bar = Image.new("RGBA", (w, bar_h), (10, 15, 28, 210))
        bd = ImageDraw.Draw(bar)
        bd.rounded_rectangle((0, 0, w - 1, bar_h - 1), radius=16,
                             fill=(10, 15, 28, 205), outline=(70, 86, 120, 200),
                             width=2)
        x = gap
        for ic in icons:
            bar.paste(ic, (x, (bar_h - icon) // 2), ic)
            x += icon + gap
        sheet.paste(bar, (16, y), bar)
        d.text((24, y + bar_h + 8), "%s  ->  %s" % (wp, setname),
               font=A.font(14), fill=(196, 204, 220))
        y += bar_h + h
    p = os.path.join(outdir, "icon-accents.png")
    sheet.save(p)
    print("wrote", p, os.path.getsize(p), "bytes")
    return p


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    outdir = args[0] if args else os.path.join(HERE, "accents")
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)

    masks = {n: A.glyph(n) for n in A.ORDER}
    for setname, label, accent, bright, lang in SETS:
        d = write_set(outdir, setname, label, accent, bright, lang, masks)
        print("set %-9s %s (%d icons x2 sizes)" % (setname, d, len(A.ORDER)))

    with open(os.path.join(outdir, "accents.conf"), "w") as f:
        f.write("# wallpaper basename -> icon set. Read by meta-icon-accent.\n")
        f.write("# Order: first match wins. Unlisted wallpapers fall back to "
                "default.\n")
        f.write("default=%s\n\n" % SETS[0][0])
        for wp, setname in WALLPAPERS:
            f.write("%s=%s\n" % (wp, setname))
        f.write("\n# every set, so the Settings picker can list them\n")
        for setname, label, accent, bright, lang in SETS:
            f.write("set=%s|%s\n" % (setname, label))

    if "--sync-default" in sys.argv:
        src = os.path.join(outdir, SETS[0][0], "128x128", "apps")
        dst = os.path.join(HERE, "metaos")
        n = 0
        for f in sorted(os.listdir(src)):
            if not f.endswith(".png"):
                continue
            with open(os.path.join(src, f), "rb") as r, \
                    open(os.path.join(dst, f), "wb") as w:
                w.write(r.read())
            n += 1
        print("synced %d files into %s (system default)" % (n, dst))

    proof(outdir, masks)


if __name__ == "__main__":
    main()
