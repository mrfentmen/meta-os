#!/usr/bin/env python3
"""MetaOS live ASCII background — the REAL kernel attract art, cycling live.

Reads the exact frames from kernel/src/logo_frames.rs (exported here as
frames.txt) and paints them in a borderless desktop-layer GTK window at
8 fps — the same cadence as the kernel console idle task. No video files,
no browser, no compositor tricks: pure GTK + Pango, ~100 lines.

Runs anywhere GTK3 + monospace exists. Falls back to a static first
frame when there is no display (headless test path).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES_PATH = os.path.join(HERE, "frames.txt")
FPS = 8
INK = (0.027, 0.043, 0.086)
BLUE = "#1877F2"
BRIGHT = "#78BAFF"
DENSE = set("#@%&M9")


def load_frames(path=FRAMES_PATH):
    with open(path) as f:
        raw = f.read()
    frames = [b.split("\n") for b in raw.split("\n===FRAME===\n")]
    return frames


def pick_color(ch):
    return BRIGHT if ch in DENSE else BLUE


class Cycler:
    """Headless-cyclable frame ticker: tick() advances, frame() reads."""

    def __init__(self, frames, fps=FPS):
        self.frames = frames
        self.fps = fps
        self.index = 0

    def tick(self):
        self.index = (self.index + 1) % len(self.frames)
        return self.index

    def frame(self):
        return self.frames[self.index]


def run_gui(frames):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GLib, Pango
    css = b"""
    .meta-bg { background: #070B16; }
    .meta-bg label { font-family: monospace; }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    win = Gtk.Window()
    win.set_decorated(False)
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.set_keep_below(True)
    win.stick()
    try:
        win.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
    except Exception:
        pass
    label = Gtk.Label()
    label.get_style_context().add_class("meta-bg")
    label.set_selectable(False)
    win.add(label)
    win.maximize()
    win.show_all()
    below = [w for w in win.get_screen().get_window_stack()
             if w != win.get_window()]
    for w in below:
        try:
            w.lower()
        except Exception:
            pass
    cycler = Cycler(frames)

    def render():
        text = "\n".join(cycler.frame())
        label.set_markup(
            '<span font_family="monospace" font="14" '
            'foreground="#1877F2">' +
            text.replace("&", "&amp;").replace("<", "&lt;") +
            "</span>")
        return True

    def on_tick():
        cycler.tick()
        render()
        GLib.timeout_add(1000 // FPS, on_tick)
        return False

    render()
    GLib.timeout_add(1000 // FPS, on_tick)
    Gtk.main()
    return 0


def main(argv):
    frames = load_frames()
    if not frames or not any(any(r.strip() for r in f) for f in frames):
        print("meta-live: no frames", file=sys.stderr)
        return 1
    if "--once" in argv or "DISPLAY" not in os.environ:
        print(f"meta-live: {len(frames)} frames loaded, headless OK")
        return 0
    return run_gui(frames)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
