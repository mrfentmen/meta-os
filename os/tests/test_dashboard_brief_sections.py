#!/usr/bin/env python3
"""DSH-031 collapsible Brief sections (spec section 4).

Acceptance: long fixture brief renders without breaking panel layout.
Each section renders as a native <details> block — Blocked open, the
other four closed — and a reader's toggle survives a re-render. Items
render whole: nothing is truncated, so no text is ever cut mid-word.

The node driver stubs U.api/busHooks/document like the other dashboard
harness tests; the stub panel body carries no querySelectorAll, so the
live toggle-listener path is skipped and the harness drives toggles
through the ip.toggleBriefSection hook instead. The driver returns the
rendered brief innerHTML so the test asserts the markup itself, not
just the open map.
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")

LONG_DECISION = ("Ship the dashboard panel only after the full suite "
                 "is green, the bus.html/index.html diff is empty, and "
                 "the remote ref, parent, and blob bytes verify. ") * 20
LONG_BLOCKED = ("Job 9 is blocked on the dispatch engine landing, which "
                "is Pax lane work and has not merged yet. ") * 20

BRIEF = {
    "kind": "morning",
    "generated_at": 1793101200,
    "age_seconds": 900,
    "template": False,
    "sections": {
        "decisions": [LONG_DECISION, "Keep the 2s core poll."],
        "in_flight": ["DSH-031 collapsible sections."],
        "owners": [{"nick": "rowan", "job": 31, "title": "DSH-031"}],
        "blocked": [{"job": 9, "title": "dispatch engine",
                      "reason": LONG_BLOCKED}],
        "watch_items": [{"alert_id": "alert:1", "summary": "watchdog ok"}],
    },
}

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const NOW = 1793102100000;
global.window = {
  busUtil: {
    panel: (id) => {
      if (!bodies[id]) {
        bodies[id] = { innerHTML: "", parentNode: { open: false } };
      }
      return bodies[id];
    },
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
    nickColor: () => "#58a6ff",
    myNick: () => "rowan",
    busKey: () => "muse-bus",
    roomName: () => "(main)",
    api: async () => { throw new Error("no live api"); },
  },
  busHooks: { connect: [], poll: [] },
};
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: () => {} } },
};
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
ip.setBrief(__BRIEF__, NOW);
const before = {
  open: ip.briefSectionOpen(),
  html: bodies["intel-brief"].innerHTML,
};
ip.toggleBriefSection("decisions", NOW);
const after = {
  open: ip.briefSectionOpen(),
  html: bodies["intel-brief"].innerHTML,
};
console.log(JSON.stringify({ before: before, after: after }));
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_driver():
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    driver = NODE_DRIVER.replace("__BRIEF__", json.dumps(BRIEF))
    with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False) as mod:
        mod.write(module)
        mod_path = mod.name
    with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False) as drv:
        drv.write(driver.replace("__MODULE_PATH__", json.dumps(mod_path)))
        drv_path = drv.name
    try:
        out = subprocess.run(["node", "--check", mod_path],
                             capture_output=True, text=True, check=False)
        assert out.returncode == 0, "node --check failed: %s" % out.stderr
        res = subprocess.run(["node", drv_path],
                             capture_output=True, text=True, check=False)
        assert res.returncode == 0, "node driver failed: %s" % res.stderr
        return json.loads(res.stdout)
    finally:
        os.unlink(mod_path)
        os.unlink(drv_path)


class DashboardBriefSectionsTest(unittest.TestCase):
    def test_blocked_open_rest_closed_by_default(self):
        data = _run_driver()
        self.assertEqual(data["before"]["open"], {
            "decisions": False, "in_flight": False, "owners": False,
            "blocked": True, "watch_items": False})
        html = data["before"]["html"]
        self.assertIn('<details data-brief-section="blocked" open>',
                      html)
        self.assertIn('<details data-brief-section="decisions">', html)
        self.assertIn('<details data-brief-section="watch_items">', html)
        for title in ("Decisions", "In flight", "Owners",
                      "Blocked and why", "Watch items"):
            self.assertIn("<summary><b>%s</b></summary>" % title, html)

    def test_long_text_renders_whole_never_truncated(self):
        data = _run_driver()
        html = data["before"]["html"]
        # Whole items, verbatim — no ellipsis, no mid-word cut. The
        # blocked item renders with its "job title: " prefix.
        self.assertIn(LONG_DECISION, html)
        self.assertIn("- 9 dispatch engine: " + LONG_BLOCKED, html)
        self.assertNotIn("…", html)

    def test_toggle_survives_rerender(self):
        data = _run_driver()
        self.assertTrue(data["after"]["open"]["decisions"])
        self.assertTrue(data["after"]["open"]["blocked"])
        self.assertIn('<details data-brief-section="decisions" open>',
                      data["after"]["html"])
        self.assertIn(LONG_DECISION, data["after"]["html"])

    def test_index_matches_bus_and_spec_notes_dsh031(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")
        self.assertIn("data-brief-section", index)
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Implemented (DSH-031)", spec)


if __name__ == "__main__":
    unittest.main()
