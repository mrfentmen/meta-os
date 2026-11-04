#!/usr/bin/env python3
"""Generate the native Meta OS theme from one token file.

Writes, next to this repo's payload-theme tree:

    gtk/gtk.css                 the GTK3 stylesheet
    xfwm4/themerc               window-manager colours and button layout
    dock/dock.theme             plank theme
    panel/xfce4-panel.xml       the 30 px top bar

Every number and colour comes from meta.tokens.json. Nothing here invents a
value, because a theme that is hand-edited in four places is a theme that
contradicts itself — which is exactly how this project ended up with a
#1877F2 bar in one file and a #4f7ec2 accent in the reference.

    python3 os-build/iso/payload-theme/tokens/gen_theme.py
    python3 os-build/iso/payload-theme/tokens/gen_theme.py --check   # no writes

Exit 1 on --check when a generated file on disk differs from what the tokens say.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.dirname(HERE)              # .../payload-theme
TOKENS = os.path.join(HERE, "meta.tokens.json")


def load():
    with open(TOKENS, "r", encoding="utf-8") as fh:
        return json.load(fh)


def rgba(hex_colour, alpha):
    """#rrggbb + 0..1 alpha -> rgba(r, g, b, a) for GTK3 CSS."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    a = ("%.2f" % alpha).rstrip("0").rstrip(".")
    return "rgba(%d, %d, %d, %s)" % (r, g, b, a or "0")


def plank_colour(hex_colour, alpha):
    """plank wants r;;g;;b;;a with every channel 0..255."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "%d;;%d;;%d;;%d" % (r, g, b, round(alpha * 255))


def gtk_css(t):
    c, m, ty, sh = t["colour"], t["metric"], t["type"], t["shadow"]
    win_shadow = "0 %dpx %dpx %s" % (
        sh["window"]["y"], sh["window"]["blur"], rgba("#000000", sh["window"]["alpha"]))
    bar_shadow = "0 %dpx %dpx %s" % (
        sh["bar"]["y"], sh["bar"]["blur"], rgba("#000000", sh["bar"]["alpha"]))
    dock_shadow = "0 %dpx %dpx %s" % (
        sh["dock"]["y"], sh["dock"]["blur"], rgba("#000000", sh["dock"]["alpha"]))
    return """/* GENERATED FILE — do not edit.
 * Source: os-build/iso/payload-theme/tokens/meta.tokens.json
 * Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py
 * Verify:     python3 os-build/iso/payload-theme/tokens/gen_theme.py --check
 *
 * Reference: face/face.css (the desktop the boss approved). Two deliberate
 * differences from the browser: no backdrop blur (GTK3 cannot do it at a sane
 * cost) and no CSS animation on hover (GTK3 toggles, it does not tween).
 */
@define-color meta_accent %(accent)s;
@define-color meta_accent_deep %(accent_deep)s;
@define-color meta_accent_bright %(accent_bright)s;
@define-color meta_ink %(ink)s;
@define-color meta_paper %(paper)s;
@define-color meta_muted %(muted)s;
@define-color meta_bg %(bg_dark)s;
@define-color meta_window %(win_bg)s;
@define-color meta_win_fg %(win_fg)s;
@define-color meta_hairline %(hairline_rgba)s;

* {
  font-family: %(ui)s;
  outline-color: @meta_accent;
  outline-style: solid;
  outline-width: 1px;
  -GtkWidget-focus-padding: 0;
  -GtkWidget-focus-line-width: 1px;
}

/* ---- windows ------------------------------------------------------- */
window, .background {
  background-color: @meta_window;
  color: @meta_win_fg;
  border-radius: %(window_radius)dpx;
}

/* X11 has no rounded corners without a compositor, so the radius is a request,
   not a guarantee. The hairline is what actually reads as a window edge. */
decoration {
  border-radius: %(window_radius)dpx %(window_radius)dpx 0 0;
  box-shadow: %(win_shadow)s;
  border: %(window_border)dpx solid %(hairline_rgba)s;
}

headerbar, .titlebar {
  background-color: %(win_bar_rgba)s;
  background-image: none;
  color: @meta_win_fg;
  padding: %(titlebar_pad_y)dpx %(titlebar_pad_x)dpx;
  border-bottom: 1px solid %(hairline_rgba)s;
  box-shadow: none;
  min-height: 0;
}
headerbar title, .titlebar .title {
  font-size: %(titlebar_px)spx;
  font-weight: 700;
}
headerbar button, .titlebar button {
  min-width: %(winbtn)dpx;
  min-height: %(winbtn)dpx;
  padding: 0;
  margin-left: %(winbtn_gap)dpx;
  border-radius: %(winbtn_half)dpx;
  border: 1px solid %(hairline_rgba)s;
  background-image: none;
  background-color: %(win_btn_rgba)s;
  color: inherit;
}

/* ---- content ------------------------------------------------------- */
textview, textview text, .view {
  background-color: @meta_window;
  color: @meta_win_fg;
  font-size: %(winbody_px)spx;
}
label { color: inherit; }

entry, spinbutton, textview.frame {
  background-color: %(entry_rgba)s;
  color: inherit;
  border: 1px solid %(hairline_rgba)s;
  border-radius: 10px;
  padding: 6px 9px;
}
entry:focus, spinbutton:focus { border-color: @meta_accent; }

button {
  background-image: none;
  background-color: %(button_rgba)s;
  color: inherit;
  border: 1px solid %(hairline_rgba)s;
  border-radius: 9px;
  padding: 6px 12px;
}
button:hover { background-color: %(button_hover_rgba)s; }
button:active, button:checked { background-color: @meta_accent; color: @meta_paper; }
button.suggested-action { background-color: @meta_accent; color: @meta_paper; }
button.destructive-action { background-color: %(urgent)s; color: @meta_paper; }

menu, .menu, popover, .popover {
  background-color: %(win_bg_opaque)s;
  color: @meta_win_fg;
  border: 1px solid %(hairline_rgba)s;
  border-radius: 10px;
  padding: 4px;
}
menuitem:hover, .menu menuitem:hover, popover modelbutton:hover {
  background-color: @meta_accent;
  color: @meta_paper;
}

*:selected, *:selected:focus, row:selected {
  background-color: @meta_accent;
  color: @meta_paper;
}
tooltip, tooltip.background {
  background-color: @meta_ink;
  color: @meta_paper;
  border: 1px solid @meta_accent;
  border-radius: 6px;
}

scrollbar slider {
  background-color: %(slider_rgba)s;
  border-radius: 999px;
  min-width: 6px;
  min-height: 6px;
}
scrollbar slider:hover { background-color: @meta_accent; }

separator { background-color: %(hairline_rgba)s; min-width: 1px; min-height: 1px; }

/* The plank dock and the panel paint themselves; these rules exist so GTK apps
   launched from them do not arrive in the base theme's grey. */
.xfce4-panel { font-size: %(bar_app_px)spx; }
""" % {
        "accent": c["accent"],
        "accent_deep": c["accent_deep"],
        "accent_bright": c["accent_bright"],
        "ink": c["ink"],
        "paper": c["paper"],
        "muted": c["muted"],
        "bg_dark": c["bg_dark"],
        "win_bg": rgba(c["win_bg"], c["win_bg_alpha"]),
        "win_bg_opaque": c["win_bg"],
        "win_fg": c["win_fg"],
        "hairline_rgba": rgba(c["hairline"], c["hairline_alpha"]),
        "win_bar_rgba": rgba(c["win_bar"], c["win_bar_alpha"]),
        "win_btn_rgba": rgba(c["hairline"], 0.25),
        "entry_rgba": rgba(c["hairline"], 0.12),
        "button_rgba": rgba(c["hairline"], 0.12),
        "button_hover_rgba": rgba(c["hairline"], 0.22),
        "slider_rgba": rgba(c["hairline"], 0.45),
        "urgent": c["urgent"],
        "window_radius": m["window_radius"],
        "window_border": m["window_border"],
        "titlebar_pad_y": m["titlebar_pad_y"],
        "titlebar_pad_x": m["titlebar_pad_x"],
        "titlebar_px": m["titlebar_px"],
        "winbtn": m["winbtn"],
        "winbtn_half": m["winbtn"] // 2,
        "winbtn_gap": m["winbtn_gap"],
        "winbody_px": m["winbody_px"],
        "bar_app_px": m["bar_app_px"],
        "ui": ty["ui"],
        "win_shadow": win_shadow,
    }



# ---------------------------------------------------------------- buttons
#
# xfwm4 draws a button ONLY if the theme dir has an image for it. A themes/
# MetaOS/xfwm4 that contains themerc and nothing else renders an empty titlebar —
# which is the "there is no x, no -, no +" report, and it cannot be fixed by
# changing the layout string alone.
#
# Geometry per button is 22x22 with the glyph on a 22-unit grid, drawn as SVG so
# one file is crisp at every scale factor and there is no second raster copy to
# drift from it.
BUTTON_GLYPHS = {
    # name: (state -> list of svg path/shape strings)
    "close": {
        "active": ["M7.2 7.2 L14.8 14.8", "M14.8 7.2 L7.2 14.8"],
        "inactive": ["M7.2 7.2 L14.8 14.8", "M14.8 7.2 L7.2 14.8"],
        "prelight": ["M7.2 7.2 L14.8 14.8", "M14.8 7.2 L7.2 14.8"],
        "pressed": ["M7.2 7.2 L14.8 14.8", "M14.8 7.2 L7.2 14.8"],
        "toggled": ["M7.2 7.2 L14.8 14.8", "M14.8 7.2 L7.2 14.8"],
    },
    "maximize": {
        # a plus, because that is what the boss asked for and what reads as
        # "fill the screen" at 22 px on a dark bar
        "active": ["M11 6.4 L11 15.6", "M6.4 11 L15.6 11"],
        "inactive": ["M11 6.4 L11 15.6", "M6.4 11 L15.6 11"],
        "prelight": ["M11 6.4 L11 15.6", "M6.4 11 L15.6 11"],
        "pressed": ["M11 6.4 L11 15.6", "M6.4 11 L15.6 11"],
        # toggled = already maximised, so the glyph becomes the restore box
        "toggled": ["M7.4 7.4 L14.6 7.4 L14.6 14.6 L7.4 14.6 Z"],
    },
    "hide": {
        "active": ["M6.4 11 L15.6 11"],
        "inactive": ["M6.4 11 L15.6 11"],
        "prelight": ["M6.4 11 L15.6 11"],
        "pressed": ["M6.4 11 L15.6 11"],
        "toggled": ["M6.4 11 L15.6 11"],
    },
}

# state -> (disc fill, glyph stroke). The fills are the hairline token at the
# opacities the reference uses for a button at rest, hovered and pressed; the
# glyph is the window foreground until the fill turns accent, then paper.
BUTTON_COLOURS = {
    "active": ("hairline", 0.25, "win_fg"),
    "inactive": ("hairline", 0.15, "muted"),
    "prelight": ("accent", 1.0, "paper"),
    "pressed": ("accent_deep", 1.0, "paper"),
    "toggled": ("accent_deep", 0.85, "paper"),
}


def _hex_alpha(t, key, alpha):
    """token colour name + alpha -> #rrggbbaa, which SVG takes directly."""
    h = t["colour"][key].lstrip("#")
    return "#%s%02x" % (h, int(round(max(0.0, min(1.0, alpha)) * 255)))


def svg_button(name, state, t):
    wb, c = t["window_buttons"], t["colour"]
    size = wb["size"]
    fill_key, fill_alpha, glyph_key = BUTTON_COLOURS[state]
    fill = _hex_alpha(t, fill_key, fill_alpha)
    glyph = c[glyph_key] if glyph_key in c else c["win_fg"]
    glyphs = BUTTON_GLYPHS[name][state]
    paths = "".join(
        '  <path d="%s" fill="none" stroke="%s" stroke-width="%s" '
        'stroke-linecap="round"/>\n'
        % (d, glyph, wb["glyph_stroke"])
        if not d.rstrip().endswith("Z") else
        '  <path d="%s" fill="none" stroke="%s" stroke-width="%s" '
        'stroke-linejoin="round"/>\n'
        % (d, glyph, wb["glyph_stroke"])
        for d in glyphs)
    half = size / 2.0
    return (
        '<!-- GENERATED FILE — do not edit.\n'
        '     Source: tokens/meta.tokens.json (window_buttons)\n'
        '     %s button, %s state, %spx disc.\n'
        '     Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py -->\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d">\n'
        '  <circle cx="%s" cy="%s" r="%s" fill="%s"/>\n'
        '%s</svg>\n'
    ) % (name, state, size, size, size, size, size,
         half, half, half, fill, paths)


def _parse_paths(glyphs, scale):
    """Turn the tiny subset of SVG path syntax used above into polylines.

    Only M/L/Z, absolute, which is all the glyphs are. Written out rather than
    pulled from a library because the PNG fallback has to be drawn from exactly
    the same numbers as the SVG — that is the whole point of having two.
    """
    import re as _re
    out = []
    for d in glyphs:
        numbers = _re.findall(r"[MLZ]|-?\d+(?:\.\d+)?", d)
        points, cmd, buf, closed = [], None, [], False
        for token in numbers:
            if token in ("M", "L", "Z"):
                if buf:
                    points.append((float(buf[0]) * scale, float(buf[1]) * scale))
                    buf = []
                cmd = token
                if token == "Z":
                    closed = True
                continue
            buf.append(token)
            if len(buf) == 2:
                points.append((float(buf[0]) * scale, float(buf[1]) * scale))
                buf = []
        if len(points) >= 2:
            out.append((points, closed))
    return out


def png_button(name, state, t, supersample=4):
    """Raster twin of svg_button(), same geometry.

    xfwm4 loads a button through GdkPixbuf, and GdkPixbuf can only read SVG when
    the rsvg pixbuf loader is installed. On a system image that has not got it,
    an SVG-only theme renders an EMPTY titlebar — the exact bug this change is
    fixing, reintroduced by a package that might not be there. So both formats
    ship, drawn from one set of coordinates.
    """
    from PIL import Image, ImageDraw
    wb = t["window_buttons"]
    size = int(wb["size"])
    scale = supersample
    px = size * scale
    fill_key, fill_alpha, glyph_key = BUTTON_COLOURS[state]
    h = t["colour"][fill_key].lstrip("#")
    disc = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (
        int(round(max(0.0, min(1.0, fill_alpha)) * 255)),)
    g = t["colour"][glyph_key].lstrip("#")
    ink = tuple(int(g[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    half = px / 2.0
    draw.ellipse((0, 0, px - 1, px - 1), fill=disc)
    width = max(1, int(round(wb["glyph_stroke"] * scale)))
    cap = max(1, width // 2)
    for points, closed in _parse_paths(BUTTON_GLYPHS[name][state], scale):
        pts = list(points)
        if closed:
            pts.append(points[0])
        draw.line(pts, fill=ink, width=width, joint="curve")
        for x, y in (pts[0], pts[-1]):
            draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=ink)
    return img.resize((size, size), Image.LANCZOS)


def xfwm4_channel(t):
    """The xfconf channel, so xfconf and themerc cannot disagree.

    xfwm4 reads button_layout from xfconf FIRST and only falls back to the
    theme's themerc. The image shipped themerc=O|SHMC while meta-desktop.sh
    wrote CM| into this channel at login, so the theme's buttons never appeared
    and the window had close+maximise on the left with no minimise anywhere.
    Both are now generated from one token.
    """
    wb = t["window_buttons"]
    return """<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED FILE — do not edit.
     Source: os-build/iso/payload-theme/tokens/meta.tokens.json
     Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py
     Install: /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml

     xfconf wins over the theme's themerc, so this file is the one that decides
     which window buttons exist. Keeping it generated means the layout here and
     button_layout in themerc are the same string by construction. -->
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="%(name)s"/>
    <property name="button_layout" type="string" value="%(layout)s"/>
    <property name="title_alignment" type="string" value="center"/>
    <property name="title_font" type="string" value="%(font)s"/>
  </property>
</channel>
""" % {"name": t["theme_name"], "layout": wb["layout"],
       "font": "%(x)s" % {"x": "Inter Bold 10"}}


def xfwm4_themerc(t):
    c, m = t["colour"], t["metric"]
    # xfwm4 draws a flat titlebar from two colours, so the "glass" titlebar is
    # approximated by a dark tint of the window background plus the accent
    # underline on focus. Stated here so nobody hunts for a gradient that the
    # window manager cannot render.
    return """# GENERATED FILE — do not edit.
# Source: os-build/iso/payload-theme/tokens/meta.tokens.json
# Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py
# Install: /usr/share/themes/%(name)s/xfwm4/themerc
#
# xfwm4 renders flat titlebars from colour pairs; there is no gradient and no
# backdrop blur. The reference's glass titlebar is approximated by the window
# background tint plus the accent on the focused title.
button_layout=%(layout)s
button_spacing=%(btn_spacing)d
button_offset=%(btn_spacing)d
title_horizontal_offset=%(titlebar_pad_x)d
title_vertical_offset_active=%(titlebar_pad_y)d
title_vertical_offset_inactive=%(titlebar_pad_y)d
title_alignment=center

active_text_color=%(win_fg)s
inactive_text_color=%(muted)s

active_color_1=%(title_bg)s
active_color_2=%(title_bg)s
active_hilight_1=%(accent)s
active_hilight_2=%(accent_deep)s
active_mid_color_1=%(title_bg)s
active_mid_color_2=%(title_bg)s
active_shadow_1=%(ink)s
active_shadow_2=%(ink)s

inactive_color_1=%(title_bg)s
inactive_color_2=%(title_bg)s
inactive_hilight_1=%(hairline)s
inactive_hilight_2=%(hairline)s
inactive_mid_color_1=%(title_bg)s
inactive_mid_color_2=%(title_bg)s
inactive_shadow_1=%(ink)s
inactive_shadow_2=%(ink)s

title_shadow_active=%(ink)s
title_shadow_inactive=%(ink)s
""" % {
        "name": t["theme_name"],
        "layout": t["window_buttons"]["layout"],
        "btn_spacing": t["window_buttons"]["spacing"],
        "winbtn_gap": m["winbtn_gap"],
        "titlebar_pad_x": m["titlebar_pad_x"],
        "titlebar_pad_y": m["titlebar_pad_y"],
        "win_fg": c["win_fg"],
        "muted": c["muted"],
        "accent": c["accent"],
        "accent_deep": c["accent_deep"],
        "ink": c["ink"],
        "hairline": c["hairline"],
        # The titlebar tint: the window background blended toward the ink, so
        # it stays the same family as the body instead of a second colour.
        "title_bg": c["win_bg"],
    }


def dock_theme(t):
    c = t["colour"]
    return """# GENERATED FILE — do not edit.
# Source: os-build/iso/payload-theme/tokens/meta.tokens.json
# Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py
# Install: /usr/share/plank/themes/%(name)s/dock.theme
#
# The reference dock is a 72%%-opaque plate with a 1 px hairline and a soft
# shadow. Plank takes colours as r;;g;;b;;a with 0..255 channels, so the alpha
# column below is the same 0..1 token multiplied by 255.
[PlankTheme]
TopColor=%(dock_bg)s
BottomColor=%(dock_bg)s
LineColor=%(hairline)s
FillStartColor=%(dock_bg)s
FillEndColor=%(dock_bg)s
InnerStrokeColor=%(hairline)s
OuterStrokeColor=%(hairline)s
UrgentDotColor=%(urgent)s
LaunchBounceTime=%(hover_ms)d
FadeOpacity=1
IconShadow=1
""" % {
        "name": t["theme_name"],
        "dock_bg": plank_colour(c["dock_bg"], c["dock_bg_alpha"]),
        "hairline": plank_colour(c["hairline"], c["hairline_alpha"]),
        "urgent": plank_colour(c["urgent"], 1.0),
        "hover_ms": t["metric"]["hover_ms"],
    }


def panel_xml(t):
    c, m = t["colour"], t["metric"]
    bar_rgba = rgba(c["bar_bg"], 0.96)
    return """<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED FILE — do not edit.
     Source: os-build/iso/payload-theme/tokens/meta.tokens.json
     Regenerate: python3 os-build/iso/payload-theme/tokens/gen_theme.py

     Meta top bar: a 30 px full-width strip, black at 96%%, the Meta mark and
     name on the left, the clock centred, network and theme mode on the right.

     Centring is done with two expanding separators, not by a "centre" property
     — Xfce panels have no such thing, and a clock placed between two stretchy
     separators is the only way to keep it centred as window buttons grow. -->
<channel name="xfce4-panel" version="1.0">
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=8;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="size" type="uint" value="%(bar_height)d"/>
      <property name="background-style" type="uint" value="1"/>
      <property name="background-rgba" type="array">
        <value type="double" value="%(bar_r)s"/>
        <value type="double" value="%(bar_g)s"/>
        <value type="double" value="%(bar_b)s"/>
        <value type="double" value="0.96"/>
      </property>
      <property name="orientation" type="uint" value="0"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu"/>
    <property name="plugin-2" type="string" value="tasklist"/>
    <property name="plugin-3" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-4" type="string" value="clock">
      <property name="digital-layout" type="uint" value="3"/>
      <property name="digital-time-format" type="string" value="%%a, %%b %%e %%H:%%M"/>
    </property>
    <property name="plugin-5" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-6" type="string" value="systray"/>
  </property>
</channel>
""" % {
        "bar_height": m["bar_height"],
        "bar_r": "%.3f" % (int(c["bar_bg"][1:3], 16) / 255),
        "bar_g": "%.3f" % (int(c["bar_bg"][3:5], 16) / 255),
        "bar_b": "%.3f" % (int(c["bar_bg"][5:7], 16) / 255),
        "bar_rgba": bar_rgba,
    }


TARGETS = [
    ("gtk.css", os.path.join("gtk", "gtk.css"), gtk_css),
    ("themerc", os.path.join("xfwm4", "themerc"), xfwm4_themerc),
    ("xfwm4.xml", os.path.join("xfwm4", "xfwm4.xml"), xfwm4_channel),
    ("dock.theme", os.path.join("dock", "dock.theme"), dock_theme),
    ("xfce4-panel.xml", os.path.join("panel", "xfce4-panel.xml"), panel_xml),
]


def button_targets(t):
    """Every <name>-<state>.svg xfwm4 will look for, one per file.

    xfwm4 resolves a button by name and state; a miss is not an error, it is a
    blank space where the button should be, which is why this list is generated
    from the token's own state list instead of being typed twice.
    """
    out = []
    for name in sorted(BUTTON_GLYPHS):
        for state in t["window_buttons"]["states"]:
            out.append(("%s-%s.svg" % (name, state),
                        os.path.join("xfwm4", "%s-%s.svg" % (name, state)),
                        (lambda n, s: (lambda cfg: svg_button(n, s, cfg)))(name, state)))
    return out


def png_targets(t):
    """Same buttons as PNG, for an image without the SVG pixbuf loader."""
    out = []
    for name in sorted(BUTTON_GLYPHS):
        for state in t["window_buttons"]["states"]:
            out.append(("%s-%s.png" % (name, state),
                        os.path.join("xfwm4", "%s-%s.png" % (name, state)),
                        (lambda n, s: (lambda cfg: png_button(n, s, cfg)))(name, state)))
    return out


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main(argv):
    check = "--check" in argv
    t = load()
    drifted = 0
    written = 0
    targets = TARGETS + button_targets(t) + png_targets(t)
    for label, rel, fn in targets:
        path = os.path.join(THEME, rel)
        is_png = label.endswith(".png")
        if check:
            fresh = fn(t)
            ok = os.path.exists(path)
            if ok and is_png:
                # Re-render and compare bytes: a PNG that differs is a hand-edit
                # or a stale copy from before a token change.
                import io as _io
                buf = _io.BytesIO()
                fresh.save(buf, format="PNG")
                with open(path, "rb") as fh:
                    ok = fh.read() == buf.getvalue()
            elif ok:
                with open(path, "r", encoding="utf-8") as fh:
                    ok = fh.read() == fresh
            if ok:
                print("PASS  %-20s matches tokens" % label)
            else:
                print("FAIL  %-20s %s" % (label, "missing" if not os.path.exists(path) else "drifted from tokens"))
                drifted += 1
            continue
        if is_png:
            img = fn(t)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path, format="PNG")
        else:
            write_text(path, fn(t))
        written += 1
        if written <= 6 or written % 15 == 0:
            print("wrote %-20s %s" % (label, path))
    if check:
        return 1 if drifted else 0
    print("wrote %d files from one token set" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
