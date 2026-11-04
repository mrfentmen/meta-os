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
IMAGES_DIR = os.path.join(os.path.dirname(HERE), "studio-loop")
# Two install layouts exist: the app tree (/usr/share/metaos/studio-loop, next
# to this file) and the theme tree (/usr/share/backgrounds/metaos-studio, which
# the ISO provision writes). Whichever holds frames first wins, so a build that
# only gets the theme tree still animates instead of silently showing nothing.
IMAGES_DIRS = [
    os.environ.get("META_LIVE_IMAGES") or IMAGES_DIR,
    IMAGES_DIR,
    "/usr/share/backgrounds/metaos-studio",
]
# The frame set is now captured from the logo studio at 60 frames per turn
# (the old kernel set was 16 frames, 22.5 degrees apart — a stutter, not a
# spin). At 30 fps one revolution takes 2 s, the same speed as before with
# nearly four times the frames.
FPS_IMAGES = int(os.environ.get("META_LIVE_FPS", "30"))
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


def _fit_to_screen(win):
    """A wallpaper window must be exactly the screen, not whatever xfwm4
    hands a maximized window.

    win.maximize() on XFCE respects panel struts, so the art ends up inset by
    the panel height and stops looking like a wallpaper. Asking the monitor
    for its geometry and setting it directly cannot be argued with.
    """
    try:
        scr = win.get_screen()
        geo = scr.get_monitor_geometry(scr.get_primary_monitor())
        win.move(geo.x, geo.y)
        win.resize(geo.width, geo.height)
    except Exception:
        pass


def _cover(pixbuf, width, height):
    """Scale a frame to FILL width x height, cropping the overflow.

    This is the fix for "the wallpaper is small and stuck in the corner".
    Gtk.Image draws a pixbuf at its natural size: a 1920x1080 frame on a
    1600x900 screen was centred with black bars, and a 1280x720 frame on a
    1920x1080 screen sat in the middle as a postage stamp. A wallpaper has to
    cover the screen, not fit inside it.

    Cover, not contain: scale by the larger of the two ratios so both edges are
    reached, then take the centred sub-pixbuf, which throws away the overflow.
    The result is exactly width x height, so the Gtk.Image can never letterbox.

    Cost: one bilinear scale per frame, only when the frame size differs from
    the screen. In the shipped configuration the studio renders its loop at
    1920x1080 and the session runs at 1920x1080, so this returns the original
    pixbuf untouched and costs nothing. It is here for every other resolution,
    and that is worth a scale per frame rather than a postage stamp.
    """
    from gi.repository import GdkPixbuf
    pw, ph = pixbuf.get_width(), pixbuf.get_height()
    if pw <= 0 or ph <= 0 or width <= 0 or height <= 0:
        return pixbuf
    if (pw, ph) == (width, height):
        return pixbuf
    scale = max(width / float(pw), height / float(ph))
    sw = max(width, int(round(pw * scale)))
    sh = max(height, int(round(ph * scale)))
    scaled = pixbuf.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
    if scaled is None:
        # Out of memory or a broken codec: a centred frame beats a blank screen.
        return pixbuf
    return scaled.new_subpixbuf((sw - width) // 2, (sh - height) // 2, width, height)


def _screen_size(win):
    """The size the wallpaper must cover, read from the window we just sized.

    _fit_to_screen() has already set the window to the monitor geometry, so the
    window's own allocation is the truth here. Falling back to the monitor
    geometry covers the frame before the first allocation, when the window is
    still 1x1.
    """
    try:
        w, h = win.get_size()
        if w > 1 and h > 1:
            return w, h
    except Exception:
        pass
    try:
        scr = win.get_screen()
        geo = scr.get_monitor_geometry(scr.get_primary_monitor())
        return geo.width, geo.height
    except Exception:
        return 0, 0


def run_gui_images(framedir):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GLib
    import glob
    for cand in ([framedir] + [d for d in IMAGES_DIRS if d != framedir]):
        files = sorted(glob.glob(os.path.join(cand, "loop-*.jpg")))
        if files:
            framedir = cand
            break
    else:
        return 1
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
    img = Gtk.Image()
    # FILL, not CENTER: with the default alignment Gtk.Image centres whatever
    # size the pixbuf happens to be, which is the small-in-the-corner bug.
    img.set_halign(Gtk.Align.FILL)
    img.set_valign(Gtk.Align.FILL)
    win.add(img)
    win.maximize()
    win.show_all()
    _fit_to_screen(win)
    # Re-assert once a second: xfwm4 can re-place the window when the panel
    # starts or the resolution changes under it (the guest tracks the window
    # size), and a wallpaper that shrinks on resize is not a wallpaper.
    GLib.timeout_add(1000, lambda: (_fit_to_screen(win), True)[1])
    state = {"i": 0}

    # Decode once, then blit. set_from_file() decodes a 1920x1080 JPEG on every
    # tick, and at 30 fps that is a file decode 30 times a second for art that
    # never changes inside the loop — the wallpaper should cost a blit, not a
    # decoding pipeline. If the decode of the whole set cannot be held in
    # memory, fall back to the per-frame file read rather than failing to draw.
    preloaded = []
    try:
        from gi.repository import GdkPixbuf
        preloaded = [GdkPixbuf.Pixbuf.new_from_file(f) for f in files]
    except Exception:
        preloaded = []

    def show():
        width, height = _screen_size(win)
        if preloaded:
            frame = preloaded[state["i"] % len(preloaded)]
        else:
            from gi.repository import GdkPixbuf
            frame = GdkPixbuf.Pixbuf.new_from_file(files[state["i"] % len(files)])
        img.set_from_pixbuf(_cover(frame, width, height))
        state["i"] += 1
        return True

    show()
    GLib.timeout_add(1000 // FPS_IMAGES, show)
    Gtk.main()
    return 0


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
    _fit_to_screen(win)
    # Re-assert once a second: xfwm4 can re-place the window when the panel
    # starts or the resolution changes under it (the guest tracks the window
    # size), and a wallpaper that shrinks on resize is not a wallpaper.
    GLib.timeout_add(1000, lambda: (_fit_to_screen(win), True)[1])
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
    imgdir = os.environ.get("META_LIVE_IMAGES", IMAGES_DIR)
    import glob as _g
    if os.path.isdir(imgdir) and _g.glob(os.path.join(imgdir, "loop-*.jpg")):
        if "--once" in argv or "DISPLAY" not in os.environ:
            n = len(_g.glob(os.path.join(imgdir, "loop-*.jpg")))
            print(f"meta-live: image mode, {n} studio frames, headless OK")
            return 0
        return run_gui_images(imgdir)
    if "--once" in argv or "DISPLAY" not in os.environ:
        print(f"meta-live: {len(frames)} frames loaded, headless OK")
        return 0
    return run_gui(frames)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
