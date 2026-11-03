#!/usr/bin/env python3
"""meta-app — open a Meta OS surface as a real application window.

What this is NOT: a browser. There is no address bar, no tab strip, no
bookmarks, no "127.0.0.1" anywhere on screen. The page is the window's content
and the title bar carries the app's name, the way a downloaded app would look.

What it is: one GTK window with a WebKit view inside. The surfaces are served
by the local backends on this machine, so a tile opens instantly and works
with no network.

If a backend is down, the window says so in Meta's own words — it never dumps
a browser error page or a raw URL at the user.

Usage:
    meta-app --title "Board" --url http://127.0.0.1:18900/board.html
    meta-app --title Music --url file:///usr/share/metaos/... --width 1200
"""
import argparse
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2  # noqa: E402

BRAND_BLUE = "#1877F2"
BRAND_WHITE = "#EDF5FF"
BRAND_BLACK = "#070B16"
BRAND_MUTED = "#8291AC"

CSS = b"""
window, headerbar { background: #070b16; color: #edf5ff; }
headerbar { border-bottom: 1px solid #16213a; box-shadow: none; }
headerbar .title { color: #edf5ff; font-weight: 600; }
headerbar .subtitle { color: #8291ac; font-size: 10px; }
"""

# Shown when the page cannot load. Built as data: here, never fetched.
FAIL_HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>
 html,body{height:100%%;margin:0;background:#070b16;color:#edf5ff;
   font-family:system-ui,-apple-system,sans-serif}
 .wrap{height:100%%;display:flex;flex-direction:column;align-items:center;
   justify-content:center;gap:10px;text-align:center;padding:24px}
 .mark{width:54px;height:54px;border:2px solid #1877F2;border-radius:14px;
   display:flex;align-items:center;justify-content:center;color:#1877F2;
   font-size:26px;font-weight:700}
 h1{font-size:17px;margin:0;font-weight:600}
 p{color:#8291ac;font-size:12.5px;margin:0;max-width:420px;line-height:1.5}
</style></head><body><div class="wrap">
 <div class="mark">M</div>
 <h1>%s is not answering</h1>
 <p>This app's background service did not start. The window is still the
 app — restart the session, or start the service and reopen it.</p>
</div></body></html>"""


class AppWindow(Gtk.Window):
    def __init__(self, title, url, width, height):
        super().__init__(title=title)
        self.title_text = title
        self.url = url
        self.set_default_size(width, height)
        self.set_position(Gtk.WindowPosition.CENTER)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(title)
        self.set_titlebar(header)

        self.web = WebKit2.WebView()
        self.web.connect("load-failed", self.on_failed)
        self.web.connect("load-changed", self.on_load_changed)

        settings = self.web.get_settings()
        # Local backends only; keep it lean and offline-safe.
        settings.set_property("enable-developer-extras", False)
        settings.set_property("enable-page-cache", True)
        # The Science Lab molecule viewer and the 3D music notes are three.js
        # scenes. WebGL has to be on or those pages show their "no 3D context"
        # notice instead of the model. Each property is set independently
        # because they arrived in different WebKitGTK versions and a missing
        # one must not stop the window from opening.
        for prop, value in (
            ("enable-webgl", True),
            ("enable-accelerated-2d-canvas", True),
            ("hardware-acceleration-policy", "always"),
        ):
            try:
                settings.set_property(prop, value)
            except Exception:
                pass

        self.add(self.web)
        self.show_all()
        self.web.load_uri(url)

    def on_load_changed(self, view, event):
        # A failed load fires load-failed; nothing to do on the success path.
        return False

    def on_failed(self, view, event, uri, error):
        # Never let WebKit paint its own error page: it would show the URL.
        view.stop_loading()
        view.load_html(FAIL_HTML % self.title_text, "file:///")
        return True  # handled


def main(argv):
    ap = argparse.ArgumentParser(prog="meta-app", add_help=True)
    ap.add_argument("--title", required=False, default="Meta OS")
    ap.add_argument("--url", required=False, default="")
    ap.add_argument("--width", type=int, default=1180)
    ap.add_argument("--height", type=int, default=780)
    args, _unknown = ap.parse_known_args(argv)

    if not args.url:
        print("meta-app: --url is required", file=sys.stderr)
        return 2

    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            __import__("gi").repository.Gdk.Screen.get_default(),
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    except Exception:
        pass  # theme is cosmetic; the app still opens

    win = AppWindow(args.title, args.url, args.width, args.height)
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
