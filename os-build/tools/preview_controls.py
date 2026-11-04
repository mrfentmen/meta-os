#!/usr/bin/env python3
"""Render the Meta OS control set to a PNG, from the theme tokens.

This is a SPEC SHEET, not a screenshot of the running OS: GTK3 cannot run on
macOS, so the sheet is drawn in the browser from the same numbers xfwm4 and
GTK will receive. Every colour and size is read out of
os-build/iso/payload-theme/tokens/meta.tokens.json — if the sheet and the theme
disagree, the tokens are the truth and the sheet is the bug.

The window buttons are not redrawn: the real SVG files from xfwm4/ are embedded
inline, so the sheet cannot drift from the art the window manager loads.

    python3 os-build/tools/preview_controls.py            # writes a capture
    python3 os-build/tools/preview_controls.py --open      # …and opens it

Output: os-build/captures/theme-controls-<UTC stamp>.png
Requires: Google Chrome (headless) for the raster step.
"""
import base64
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
THEME = os.path.join(REPO, "os-build", "iso", "payload-theme")
TOKENS = os.path.join(THEME, "tokens", "meta.tokens.json")
XFWM = os.path.join(THEME, "xfwm4")
OUTDIR = os.path.join(REPO, "os-build", "captures")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def load():
    with open(TOKENS, "r", encoding="utf-8") as fh:
        return json.load(fh)


def svg_inline(name):
    p = os.path.join(XFWM, name)
    if not os.path.exists(p):
        return ""
    data = base64.b64encode(open(p, "rb").read()).decode()
    return "data:image/svg+xml;base64," + data


def rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "rgba(%d,%d,%d,%.2f)" % (r, g, b, alpha)


def build(t):
    c, m, k = t["colour"], t["metric"], t["controls"]
    accent, paper, ink = c["accent"], c["paper"], c["ink"]
    fg = c["win_fg"]
    muted = c["muted"]
    hair = rgba(c["hairline"], c["hairline_alpha"])
    wash12 = rgba(c["hairline"], 0.12)
    wash18 = rgba(c["hairline"], 0.18)
    win_bg = c["win_bg"]
    radius = k["radius"]
    height = k["height"]

    def btn(name, cls="", style=""):
        return ('<button class="btn %s" style="%s">%s</button>' % (cls, style, name))

    def roww(label, content, note=""):
        return ('<div class="row"><div class="rl">%s</div>'
                '<div class="rc">%s</div><div class="rn">%s</div></div>'
                % (label, content, note))

    buttons = "".join([
        roww("default", btn("Default")),
        roww("primary", btn("Submit a job", "primary")),
        roww("destructive", btn("Purge queue", "destructive")),
        roww("disabled", btn("Disabled", "disabled")),
        roww("icon button", '<button class="iconbtn">&#10227;</button>',
             "26 px, 8 px radius, flat"),
        roww("segmented", '<div class="seg"><button class="on">Runs</button>'
                          '<button>Fleet</button><button>Receipts</button></div>',
             "pill tabs"),
        roww("menu button", '<button class="btn">Actions &#9662;</button>',
             "opens a popover"),
    ])

    inputs = "".join([
        roww("entry", '<input class="entry" placeholder="Submit a job to the fleet">'),
        roww("search", '<input class="entry pill" placeholder="Search runs">',
             "999 px radius"),
        roww("spinbutton", '<div class="spin"><input value="4"><div class="stp">'
                           '<span>&#9650;</span><span>&#9660;</span></div></div>',
             "22 px steppers"),
        roww("combo box", '<button class="btn">Auto &#9662;</button>'),
        roww("slider", '<div class="slider"><div class="track"><div class="fill" '
                       'style="width:62%"></div><div class="thumb" '
                       'style="left:62%"></div></div></div>',
             "track 4 px · thumb 14 px"),
        roww("switch", '<div class="sw on"><div class="knob"></div></div>'
                       '<div class="sw"><div class="knob"></div></div>'),
        roww("check / radio", '<span class="chk on">&#10003;</span>'
                              '<span class="rad on"></span><span class="chk"></span>'),
        roww("text view", '<div class="textarea">Job watch-mw17tpki<br>'
                          'status: refused — 18940 not answering</div>'),
    ])

    selection = "".join([
        roww("list row", '<div class="listrow">hover row</div>'
                         '<div class="listrow sel">selected row</div>'),
        roww("badges", '<span class="badge">LIVE</span>'
                       '<span class="badge">QUEUED</span>'
                       '<span class="badge err">FAILED</span>'),
        roww("tooltip", '<div class="tooltip">Open the run receipt</div>'),
        roww("card", '<div class="card"><div class="cl">RUNS TODAY</div>'
                     '<div class="cv">47</div></div>'),
    ])

    nav = "".join([
        roww("menubar", '<div class="menubar"><span>File</span><span>Edit</span>'
                        '<span>View</span><span>Agents</span></div>',
             "28 px, accent underline on hover"),
        roww("notebook", '<div class="tabs"><div class="tab on">Runs '
                         '<span class="tabx">&#10005;</span></div>'
                         '<div class="tab">Fleet <span class="tabx">&#10005;</span></div>'
                         '<div class="tab">Receipts <span class="tabx">&#10005;</span></div>'
                         '</div>', "close button per tab"),
        roww("stack switcher", '<div class="seg"><button class="on">One</button>'
                               '<button>Two</button></div>'),
        roww("sidebar", '<div class="side"><div class="srow">Overview</div>'
                        '<div class="srow sel">Window controls</div>'
                        '<div class="srow">Agents</div></div>',
             "196 px · selected is accent"),
    ])

    feedback = "".join([
        roww("progress", '<div class="pbar"><div style="width:42%"></div></div>'
                         '<span class="pct">42 %</span>'),
        roww("level bar", '<div class="lbar"><i style="width:62%"></i></div>'),
        roww("infobar", '<div class="infobar">18940 answers. Jobs are accepted.</div>'),
        roww("infobar (error)", '<div class="infobar err">18940 is not answering '
                                '— the relay is down.</div>'),
        roww("toast", '<div class="toast">Job accepted — watch-mw17tpki</div>',
             "slides in bottom-right"),
        roww("spinner", '<div class="spinner"></div>'),
        roww("osd", '<div class="osd"><span>Volume</span>'
                    '<div class="osdbar"><i style="width:55%"></i></div></div>',
             "keyboard volume/brightness overlay"),
    ])

    data = "".join([
        roww("treeview", '<table class="tree"><tr><th>Run id</th><th>Agent</th>'
                         '<th>Outcome</th><th>Took</th></tr>'
                         '<tr><td>watch-mw17tpki</td><td>watchman</td>'
                         '<td>refused</td><td>0.08 s</td></tr>'
                         '<tr><td>officina-faber-mw17ztds</td><td>officina</td>'
                         '<td>refused</td><td>0.02 s</td></tr></table>',
             "headers are 28 px, muted, hairline bottom"),
        roww("statusbar", '<div class="statusbar">3 runs · 0 receipts · relay 18940</div>'),
        roww("calendar", '<div class="cal"><div class="calh">November 2026</div>'
                         '<div class="calg">' + "".join(
            '<span class="%s">%d</span>' % ("cd sel" if d == 3 else "cd", d)
            for d in range(1, 31)) + '</div></div>'),
    ])

    wb = "".join(
        '<div class="wbcell"><img src="%s"><span>%s</span></div>'
        % (svg_inline("%s-%s.svg" % (name, state)), state)
        for name, state in (("close", "active"), ("hide", "active"),
                            ("maximize", "active"), ("maximize", "toggled"),
                            ("close", "inactive")))

    css = """
    *{box-sizing:border-box}
    body{margin:0;background:%(bg)s;color:%(fg)s;
      font:13px/1.5 'Inter',-apple-system,'Segoe UI',sans-serif}
    .wrap{padding:26px 30px 34px;width:1560px}
    h1{font-size:19px;margin:0 0 2px}
    .sub{color:%(muted)s;font-size:12px;margin-bottom:20px}
    .cols{display:flex;gap:34px;align-items:flex-start}
    .col{flex:1;min-width:0}
    h2{font-size:11px;letter-spacing:.09em;color:%(muted)s;margin:0 0 8px;
      text-transform:uppercase;font-weight:700}
    .panel{background:%(winbg)s;border:1px solid %(hair)s;border-radius:%(wr)spx;
      padding:14px 16px;margin-bottom:18px}
    .row{display:flex;align-items:center;gap:12px;padding:6px 0;
      border-bottom:1px solid %(wash12)s;min-height:44px}
    .row:last-child{border-bottom:0}
    .rl{width:132px;flex:none;color:%(muted)s;font-size:12px}
    .rc{flex:none;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .rn{color:%(muted)s;font-size:11px;opacity:.75}
    .btn{height:%(h)spx;padding:0 14px;border-radius:%(r)spx;
      border:1px solid %(hair)s;background:%(wash12)s;color:%(fg)s;
      font:600 12.5px 'Inter',sans-serif;cursor:pointer}
    .btn.primary{background:%(accent)s;border-color:%(accent)s;color:%(paper)s}
    .btn.destructive{background:%(urgent)s;border-color:%(urgent)s;color:%(paper)s}
    .btn.disabled{opacity:.45;cursor:default}
    .iconbtn{height:26px;width:26px;border-radius:8px;border:0;
      background:transparent;color:%(fg)s;font-size:15px;cursor:pointer}
    .iconbtn:hover{background:%(wash18)s}
    .seg{display:flex}
    .seg button{height:%(h)spx;padding:0 14px;border-radius:0;cursor:pointer;
      border:1px solid %(hair)s;background:transparent;color:%(fg)s;
      font:600 12.5px 'Inter',sans-serif}
    .seg button:first-child{border-radius:999px 0 0 999px}
    .seg button:last-child{border-radius:0 999px 999px 0}
    .seg button.on{background:%(accent)s;border-color:%(accent)s;color:%(paper)s}
    .entry{height:%(h)spx;width:250px;padding:0 12px;border-radius:%(r)spx;
      border:1px solid %(hair)s;background:%(wash12)s;color:%(fg)s;
      font:13px 'Inter',sans-serif;outline:none}
    .entry.pill{border-radius:999px}
    .entry::placeholder{color:%(muted)s}
    .spin{display:flex;height:%(h)spx;border:1px solid %(hair)s;
      border-radius:%(r)spx;background:%(wash12)s;overflow:hidden}
    .spin input{background:transparent;border:0;color:%(fg)s;width:56px;
      padding:0 10px;font:13px 'Inter'}
    .stp{display:flex;flex-direction:column;width:%(stp)dpx;
      border-left:1px solid %(hair)s}
    .stp span{flex:1;font-size:8px;color:%(muted)s;display:flex;
      align-items:center;justify-content:center}
    .slider{width:300px}
    .track{position:relative;height:4px;border-radius:2px;background:%(wash18)s}
    .fill{position:absolute;height:4px;border-radius:2px;background:%(accent)s}
    .thumb{position:absolute;top:-5px;width:14px;height:14px;margin-left:-7px;
      border-radius:50%%;background:%(paper)s;border:2px solid %(accent)s}
    .sw{width:40px;height:22px;border-radius:11px;background:%(wash18)s;
      border:1px solid %(hair)s;position:relative}
    .sw.on{background:%(accent)s;border-color:%(accent)s}
    .knob{position:absolute;top:2px;left:2px;width:16px;height:16px;
      border-radius:50%%;background:%(paper)s}
    .sw.on .knob{left:20px}
    .chk,.rad{display:inline-flex;align-items:center;justify-content:center;
      width:16px;height:16px;border-radius:4px;border:1px solid %(hair)s;
      background:%(wash12)s;font-size:11px;color:%(paper)s;margin-right:8px}
    .rad{border-radius:50%%}
    .chk.on{background:%(accent)s;border-color:%(accent)s}
    .rad.on{background:%(accent)s;border-color:%(accent)s;
      box-shadow:inset 0 0 0 3px %(winbg)s}
    .textarea{width:300px;min-height:58px;padding:8px 10px;border-radius:%(r)spx;
      border:1px solid %(hair)s;background:%(wash12)s;color:%(fg)s;
      font:12px ui-monospace,Menlo,monospace}
    .listrow{padding:8px 14px;border-radius:8px;color:%(fg)s}
    .listrow:hover{background:%(wash12)s}
    .listrow.sel{background:%(accent)s;color:%(paper)s;font-weight:600}
    .badge{font:700 10px 'Inter';letter-spacing:.06em;padding:2px 7px;
      border:1px solid currentColor;border-radius:%(br)spx;color:%(fg)s}
    .badge.err{color:%(urgent)s}
    .tooltip{background:%(ink)s;color:%(paper)s;border:1px solid %(accent)s;
      border-radius:10px;padding:6px 10px;font-size:11.5px}
    .card{display:inline-block;padding:10px 14px;border:1px solid %(hair)s;
      border-radius:10px}
    .cl{font:700 10px 'Inter';letter-spacing:.07em;color:%(muted)s}
    .cv{font:700 22px 'Inter'}
    .menubar{display:flex;gap:4px;height:%(mb)dpx;align-items:center}
    .menubar span{padding:0 10px;line-height:%(mb)dpx;border-radius:6px;
      font-size:12.5px}
    .menubar span:hover{background:%(wash18)s}
    .tabs{display:flex;gap:4px}
    .tab{display:flex;align-items:center;gap:8px;height:%(tabh)dpx;padding:0 12px;
      border:1px solid %(hair)s;border-bottom:0;border-radius:%(tabr)spx %(tabr)spx 0 0;
      color:%(muted)s;font-size:12.5px}
    .tab.on{color:%(fg)s;font-weight:600;background:%(wash12)s;
      border-bottom:2px solid %(accent)s}
    .tabx{font-size:9px;opacity:.7}
    .side{width:%(side)dpx;border:1px solid %(hair)s;border-radius:10px;
      background:rgba(0,0,0,.18);padding:6px}
    .srow{height:%(rowh)dpx;line-height:%(rowh)dpx;padding:0 10px;border-radius:8px;
      font-size:12.5px}
    .srow.sel{background:%(accent)s;color:%(paper)s;font-weight:600}
    .pbar{width:280px;height:10px;border-radius:999px;background:%(wash12)s;
      overflow:hidden}
    .pbar div{height:10px;background:%(accent)s}
    .pct{color:%(muted)s;font-size:11px}
    .lbar{width:280px;height:%(lvl)dpx;border-radius:999px;background:%(wash12)s;
      overflow:hidden;display:block}
    .lbar i{display:block;height:%(lvl)dpx;background:%(accent)s}
    .infobar{width:330px;padding:8px 12px;border-radius:%(r)spx;
      background:rgba(79,126,194,.18);border:1px solid %(accent)s;font-size:12.5px}
    .infobar.err{background:rgba(232,85,63,.18);border-color:%(urgent)s}
    .toast{width:%(toastw)dpx;padding:10px 14px;border-radius:%(toastr)dpx;
      background:%(winbg2)s;border:1px solid %(hair)s;
      box-shadow:0 8px 24px rgba(0,0,0,.45);font-size:12.5px}
    .osd{display:flex;align-items:center;gap:10px;padding:10px 16px;
      border-radius:12px;background:%(winbg2)s;border:1px solid %(accent)s;
      box-shadow:0 10px 30px rgba(0,0,0,.5);font:600 12px 'Inter'}
    .osdbar{width:120px;height:4px;border-radius:2px;background:%(wash18)s}
    .osdbar i{display:block;height:4px;border-radius:2px;background:%(accent)s}
    .spinner{width:22px;height:22px;border-radius:50%%;
      border:2px solid %(wash18)s;border-top-color:%(accent)s}
    .tree{border-collapse:collapse;width:100%%;font-size:12.5px}
    .tree th{text-align:left;font-size:11px;color:%(muted)s;font-weight:700;
      padding:6px 10px;border-bottom:1px solid %(hair)s}
    .tree td{padding:7px 10px;border-bottom:1px solid %(wash12)s}
    .statusbar{width:100%%;min-height:%(sbh)dpx;line-height:%(sbh)dpx;
      padding:0 10px;color:%(muted)s;font-size:11.5px;
      border-top:1px solid %(hair)s;background:rgba(0,0,0,.2)}
    .cal{width:250px;border:1px solid %(hair)s;border-radius:%(r)spx;padding:8px}
    .calh{font:700 12px 'Inter';padding:2px 4px 8px;
      border-bottom:1px solid %(hair)s;margin-bottom:8px}
    .calg{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}
    .cd{height:22px;display:flex;align-items:center;justify-content:center;
      border-radius:6px;font-size:11.5px}
    .cd.sel{background:%(accent)s;color:%(paper)s;font-weight:700}
    .wbrow{display:flex;gap:18px;align-items:center;margin-top:6px}
    .wbcell{display:flex;flex-direction:column;align-items:center;gap:6px;
      font-size:10.5px;color:%(muted)s}
    .wbcell img{width:66px;height:66px;display:block}
    .wb1x img{width:22px;height:22px}
    .foot{color:%(muted)s;font-size:11px;margin-top:16px}
    """ % {
        "bg": c["bg_dark"], "fg": fg, "muted": muted, "hair": hair,
        "accent": accent, "paper": paper, "ink": ink, "urgent": c["urgent"],
        "winbg": rgba(win_bg, 0.55), "winbg2": rgba(win_bg, 0.96),
        "wash12": wash12, "wash18": wash18, "wr": m["window_radius"],
        "h": height, "r": radius, "stp": k["stepper_w"], "br": k["badge_radius"],
        "mb": k["menubar_h"], "tabh": k["tab_h"], "tabr": k["tab_radius"],
        "side": k["sidebar_w"], "rowh": k["row_h"], "lvl": k["level_h"],
        "toastw": k["toast_w"], "toastr": k["toast_radius"],
        "sbh": k["statusbar_h"],
    }

    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>%(css)s</style>
</head><body><div class="wrap">
<div style="display:flex;justify-content:space-between;align-items:flex-end">
<div><h1>Meta OS control set</h1>
<div class="sub">generated from meta.tokens.json · window buttons embedded from the real
xfwm4 SVGs · a spec sheet, not a screenshot of the running OS</div></div>
<div class="wbrow">%(wb)s</div></div>
<div class="cols">
  <div class="col">
    <h2>Buttons</h2><div class="panel">%(buttons)s</div>
    <h2>Inputs</h2><div class="panel">%(inputs)s</div>
    <h2>Selection</h2><div class="panel">%(selection)s</div>
  </div>
  <div class="col">
    <h2>Navigation</h2><div class="panel">%(nav)s</div>
    <h2>Feedback</h2><div class="panel">%(feedback)s</div>
    <h2>Data</h2><div class="panel">%(data)s</div>
  </div>
</div>
<div class="foot">Every one of these is a selector in gtk/gtk.css and a widget in
Meta OS Controls — the native app on the dock. Anything not on this sheet is a GTK
default, and therefore a bug.</div>
</div></body></html>""" % {
        "css": css, "wb": wb, "buttons": buttons, "inputs": inputs,
        "selection": selection, "nav": nav, "feedback": feedback, "data": data,
    }
    return html


def main(argv):
    t = load()
    html = build(t)
    os.makedirs(OUTDIR, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    png = os.path.join(OUTDIR, "theme-controls-%s.png" % stamp)
    tmp = "/tmp/meta-controls-sheet.html"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(html)
    cmd = [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--window-size=1560,1420",
           "--default-background-color=00000000", "--screenshot=" + png, tmp]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(png):
        print("controls preview: chrome failed\n%s\n%s" % (res.stdout, res.stderr))
        return 1
    print("controls preview: %s (%d bytes)" % (png, os.path.getsize(png)))
    if "--open" in argv:
        subprocess.run(["open", png])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
