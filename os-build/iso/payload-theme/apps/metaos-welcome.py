#!/usr/bin/env python3
"""MetaOS Welcome - first-run welcome window for MetaOS 1.0.

Python + GTK3, single file. Shows once per user (flag file), presents
Meta branding (brand colors, original drawn mark - no third-party
assets), system info (hostname, OS, memory), quick-launch buttons
(Files, Terminal, Settings, Browser via Gio.AppInfo with graceful
degradation) and the metafetch one-shot output when node exists.

Never crashes: every external source (GTK, Gio, node, /etc/os-release,
/proc/meminfo) degrades to a hidden section or fallback string.
"""
import os
import shutil
import socket
import subprocess
import sys

# Brand tokens (metaos-contracts/tokens.json). CSS hex only.
BRAND_BLUE = "#1877F2"
BRAND_WHITE = "#EDF5FF"
BRAND_BLACK = "#070B16"
BRAND_CYAN = "#00C8FF"
BRAND_VIOLET = "#8B5CF6"

# First-run flag: shown once, not every login.
FLAG_RELATIVE = os.path.join(".config", "metaos", "welcome-shown")

# Install location the .desktop Exec/TryExec point at.
INSTALL_PREFIX = "/usr/share/metaos/apps"
APP_FILENAME = "metaos-welcome.py"

# Frozen launcher set (metaos-contracts/APPS.md): candidate .desktop IDs
# in preference order. First hit wins; none found -> button disabled.
QUICK_LAUNCH = [
    {"label": "Files",
     "ids": ["thunar.desktop", "org.xfce.thunar.desktop",
             "nautilus.desktop", "nemo.desktop"]},
    {"label": "Terminal",
     "ids": ["xfce4-terminal.desktop", "gnome-terminal.desktop",
             "xterm.desktop"]},
    {"label": "Settings",
     "ids": ["xfce4-settings-manager.desktop",
             "gnome-control-center.desktop"]},
    {"label": "Browser",
     "ids": ["firefox.desktop", "chromium.desktop",
             "chromium-browser.desktop", "google-chrome.desktop"]},
]

# GTK is optional at import time so unit tests run headless (no display).
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gio  # noqa: E402
    GTK_AVAILABLE = True
except Exception:
    Gtk = None
    Gio = None
    GTK_AVAILABLE = False


def get_flag_path(home=None):
    """Absolute path of the FirstRun flag file."""
    base = home if home is not None else os.path.expanduser("~")
    return os.path.join(base, FLAG_RELATIVE)


def should_show(flag_path=None):
    """True when the welcome window should be presented (flag absent)."""
    path = flag_path if flag_path is not None else get_flag_path()
    return not os.path.exists(path)


def mark_shown(flag_path=None):
    """Record that welcome was shown. Never raises."""
    path = flag_path if flag_path is not None else get_flag_path()
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("shown\n")
        return True
    except OSError:
        return False


def parse_os_release(path="/etc/os-release"):
    """Parse an os-release file into a dict. Missing file -> {}."""
    fields = {}
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                fields[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return fields


def get_os_name(os_release_path="/etc/os-release"):
    """Human OS name from os-release. Never raises, never empty."""
    try:
        fields = parse_os_release(os_release_path)
        pretty = fields.get("PRETTY_NAME", "").strip()
        if pretty:
            return pretty
        name = fields.get("NAME", "").strip()
        version = fields.get("VERSION_ID", "").strip()
        if name:
            return (name + " " + version).strip()
    except Exception:
        pass
    return "MetaOS 1.0"


def get_hostname():
    """Local hostname. Never raises, never empty."""
    try:
        name = socket.gethostname().strip()
        if name:
            return name
    except Exception:
        pass
    return "localhost"


def get_memory_text(meminfo_path="/proc/meminfo"):
    """Human memory summary from meminfo. Fallback string if unreadable."""
    try:
        with open(meminfo_path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    kb = int(parts[1])
                    if kb >= 1024 * 1024:
                        return "%.1f GB" % (kb / (1024.0 * 1024.0))
                    return "%d MB" % (kb // 1024)
    except (OSError, ValueError, IndexError):
        pass
    except Exception:
        pass
    return "unavailable"


def get_system_info(os_release_path="/etc/os-release",
                    meminfo_path="/proc/meminfo"):
    """Combined system info dict for the info section. Never raises."""
    return {
        "hostname": get_hostname(),
        "os": get_os_name(os_release_path),
        "memory": get_memory_text(meminfo_path),
    }


def find_metafetch_script():
    """Locate metafetch.mjs (installed or in-tree). None when absent."""
    candidates = []
    env_path = os.environ.get("METAFETCH_PATH", "").strip()
    if env_path:
        candidates.append(env_path)
    candidates.append("/usr/share/metaos/metafetch.mjs")
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "metafetch.mjs"))
    candidates.append(os.path.normpath(
        os.path.join(here, "..", "..", "..", "tools", "metafetch.mjs")))
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                return path
        except Exception:
            continue
    return None


def get_metafetch_text(node_bin=None, script_path=None, timeout=10):
    """Run `node metafetch.mjs --once`. Output text, or None. Never raises."""
    try:
        node = node_bin or shutil.which("node")
        if not node:
            return None
        script = script_path or find_metafetch_script()
        if not script:
            return None
        proc = subprocess.run(
            [node, script, "--once"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            universal_newlines=True,
        )
        text = (proc.stdout or "").strip()
        if proc.returncode != 0 or not text:
            return None
        return text
    except Exception:
        return None


def launch_entry(app_ids, gio_module=None):
    """Launch the first available desktop ID. True on launch, else False."""
    gio = gio_module if gio_module is not None else Gio
    if gio is None:
        return False
    new_info = getattr(getattr(gio, "DesktopAppInfo", None), "new", None)
    if new_info is None:
        return False
    for app_id in app_ids:
        try:
            info = new_info(app_id)
        except Exception:
            continue
        if info is None:
            continue
        try:
            if info.launch([], None):
                return True
        except Exception:
            continue
    return False


def on_launch_clicked(button, app_ids):
    """GTK callback: quick-launch button pressed."""
    return launch_entry(app_ids)


def on_quit_accel(*_args):
    """GTK callback: Ctrl+Q accelerator. Destroys the welcome window."""
    if not GTK_AVAILABLE or Gtk is None:
        return True
    for window in Gtk.Window.list_toplevels():
        try:
            if window.get_title() == "Welcome to MetaOS":
                window.destroy()
        except Exception:
            pass
    try:
        Gtk.main_quit()
    except Exception:
        pass
    return True


def on_dismiss_clicked(button, window):
    """GTK callback: dismiss button. Marks shown and closes the window."""
    mark_shown()
    try:
        window.destroy()
    except Exception:
        pass
    if GTK_AVAILABLE and Gtk is not None:
        try:
            Gtk.main_quit()
        except Exception:
            pass


def on_brand_draw(area, cr):
    """Draw the original Meta 'M' badge (brand colors, no image assets)."""
    try:
        width = area.get_allocated_width()
        height = area.get_allocated_height()
        size = min(width, height)
        if size <= 0:
            return False
        # Blue rounded badge.
        cr.set_source_rgb(0x18 / 255.0, 0x77 / 255.0, 0xF2 / 255.0)
        radius = size * 0.22
        x0 = (width - size) / 2.0 + 2
        y0 = (height - size) / 2.0 + 2
        side = size - 4
        cr.move_to(x0 + radius, y0)
        cr.arc(x0 + side - radius, y0 + radius, radius, -1.5708, 0)
        cr.arc(x0 + side - radius, y0 + side - radius, radius, 0, 1.5708)
        cr.arc(x0 + radius, y0 + side - radius, radius, 1.5708, 3.1416)
        cr.arc(x0 + radius, y0 + radius, radius, 3.1416, 4.7124)
        cr.close_path()
        cr.fill()
        # White 'M' strokes.
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(max(2.0, size * 0.07))
        cr.set_line_cap(1)
        cr.set_line_join(1)
        mx = x0 + side * 0.28
        my = y0 + side * 0.30
        mw = side * 0.44
        mh = side * 0.40
        cr.move_to(mx, my + mh)
        cr.line_to(mx, my)
        cr.line_to(mx + mw / 2.0, my + mh * 0.55)
        cr.line_to(mx + mw, my)
        cr.line_to(mx + mw, my + mh)
        cr.stroke()
    except Exception:
        pass
    return False


def brand_css():
    """GTK CSS carrying the brand tokens. Used by build_window."""
    return (
        ".metaos-welcome { background-color: %s; color: %s; }"
        ".metaos-title { color: %s; font-size: 28px; font-weight: bold; }"
        ".metaos-subtitle { color: %s; font-size: 13px; }"
        ".metaos-info { background-color: %s; color: %s;"
        " border: 1px solid %s; border-radius: 8px; padding: 12px; }"
        ".metaos-launch { background-color: %s; color: %s;"
        " border-radius: 8px; padding: 10px 18px; font-weight: bold; }"
        ".metaos-dismiss { color: %s; padding: 8px 16px; }"
        % (BRAND_WHITE, BRAND_BLACK, BRAND_BLUE, BRAND_BLACK,
           BRAND_WHITE, BRAND_BLACK, BRAND_BLUE,
           BRAND_BLUE, BRAND_WHITE, BRAND_BLACK)
    )


def build_window(system_info=None, metafetch_text=None):
    """Construct the welcome Gtk.Window. Requires GTK; raises RuntimeError."""
    if not GTK_AVAILABLE or Gtk is None:
        raise RuntimeError("GTK 3 is not available")
    info = system_info if system_info is not None else get_system_info()
    if metafetch_text is None:
        metafetch_text = get_metafetch_text()

    window = Gtk.Window(title="Welcome to MetaOS")
    window.set_default_size(620, 520)
    # Chrome only (R2-T2 A): a per-window minimum size and Ctrl+Q to quit.
    # The window keeps server-side decorations, so minimise/maximise/close
    # and Alt+F4 come from the window manager. Escape is deliberately left
    # inert here: closing the welcome window quits the app, and Escape must
    # never close an app window.
    try:
        window.set_size_request(480, 400)
    except Exception:
        pass
    try:
        quit_group = Gtk.AccelGroup()
        window.add_accel_group(quit_group)
        quit_key, quit_mods = Gtk.accelerator_parse("<Control>q")
        if quit_key != 0:
            quit_group.connect(quit_key, quit_mods, Gtk.AccelFlags.VISIBLE,
                               on_quit_accel)
    except Exception:
        pass
    window.set_position(Gtk.WindowPosition.CENTER)
    window.get_style_context().add_class("metaos-welcome")
    try:
        window.set_icon_name("help-about")
    except Exception:
        pass

    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(brand_css().encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            window.get_screen(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    except Exception:
        pass

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    root.set_margin_top(24)
    root.set_margin_bottom(24)
    root.set_margin_start(28)
    root.set_margin_end(28)
    window.add(root)

    badge = Gtk.DrawingArea()
    badge.set_size_request(96, 96)
    badge.connect("draw", on_brand_draw)
    root.pack_start(badge, False, False, 0)

    title = Gtk.Label(label="Welcome to MetaOS")
    title.get_style_context().add_class("metaos-title")
    root.pack_start(title, False, False, 0)

    subtitle = Gtk.Label(label="Your system is ready. Here's what's inside.")
    subtitle.get_style_context().add_class("metaos-subtitle")
    root.pack_start(subtitle, False, False, 0)

    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    info_box.get_style_context().add_class("metaos-info")
    for label_text in ("Hostname: %s" % info.get("hostname", "?"),
                       "OS: %s" % info.get("os", "?"),
                       "Memory: %s" % info.get("memory", "?")):
        row = Gtk.Label(label=label_text)
        row.set_halign(Gtk.Align.START)
        row.set_selectable(True)
        info_box.pack_start(row, False, False, 0)
    root.pack_start(info_box, False, False, 0)

    if metafetch_text:
        fetch_view = Gtk.TextView()
        fetch_view.set_editable(False)
        fetch_view.set_cursor_visible(False)
        fetch_view.set_monospace(True)
        fetch_view.get_buffer().set_text(metafetch_text[:4000])
        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(160)
        scroller.add(fetch_view)
        root.pack_start(scroller, True, True, 0)

    launch_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    for entry in QUICK_LAUNCH:
        button = Gtk.Button(label=entry["label"])
        button.get_style_context().add_class("metaos-launch")
        button.connect("clicked", on_launch_clicked, entry["ids"])
        launch_row.pack_start(button, True, True, 0)
    root.pack_start(launch_row, False, False, 0)

    dismiss = Gtk.Button(label="Get Started")
    dismiss.get_style_context().add_class("metaos-dismiss")
    dismiss.connect("clicked", on_dismiss_clicked, window)
    root.pack_start(dismiss, False, False, 0)

    window.connect("delete-event", lambda w, e: Gtk.main_quit())
    window.connect("destroy", lambda w: mark_shown())
    return window


def main(argv=None):
    """Entry point. Returns process exit code. Never raises."""
    args = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in args
    try:
        if not force and not should_show():
            return 0
        if not GTK_AVAILABLE or Gtk is None:
            sys.stderr.write("metaos-welcome: GTK 3 unavailable, skipping\n")
            return 0
        window = build_window()
        mark_shown()
        window.show_all()
        Gtk.main()
        return 0
    except Exception as exc:
        sys.stderr.write("metaos-welcome: %s\n" % exc)
        return 0


if __name__ == "__main__":
    sys.exit(main())
