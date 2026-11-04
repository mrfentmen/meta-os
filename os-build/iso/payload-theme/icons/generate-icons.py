#!/usr/bin/env python3
"""Draw the MetaOS dock icons missing from the vendored set, in its own style.

The 16 shipped icons (vendored in metaos/, see SOURCES.md) are 128x128 RGBA,
transparent, drawn in three blue tones:
  FILL (0,0,170)  EDGE #1877F2 (24,119,242)  LITE (85,85,255)
This file draws only the glyphs the dock set lacks:
  web, editor, agents, custos (first batch), boards, messages, logo,
  music3d, notes3d, budget (second batch, agent-1). Same canvas, same tones,
  PIL only. No fonts, no randomness: byte-identical on re-run.
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "metaos")
S = 128
FILL = (0, 0, 170, 255)
EDGE = (24, 119, 242, 255)
LITE = (85, 85, 255, 255)


def canvas():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def save(name, img):
    p = os.path.join(DST, name)
    img.save(p)
    print(f"icon: {name} {img.size}")


def web():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((20, 20, 108, 108), outline=EDGE, width=10)
    d.ellipse((28, 28, 100, 100), outline=FILL, width=14)
    d.line((20, 64, 108, 64), fill=LITE, width=6)
    save("web.png", img)


def editor():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.line((66, 22, 30, 64), fill=EDGE, width=13)
    d.line((30, 64, 66, 106), fill=EDGE, width=13)
    d.line((62, 106, 98, 22), fill=LITE, width=11)
    d.line((98, 22, 98, 22), fill=LITE, width=1)
    save("editor.png", img)


def agents():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((20, 20, 108, 108), outline=EDGE, width=10)
    d.ellipse((28, 28, 100, 100), outline=FILL, width=14)
    d.ellipse((52, 52, 76, 76), fill=LITE)
    save("agents.png", img)


def custos():
    img = canvas()
    d = ImageDraw.Draw(img)
    shield = [(64, 14), (104, 30), (104, 64), (64, 112), (24, 64), (24, 30)]
    d.line(shield + [shield[0]], fill=EDGE, width=11, joint="curve")
    d.line((64, 34, 64, 92), fill=FILL, width=16)
    d.line((64, 34, 64, 92), fill=LITE, width=6)
    save("custos.png", img)


def boards():
    """Dispatch boards: four solid tiles, not the dashboard's line grid."""
    img = canvas()
    d = ImageDraw.Draw(img)
    # 2x2 chunky blocks (FILL) with EDGE gutters; top-left block LITE so the
    # tile reads at 40px next to dashboard.png's thin 3x3 grid.
    d.rounded_rectangle((22, 22, 60, 60), radius=8, fill=FILL)
    d.rounded_rectangle((68, 22, 106, 60), radius=8, fill=LITE)
    d.rounded_rectangle((22, 68, 60, 106), radius=8, fill=FILL)
    d.rounded_rectangle((68, 68, 106, 106), radius=8, fill=FILL)
    d.rounded_rectangle((22, 22, 106, 106), radius=10, outline=EDGE, width=6)
    save("boards.png", img)


def messages():
    """Messaging: a speech bubble with text bars, not agents' ring + dot."""
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 26, 108, 88), radius=16, outline=EDGE, width=10)
    d.polygon([(38, 88), (30, 110), (58, 88)], fill=EDGE)
    d.line((36, 46, 92, 46), fill=FILL, width=9)
    d.line((36, 64, 76, 64), fill=FILL, width=9)
    d.line((36, 64, 76, 64), fill=LITE, width=4)
    save("messages.png", img)


def logo():
    """Logo Studio: a canvas frame with an M-stroke inside, no pencil."""
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rectangle((22, 30, 106, 98), outline=EDGE, width=9)
    # M polyline: the studio draws letterforms, the board draws lines.
    m = [(36, 84), (36, 48), (52, 66), (64, 48), (76, 66), (92, 48), (92, 84)]
    d.line(m, fill=FILL, width=11, joint="curve")
    d.line(m, fill=LITE, width=4, joint="curve")
    save("logo.png", img)


def _note(d, ox, oy, body, accent):
    # Quaver: stem + beam + two heads, shifted by (ox, oy) for the 3D offset.
    d.line((78 + ox, 28 + oy, 78 + ox, 78 + oy), fill=body, width=12)
    d.line((78 + ox, 28 + oy, 44 + ox, 40 + oy), fill=body, width=12)
    d.line((44 + ox, 40 + oy, 44 + ox, 84 + oy), fill=body, width=12)
    d.ellipse((24 + ox, 76 + oy, 56 + ox, 100 + oy), fill=body)
    d.ellipse((58 + ox, 70 + oy, 90 + ox, 94 + oy), fill=body)
    d.ellipse((30 + ox, 80 + oy, 50 + ox, 96 + oy), fill=accent)


def music3d():
    """Music 3D: the Musica quaver with a LITE depth ghost behind it."""
    img = canvas()
    d = ImageDraw.Draw(img)
    _note(d, 12, -8, LITE, LITE)
    _note(d, 0, 4, FILL, EDGE)
    save("music3d.png", img)


def notes3d():
    """3D Notes: a stack of two pages, no pencil, no note head."""
    img = canvas()
    d = ImageDraw.Draw(img)
    # Back page (LITE outline, offset up-right), front page (EDGE) with bars.
    d.rounded_rectangle((44, 18, 108, 92), radius=6, outline=LITE, width=8)
    d.rounded_rectangle((20, 36, 84, 110), radius=6, outline=EDGE, width=9)
    d.line((32, 56, 72, 56), fill=FILL, width=8)
    d.line((32, 72, 72, 72), fill=FILL, width=8)
    d.line((32, 88, 58, 88), fill=FILL, width=8)
    d.line((32, 56, 72, 56), fill=LITE, width=3)
    save("notes3d.png", img)


def budget():
    """Agent Budget: ascending bars on an axis, the only chart glyph."""
    img = canvas()
    d = ImageDraw.Draw(img)
    d.line((22, 22, 22, 106), fill=EDGE, width=9)
    d.line((22, 106, 108, 106), fill=EDGE, width=9)
    d.rectangle((34, 74, 52, 102), fill=FILL)
    d.rectangle((60, 56, 78, 102), fill=FILL)
    d.rectangle((86, 34, 104, 102), fill=FILL)
    d.rectangle((86, 34, 104, 48), fill=LITE)
    save("budget.png", img)


def controls():
    """Meta OS Controls: three sliders with their knobs, the plainest possible
    glyph for 'this is the widget set'. Knob positions differ so it does not
    read as a barcode at 32 px."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for i, (y, knob) in enumerate(((32, 40), (64, 82), (96, 58))):
        d.line((24, y, 104, y), fill=EDGE, width=8)
        d.ellipse((knob - 12, y - 12, knob + 12, y + 12), fill=FILL,
                  outline=LITE, width=4)
    save("controls.png", img)


def main():
    os.makedirs(DST, exist_ok=True)
    web()
    editor()
    agents()
    custos()
    boards()
    messages()
    logo()
    music3d()
    notes3d()
    budget()
    controls()


if __name__ == "__main__":
    main()
