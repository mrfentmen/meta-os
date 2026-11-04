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
# The frame set is captured from the logo studio at 240 frames per turn — 1.5
# degrees apart. At 60 fps one revolution takes 4 s, and there is a new frame on
# every screen refresh, which is what makes it read as a live object rather than
# a slideshow. The set is too big to hold decoded (240 x 1920 x 1080 x 3 = 1.5
# GB), so FrameRing decodes ahead of the playhead instead.
FPS_IMAGES = int(os.environ.get("META_LIVE_FPS", "60"))
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


def _root_size(win):
    """The live size of the X root window — not a cached monitor list.

    The old code asked the screen for its primary monitor geometry. That list
    is rebuilt on a monitor change, and a resolution change driven from the
    QEMU window (the guest's mode follows the host window's size) does not
    always count as one — so the window kept being pushed back to the size the
    screen had a moment ago. get_width()/get_height() read the root window
    itself, which is the thing a wallpaper has to cover.
    """
    try:
        scr = win.get_screen()
        w, h = scr.get_width(), scr.get_height()
        if w > 1 and h > 1:
            return w, h
    except Exception:
        pass
    return 0, 0


def cover_metrics(pw, ph, width, height):
    """(scale, dx, dy) that paint a pw x ph frame over width x height.

    This is the arithmetic behind "the wallpaper is small and stuck in the
    corner": an image drawn at its natural size occupies one small rectangle of
    a bigger screen. Cover, not contain — the larger ratio reaches both edges
    and the overflow is split evenly, so the centre of the loop stays centred.

    A pure function of four numbers on purpose: test_cover.py checks every
    aspect ratio without a display, a pixbuf, or GTK.
    """
    if pw <= 0 or ph <= 0 or width <= 0 or height <= 0:
        return 1.0, 0.0, 0.0
    scale = max(width / float(pw), height / float(ph))
    return scale, (width - pw * scale) / 2.0, (height - ph * scale) / 2.0


def _pin_to_screen(win):
    """Sit exactly on the root window, and follow it when the screen resizes.

    Both halves of the resize bug lived in the old version of this: a
    win.maximize() (which xfwm4 sizes to the work area, i.e. inset by the
    panel, so the art stopped being a wallpaper) and a 1 s timer that
    re-applied the CACHED monitor geometry. After the resolution changed, that
    timer kept forcing the window back to the old size — the art stayed small
    in the corner of a screen that had grown around it, until something
    replaced the window (changing the wallpaper did).

    So: no timer. Resize once now, then again only on the signals that actually
    mean "the screen changed", and let the drawing surface cover whatever
    rectangle it is given.
    """
    from gi.repository import GLib

    def apply_now(*_args):
        w, h = _root_size(win)
        if w > 1 and h > 1:
            # move+resize, never maximize: the WM would apply panel struts.
            win.move(0, 0)
            win.resize(w, h)
        return False

    pending = {"id": 0}

    def schedule(*_args):
        # One idle refit per burst: a resize arrives as several signals
        # (size-changed, monitors-changed, configure) and resizing the window
        # again for each one would fight the server for no gain.
        if pending["id"]:
            return
        pending["id"] = GLib.idle_add(apply_now)

    try:
        scr = win.get_screen()
        scr.connect("size-changed", schedule)
        scr.connect("monitors-changed", schedule)
    except Exception:
        pass
    GLib.idle_add(apply_now)


def _cover_pixbuf(pixbuf, width, height):
    """Scale a frame to FILL width x height, cropping the overflow.

    Cover, not contain: cover_metrics() gives the scale and the centred offset,
    and the overflow is cut off. The result is exactly width x height, so the
    Gtk.Image that draws it can never letterbox or centre a smaller picture.

    GdkPixbuf scaling, not Cairo on purpose: this image has no python3-cairo,
    and a `draw` handler that receives a cairo.Context dies on the spot with
    "Couldn't find foreign struct converter for 'cairo.Context'" — which is
    exactly what happened when this was first written as a DrawingArea paint.
    When the frame is already the screen size, the original pixbuf is returned
    untouched, so the shipped 1920x1080 case costs nothing.
    """
    from gi.repository import GdkPixbuf
    pw, ph = pixbuf.get_width(), pixbuf.get_height()
    if pw <= 0 or ph <= 0 or width <= 0 or height <= 0:
        return pixbuf
    if (pw, ph) == (width, height):
        return pixbuf
    scale, _dx, _dy = cover_metrics(pw, ph, width, height)
    sw = max(width, int(round(pw * scale)))
    sh = max(height, int(round(ph * scale)))
    scaled = pixbuf.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
    if scaled is None:
        return pixbuf
    return scaled.new_subpixbuf((sw - width) // 2, (sh - height) // 2, width, height)


class FrameRing:
    """A bounded, decode-ahead window over a large frame set.

    Three ways to play 240 full-HD frames were possible and only one survives:

    * preload all of them — 1.5 GB of pixbufs, which is the VM's whole RAM;
    * decode on every tick — a 1920x1080 JPEG decode is ~10 ms, so at 60 fps
      every frame would arrive late and the animation would stutter worse than
      the 32-frame set it replaced;
    * decode ahead on one worker thread into a window of ~64 frames (~400 MB).
      The UI thread only blits.

    If the worker falls behind, get() returns None for that tick and the caller
    keeps the frame already on screen: a spin that is momentarily slower is
    honest, a blank desktop is not.
    """

    def __init__(self, files, window=64):
        import threading
        self.files = files
        self.window = max(4, window)
        self.frames = {}
        self.lock = threading.Lock()
        self.want = 0
        self.error = None
        self.stop = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _evict(self):
        n = len(self.files)
        keep = set((self.want + k) % n for k in range(-1, self.window))
        self.frames = dict((k, v) for k, v in self.frames.items() if k in keep)

    def _run(self):
        import time
        from gi.repository import GdkPixbuf
        n = len(self.files)
        while not self.stop:
            i = self.want % n
            with self.lock:
                have = i in self.frames
            if have:
                time.sleep(0.002)
                continue
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(self.files[i])
            except Exception as exc:
                self.error = str(exc)
                time.sleep(0.05)
                continue
            with self.lock:
                self.frames[i] = pb
                self._evict()

    def get(self, index):
        n = len(self.files)
        self.want = index + 1
        with self.lock:
            return self.frames.get(index % n)


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
    # size the pixbuf happens to be, which was the small-in-the-corner bug.
    # Below, the pixbuf is also re-cut to exactly the widget's allocation, so
    # "whatever size it happens to be" is always the whole window.
    img.set_halign(Gtk.Align.FILL)
    img.set_valign(Gtk.Align.FILL)
    win.add(img)
    win.show_all()
    _pin_to_screen(win)
    state = {"i": 0, "frame": None, "size": (0, 0)}

    # Decode-ahead window instead of a full preload: the set is 240 frames and
    # holding it decoded would cost more memory than the VM has.
    ring = FrameRing(files)

    def target_size():
        """What the picture is actually drawn into.

        The widget's allocation, not the window's: that is the rectangle GTK
        will paint, and it is already correct in the frame that follows a
        resize. The root window is only the fallback for the first ticks,
        before anything has been allocated.
        """
        w, h = img.get_allocated_width(), img.get_allocated_height()
        if w <= 1 or h <= 1:
            return _root_size(win)
        return w, h

    def repaint():
        frame = state["frame"]
        w, h = target_size()
        if frame is None or w <= 1 or h <= 1:
            return
        state["size"] = (w, h)
        img.set_from_pixbuf(_cover_pixbuf(frame, w, h))

    busy = {"v": False}

    def on_allocate(*_args):
        # A new allocation invalidates the pixbuf cut for the old one, so cut it
        # again from the frame already on screen — do not wait for the next
        # 1/60 s tick, which a stalled decode ring could delay indefinitely.
        # Guarded, because set_from_pixbuf can itself trigger an allocate in a
        # window that is not allowed to shrink, and the two would then bounce
        # off each other forever.
        if busy["v"] or state["frame"] is None:
            return
        if target_size() == state["size"]:
            return
        busy["v"] = True
        try:
            repaint()
        finally:
            busy["v"] = False

    img.connect("size-allocate", on_allocate)

    def show():
        frame = ring.get(state["i"])
        if frame is not None:
            state["frame"] = frame
            repaint()
        state["i"] += 1
        return True

    show()
    GLib.timeout_add(max(1, 1000 // FPS_IMAGES), show)
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
    label.set_halign(Gtk.Align.CENTER)
    label.set_valign(Gtk.Align.CENTER)
    win.add(label)
    win.show_all()
    _pin_to_screen(win)
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
