#!/usr/bin/env python3
"""HN-008 Start screen: product start first, credentials behind Enter.

Acceptance: the first screen is a product start (product name,
systems list, status line, Enter button), not a raw credential form.
The credential inputs (URL, token, room, nick) and Connect live in
#credentials, hidden until Enter reveals them; Enter hides the start
screen and focuses the URL input. All credential element ids are
preserved, so the Connect flow and its tests are untouched. In demo
mode the start screen is hidden (the presentation shows panels).

These are static checks (the start screen lives in the shell script,
not the intelPanel module, so no node harness drives it): they pin
the structure and the handler code itself.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
# The dashboard page is bus.html. index.html was a second copy of it
# (DSH-026) and then became an app hub that nothing linked to; it was
# deleted 2026-11-04, so these tests read the one page that ships.
INDEX = os.path.join(REPO, "bus.html")

SYSTEMS = ("bus relay", "crew board", "jobs", "brief", "dispatch",
           "alerts", "watchdog")


class DashboardStartScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()

    def test_bus_and_index_identical(self):
        # One dashboard page, not two copies. index.html was the duplicate of
        # this file (DSH-026), then an app hub nothing linked to; it was deleted
        # 2026-11-04. The invariant these tests were protecting is now the
        # absence of the second file, not byte equality with it.
        self.assertFalse(os.path.exists(os.path.join(REPO, "index.html")),
                         "index.html must not exist; bus.html is the dashboard")


    def test_start_screen_comes_first(self):
        start = self.bus.index('<section id="start-screen">')
        header = self.bus.index("<header>")
        self.assertLess(start, header,
                        "start screen must precede the header")

    def test_start_screen_has_product_systems_status_enter(self):
        section = self.bus.split(
            '<section id="start-screen">', 1)[1].split("</section>", 1)[0]
        self.assertIn("muse-relay", section)
        for system in SYSTEMS:
            self.assertIn(system, section,
                          "start screen missing system %s" % system)
        self.assertIn('id="start-status"', section)
        self.assertIn("not connected", section)
        self.assertIn('<button id="start-enter">Enter</button>', section)

    def test_credentials_hidden_behind_enter(self):
        creds = self.bus.split('<div id="credentials" hidden>', 1)
        self.assertEqual(len(creds), 2,
                         "#credentials wrapper with hidden missing")
        body = creds[1].split("</div>", 1)[0]
        for element in ('id="url"', 'id="token"', 'id="room"',
                        'id="mynick"', 'id="go"'):
            self.assertIn(element, body,
                          "credential element %s left outside #credentials"
                          % element)

    def test_enter_handler_reveals_credentials_hides_start(self):
        handler = self.bus.split('HN-008: start screen.', 1)[1]
        handler = handler.split('("go")', 1)[0]
        self.assertIn('$("start-enter")', handler)
        self.assertIn('$("credentials")', handler)
        self.assertIn("creds.hidden = false", handler)
        self.assertIn('$("start-screen")', handler)
        self.assertIn("start.hidden = true", handler)
        self.assertIn('$("url")', handler)

    def test_demo_mode_hides_start_screen(self):
        style = self.bus.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertIn("body.demo-mode #start-screen { display: none; }",
                      style)

    def test_hint_directs_through_enter(self):
        self.assertIn("Click Enter above", self.bus)

    def test_no_new_hex_colors_in_start_screen(self):
        section = self.bus.split(
            '<section id="start-screen">', 1)[1].split("</section>", 1)[0]
        self.assertIsNone(
            re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", section),
            "start screen must use no new colors (DSH-018)")


if __name__ == "__main__":
    unittest.main()
