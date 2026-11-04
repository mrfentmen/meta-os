#!/usr/bin/env python3
"""Headless contract test: native window title-bar controls (lane R2-T2, E/85).

Honest option chosen: (a) — pure-logic tests against importable window-spec
functions. This became possible when sections A/B restructured meta-app.py so
the whole policy surface (button spec, menu map, accelerators, click/escape
actions, keep-above subtitle, backdrop/focus CSS) imports WITHOUT gi: on this
macOS box `import gi` fails (no PyGObject, no X server, no Xvfb) and the
module still loads with GTK_AVAILABLE False. No stubs, no restructuring of
anyone else's code — the tests below call the shipped helpers directly.

What this proves headless (real logic, real assertions):
  * header_button_spec() exposes exactly one close, one minimise and one
    maximise control (section A task 21), plus an unmute toggle ONLY for
    audio apps (task 32).
  * TITLE_MENU_ITEMS carries Close/Minimise/Maximise/Always-on-top in order
    (task 16); title_menu_action() maps each label to its window action.
  * ACCEL_MAP binds Alt+F4/F9/F10 (task 7); escape_action() never closes the
    app itself (task 8); double_click_action() toggles maximise (task 15);
    above_subtitle() reflects keep-above in the bar (task 17).
  * The CSS ships backdrop (unfocused) styling (task 18: focused window is
    visually distinct) and a visible focus ring for keyboard reachability
    (task 19).
  * AppWindow consumes header_button_spec (wiring check against the source,
    so the spec cannot rot unreferenced).
What still needs a booted guest: pixels, hover/active/disabled states,
drag-select behavior, title-bar geometry vs page header at 1440x900, focus
ring visibility, WM decoration layout. See GUEST_STEPS / --guest.

Usage: python3 test-window-chrome.py            (unittest, exit != 0 on fail)
       python3 test-window-chrome.py --guest    (print the guest test only)
"""
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_PATH = os.path.join(_HERE, "meta-app.py")


def load_app_module():
    spec = importlib.util.spec_from_file_location("meta_app_live", _APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_app_module()
if app.GTK_AVAILABLE:
    raise SystemExit("unexpected: GTK importable on the headless prover")

GUEST_STEPS = """Guest proof for title-bar controls (needs a booted MetaOS guest):
  G1. Boot the image at 1440x900, log in, open Board from the dock.
      Expect: one window titled "Board" (never a URL or "Epiphany"); top-right
      shows exactly three controls: minimise, maximise, close.
  G2. Hover/press/disabled on close: hover highlights, press closes ONLY that
      app window (session stays up; dock running indicator for Board clears).
  G3. Alt+F4 closes, Alt+F9 minimises, Alt+F10 maximises; Esc in a dialog
      closes the dialog, never the app.
  G4. Drag the title bar: window moves, no text selection. Double-click the
      bar toggles maximise/restore. Right-click the bar shows
      Close/Minimise/Maximise/Always-on-top; Always-on-top pins and shows the
      "Always on top" subtitle marker in the bar.
  G5. Screenshot: `import -window <id> /tmp/t2-titlebar-1440x900.png`
      (or gnome-screenshot -w). The capture must show all three controls and
      no page header overlapping them.
"""


class TestButtonSpec(unittest.TestCase):
    def test_exactly_one_of_each_control(self):
        # Section A task 21: every native window exposes exactly one close,
        # one minimise and one maximise control.
        roles = [b["role"] for b in app.header_button_spec()]
        self.assertEqual(roles.count("close"), 1, roles)
        self.assertEqual(roles.count("minimize"), 1, roles)
        self.assertEqual(roles.count("maximize"), 1, roles)
        self.assertEqual(len(roles), 3, roles)

    def test_close_is_wm_provided_min_max_are_explicit(self):
        # The contract: the WM draws the single close button; our own header
        # buttons supply minimise/maximise (see AppWindow wiring + task 2).
        by_role = {b["role"]: b for b in app.header_button_spec()}
        self.assertEqual(by_role["close"]["kind"], "wm")
        self.assertEqual(by_role["minimize"]["kind"], "explicit")
        self.assertEqual(by_role["maximize"]["kind"], "explicit")

    def test_unmute_toggle_only_for_audio_apps(self):
        # Section B task 32: autoplay off by default; a visible unmute
        # control exists only where the app needs it (Musica tile).
        plain = [b["role"] for b in app.header_button_spec()]
        audio = [b["role"] for b in app.header_button_spec(allow_audio=True)]
        self.assertNotIn("unmute", plain)
        self.assertIn("unmute", audio)
        self.assertEqual(audio.count("unmute"), 1)

    def test_spec_consumed_by_app_window(self):
        # The spec must actually drive the window, not sit unused: AppWindow
        # builds its chrome from header_button_spec().
        with open(_APP_PATH, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("header_button_spec(", src)
        self.assertIn("for spec in header_button_spec(", src)


class TestTitleMenuAndShortcuts(unittest.TestCase):
    def test_title_menu_items_in_order(self):
        # Section A task 16: right-click title-bar menu.
        labels = [label for label, _action in app.TITLE_MENU_ITEMS]
        self.assertEqual(labels,
                         ["Close", "Minimise", "Maximise", "Always on top"])

    def test_title_menu_maps_to_actions(self):
        self.assertEqual(app.title_menu_action("Close"), "close-window")
        self.assertEqual(app.title_menu_action("Minimise"), "minimize")
        self.assertEqual(app.title_menu_action("Maximise"),
                         "toggle-maximize")
        self.assertEqual(app.title_menu_action("Always on top"),
                         "toggle-above")
        self.assertIsNone(app.title_menu_action("No such item"))

    def test_accelerators(self):
        # Section A task 7: Alt+F4 close, Alt+F9 minimise, Alt+F10 maximise.
        self.assertEqual(app.ACCEL_MAP.get("<Alt>F4"), "close-window")
        self.assertEqual(app.ACCEL_MAP.get("<Alt>F9"), "minimize")
        self.assertEqual(app.ACCEL_MAP.get("<Alt>F10"), "toggle-maximize")

    def test_escape_never_closes_app(self):
        # Section A task 8: Escape closes transient dialogs only.
        self.assertEqual(app.escape_action("dialog"), "close")
        self.assertEqual(app.escape_action("menu"), "close")
        self.assertEqual(app.escape_action("find-visible"), "hide-find")
        self.assertEqual(app.escape_action("main"), "none")

    def test_double_click_toggles_maximise(self):
        # Section A task 15.
        self.assertEqual(app.double_click_action(2, 1), "toggle-maximize")
        self.assertIsNone(app.double_click_action(1, 1))
        self.assertIsNone(app.double_click_action(2, 3))

    def test_keep_above_reflected_in_bar(self):
        # Section A task 17: "always on top" is real AND visible.
        self.assertEqual(app.above_subtitle(True), "Always on top")
        self.assertEqual(app.above_subtitle(False), "")


class TestFocusAndTheme(unittest.TestCase):
    def test_backdrop_style_distinguishes_unfocused(self):
        # Section A task 18: the focused window is visually distinct.
        self.assertIn("window:backdrop", app.CSS.decode("utf-8"))

    def test_focus_ring_for_keyboard_reachability(self):
        # Section A task 19: Tab-reachable controls show a focus ring.
        css = app.CSS.decode("utf-8")
        self.assertIn("button:focus", css)
        self.assertIn("#1877f2", css.lower())

    def test_guest_steps_documented(self):
        self.assertIn("1440x900", GUEST_STEPS)
        self.assertIn("Alt+F4", GUEST_STEPS)


if __name__ == "__main__":
    if "--guest" in sys.argv:
        sys.stdout.write(GUEST_STEPS)
    else:
        unittest.main()
