#!/usr/bin/env python3
"""DSH-019 accessibility pass: no meaning carried by color alone.

Acceptance: each alert shows text severity; contrast notes in spec.
The audit at implementation time (2026-10-27) found the panel code
already satisfied the behavior — DSH-013's alert cards render icon +
severity text, DSH-006's crew rows render dot + state text, the
DSH-016 header strip is plain text, and every intel button carries a
visible text label. This file pins those facts so a later panel change
that drops a label, or introduces a color-only signal, fails the suite
instead of shipping silently, and it recomputes the spec's contrast
table instead of trusting the prose.

Contrast: WCAG relative-luminance ratios of the DSH-018 palette
foregrounds against the page background #0d1117 and the panel
background #161b22. Every value must clear WCAG AA for normal text
(4.5:1); the pass changes no palette value.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")

# Foreground -> backgrounds the panels render on (spec section 0).
BACKGROUNDS = ("#0d1117", "#161b22")
FOREGROUNDS = {
    "critical": "#f85149",
    "warning": "#d29922",
    "info": "#58a6ff",
    "muted": "#8b949e",
    "working": "#3fb950",
    "body": "#c9d1d9",
}
SEVERITY_ICONS = {"critical": "●", "warning": "▲", "info": "ℹ"}


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers (open + close), "
        "found %d" % len(parts))
    return parts[1]


def _luminance(hexcolor):
    rgb = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(fg, bg):
    a, b = _luminance(fg), _luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


class DashboardAccessibilityTest(unittest.TestCase):
    def test_bus_and_index_identical(self):
        # DSH-026 invariant: the accessibility checks on bus.html cover
        # index.html only if the two files are the same file.
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")

    def test_every_intel_button_has_text_label(self):
        # No icon-only buttons: each <button ...> in the intel module
        # must carry a visible text label before its </button>. Labels
        # are built by string concatenation (">Plan", "Post " + n +
        # " jobs"), so the check is per-chunk label containment, and
        # the button count is pinned — a new button fails here until
        # its label is added to the list, instead of slipping through
        # as an unlabeled control.
        with open(BUS, encoding="utf-8") as f:
            intel = _intel_module(f.read())
        opens = [m.start() for m in re.finditer(r"<button\b", intel)]
        self.assertEqual(len(opens), 6,
                         "intel button count changed from the DSH-014 "
                         "audit (Brief me now, Plan, Post N jobs, Reject "
                         "plan, Acknowledge, Resolve) — extend the label "
                         "list for the new button")
        labels = ("Brief me now", "Plan", "Post ", "Reject plan",
                  "Acknowledge", "Resolve")
        for start in opens:
            close = intel.find("</button>", start)
            self.assertNotEqual(close, -1,
                                "unclosed <button> in intel module: %r"
                                % intel[start:start + 80])
            chunk = intel[start:close]
            self.assertTrue(
                any(label in chunk for label in labels),
                "icon-only or unlabeled button in intel module: %r" % chunk)

    def test_severity_never_color_alone(self):
        # SEVERITY_STYLE pairs every severity with an icon, and
        # alertCardHTML emits icon + severity text in the same span.
        with open(BUS, encoding="utf-8") as f:
            intel = _intel_module(f.read())
        m = re.search(r"SEVERITY_STYLE = \{(.*?)\n  \};", intel, re.S)
        self.assertIsNotNone(m, "SEVERITY_STYLE block missing")
        for severity, icon in SEVERITY_ICONS.items():
            self.assertIn('%s: { color: "%s", icon: "%s"'
                          % (severity, FOREGROUNDS[severity], icon),
                          m.group(0),
                          "severity %s must pair color with icon" % severity)
        self.assertIn('U.esc(style.icon + " " + r.severity)',
                      intel,
                      "alert card must emit icon + severity text, not color alone")
        # The unknown-severity fallback also carries text, not just grey.
        self.assertIn('{ color: "#8b949e", icon: "○" }', intel)

    def test_crew_state_never_color_alone(self):
        # DSH-006 crew rows render dot + state text, not a bare color.
        with open(BUS, encoding="utf-8") as f:
            intel = _intel_module(f.read())
        self.assertIn("● ' + U.esc(stateText)", intel,
                      "crew row must emit dot + state text")
        # Header strip is plain escaped text — no color span at all.
        # DSH-032 adds a second line (today counters) the same way:
        # escaped text joined by <br>, still no color span.
        self.assertIn(
            'el.innerHTML = U.esc(line) + "<br>" + U.esc(todayLine(nowMs));',
            intel)

    def test_palette_contrast_meets_aa(self):
        # Every DSH-018 palette foreground clears WCAG AA (4.5:1) for
        # normal text on both panel backgrounds.
        for name, fg in FOREGROUNDS.items():
            for bg in BACKGROUNDS:
                self.assertGreaterEqual(
                    _ratio(fg, bg), 4.5,
                    "%s %s on %s fails WCAG AA: %.2f"
                    % (name, fg, bg, _ratio(fg, bg)))

    def test_spec_carries_dsh019_contrast_notes(self):
        # Acceptance: contrast notes in spec. The section must name
        # the DSH-019 audit, every severity hex, and the AA bar.
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Accessibility (DSH-019)", spec)
        for hexcolor in ("#f85149", "#d29922", "#58a6ff", "#8b949e"):
            self.assertIn(hexcolor, spec,
                          "spec contrast notes missing %s" % hexcolor)
        self.assertIn("4.5", spec, "spec contrast notes must state the AA bar")


if __name__ == "__main__":
    unittest.main()
