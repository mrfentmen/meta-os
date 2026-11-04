#!/usr/bin/env python3
"""Render the Meta theme from its tokens, so it can be reviewed before a boot.

Two sheets are produced next to each other:

    desktop.png   a composed desktop: bar, dock with the real icons, a window
                  with the real window buttons, an OSD and a tooltip
    controls.png  every control the theme styles, at 1x and 2x

Both are COMPOSED PREVIEWS. They are built from the same generated files the
image installs (gtk.css values, xfwm4 svgs, icon PNGs, panel token values), not
from a screenshot of the running system. What they prove is the design; what
they cannot prove is that GTK and xfwm4 paint it the same way. Say so when you
show them to anyone.

    python3 os-build/tools/preview_theme.py            # writes HTML + PNG
    python3 os-build/tools/preview_theme.py --html-only

Chrome is used headless when it is found; without it only the HTML is written,
and the script says so instead of pretending it rendered.
"""
import base64
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
THEME = os.path.join(REPO, "os-build", "iso", "payload-theme")
TOKENS = os.path.join(THEME, "tokens", "meta.tokens.json")
ICONS = os.path.join(THEME, "icons", "metaos")
FRAMES = os.path.join(THEME, "wallpapers", "studio-loop")
OUT = os.path.join(REPO, "os-build", "captures", "preview")

CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

# The twelve dock tiles, in the order the dock installs them.
DOCK = ["dashboard", "agents", "board", "messages", "editor", "notes", "calendar",
        "calculator", "science", "musica", "custos", "officina"]


def load_tokens():
    with open(TOKENS, "r", encoding="utf-8") as fh:
        return json.load(fh)


def data_uri(path):
    mime = "image/png"
    if path.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())


def button_svg(name, state, size):
    """Inline one generated button at an arbitrary size.

    The file on disk is 22 px; inlining lets the sheet show it at 22 and at 66
    from the same source, which is the point of shipping vectors.
    """
    path = os.path.join(THEME, "xfwm4", "%s-%s.svg" % (name, state))
    with open(path, "r", encoding="utf-8") as fh:
        body = fh.read().split(">", 1)[1].rsplit("</svg>", 1)[0]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 22 22">%s</svg>' % (size, size, body))


def icon(name, size):
    path = os.path.join(ICONS, "%s.png" % name)
    if not os.path.exists(path):
        return ""
    return '<img src="%s" width="%d" height="%d">' % (data_uri(path), size, size)


PANEL_XML = os.path.join(THEME, "panel", "xfce4-panel.xml")


def panel_items():
    """[(plugin, {property: value})] in the order the panel loads them."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(PANEL_XML).getroot()
    except Exception as exc:                      # missing file is not fatal
        print("preview: no panel xml (%s) — bar drawn empty" % exc)
        return []
    by_id = {}
    for prop in root.findall("property"):
        if prop.get("name") != "plugins":
            continue
        for plug in prop.findall("property"):
            pid = plug.get("name", "")
            if not pid.startswith("plugin-"):
                continue
            props = {s.get("name"): s.get("value") for s in plug.findall("property")}
            by_id[pid.split("-", 1)[1]] = (plug.get("value"), props)
    ids = root.find(".//property[@name='plugin-ids']")
    order = [v.get("value") for v in ids.findall("value")] if ids is not None else []
    return [by_id[i] for i in order if i in by_id]


def panel_bar(t):
    """Draw the generated top bar, item for item."""
    c, m = t["colour"], t["metric"]
    h, px = m["bar_height"], m["bar_app_px"]
    paper, accent, muted = c["paper"], c["accent"], c["muted"]

    def svg(body, size=16, stroke=None, fill="none"):
        return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="%s" '
                'stroke="%s" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round">%s</svg>'
                % (size, size, fill, stroke or paper, body))

    def pill(inner, bg="rgba(255,255,255,.07)", pad="0 9px"):
        return ('<span style="display:inline-flex;align-items:center;gap:6px;height:%dpx;'
                'padding:%s;border-radius:7px;background:%s;font-size:%dpx">%s</span>'
                % (h - 8, pad, bg, px, inner))

    task_icon = svg('<rect x="4" y="5" width="16" height="14" rx="2"/>'
                    '<path d="M7 10l3 2-3 2"/>', 15)
    win_chip = lambda label, on: pill(
        '%s<span>%s</span>' % (task_icon, label),
        bg="rgba(255,255,255,.20)" if on else "rgba(255,255,255,.06)")
    speaker = svg('<path d="M4 9h4l5-4v14l-5-4H4z" fill="%s" stroke="none"/>'
                  '<path d="M16.5 8.5a6 6 0 0 1 0 7"/>' % paper, 15)
    squares = svg('<rect x="3" y="4" width="18" height="14" rx="2"/>'
                  '<path d="M3 9h18"/>', 16)
    power = svg('<path d="M12 3v9"/><path d="M6.6 6.6a8 8 0 1 0 10.8 0"/>', 16)

    out = []
    for name, props in panel_items():
        if name == "applicationsmenu":
            out.append(pill(icon("logo", 16) + '<b>%s</b>'
                            % (props.get("button-title") or "Meta"),
                            bg="rgba(255,255,255,.12)"))
        elif name == "tasklist":
            out.append(win_chip("Agents", True) + win_chip("Terminal", False))
        elif name == "pager":
            out.append('<span style="display:inline-flex;gap:4px;align-items:center">'
                       '<span style="width:26px;height:16px;border-radius:4px;background:%s;'
                       'color:%s;font-size:9px;display:inline-flex;align-items:center;'
                       'justify-content:center">1</span>'
                       '<span style="width:26px;height:16px;border-radius:4px;background:rgba(255,255,255,.10);'
                       'color:%s;font-size:9px;display:inline-flex;align-items:center;'
                       'justify-content:center">2</span></span>'
                       % (accent, paper, muted))
        elif name == "separator":
            if props.get("expand") == "true":
                out.append('<span style="flex:1"></span>')
            else:
                out.append('<span style="width:1px;height:%dpx;background:rgba(255,255,255,.16)"></span>'
                           % (h - 12))
        elif name == "clock":
            out.append('<span style="opacity:.92">Sat, Nov 1&nbsp;&nbsp;14:32</span>')
        elif name == "pulseaudio-plugin":
            out.append(pill(speaker + '<span style="font-size:%dpx;opacity:.8">68%%</span>'
                            % (px - 2), bg="none", pad="0 6px"))
        elif name == "showdesktop":
            out.append(pill(squares, bg="none", pad="0 6px"))
        elif name == "actions":
            out.append(pill(power, bg="none", pad="0 6px"))
        elif name == "systray":
            out.append('<span style="display:inline-flex;gap:5px;align-items:center;opacity:.55">'
                       '<span style="width:5px;height:5px;border-radius:3px;background:%s"></span>'
                       '<span style="width:5px;height:5px;border-radius:3px;background:%s"></span>'
                       '<span style="width:5px;height:5px;border-radius:3px;background:%s"></span></span>'
                       % (paper, paper, paper))
    return ('<div style="height:%dpx;display:flex;align-items:center;gap:8px;padding:0 10px;'
            'background:%s;color:%s;font-size:%dpx">%s</div>'
            % (h, c["bar_bg"], paper, px, "".join(out)))


def desktop(t):
    c, m, wb = t["colour"], t["metric"], t["window_buttons"]
    frames = sorted(glob.glob(os.path.join(FRAMES, "loop-*.jpg")))
    wall = data_uri(frames[0]) if frames else ""
    bg = ("background-image:url(%s);background-size:cover;background-position:center;" % wall
          if wall else "background:%s;" % c["bg_dark"])

    dock = "".join(
        '<div style="width:%dpx;text-align:center">%s'
        '<div style="font-size:%dpx;color:%s;margin-top:3px;white-space:nowrap">%s</div>'
        '<div style="height:4px;font-size:8px;line-height:4px;color:%s">%s</div></div>'
        % (m["dock_item"], icon(name, m["dock_glyph"]), m["dock_label_px"], c["paper"],
           name.capitalize(), c["accent"], "●" if i < 4 else "&nbsp;")
        for i, name in enumerate(DOCK))

    # The bar is drawn from the generated panel XML, item by item, in the order
    # the panel will load them. A preview that invents its own bar proves
    # nothing about the bar the image installs; this one cannot drift from it.
    bar = panel_bar(t)

    title_buttons = "".join(
        '<span style="margin-left:%dpx">%s</span>' % (wb["spacing"], button_svg(n, "active", wb["size"]))
        for n in ("hide", "maximize", "close"))

    def tab(label, on=False):
        return ('<span style="display:inline-flex;align-items:center;gap:6px;height:%dpx;'
                'padding:0 %dpx;border-radius:%dpx %dpx 0 0;font-size:13px;'
                'background:%s;color:%s;border:1px solid rgba(127,127,127,.3);border-bottom:0;%s">%s'
                '<span style="width:16px;height:16px;border-radius:8px;display:inline-flex;'
                'align-items:center;justify-content:center;font-size:10px;%s">&times;</span></span>'
                % (t["controls"]["tab_h"], t["controls"]["pad_x"],
                   t["controls"]["tab_radius"], t["controls"]["tab_radius"],
                   "rgba(255,255,255,.03)" if on else "rgba(127,127,127,.10)",
                   c["win_fg"] if on else c["muted"],
                   "box-shadow:inset 0 2px 0 %s" % c["accent"] if on else "",
                   label,
                   "background:%s;color:%s" % (c["accent"], c["paper"]) if on else ""))

    window = ('<div style="position:absolute;left:120px;top:120px;width:560px;border-radius:%dpx;'
              'background:%s;border:1px solid rgba(127,127,127,.3);'
              'box-shadow:0 22px 55px rgba(0,0,0,.45);overflow:hidden">'
              '<div style="display:flex;align-items:center;height:34px;padding:0 12px;'
              'background:rgba(255,255,255,.08);border-bottom:1px solid rgba(127,127,127,.3)">'
              '<span style="font-size:13px;font-weight:700;color:%s">Agents</span>'
              '<span style="margin-left:auto;display:flex;align-items:center">%s</span></div>'
              '<div style="padding:0 14px;display:flex;gap:4px;background:rgba(0,0,0,.25)">%s%s%s</div>'
              '<div style="padding:14px 16px;color:%s;font-size:13.5px;line-height:1.55">'
              '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
              '%s%s</div>'
              '<div style="margin-top:12px;display:flex;align-items:center;gap:10px">'
              '%s%s%s</div></div></div>'
              % (m["window_radius"], rgba_hex(c["win_bg"], c["win_bg_alpha"]),
                 c["win_fg"], title_buttons,
                 tab("Runs", True), tab("Fleet"), tab("Receipts"),
                 c["win_fg"],
                 card(t, "JOBS QUEUED", "16"), card(t, "RUNS TODAY", "47"),
                 pill(t, "LIVE", c["accent"]),
                 primary(t, "Submit a job"), ghost(t, "Clear")))

    osd = ('<div style="position:absolute;right:150px;top:180px;width:210px;padding:14px 16px;'
           'background:%s;border:1px solid %s;border-radius:12px;color:%s;'
           'box-shadow:0 18px 40px rgba(0,0,0,.5)">'
           '<div style="font-size:%dpx;font-weight:700;margin-bottom:8px">Volume</div>'
           '<div style="height:6px;border-radius:3px;background:rgba(127,127,127,.18)">'
           '<div style="height:6px;width:64%%;border-radius:3px;background:%s"></div></div></div>'
           % (c["ink"], c["accent"], c["paper"], t["controls"]["osd_px"], c["accent"]))

    tip = ('<div style="position:absolute;left:470px;top:470px;padding:5px 9px;background:%s;'
           'color:%s;border:1px solid %s;border-radius:6px;font-size:11.5px">'
           'Open the run receipt</div>'
           % (c["ink"], c["paper"], c["accent"]))

    dockplate = ('<div style="position:absolute;left:50%%;transform:translateX(-50%%);bottom:%dpx;'
                 'display:flex;gap:%dpx;padding:%dpx %dpx;border-radius:%dpx;'
                 'background:%s;border:1px solid rgba(127,127,127,.25);'
                 'box-shadow:0 14px 40px rgba(0,0,0,.35)">%s</div>'
                 % (m["dock_bottom"], m["dock_gap"], m["dock_pad_y"], m["dock_pad_x"],
                    m["dock_radius"], rgba_hex(c["dock_bg"], c["dock_bg_alpha"]), dock))

    return """<!doctype html><meta charset=utf-8>
<body style="margin:0;width:1600px;height:900px;overflow:hidden;%s
             font-family:%s;color:%s;position:relative">
%s
<div style="position:absolute;left:0;right:0;bottom:0;height:150px;
            background:linear-gradient(to top,rgba(0,0,0,.55),transparent)"></div>
%s%s%s%s
<div style="position:absolute;left:16px;bottom:14px;font:11px %s;color:rgba(255,255,255,.45)">
composed preview from the generated theme files — not a screenshot of the running system</div>
</body>""" % (bg, t["type"]["ui"], c["win_fg"], bar, window, osd, tip, dockplate,
              t["type"]["ui"])


def controls(t):
    c, k, wb = t["colour"], t["controls"], t["window_buttons"]

    def row(label, cell):
        return ('<div style="display:flex;align-items:center;gap:14px;padding:10px 0;'
                'border-bottom:1px solid rgba(127,127,127,.14)">'
                '<div style="width:190px;font-size:11px;color:%s">%s</div>'
                '<div style="display:flex;align-items:center;gap:10px">%s</div></div>'
                % (c["muted"], label, cell))

    def track(width, pct=64):
        return ('<div style="width:%dpx;height:%dpx;border-radius:%dpx;background:rgba(127,127,127,.18)">'
                '<div style="width:%d%%;height:%dpx;border-radius:%dpx;background:%s"></div></div>'
                % (width, k["slider_track"], k["slider_track"] // 2, pct,
                   k["slider_track"], k["slider_track"] // 2, c["accent"]))

    thumb = ('<span style="display:inline-block;width:%dpx;height:%dpx;border-radius:%dpx;'
             'background:%s;border:1px solid %s;margin-left:-10px"></span>'
             % (k["slider_thumb"], k["slider_thumb"], k["slider_thumb"] // 2,
                c["paper"], c["accent"]))

    sw_off = ('<span style="display:inline-block;width:%dpx;height:%dpx;border-radius:%dpx;'
              'background:rgba(127,127,127,.18);border:1px solid %s;position:relative">'
              '<span style="position:absolute;left:2px;top:1px;width:%dpx;height:%dpx;'
              'border-radius:%dpx;background:%s"></span></span>'
              % (k["switch_w"], k["switch_h"], k["switch_h"] // 2, rgba_hex(c["hairline"], .3),
                 k["switch_thumb"], k["switch_thumb"], k["switch_thumb"] // 2, c["paper"]))
    sw_on = ('<span style="display:inline-block;width:%dpx;height:%dpx;border-radius:%dpx;'
             'background:%s;border:1px solid %s;position:relative">'
             '<span style="position:absolute;right:2px;top:1px;width:%dpx;height:%dpx;'
             'border-radius:%dpx;background:%s"></span></span>'
             % (k["switch_w"], k["switch_h"], k["switch_h"] // 2, c["accent"], c["accent"],
                k["switch_thumb"], k["switch_thumb"], k["switch_thumb"] // 2, c["paper"]))

    check = ('<span style="display:inline-flex;align-items:center;justify-content:center;'
             'width:%dpx;height:%dpx;border-radius:5px;background:%s;color:%s;font-size:11px">&#10003;</span>'
             % (k["check_size"], k["check_size"], c["accent"], c["paper"]))
    radio = ('<span style="display:inline-block;width:%dpx;height:%dpx;border-radius:999px;'
             'background:%s;border:4px solid %s;box-sizing:border-box"></span>'
             % (k["check_size"], k["check_size"], c["paper"], c["accent"]))
    unchecked = ('<span style="display:inline-block;width:%dpx;height:%dpx;border-radius:5px;'
                 'background:rgba(127,127,127,.12);border:1px solid %s"></span>'
                 % (k["check_size"], k["check_size"], rgba_hex(c["hairline"], .3)))

    tabs = "".join(
        '<span style="display:inline-flex;align-items:center;gap:8px;height:%dpx;padding:0 %dpx;'
        'border-radius:%dpx %dpx 0 0;font-size:13px;background:%s;color:%s;'
        'border:1px solid rgba(127,127,127,.3);border-bottom:0;%s">%s'
        '<span style="width:16px;height:16px;border-radius:8px;display:inline-flex;'
        'align-items:center;justify-content:center;font-size:10px;background:%s;color:%s">&times;</span></span>'
        % (k["tab_h"], k["pad_x"], k["tab_radius"], k["tab_radius"],
           "rgba(14,16,22,.92)" if on else "rgba(127,127,127,.10)",
           c["win_fg"] if on else c["muted"],
           "box-shadow:inset 0 2px 0 %s" % c["accent"] if on else "",
           name, c["accent"] if on else "transparent", c["paper"] if on else c["muted"])
        for name, on in (("Runs", True), ("Fleet", False), ("Receipts", False)))

    def btn(label, kind):
        base = {
            "default": "background:rgba(127,127,127,.12);color:%s;border:1px solid %s" % (c["win_fg"], rgba_hex(c["hairline"], .3)),
            "primary": "background:%s;color:%s;border:1px solid %s" % (c["accent"], c["paper"], c["accent"]),
            "destructive": "background:%s;color:%s;border:1px solid %s" % (c["urgent"], c["paper"], c["urgent"]),
            "flat": "background:transparent;color:%s;border:1px solid transparent" % c["win_fg"],
            "disabled": "background:rgba(127,127,127,.08);color:%s;border:1px solid %s;opacity:.5"
                        % (c["muted"], rgba_hex(c["hairline"], .2)),
        }[kind]
        return ('<span style="display:inline-flex;align-items:center;height:%dpx;padding:0 %dpx;'
                'border-radius:%dpx;font-size:13px;font-weight:600;%s">%s</span>'
                % (k["height"], k["pad_x"], k["radius"], base, label))

    entry = ('<span style="display:inline-flex;align-items:center;height:%dpx;padding:0 %dpx;'
             'border-radius:10px;background:rgba(127,127,127,.12);color:%s;'
             'border:1px solid %s;font-size:13px;min-width:220px">Submit a job to the fleet</span>'
             % (k["height"], k["pad_x"], c["muted"], rgba_hex(c["hairline"], .3)))
    entry_focus = ('<span style="display:inline-flex;align-items:center;height:%dpx;padding:0 %dpx;'
                   'border-radius:10px;background:rgba(127,127,127,.12);color:%s;'
                   'border:1px solid %s;box-shadow:0 0 0 %dpx %s;font-size:13px;min-width:220px">'
                   'focused entry</span>'
                   % (k["height"], k["pad_x"], c["win_fg"], c["accent"], k["focus_ring"],
                      rgba_hex(c["accent"], .35)))

    badges = "".join(pill(t, label, col) for label, col in
                     (("LIVE", c["accent"]), ("QUEUED", c["muted"]), ("FAILED", c["urgent"])))

    winbtns = "".join(
        '<div style="text-align:center;margin-right:22px">'
        '<div>%s %s %s</div><div style="font-size:10.5px;color:%s;margin-top:5px">%s</div></div>'
        % (button_svg("hide", s, 44), button_svg("maximize", s, 44),
           button_svg("close", s, 44), c["muted"], s)
        for s in ("active", "prelight", "pressed", "toggled", "inactive"))

    return """<!doctype html><meta charset=utf-8>
<body style="margin:0;padding:26px 30px;background:%s;font-family:%s;color:%s">
<div style="font:700 20px %s">Meta OS control set</div>
<div style="font-size:13px;color:%s;margin:4px 0 18px">
generated from meta.tokens.json — every control the theme styles, so nothing an app shows arrives in Adwaita</div>
<div style="display:flex;gap:40px;align-items:flex-start">
<div style="flex:1">
%s%s%s%s%s%s%s%s%s%s%s%s%s
</div>
<div style="width:520px">
<div style="font-size:11px;color:%s;margin-bottom:8px">window buttons — close black, minimise white, maximise blue</div>
<div style="display:flex">%s</div>
<div style="font-size:11px;color:%s;margin:20px 0 8px">dock tile states — rest / running / urgent</div>
<div style="display:flex;gap:14px;align-items:center">%s%s%s</div>
<div style="font-size:11px;color:%s;margin:20px 0 8px">badges</div>
<div style="display:flex;gap:8px">%s</div>
<div style="font-size:11px;color:%s;margin:20px 0 8px">tooltip</div>
<div style="display:inline-block;padding:5px 9px;background:%s;color:%s;border:1px solid %s;border-radius:6px;font-size:11.5px">Open the run receipt</div>
</div></div>
<div style="margin-top:16px;font:11px %s;color:rgba(255,255,255,.4)">
composed preview from the generated theme files — GTK paints these values; this sheet is the spec, not a screenshot</div>
</body>""" % (
        c["bg_dark"], t["type"]["ui"], c["win_fg"], t["type"]["ui"], c["muted"],
        row("button — default", btn("Default", "default")),
        row("button — primary", btn("Submit a job", "primary")),
        row("button — destructive", btn("Purge queue", "destructive")),
        row("button — flat / icon", btn("&#8942;", "flat") + btn("&#8635;", "flat")),
        row("button — disabled", btn("Disabled", "disabled")),
        row("entry — rest / focused", entry + entry_focus),
        row("switch — off / on", sw_off + sw_on),
        row("check / radio / unchecked", check + radio + unchecked),
        row("slider", track(220, 64) + thumb),
        row("tabs (close button on each)", tabs),
        row("progress", track(220, 38)),
        row("list row — hover / selected",
            '<span style="padding:6px 10px;border-radius:8px;background:rgba(127,127,127,.10);font-size:13px">hover row</span>'
            '<span style="padding:6px 10px;border-radius:8px;background:%s;color:%s;font-size:13px">selected row</span>'
            % (c["accent"], c["paper"])),
        row("card", card(t, "RUNS TODAY", "47", wide=True)),
        c["muted"], winbtns, c["muted"],
        tile(t, "dashboard", "rest"), tile(t, "dashboard", "running"), tile(t, "dashboard", "urgent"),
        c["muted"], badges, c["muted"], c["ink"], c["paper"], c["accent"],
        t["type"]["ui"])


def rgba_hex(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "rgba(%d,%d,%d,%s)" % (r, g, b, ("%.2f" % alpha).rstrip("0").rstrip("."))


def card(t, label, value, wide=False):
    c = t["colour"]
    return ('<div style="border:1px solid %s;border-radius:%dpx;padding:10px 12px;%s">'
            '<div style="font-size:12px;letter-spacing:.06em;color:%s;text-transform:uppercase">%s</div>'
            '<div style="font-size:20px;font-weight:700;color:%s">%s</div></div>'
            % (rgba_hex(c["hairline"], .3), t["controls"]["radius"],
               "min-width:200px" if wide else "", c["muted"], label, c["win_fg"], value))


def pill(t, label, colour):
    c = t["colour"]
    return ('<span style="font-size:%dpx;font-weight:700;padding:1px 6px;border-radius:%dpx;'
            'border:1px solid %s;color:%s">%s</span>'
            % (t["controls"]["badge_px"], t["controls"]["badge_radius"], colour, colour, label))


def primary(t, label):
    c, k = t["colour"], t["controls"]
    return ('<span style="display:inline-flex;align-items:center;height:%dpx;padding:0 %dpx;'
            'border-radius:%dpx;background:%s;color:%s;font-size:13px;font-weight:600">%s</span>'
            % (k["height"], k["pad_x"], k["radius"], c["accent"], c["paper"], label))


def ghost(t, label):
    c, k = t["colour"], t["controls"]
    return ('<span style="display:inline-flex;align-items:center;height:%dpx;padding:0 %dpx;'
            'border-radius:%dpx;background:transparent;color:%s;font-size:13px">%s</span>'
            % (k["height"], k["pad_x"], k["radius"], c["muted"], label))


def tile(t, name, state):
    c, m = t["colour"], t["metric"]
    ring = {"rest": "1px solid rgba(127,127,127,.3)",
            "running": "1px solid %s" % c["accent"],
            "urgent": "1px solid %s" % c["urgent"]}[state]
    dot = '<span style="display:inline-block;width:4px;height:4px;border-radius:2px;background:%s"></span>' % (
        c["urgent"] if state == "urgent" else c["accent"])
    return ('<div style="text-align:center"><div style="width:%dpx;height:%dpx;border-radius:%dpx;'
            'border:%s;display:flex;align-items:center;justify-content:center;background:%s">%s</div>'
            '<div style="margin-top:3px">%s</div></div>'
            % (m["dock_glyph"], m["dock_glyph"], m["dock_glyph"] // 4, ring,
               "rgba(255,255,255,.04)", icon(name, m["dock_glyph"] - 8), dot))


def shoot(html_path, png_path, width, height, scale=2):
    chrome = next((p for p in CHROME if os.path.exists(p)), None)
    if chrome is None:
        return "no Chrome found: wrote %s only" % os.path.basename(html_path)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--window-size=%d,%d" % (width, height),
           "--force-device-scale-factor=%d" % scale,
           "--screenshot=%s" % png_path, "file://" + html_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(png_path):
        return "Chrome failed for %s: %s" % (os.path.basename(html_path),
                                             (res.stderr or "").strip().splitlines()[-1:])
    return "rendered %s" % os.path.basename(png_path)


def main(argv):
    t = load_tokens()
    os.makedirs(OUT, exist_ok=True)
    html_only = "--html-only" in argv
    jobs = [("desktop", desktop, 1600, 900, 2), ("controls", controls, 1180, 900, 2)]
    for name, fn, w, h, scale in jobs:
        path = os.path.join(OUT, "%s.html" % name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn(t))
        print("wrote %s" % path)
        if html_only:
            continue
        print(shoot(path, os.path.join(OUT, "%s.png" % name), w, h, scale))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
