#!/usr/bin/env python3
"""meta-welcome.py — the first screen after the password.

Shown once, at first login, by `meta-first-login`. It says what MetaOS is,
what is actually installed on this machine, and where to go next. The list of
apps is read from the installed launchers at run time, so it cannot advertise
something the dock does not have.

    meta-welcome                 show it (does nothing if already shown)
    meta-welcome --json          the same content as JSON, no GTK, no display
    meta-welcome --mark          record that it was shown
    meta-welcome --reset         forget that, so it shows again
    meta-welcome --apps-dir DIR  read launchers from DIR
    meta-welcome --css FILE      stylesheet (default: the installed one)
    meta-welcome --palette FILE  colours for the ring (default: installed)

Nothing here touches the network. The ring is drawn with cairo, so no image
file can go missing and leave a blank window.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PAGES = ("welcome", "installed", "ready")

# The frozen launcher order from metaos-contracts/APPS.md. Anything else the
# tree ships is listed after these, alphabetically.
PREFERRED = ("meta-files", "meta-terminal", "meta-settings",
             "meta-browser", "meta-agent-status")

DEFAULT_CSS = "/usr/share/metaos/welcome/welcome.css"
DEFAULT_PALETTE = "/usr/share/metaos/welcome/palette.json"
DEFAULT_APPS = "/usr/share/applications"


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def marker_path() -> Path:
    return config_home() / "metaos" / "welcome.done"


def read_apps(apps_dir: Path) -> list[dict]:
    """Every Meta launcher on disk, in dock order, with its own wording."""
    found = {}
    for path in sorted(Path(apps_dir).glob("meta-*.desktop")):
        name = comment = ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name=") and not name:
                name = line[5:].strip()
            elif line.startswith("Comment=") and not comment:
                comment = line[8:].strip()
        found[path.stem] = {"id": path.stem, "name": name or path.stem,
                            "comment": comment}

    order = [stem for stem in PREFERRED if stem in found]
    order += sorted(stem for stem in found if stem not in PREFERRED)
    return [found[stem] for stem in order]


def load_palette(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [key for key in ("black", "blue", "white", "cyan") if key not in data]
    if missing:
        raise SystemExit("welcome: palette %s is missing %s" % (path, ", ".join(missing)))
    return data


def mark() -> Path:
    path = marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("shown\n", encoding="utf-8")
    return path


def build_content(args) -> dict:
    apps = read_apps(Path(args.apps_dir))
    return {
        "pages": list(PAGES),
        "apps": apps,
        "shown": marker_path().is_file(),
        "marker": str(marker_path()),
        "offline": True,
    }


# --- the window ---------------------------------------------------------

def run_gui(args) -> int:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, Gtk
    except Exception as exc:  # noqa: BLE001 - a missing GTK is a plain message
        print("welcome: GTK 3 is not available (%s)" % exc, file=sys.stderr)
        return 2

    try:
        palette = load_palette(Path(args.palette))
        css_path = Path(args.css)
    except (OSError, ValueError, SystemExit) as exc:
        print("welcome: %s" % exc, file=sys.stderr)
        return 2

    provider = Gtk.CssProvider()
    if css_path.is_file():
        provider.load_from_path(str(css_path))
    else:
        print("welcome: %s is missing, using GTK defaults" % css_path, file=sys.stderr)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    content = build_content(args)

    def draw_ring(area, cr):
        width, height = area.get_allocated_width(), area.get_allocated_height()
        cr.set_line_width(6)
        cr.set_source_rgb(*hex_rgb(palette["blue"]))
        radius = min(width, height) / 2 - 4
        cr.arc(width / 2, height / 2, radius, 0, 2 * 3.141592653589793)
        cr.stroke()
        cr.set_source_rgb(*hex_rgb(palette["white"]))
        cr.arc(width / 2, height / 2, 4, 0, 2 * 3.141592653589793)
        cr.fill()

    def label(text, css_class):
        node = Gtk.Label(label=text)
        node.set_xalign(0)
        node.set_line_wrap(True)
        node.get_style_context().add_class(css_class)
        return node

    window = Gtk.Window(title="MetaOS")
    window.set_default_size(760, 520)
    window.set_position(Gtk.WindowPosition.CENTER)
    window.get_style_context().add_class("meta-welcome")

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    for edge in ("top", "bottom", "start", "end"):
        getattr(outer, "set_margin_" + edge)(36)
    window.add(outer)

    ring = Gtk.DrawingArea()
    ring.set_size_request(88, 88)
    ring.connect("draw", draw_ring)
    outer.pack_start(ring, False, False, 0)
    outer.pack_start(label("MetaOS 1.0", "meta-title"), False, False, 0)

    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
    outer.pack_start(stack, True, True, 0)

    first = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    first.pack_start(label("Welcome. Everything is local.", "meta-lede"), False, False, 0)
    first.pack_start(label(
        "No account, no sync, no telemetry. The desktop, the boot splash and "
        "this window are drawn from one colour contract.", "meta-body"), False, False, 0)
    stack.add_named(first, PAGES[0])

    second = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    second.pack_start(label("Installed and on the dock", "meta-lede"), False, False, 0)
    if content["apps"]:
        grid = Gtk.Grid(column_spacing=18, row_spacing=8)
        for row, app in enumerate(content["apps"]):
            grid.attach(label(app["name"], "meta-app"), 0, row, 1, 1)
            grid.attach(label(app["comment"] or "installed launcher", "meta-body"), 1, row, 1, 1)
        second.pack_start(grid, False, False, 0)
    else:
        second.pack_start(label(
            "No Meta launchers were found. Run the installer again.", "meta-warn"),
            False, False, 0)
    stack.add_named(second, PAGES[1])

    third = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    third.pack_start(label("You are set", "meta-lede"), False, False, 0)
    for line in (
        "The dock sits at the bottom. Files, Terminal, Settings, Web and Agent status.",
        "Settings holds display, keyboard, sound and appearance.",
        "This window shows once. Bring it back with: meta-welcome --reset",
    ):
        third.pack_start(label(line, "meta-body"), False, False, 0)
    stack.add_named(third, PAGES[2])

    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    dots = label("1 / %d" % len(PAGES), "meta-body")
    footer.pack_start(dots, True, True, 0)
    back = Gtk.Button(label="Back")

    def go_back(_button=None):
        index = max(0, PAGES.index(stack.get_visible_child_name()) - 1)
        stack.set_visible_child_name(PAGES[index])
        update()

    next_button = Gtk.Button(label="Next")
    next_button.get_style_context().add_class("meta-primary")

    state = {"index": 0}

    def advance(_button=None):
        if state["index"] >= len(PAGES) - 1:
            finish()
            return
        state["index"] += 1
        stack.set_visible_child_name(PAGES[state["index"]])
        update()

    def update():
        state["index"] = PAGES.index(stack.get_visible_child_name())
        dots.set_text("%d / %d" % (state["index"] + 1, len(PAGES)))
        back.set_sensitive(state["index"] > 0)
        next_button.set_label("Start" if state["index"] == len(PAGES) - 1 else "Next")

    back.connect("clicked", go_back)
    next_button.connect("clicked", advance)
    footer.pack_end(next_button, False, False, 0)
    footer.pack_end(back, False, False, 0)
    outer.pack_start(footer, False, False, 0)

    def finish(_widget=None):
        if not content["shown"]:
            mark()
        window.destroy()

    def on_key(_widget, event):
        if event.keyval == Gdk.KEY_Escape:
            finish()
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            advance()
        else:
            return False
        return True

    window.connect("destroy", Gtk.main_quit)
    window.connect("key-press-event", on_key)

    window.show_all()
    back.set_sensitive(False)
    Gtk.main()
    return 0


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="MetaOS first-login welcome")
    parser.add_argument("--json", action="store_true", help="print the content as JSON")
    parser.add_argument("--mark", action="store_true", help="record that it was shown")
    parser.add_argument("--reset", action="store_true", help="show it again next login")
    parser.add_argument("--apps-dir", default=DEFAULT_APPS)
    parser.add_argument("--css", default=DEFAULT_CSS)
    parser.add_argument("--palette", default=DEFAULT_PALETTE)
    args = parser.parse_args(argv)

    if args.mark:
        print(mark())
        return 0
    if args.reset:
        marker_path().unlink(missing_ok=True)
        print("welcome: reset")
        return 0
    if args.json:
        print(json.dumps(build_content(args), indent=2))
        return 0

    if marker_path().is_file():
        print("welcome: already shown (%s)" % marker_path())
        return 0
    return run_gui(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
