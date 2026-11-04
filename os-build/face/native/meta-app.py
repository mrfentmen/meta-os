#!/usr/bin/env python3
"""meta-app — open a Meta OS surface as a real application window.

What this is NOT: a browser. There is no address bar, no tab strip, no
bookmarks, no "127.0.0.1" anywhere on screen. The page is the window's content
and the title bar carries the app's name, the way a downloaded app would look.

What it is: one GTK window with a WebKit view inside. The surfaces are served
by the local backends on this machine, so a tile opens instantly and works
with no network.

If a backend is down, the window says so in Meta's own words — it never dumps
a browser error page or a raw URL at the user. The dead-backend screen names
the host, the port and the failing URL, and offers Retry (re-requests only
the failed page) and Copy URL.

Usage:
    meta-app --title "Board" --url http://127.0.0.1:18900/board.html
    meta-app --title Music --url file:///usr/share/metaos/... --width 1200

Window chrome (all in this file, Section A of the R2-T2 lane):
  close / minimise / maximise controls top-right in a Gtk.HeaderBar; the
  WM-provided close button is kept and the process forces
  gtk-decoration-layout to "menu:close" so there is exactly one of each.
  Alt+F4 closes, Alt+F9 minimises, Alt+F10 toggles maximise (accel group).
  Escape closes transient popups/dialogs only, never the app. Double-click
  on the title bar toggles maximise. Right-click on the title bar opens a
  menu: Close, Minimise, Maximise, Always on top (a real keep-above hint,
  reflected in the title-bar subtitle). Geometry persists per app id and is
  only restored when the saved rectangle is still on screen.

App shell (Section B):
  This file is the ONLY browser-backed host: one Gtk.Window containing one
  WebKit2.WebView, no URL bar, no tab strip, no browser chrome. Autoplay
  stays off (media-playback-requires-user-gesture); a visible unmute toggle
  appears only with --allow-audio (the Musica tile). Downloads go to
  ~/Downloads with no shelf. Printing is cancelled unless --allow-print.
  Dev tools stay disabled. Zoom clamps to 80-125%. Ctrl+Q quits, Ctrl+W
  closes the window, Ctrl+F opens find-in-page (Esc closes it). One running
  instance per app id (hold file); a second launch focuses the existing
  window. file:// pages never touch the network.

Config (one file per user):
  ~/.config/metaos/meta-app.json  {"apps": {"<app-id>": {"x":..,"y":..,
  "w":..,"h":..,"maximized": bool}}}
  Locks live beside it in ~/.config/metaos/locks/<app-id>.lock.

Exit codes (--check modes and failures are all named, never tracebacks):
  0  ok (window ran, check passed, or second instance focused the old window)
  1  runtime failure inside GTK (message on stderr, no traceback)
  2  usage: --url missing (and not implied by the check mode)
  3  --check port: the URL's host:port is not answering
  4  --check page: the page is not reachable (HTTP >= 400 / error, or missing file)
  5  backend missing: GTK/WebKit2 not importable on this machine
  6  already running: another instance holds this app id (focused it instead)

Headless checks (no display needed):
  python3 test_meta_app_headless.py        # full logic suite
  meta-app --check binary                  # 0 when GTK+WebKit2 import
  meta-app --check port --url http://127.0.0.1:18900/board.html
  meta-app --check page --url file:///usr/share/metaos/x.html

Guest (needs the booted MetaOS session) recipes are collected in the
R2-T2 lane report-back; every GTK-only path below names its recipe there.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.parse
import urllib.request

BRAND_BLUE = "#1877F2"
BRAND_WHITE = "#EDF5FF"
BRAND_BLACK = "#070B16"
BRAND_MUTED = "#8291AC"

# --------------------------------------------------------------------------
# Constants: the whole policy surface in one place so headless tests can
# assert it without importing GTK.
# --------------------------------------------------------------------------
MIN_WIDTH = 640
MIN_HEIGHT = 440
ZOOM_MIN = 0.80
ZOOM_MAX = 1.25
ZOOM_STEP = 0.10
ZOOM_DEFAULT = 1.00
LOADING_FLASH_MS = 300  # spinner appears only after a load lasts this long
ON_SCREEN_GRAB = 64  # px of a restored window that must stay on screen
CONFIG_RELATIVE = os.path.join(".config", "metaos", "meta-app.json")
LOCKS_RELATIVE = os.path.join(".config", "metaos", "locks")
DOWNLOAD_DIRNAME = "Downloads"
DEVTOOLS_ENABLED = False
AUTOPLAY_GESTURE_REQUIRED = True  # autoplay stays disabled, always

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2
EXIT_PORT_DOWN = 3
EXIT_PAGE_DOWN = 4
EXIT_NO_BACKEND = 5
EXIT_ALREADY_RUNNING = 6

EXIT_DESCRIPTIONS = {
    EXIT_OK: "ok",
    EXIT_RUNTIME: "runtime failure",
    EXIT_USAGE: "missing --url",
    EXIT_PORT_DOWN: "port not answering",
    EXIT_PAGE_DOWN: "page not reachable",
    EXIT_NO_BACKEND: "GTK/WebKit backend missing",
    EXIT_ALREADY_RUNNING: "already running, focused existing window",
}

# Accelerators wired through a Gtk.AccelGroup (task 6/37/38/39).
ACCEL_MAP = {
    "<Alt>F4": "close-window",
    "<Alt>F9": "minimize",
    "<Alt>F10": "toggle-maximize",
    "<Control>q": "quit",
    "<Control>w": "close-window",
    "<Control>f": "find",
    "<Control>plus": "zoom-in",
    "<Control>equal": "zoom-in",
    "<Control>KP_Add": "zoom-in",
    "<Control>minus": "zoom-out",
    "<Control>KP_Subtract": "zoom-out",
    "<Control>0": "zoom-reset",
    "<Control>KP_0": "zoom-reset",
}

# Right-click title-bar menu, in order (task 16).
TITLE_MENU_ITEMS = (
    ("Close", "close-window"),
    ("Minimise", "minimize"),
    ("Maximise", "toggle-maximize"),
    ("Always on top", "toggle-above"),
)

CSS = b"""
window, headerbar { background: #070b16; color: #edf5ff; }
window:backdrop, headerbar:backdrop { background: #05080f; color: #8291ac; }
headerbar { border-bottom: 1px solid #16213a; box-shadow: none; }
headerbar .title { color: #edf5ff; font-weight: 600; }
headerbar .title:backdrop { color: #8291ac; }
headerbar .subtitle { color: #8291ac; font-size: 10px; }
/* WM-drawn title buttons: all four states from the brand tokens. */
headerbar button.titlebutton.close,
headerbar button.titlebutton.minimize,
headerbar button.titlebutton.maximize { color: #edf5ff; background: transparent; border: none; }
headerbar button.titlebutton.close:hover { background: #3a1620; color: #ffffff; }
headerbar button.titlebutton.close:active { background: #5a1f2b; color: #ffffff; }
headerbar button.titlebutton.close:disabled { background: transparent; color: #3d4a63; }
headerbar button.titlebutton.close:backdrop { color: #8291ac; }
headerbar button.titlebutton.minimize:hover,
headerbar button.titlebutton.maximize:hover { background: #16213a; color: #ffffff; }
headerbar button.titlebutton.minimize:active,
headerbar button.titlebutton.maximize:active { background: #1e2c4d; color: #ffffff; }
/* Our explicit minimise/maximise header buttons: same four states. */
headerbar button.meta-winbtn { color: #edf5ff; background: transparent; border: none; }
headerbar button.meta-winbtn:hover { background: #16213a; color: #ffffff; }
headerbar button.meta-winbtn:active { background: #1e2c4d; color: #ffffff; }
headerbar button.meta-winbtn:disabled { background: transparent; color: #3d4a63; }
/* Keyboard reachability: every focused control shows the ring. */
button:focus, entry:focus { outline: 2px solid #1877f2; outline-offset: 1px; }
/* Dead-backend + crash screens reuse the house style. */
.meta-deadbar { background: #0b1220; color: #edf5ff; border-bottom: 1px solid #16213a; }
.meta-crash { background: #0b1220; color: #edf5ff; border: 1px solid #16213a; border-radius: 12px; }
"""

# Shown when the page cannot load. Built as data here, never fetched.
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
 p{color:#8291ac;font-size:12.5px;margin:0;max-width:480px;line-height:1.5}
 code{color:#edf5ff;font-size:12px;word-break:break-all}
 .route{color:#8291ac;font-size:11.5px}
</style></head><body><div class="wrap">
 <div class="mark">M</div>
 <h1>%s is not answering</h1>
 <p>This app's background service did not start. The window is still the
 app &mdash; restart the session, or start the service and press Retry.</p>
 <p class="route">host <code>%s</code> &middot; port <code>%s</code></p>
 <p><code>%s</code></p>
</div></body></html>"""


# --------------------------------------------------------------------------
# Pure helpers: no GTK, no network side effects. Everything below imports
# cleanly with `import gi` absent, which is what the headless suite proves.
# --------------------------------------------------------------------------
def slug_app_id(title, explicit=None):
    """Single-instance id: explicit --app-id wins, else a slug of --title."""
    if explicit:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", explicit.strip().lower())
        return cleaned or "app"
    s = re.sub(r"[^a-z0-9 _-]+", "", (title or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "app"


def config_file_path(home=None):
    """The ONE geometry file for this user."""
    base = home if home is not None else os.path.expanduser("~")
    return os.path.join(base, CONFIG_RELATIVE)


def lock_dir(home=None):
    base = home if home is not None else os.path.expanduser("~")
    return os.path.join(base, LOCKS_RELATIVE)


def lock_path_for(app_id, home=None):
    safe = re.sub(r"[^a-z0-9-]+", "-", (app_id or "app").lower()) or "app"
    return os.path.join(lock_dir(home), safe + ".lock")


def pid_alive(pid):
    """True when a process with this pid exists (never raises)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return False
    return True


def acquire_app_lock(app_id, home=None):
    """Claim the single-instance hold file.

    Returns (status, pid): ("acquired", own pid) or ("held", holder pid).
    A stale lock (dead pid) is stolen. Never raises.
    """
    path = lock_path_for(app_id, home)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        return ("held", None)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError:
        holder = read_lock_pid(path)
        if holder is not None and pid_alive(holder):
            return ("held", holder)
        try:
            os.unlink(path)
        except OSError:
            return ("held", holder)
        try:
            fd = os.open(path, flags, 0o644)
        except OSError:
            return ("held", holder)
    except OSError:
        return ("held", None)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass
    return ("acquired", os.getpid())


def read_lock_pid(path):
    try:
        with open(path, "r", encoding="ascii") as fh:
            return int(fh.read().strip().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def release_app_lock(app_id, home=None):
    """Drop our hold file, but only when we own it. Never raises."""
    path = lock_path_for(app_id, home)
    try:
        if read_lock_pid(path) == os.getpid():
            os.unlink(path)
            return True
    except OSError:
        pass
    return False


def load_store(path):
    """Read the geometry store; missing/corrupt files degrade to {}."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    apps = data.get("apps")
    return {"apps": apps} if isinstance(apps, dict) else {}


def save_store(path, store):
    """Write the geometry store atomically. Never raises."""
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(store if isinstance(store, dict) else {}, fh)
        os.replace(tmp, path)
        return True
    except (OSError, ValueError, TypeError):
        return False


def geometry_for(app_id, store):
    """Saved rectangle for one app, or None. Never raises."""
    try:
        rect = (store.get("apps") or {}).get(app_id)
    except AttributeError:
        return None
    if not isinstance(rect, dict):
        return None
    try:
        return {"x": int(rect["x"]), "y": int(rect["y"]),
                "w": int(rect["w"]), "h": int(rect["h"]),
                "maximized": bool(rect.get("maximized", False))}
    except (KeyError, ValueError, TypeError):
        return None


def record_geometry(store, app_id, rect):
    """Remember one app's rectangle inside the store dict (pure)."""
    if not isinstance(store, dict):
        store = {}
    apps = store.get("apps")
    if not isinstance(apps, dict):
        apps = {}
        store["apps"] = apps
    apps[app_id] = {"x": int(rect["x"]), "y": int(rect["y"]),
                    "w": int(rect["w"]), "h": int(rect["h"]),
                    "maximized": bool(rect.get("maximized", False))}
    return store


def clamp_size(w, h, min_w=MIN_WIDTH, min_h=MIN_HEIGHT):
    """Clamp a requested size up to the per-app minimum (tasks 12/28)."""
    try:
        w, h = int(w), int(h)
    except (ValueError, TypeError):
        return (min_w, min_h)
    return (max(w, min_w), max(h, min_h))


def size_notice(work_w, work_h, min_w=MIN_WIDTH, min_h=MIN_HEIGHT):
    """Clear message when the screen itself is smaller than the minimum."""
    if work_w < min_w or work_h < min_h:
        return ("meta-app: screen is %dx%d, smaller than the %dx%d minimum; "
                "the window is clamped to the minimum and may not fit." % (
                    work_w, work_h, min_w, min_h))
    return None


def rect_on_screen(rect, work):
    """True when a saved rectangle is still usable on this work area.

    rect: dict(x, y, w, h). work: (wx, wy, ww, wh). At least
    ON_SCREEN_GRAB px of the window's top-left must be inside, and the
    size must be positive; sizes are clamped by the caller.
    """
    try:
        x, y = int(rect["x"]), int(rect["y"])
        w, h = int(rect["w"]), int(rect["h"])
        wx, wy, ww, wh = (int(v) for v in work)
    except (KeyError, ValueError, TypeError):
        return False
    if w <= 0 or h <= 0 or ww <= 0 or wh <= 0:
        return False
    return (wx <= x <= wx + ww - ON_SCREEN_GRAB and
            wy <= y <= wy + wh - ON_SCREEN_GRAB)


def restore_or_default(saved, work, default_w, default_h):
    """Task 14: restore only when the saved rectangle is still on screen.

    Returns the rect dict to apply, or None for "use defaults + center".
    """
    if saved and work and rect_on_screen(saved, work):
        w, h = clamp_size(saved["w"], saved["h"])
        return {"x": saved["x"], "y": saved["y"], "w": w, "h": h,
                "maximized": bool(saved.get("maximized", False))}
    return None


class MinimizeState(object):
    """Headless model of minimise/restore (task 4).

    The GTK window calls self.iconify()/present() for the real thing; this
    class records the transition so the call sequence is unit-testable.
    """

    def __init__(self):
        self.minimized = False

    def iconify(self):
        """Hide the window, keep the process alive. Returns the GTK call."""
        self.minimized = True
        return "iconify"

    def restore(self):
        """Bring the window back. Returns the GTK call, or 'none'."""
        if not self.minimized:
            return "none"
        self.minimized = False
        return "present"


class LoadDelay(object):
    """Cancellable 300ms loading gate (task 41) with an injectable clock."""

    def __init__(self, threshold_ms=LOADING_FLASH_MS):
        self.threshold_ms = threshold_ms
        self.reset()

    def reset(self):
        self._start = None
        self._finished = False

    def start(self, now_ms):
        self._start = now_ms
        self._finished = False

    def finish(self, now_ms):
        """Returns True when the spinner had time to show (caller hides it)."""
        if self._start is None:
            return False
        shown = (now_ms - self._start) >= self.threshold_ms
        self._finished = True
        return shown

    def cancel(self):
        self.reset()

    def due(self, now_ms):
        """True when the spinner should appear right now."""
        return (self._start is not None and not self._finished and
                (now_ms - self._start) >= self.threshold_ms)


def loading_should_show(elapsed_ms, threshold_ms=LOADING_FLASH_MS):
    """Spinner appears only after the threshold; fast pages never flash."""
    return elapsed_ms >= threshold_ms


def zoom_clamp(level):
    """Clamp a zoom level into [80%, 125%]. Never raises."""
    try:
        level = float(level)
    except (ValueError, TypeError):
        return ZOOM_DEFAULT
    return min(ZOOM_MAX, max(ZOOM_MIN, level))


def zoom_step(level, direction):
    """direction in {"in", "out", "reset"}; returns the clamped new level."""
    if direction == "reset":
        return ZOOM_DEFAULT
    try:
        level = float(level)
    except (ValueError, TypeError):
        level = ZOOM_DEFAULT
    if direction == "in":
        level += ZOOM_STEP
    elif direction == "out":
        level -= ZOOM_STEP
    return round(zoom_clamp(level), 2)


def classify_url(url):
    """file | http | https | other. file:// pages must never use sockets."""
    try:
        scheme = urllib.parse.urlparse(url or "").scheme.lower()
    except (ValueError, AttributeError):
        return "other"
    if scheme == "file":
        return "file"
    if scheme == "http":
        return "http"
    if scheme == "https":
        return "https"
    return "other"


def split_target(url):
    """(host, port, kind) for the dead-backend screen and --check port.

    file:// URLs have no host/port: (None, None, 'file').
    """
    kind = classify_url(url)
    if kind == "file":
        return (None, None, kind)
    try:
        parts = urllib.parse.urlparse(url)
    except ValueError:
        return (None, None, kind)
    host = parts.hostname
    port = parts.port
    if port is None and kind == "http":
        port = 80
    elif port is None and kind == "https":
        port = 443
    return (host, port, kind)


def fail_context(title, url):
    """Named-screen strings: app title, host, port AND the failing URL."""
    host, port, _kind = split_target(url)
    return {"title": title or "Meta OS",
            "host": host or "this machine",
            "port": str(port) if port else "n/a",
            "url": url or ""}


def fail_html(title, url):
    ctx = fail_context(title, url)
    return FAIL_HTML % (ctx["title"], ctx["host"], ctx["port"], ctx["url"])


def crash_texts(title):
    """Crash screen names the app (process) and offers Reload."""
    name = title or "Meta OS"
    return {"heading": "%s stopped responding" % name,
            "body": ("The %s page process ended. Your window and the rest of "
                     "the session are untouched — press Reload to re-request "
                     "the page." % name)}


def header_button_spec(allow_audio=False):
    """The window-control contract (task 21): exactly one close, one
    minimise, one maximise — plus an unmute toggle only for audio apps."""
    spec = [
        {"role": "close", "kind": "wm",
         "tooltip": "Close (Alt+F4)"},
        {"role": "minimize", "kind": "explicit",
         "icon": "window-minimize-symbolic",
         "tooltip": "Minimise (Alt+F9)"},
        {"role": "maximize", "kind": "explicit",
         "icon": "window-maximize-symbolic",
         "tooltip": "Maximise (Alt+F10)"},
    ]
    if allow_audio:
        spec.append({"role": "unmute", "kind": "explicit",
                     "icon": "audio-volume-muted-symbolic",
                     "tooltip": "Unmute"})
    return spec


def title_menu_action(label):
    """Map a right-click title-menu label to a window action (task 16)."""
    for text, action in TITLE_MENU_ITEMS:
        if text == label:
            return action
    return None


def double_click_action(click_count, button):
    """Title-bar double-left-click toggles maximise (task 15)."""
    if button == 1 and click_count == 2:
        return "toggle-maximize"
    return None


def escape_action(context):
    """Escape closes transient dialogs/popups only, never the app (task 8).

    context in {"dialog", "find-visible", "menu", "main"}.
    """
    if context in ("dialog", "menu"):
        return "close"
    if context == "find-visible":
        return "hide-find"
    return "none"


def above_subtitle(on):
    """Title-bar reflection of the keep-above hint (task 17)."""
    return "Always on top" if on else ""


def audio_policy(allow_audio):
    """Autoplay stays disabled; unmute UI exists only for audio apps."""
    allowed = bool(allow_audio)
    return {"gesture_required": True,
            "muted": not allowed,
            "show_toggle": allowed}


def print_allowed(allow_print):
    return bool(allow_print)


def resolve_icon(icon_arg):
    """--icon: an existing file wins (set_icon_from_file), else an icon
    name (set_icon_name), else None (leave the default)."""
    if not icon_arg:
        return None
    if os.path.isfile(icon_arg):
        return ("file", icon_arg)
    return ("name", icon_arg)


def download_target(uri_or_name, downloads_dir=None):
    """Route every download into ~/Downloads (task 34). Pure path join."""
    base = downloads_dir or os.path.join(os.path.expanduser("~"),
                                         DOWNLOAD_DIRNAME)
    try:
        path = urllib.parse.urlparse(uri_or_name or "").path
        name = os.path.basename(path) or "download"
    except ValueError:
        name = "download"
    name = os.path.basename(name) or "download"
    return os.path.join(base, name)


def check_port_reachable(host, port, timeout=2.0):
    """True when host:port accepts TCP. Never raises, never traces back."""
    if not host or not port:
        return False
    try:
        sock = socket.create_connection((host, int(port)), timeout=timeout)
    except (OSError, ValueError, OverflowError):
        return False
    except Exception:
        return False
    try:
        sock.close()
    except Exception:
        pass
    return True


def check_page_reachable(url, timeout=5.0):
    """(ok, reason). file:// is a stat, never a socket (task 44)."""
    kind = classify_url(url)
    if kind == "file":
        try:
            path = urllib.parse.urlparse(url).path
            path = urllib.parse.unquote(path)
        except ValueError:
            return (False, "bad file URL")
        if path and os.path.exists(path):
            return (True, "file exists")
        return (False, "file not found: %s" % path)
    if kind not in ("http", "https"):
        return (False, "unsupported scheme for --check page")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "meta-app-check/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
        if status is not None and status < 400:
            return (True, "HTTP %s" % status)
        return (False, "HTTP %s" % status)
    except Exception as exc:
        return (False, "error: %s" % exc)


def webkit_backend_available():
    """--check binary: is the GTK+WebKit2 backend importable here?"""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2  # noqa: F401
    except Exception:
        return False
    return True


def build_arg_parser():
    ap = argparse.ArgumentParser(
        prog="meta-app", add_help=True,
        description="Open a Meta OS surface as a real application window.",
        epilog=("exit codes: 0 ok · 1 runtime failure · 2 missing --url · "
                "3 port not answering · 4 page not reachable · "
                "5 GTK/WebKit backend missing · 6 already running"))
    ap.add_argument("--title", required=False, default="Meta OS")
    ap.add_argument("--url", required=False, default="")
    ap.add_argument("--width", type=int, default=1180)
    ap.add_argument("--height", type=int, default=780)
    ap.add_argument("--min-width", type=int, default=MIN_WIDTH)
    ap.add_argument("--min-height", type=int, default=MIN_HEIGHT)
    ap.add_argument("--icon", required=False, default="",
                    help="icon name or image file for this app window")
    ap.add_argument("--app-id", required=False, default="",
                    help="single-instance id (default: slug of --title)")
    ap.add_argument("--allow-audio", action="store_true",
                    help="show the unmute toggle; autoplay still needs a gesture")
    ap.add_argument("--allow-print", action="store_true",
                    help="let this app print; otherwise printing is cancelled")
    ap.add_argument("--check", choices=("binary", "port", "page"),
                    default=None,
                    help="headless probe, no window: backend, port or page")
    return ap


def run_check(mode, args):
    """Headless --check paths. Returns a named exit code, never raises."""
    if mode == "binary":
        if webkit_backend_available():
            print("meta-app: backend present (Gtk 3 + WebKit2)")
            return EXIT_OK
        print("meta-app: backend missing (Gtk 3 + WebKit2 not importable)",
              file=sys.stderr)
        return EXIT_NO_BACKEND
    if not args.url:
        print("meta-app: --url is required", file=sys.stderr)
        return EXIT_USAGE
    if mode == "port":
        host, port, kind = split_target(args.url)
        if kind == "file":
            print("meta-app: file URL has no port; nothing to probe")
            return EXIT_OK
        if not host or not port:
            print("meta-app: cannot parse host:port from %s" % args.url,
                  file=sys.stderr)
            return EXIT_USAGE
        if check_port_reachable(host, port):
            print("meta-app: port %s on %s is answering" % (port, host))
            return EXIT_OK
        print("meta-app: port %s on %s is not answering" % (port, host),
              file=sys.stderr)
        return EXIT_PORT_DOWN
    if mode == "page":
        ok, reason = check_page_reachable(args.url)
        if ok:
            print("meta-app: page reachable (%s)" % reason)
            return EXIT_OK
        print("meta-app: page not reachable (%s)" % reason, file=sys.stderr)
        return EXIT_PAGE_DOWN
    print("meta-app: unknown --check mode", file=sys.stderr)
    return EXIT_USAGE


# --------------------------------------------------------------------------
# GTK half. Imported lazily so every helper above stays headless-testable.
# --------------------------------------------------------------------------
try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("WebKit2", "4.1")
    from gi.repository import Gtk, WebKit2
    try:
        from gi.repository import Gdk, GLib
    except ImportError:  # minimal gi stubs (headless contract tests)
        Gdk, GLib = None, None
    GTK_AVAILABLE = True
except Exception:
    Gtk = None
    Gdk = None
    GLib = None
    WebKit2 = None
    GTK_AVAILABLE = False


if GTK_AVAILABLE:
    _DOUBLE_PRESS = getattr(getattr(Gdk, "EventType", object),
                            "_2BUTTON_PRESS", None)
    _BUTTON_PRESS = getattr(getattr(Gdk, "EventType", object),
                            "BUTTON_PRESS", None)

    class AppWindow(Gtk.Window):
        """One app window: headerbar chrome outside the page flow, one
        WebView inside, dead/crash overlays, find bar, spinner gate."""

        def __init__(self, title, url, width, height, icon="",
                     app_id="", allow_audio=False, allow_print=False,
                     min_width=MIN_WIDTH, min_height=MIN_HEIGHT):
            super().__init__(title=title)
            self.title_text = title or "Meta OS"
            self.url = url
            self.app_id = slug_app_id(title, explicit=app_id or None)
            self.allow_audio = bool(allow_audio)
            self.allow_print = bool(allow_print)
            self.min_size = (max(int(min_width or MIN_WIDTH), 1),
                             max(int(min_height or MIN_HEIGHT), 1))
            self.min_state = MinimizeState()
            self.load_delay = LoadDelay()
            self._spinner_timer = None
            self._store_path = config_file_path()
            self._is_max = False
            self._pre_max = None
            self._above = False

            # Minimum size: edge/corner resize handles clamp here (task 11).
            self.set_resizable(True)
            self.set_size_request(*self.min_size)
            w, h = clamp_size(width, height, *self.min_size)
            self.set_default_size(w, h)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_role("meta-app-%s" % self.app_id)

            resolved = resolve_icon(icon)
            try:
                if resolved and resolved[0] == "file":
                    self.set_icon_from_file(resolved[1])
                elif resolved and resolved[0] == "name":
                    self.set_icon_name(resolved[1])
            except Exception:
                pass

            # Deterministic chrome: the WM draws exactly one close button;
            # minimise/maximise are our own header buttons (task 2/21).
            try:
                Gtk.Settings.get_default().set_property(
                    "gtk-decoration-layout", "menu:close")
            except Exception:
                pass

            # -- header: title + subtitle live OUTSIDE the page flow ------
            # set_titlebar() keeps the chrome out of the content box, so page
            # content can never cover the controls (task 20). The header has
            # no selectable labels, so dragging empty header space moves the
            # window without ever selecting text (task 10).
            header = Gtk.HeaderBar()
            header.set_show_close_button(True)  # the kept close button
            header.set_title(self.title_text)
            for spec in header_button_spec(self.allow_audio):
                if spec["role"] == "close":
                    continue  # drawn by the WM, exactly once
                btn = Gtk.Button.new_from_icon_name(
                    spec["icon"], Gtk.IconSize.MENU)
                btn.get_style_context().add_class("meta-winbtn")
                btn.set_tooltip_text(spec["tooltip"])
                btn.set_can_focus(True)
                btn.set_focus_on_click(False)
                btn.connect("clicked", self._on_winbtn, spec["role"])
                header.pack_end(btn)
                if spec["role"] == "unmute":
                    self._mute_btn = btn
                    self._sync_mute_icon(True)
            self._header = header
            self.set_titlebar(header)
            header.connect("button-press-event", self._on_header_button)

            # -- content column: dead bar, page, find bar ------------------
            column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                             spacing=0)
            self.add(column)

            self.deadbar = Gtk.InfoBar()
            self.deadbar.set_message_type(Gtk.MessageType.WARNING)
            self.deadbar.get_style_context().add_class("meta-deadbar")
            self._dead_label = Gtk.Label(label="")
            self._dead_label.set_selectable(True)
            self.deadbar.get_content_area().pack_start(
                self._dead_label, False, False, 0)
            self.deadbar.add_button("Copy URL", 2)
            self.deadbar.add_button("Retry", 1)
            self.deadbar.connect("response", self._on_deadbar)
            self.deadbar.set_no_show_all(True)
            self.deadbar.hide()
            column.pack_start(self.deadbar, False, False, 0)

            self.overlay = Gtk.Overlay()
            column.pack_start(self.overlay, True, True, 0)

            self.web = WebKit2.WebView()
            self.web.connect("load-failed", self.on_failed)
            self.web.connect("load-changed", self.on_load_changed)
            self.web.connect("decide-policy", self.on_decide_policy)
            try:
                self.web.connect("print", self.on_print)
            except Exception:
                pass
            try:
                self.web.connect("web-process-terminated",
                                 self.on_crashed)
            except Exception:
                try:
                    self.web.connect("web-process-crashed",
                                     self.on_crashed_legacy)
                except Exception:
                    pass
            self.overlay.add(self.web)

            self.spinner = Gtk.Spinner()
            self.spinner.set_size_request(36, 36)
            self.spinner.set_halign(Gtk.Align.CENTER)
            self.spinner.set_valign(Gtk.Align.CENTER)
            self.spinner.set_no_show_all(True)
            self.spinner.hide()
            self.overlay.add_overlay(self.spinner)

            self.crash = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 spacing=10)
            self.crash.get_style_context().add_class("meta-crash")
            self.crash.set_border_width(24)
            self._crash_title = Gtk.Label(label="")
            self._crash_body = Gtk.Label(label="")
            self._crash_body.set_line_wrap(True)
            self._crash_body.set_max_width_chars(48)
            reload_btn = Gtk.Button(label="Reload")
            reload_btn.connect("clicked", self._on_reload)
            self.crash.pack_start(self._crash_title, False, False, 0)
            self.crash.pack_start(self._crash_body, False, False, 0)
            self.crash.pack_start(reload_btn, False, False, 0)
            self.crash.set_halign(Gtk.Align.CENTER)
            self.crash.set_valign(Gtk.Align.CENTER)
            self.crash.set_no_show_all(True)
            self.crash.hide()
            self.overlay.add_overlay(self.crash)

            self.findbar = Gtk.SearchBar()
            self.find_entry = Gtk.SearchEntry()
            self.find_entry.set_placeholder_text("Find in page…")
            self.find_entry.connect("activate", self._on_find_next)
            self.find_entry.connect("key-press-event", self._on_find_key)
            self.findbar.add(self.find_entry)
            self.findbar.connect_entry(self.find_entry)
            self.findbar.set_no_show_all(True)
            self.findbar.hide()
            column.pack_start(self.findbar, False, False, 0)

            settings = self.web.get_settings()
            settings.set_property("enable-developer-extras",
                                  DEVTOOLS_ENABLED)  # task 40: stays off
            settings.set_property("enable-page-cache", True)
            # Autoplay stays disabled: media needs a user gesture (task 32).
            for prop, value in (
                    ("media-playback-requires-user-gesture",
                     AUTOPLAY_GESTURE_REQUIRED),
                    ("enable-webgl", True),
                    ("enable-accelerated-2d-canvas", True),
                    ("hardware-acceleration-policy", "always")):
                try:
                    settings.set_property(prop, value)
                except Exception:
                    pass
            # Start muted unless this app asked for audio; the unmute toggle
            # exists only then (task 32).
            try:
                self.web.set_is_muted(audio_policy(
                    self.allow_audio)["muted"])
            except Exception:
                pass

            # Downloads bypass any shelf and land in ~/Downloads (task 34).
            try:
                WebKit2.WebContext.get_default().connect(
                    "download-started", self.on_download)
            except Exception:
                pass

            self._install_accels()
            self.connect("key-press-event", self._on_key)
            self.connect("configure-event", self._on_configure)
            self.connect("window-state-event", self._on_window_state)
            try:
                os.makedirs(os.path.expanduser("~/Downloads"), exist_ok=True)
            except OSError:
                pass
            self._restore_geometry()

        # -- window controls (Section A) -----------------------------------
        def _on_winbtn(self, _btn, role):
            if role == "minimize":
                self.minimize_window()
            elif role == "toggle-maximize":
                self.toggle_maximize()
            elif role == "unmute":
                self.toggle_mute()

        def minimize_window(self):
            """Task 4: hide the window, keep the process alive."""
            call = self.min_state.iconify()
            if call == "iconify":
                try:
                    self.iconify()
                except Exception:
                    pass

        def restore_window(self):
            call = self.min_state.restore()
            if call == "present":
                try:
                    self.present()
                except Exception:
                    pass

        def toggle_maximize(self):
            """Task 5: work-area geometry vs the previous geometry."""
            try:
                if self._is_max:
                    self.unmaximize()
                    if self._pre_max:
                        w, h = clamp_size(*self._pre_max, *self.min_size)
                        self.resize(w, h)
                else:
                    self._pre_max = self.get_size()
                    self.maximize()
            except Exception:
                pass

        def toggle_mute(self):
            try:
                muted = self.web.get_is_muted()
            except Exception:
                return
            try:
                self.web.set_is_muted(not muted)
            except Exception:
                return
            self._sync_mute_icon(not muted)

        def _sync_mute_icon(self, muted):
            try:
                img = Gtk.Image.new_from_icon_name(
                    "audio-volume-muted-symbolic" if muted
                    else "audio-volume-high-symbolic",
                    Gtk.IconSize.MENU)
                self._mute_btn.set_image(img)
            except Exception:
                pass

        def toggle_above(self):
            """Task 17: a real keep-above hint, shown in the title bar."""
            self._above = not self._above
            try:
                self.set_keep_above(self._above)
            except Exception:
                pass
            try:
                self._header.set_subtitle(above_subtitle(self._above))
            except Exception:
                pass

        def close_window(self):
            """Task 3: terminate ONLY this app window, never the session.

            One Gtk.Window.destroy(); no session-manager, logout, power-off
            or session-quit call anywhere on this path.
            """
            try:
                self.destroy()
            except Exception:
                pass

        def _on_header_button(self, _header, event):
            try:
                button = event.button
                etype = event.type
            except AttributeError:
                return False
            if button == 3 and _BUTTON_PRESS is not None and \
                    etype == _BUTTON_PRESS:
                self._popup_title_menu(event)
                return True
            if (button == 1 and _DOUBLE_PRESS is not None and
                    etype == _DOUBLE_PRESS):
                self.toggle_maximize()  # task 15
                return True
            return False

        def _popup_title_menu(self, event):
            """Task 16: Close, Minimise, Maximise, Always on top."""
            menu = Gtk.Menu()
            for text, action in TITLE_MENU_ITEMS:
                if action == "toggle-above":
                    item = Gtk.CheckMenuItem(label=text)
                    try:
                        item.set_active(self._above)
                    except Exception:
                        pass
                    item.connect("activate",
                                 lambda _i: self.toggle_above())
                else:
                    item = Gtk.MenuItem(label=text)
                    item.connect("activate",
                                 lambda _i, a=action: self.perform(a))
                menu.append(item)
            menu.show_all()
            try:
                menu.popup_at_pointer(event)
            except Exception:
                try:
                    menu.popup(None, None, None, None,
                               event.button, event.time)
                except Exception:
                    pass

        # -- keyboard -------------------------------------------------------
        def _install_accels(self):
            """Alt+F4/F9/F10 and the shell keys through an accel group."""
            try:
                ag = Gtk.AccelGroup()
                self.add_accel_group(ag)
                for spec, action in ACCEL_MAP.items():
                    if spec == "<Control>f":
                        continue  # search bar owns Ctrl+F natively below
                    key, mods = Gtk.accelerator_parse(spec)
                    if key == 0:
                        continue
                    ag.connect(key, mods, Gtk.AccelFlags.VISIBLE,
                               self._make_accel(action))
            except Exception:
                pass

        def _make_accel(self, action):
            def _fire(_ag, _obj, _key, _mods):
                self.perform(action)
                return True
            return _fire

        def perform(self, action):
            if action == "close-window":
                self.close_window()
            elif action == "quit":
                try:
                    Gtk.main_quit()
                except Exception:
                    pass
            elif action == "minimize":
                self.minimize_window()
            elif action == "toggle-maximize":
                self.toggle_maximize()
            elif action == "toggle-above":
                self.toggle_above()
            elif action == "find":
                self.show_findbar()
            elif action in ("zoom-in", "zoom-out", "zoom-reset"):
                self.apply_zoom(action.split("-", 1)[1])
            return True

        def _on_key(self, _win, event):
            try:
                keyval = event.keyval
                state = event.state & Gtk.accelerator_get_default_mod_mask()
            except Exception:
                return False
            name = Gtk.accelerator_name(keyval, state) or ""
            norm = name.lower().replace("<primary>", "<control>")
            if norm in ("escape",):
                return self._on_escape()
            if norm in ("<control>f",):
                self.show_findbar()
                return True
            if norm in ("<control>plus", "<control>equal",
                        "<control>kp_add"):
                self.apply_zoom("in")
                return True
            if norm in ("<control>minus", "<control>kp_subtract"):
                self.apply_zoom("out")
                return True
            if norm in ("<control>0", "<control>kp_0"):
                self.apply_zoom("reset")
                return True
            return False

        def _on_escape(self):
            """Task 8/39: Esc hides find or popups, never the app."""
            try:
                if self.findbar.get_search_mode():
                    self.findbar.set_search_mode(False)
                    return True
            except Exception:
                pass
            return False  # menus/dialogs consume Esc natively; app stays

        # -- find-in-page (task 39) -----------------------------------------
        def show_findbar(self):
            try:
                self.findbar.set_search_mode(True)
                self.find_entry.grab_focus()
            except Exception:
                pass

        def _on_find_next(self, entry):
            self._run_find(entry.get_text(), backward=False)

        def _on_find_key(self, _entry, event):
            try:
                if (event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)
                        and event.state & Gdk.ModifierType.SHIFT_MASK):
                    self._run_find(self.find_entry.get_text(), backward=True)
                    return True
            except Exception:
                pass
            return False

        def _run_find(self, text, backward=False):
            if not text:
                return
            try:
                controller = self.web.get_find_controller()
            except Exception:
                return
            try:
                options = 0
                try:
                    options = WebKit2.FindOptions.BACKWARDS if backward else 0
                except Exception:
                    pass
                controller.search(text, options, 500)
            except Exception:
                pass

        # -- zoom (task 38) --------------------------------------------------
        def apply_zoom(self, direction):
            try:
                level = zoom_step(self.web.get_zoom_level(), direction)
            except Exception:
                level = ZOOM_DEFAULT
            try:
                self.web.set_zoom_level(level)
            except Exception:
                pass
            return level

        # -- geometry persist/restore (tasks 13/14/29) -----------------------
        def _work_area(self):
            try:
                scr = self.get_screen()
                mon = scr.get_monitor_at_window(self.get_window())
                rect = scr.get_monitor_workarea(mon)
                return (rect.x, rect.y, rect.width, rect.height)
            except Exception:
                return None

        def _restore_geometry(self):
            store = load_store(self._store_path)
            saved = geometry_for(self.app_id, store)
            work = self._work_area()
            if work:
                notice = size_notice(work[2], work[3], *self.min_size)
                if notice:
                    print(notice, file=sys.stderr)
            rect = restore_or_default(saved, work, *self.min_size)
            if rect is None:
                return
            try:
                self.move(rect["x"], rect["y"])
                w, h = clamp_size(rect["w"], rect["h"], *self.min_size)
                self.resize(w, h)
                if rect["maximized"]:
                    self.maximize()
            except Exception:
                pass

        def _snapshot_rect(self):
            try:
                x, y = self.get_position()
                w, h = self.get_size()
            except Exception:
                return None
            w, h = clamp_size(w, h, *self.min_size)
            return {"x": int(x), "y": int(y), "w": w, "h": h,
                    "maximized": bool(self._is_max)}

        def _persist(self):
            rect = self._snapshot_rect()
            if rect is None:
                return
            store = load_store(self._store_path)
            record_geometry(store, self.app_id, rect)
            save_store(self._store_path, store)

        def _on_configure(self, _win, _event):
            if not self._is_max:
                self._persist()
            return False

        def _on_window_state(self, _win, event):
            try:
                self._is_max = bool(
                    event.new_window_state &
                    Gdk.WindowState.MAXIMIZED)
            except Exception:
                pass
            return False

        # -- loading gate (task 41) ------------------------------------------
        def _arm_spinner(self):
            import time
            self.load_delay.start(int(time.monotonic() * 1000))
            self._cancel_spinner_timer()
            try:
                self._spinner_timer = GLib.timeout_add(
                    self.load_delay.threshold_ms, self._on_spinner_due)
            except Exception:
                self._spinner_timer = None

        def _cancel_spinner_timer(self):
            if self._spinner_timer is not None:
                try:
                    GLib.source_remove(self._spinner_timer)
                except Exception:
                    pass
                self._spinner_timer = None

        def _on_spinner_due(self):
            import time
            now = int(time.monotonic() * 1000)
            if self.load_delay.due(now):
                try:
                    self.spinner.show()
                    self.spinner.start()
                except Exception:
                    pass
            self._spinner_timer = None
            return False

        def _hide_spinner(self):
            import time
            now = int(time.monotonic() * 1000)
            self._cancel_spinner_timer()
            if self.load_delay.finish(now):
                try:
                    self.spinner.stop()
                    self.spinner.hide()
                except Exception:
                    pass
            self.load_delay.reset()

        # -- page events ------------------------------------------------------
        def on_load_changed(self, view, event):
            try:
                finished = (event == WebKit2.LoadEvent.FINISHED)
            except Exception:
                finished = False
            if finished:
                self._hide_spinner()
                try:
                    if view.get_uri() == self.url and self.crash_hidden():
                        self.deadbar.hide()
                except Exception:
                    pass
            else:
                try:
                    started = (event == WebKit2.LoadEvent.STARTED)
                except Exception:
                    started = False
                if started:
                    self._arm_spinner()
            return False

        def crash_hidden(self):
            try:
                return not self.crash.get_visible()
            except Exception:
                return True

        def on_failed(self, view, event, uri, _error):
            # Never let WebKit paint its own error page: it would show the URL.
            self._hide_spinner()
            try:
                view.stop_loading()
            except Exception:
                pass
            ctx = fail_context(self.title_text, uri or self.url)
            try:
                self._dead_label.set_text(
                    "%s is not answering — host %s, port %s" % (
                        ctx["title"], ctx["host"], ctx["port"]))
                self.deadbar.show_all()
            except Exception:
                pass
            try:
                view.load_html(fail_html(self.title_text, uri or self.url),
                               "file:///")
            except Exception:
                pass
            return True  # handled

        def _on_deadbar(self, _bar, response):
            if response == 1:  # Retry: re-request ONLY the failed page
                try:
                    self.deadbar.hide()
                    self.crash.hide()
                    self.web.load_uri(self.url)
                except Exception:
                    pass
            elif response == 2:  # Copy URL
                try:
                    clip = Gtk.Clipboard.get(
                        Gdk.SELECTION_CLIPBOARD)
                    clip.set_text(self.url, -1)
                except Exception:
                    pass

        def _on_reload(self, _btn):
            try:
                self.crash.hide()
                self.web.load_uri(self.url)
            except Exception:
                pass

        def on_decide_policy(self, _view, decision, dtype):
            # Downloads never show a shelf; the download-started handler
            # below routes them to ~/Downloads (task 34).
            return False

        def on_download(self, _context, download):
            try:
                uri = download.get_request().get_uri()
            except Exception:
                uri = ""
            target = download_target(uri)
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                download.set_destination("file://" + target)
            except Exception:
                pass
            return False

        def on_print(self, _view, _operation):
            """Task 35: cancel printing unless this app asked for it."""
            return not print_allowed(self.allow_print)

        def on_crashed(self, view, reason=None):
            """Task 42: the crash screen names the app and offers Reload."""
            texts = crash_texts(self.title_text)
            try:
                self._hide_spinner()
                self._crash_title.set_text(texts["heading"])
                self._crash_body.set_text(texts["body"])
                self.crash.show_all()
            except Exception:
                pass
            return False

        def on_crashed_legacy(self, view):
            return self.on_crashed(view)

        def on_destroy(self):
            try:
                self._persist()
            except Exception:
                pass
            try:
                release_app_lock(self.app_id)
            except Exception:
                pass
            try:
                Gtk.main_quit()
            except Exception:
                pass


def run_gtk_window(args):
    """Build the window, run the loop. Returns EXIT_* (never raises)."""
    try:
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception:
            pass  # theme is cosmetic; the app still opens

        win = AppWindow(args.title, args.url, args.width, args.height,
                        icon=args.icon, app_id=args.app_id,
                        allow_audio=args.allow_audio,
                        allow_print=args.allow_print,
                        min_width=args.min_width,
                        min_height=args.min_height)
        win.connect("destroy", win.on_destroy)
        win.show_all()
        # Overlays and bars start hidden even under show_all().
        try:
            win.deadbar.hide()
            win.spinner.hide()
            win.crash.hide()
            win.findbar.hide()
            win.findbar.set_search_mode(False)
        except Exception:
            pass
        win.web.load_uri(win.url)
        Gtk.main()
    except Exception as exc:
        print("meta-app: %s" % exc, file=sys.stderr)
        return EXIT_RUNTIME
    finally:
        try:
            release_app_lock(slug_app_id(args.title,
                                         explicit=args.app_id or None))
        except Exception:
            pass
    return EXIT_OK


def focus_existing_window(title):
    """Best-effort focus of the already-running window (task 43)."""
    if not shutil.which("wmctrl"):
        return False
    try:
        proc = subprocess.run(["wmctrl", "-r", title, "-a"],
                              timeout=3, capture_output=True)
        return proc.returncode == 0
    except Exception:
        return False


def main(argv):
    ap = build_arg_parser()
    args, _unknown = ap.parse_known_args(argv)

    if args.check:
        try:
            return run_check(args.check, args)
        except Exception as exc:
            print("meta-app: check failed (%s)" % exc, file=sys.stderr)
            return EXIT_RUNTIME

    if not args.url:
        print("meta-app: --url is required", file=sys.stderr)
        return EXIT_USAGE

    app_id = slug_app_id(args.title, explicit=args.app_id or None)
    try:
        status, holder = acquire_app_lock(app_id)
    except Exception:
        status, holder = ("acquired", os.getpid())
    if status == "held":
        healed = focus_existing_window(args.title or "Meta OS")
        if holder:
            print("meta-app: %s is already running (pid %s)%s" % (
                args.title or "Meta OS", holder,
                ", focused" if healed else ""))
        else:
            print("meta-app: %s is already running" % (
                args.title or "Meta OS",))
        return EXIT_ALREADY_RUNNING

    if not GTK_AVAILABLE:
        try:
            release_app_lock(app_id)
        except Exception:
            pass
        print("meta-app: GTK/WebKit backend missing on this machine",
              file=sys.stderr)
        return EXIT_NO_BACKEND

    return run_gtk_window(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
