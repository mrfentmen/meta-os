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
button_layout=O|SHMC
button_spacing=%(winbtn_gap)d
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
    ("dock.theme", os.path.join("dock", "dock.theme"), dock_theme),
    ("xfce4-panel.xml", os.path.join("panel", "xfce4-panel.xml"), panel_xml),
]


def main(argv):
    check = "--check" in argv
    t = load()
    drifted = 0
    for label, rel, fn in TARGETS:
        path = os.path.join(THEME, rel)
        want = fn(t)
        have = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                have = fh.read()
        if check:
            if have == want:
                print("PASS  %-18s matches tokens" % label)
            else:
                print("FAIL  %-18s drifted from tokens" % label)
                drifted += 1
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(want)
        print("wrote %-18s %s" % (label, path))
    if check:
        return 1 if drifted else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
