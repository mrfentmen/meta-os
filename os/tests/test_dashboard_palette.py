#!/usr/bin/env python3
"""DSH-018 dark-theme consistency: no off-palette colors in new dashboard UI.

The four intel panels (Crew Board, Brief, Dispatch, Alerts) plus the
DSH-016 header strip and the DSH-017 mobile rules are the dashboard's
new UI in bus.html. This test is the automated form of DSH-018's
acceptance check (visual diff review vs the existing panels): every
hex color literal in the intelPanel module, and every hex in a
head-CSS rule that mentions an intel panel, must already be used
elsewhere in bus.html — i.e. it is part of the pre-existing
GitHub-dark palette, not a new color scheme.

Audit at time of writing (2026-10-26, DSH-018): the intel module uses
exactly six hex values, all pre-existing —
  #30363d (panel border), #3fb950 (working / live green),
  #58a6ff (info / link blue), #8b949e (muted / unknown severity),
  #d29922 (warning / amber), #f85149 (blocked / critical / watchdog-silent red).
The severity mapping is exactly those pre-existing values: critical
is the blocked red, warning the amber bar, info the link blue — the
colors Milo's alert mapping already names (spec section 6), not new
ones. The intel head-CSS rules (DSH-017 mobile pass, header strip)
contain no hex at all. Nick colors are not hex literals: the panels
reuse the core U.nickColor() hsl() helper, as every existing panel does.

No new timers, no posting, no panel behavior is changed here — this
file only pins the palette, so a future panel change that introduces
an off-palette hex fails the suite instead of shipping silently.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# The six palette values the audit found in the intel module, each
# with the pre-existing panel element it matches.
INTEL_HEX = {"#30363d", "#3fb950", "#58a6ff", "#8b949e", "#d29922", "#f85149"}
SEVERITY_HEX = {"critical": "#f85149", "warning": "#d29922", "info": "#58a6ff"}


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers (open + close), "
        "found %d" % len(parts))
    return parts[1], parts[0] + parts[2]


def _head_css(html):
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    assert m, "bus.html <style> block missing"
    return m.group(1)


class DashboardPaletteTest(unittest.TestCase):
    def test_bus_and_index_identical(self):
        # DSH-026 invariant: the palette check on bus.html covers
        # index.html only if the two files are the same file.
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")

    def test_intel_hex_subset_of_preexisting_palette(self):
        with open(BUS, encoding="utf-8") as f:
            html = f.read()
        intel, rest = _intel_module(html)
        intel_hex = set(HEX_RE.findall(intel))
        preexisting = set(HEX_RE.findall(rest))
        self.assertEqual(intel_hex, INTEL_HEX,
                         "intel module hex set changed from the DSH-018 audit: %s"
                         % sorted(intel_hex))
        off_palette = sorted(intel_hex - preexisting)
        self.assertEqual(off_palette, [],
                         "off-palette hex in intel panels (not used elsewhere "
                         "in bus.html): %s" % off_palette)

    def test_severity_colors_are_existing_palette_only(self):
        with open(BUS, encoding="utf-8") as f:
            html = f.read()
        intel, _rest = _intel_module(html)
        m = re.search(r"SEVERITY_STYLE = \{(.*?)\n  \};", intel, re.S)
        self.assertIsNotNone(m, "SEVERITY_STYLE block missing from intel module")
        for severity, color in SEVERITY_HEX.items():
            self.assertIn('%s: { color: "%s"' % (severity, color),
                          m.group(0),
                          "severity %s must use pre-existing %s" % (severity, color))
        # The unknown-severity fallback is the muted grey, not a new color.
        self.assertIn('{ color: "#8b949e"', intel)

    def test_intel_head_css_has_no_hex(self):
        with open(BUS, encoding="utf-8") as f:
            html = f.read()
        css = _head_css(html)
        for line in css.splitlines():
            if "intel" in line:
                self.assertEqual(HEX_RE.findall(line), [],
                                 "intel head-CSS rule carries a color: %s"
                                 % line.strip())


if __name__ == "__main__":
    unittest.main()
