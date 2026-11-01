#!/usr/bin/env python3
"""STR-005 SAM visual verdicts in the Brief panel (spec section 4).

Acceptance: the Visual checks subsection renders from an example
payload and is absent cleanly when no data exists. The SAM pass /
STR-002 screenshot digest has not landed, so this pins the render
path only: no verdict is produced here, and a brief without
visual_checks renders exactly as before.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests; setBrief feeds the fixture brief and the
driver returns the rendered brief innerHTML plus the normalized
checks from the briefVisualChecks hook.
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

BASE = {
    "kind": "morning",
    "generated_at": 1793101200,
    "age_seconds": 900,
    "template": False,
    "sections": {
        "decisions": ["Keep the 2s core poll."],
        "in_flight": [],
        "owners": [],
        "blocked": [],
        "watch_items": [],
    },
}

WITH_CHECKS = dict(BASE)
WITH_CHECKS["visual_checks"] = [
    {"screenshot": "dashboard 2026-10-27 09:00",
     "verdict": "build ok",
     "detail": "All four panels render."},
    {"screenshot": "dispatch preview 2026-10-27 09:00",
     "verdict": "build broken",
     "detail": "Plan rows missing at phone width."},
    {"screenshot": "alerts 2026-10-27 09:00",
     "verdict": "unclear",
     "detail": "Screenshot too dark to read."},
    {"ref": "alias shot", "label": "build ok", "note": "alias form."},
    {"verdict": "maybe", "detail": "unrecognized verdict stays verbatim."},
    {"verdict": "  ", "detail": "blank verdicts are dropped."},
    {"verdict": "build ok",
     "detail": "<script>alert(1)</script> is escaped, not run."},
]

WITHOUT_CHECKS = dict(BASE)

EMPTY_CHECKS = dict(BASE)
EMPTY_CHECKS["visual_checks"] = []

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
console.log(JSON.stringify({
  html: bodies["intel-brief"].innerHTML,
  checks: ip.briefVisualChecks(),
}));
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_driver(brief):
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    driver = NODE_DRIVER.replace("__BRIEF__", json.dumps(brief))
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


class DashboardStr005Test(unittest.TestCase):
    def test_visual_checks_render_with_verdicts_and_refs(self):
        data = _run_driver(WITH_CHECKS)
        html = data["html"]
        self.assertIn('<details data-brief-visual-checks open>', html)
        self.assertIn("<summary><b>Visual checks</b></summary>", html)
        self.assertIn("✓ build ok", html)
        self.assertIn("✗ build broken", html)
        self.assertIn("? unclear", html)
        self.assertIn("dashboard 2026-10-27 09:00", html)
        self.assertIn("All four panels render.", html)
        self.assertIn("Plan rows missing at phone width.", html)
        # The five normal sections still render alongside.
        for title in ("Decisions", "In flight", "Owners",
                      "Blocked and why", "Watch items"):
            self.assertIn("<summary><b>%s</b></summary>" % title, html)

    def test_alias_forms_normalize_and_unknown_stays_verbatim(self):
        data = _run_driver(WITH_CHECKS)
        checks = data["checks"]
        self.assertEqual(len(checks), 6)
        alias = [c for c in checks if c["screenshot"] == "alias shot"]
        self.assertEqual(len(alias), 1)
        self.assertEqual(alias[0]["verdict"], "build ok")
        self.assertEqual(alias[0]["detail"], "alias form.")
        unknown = [c for c in checks if c["verdict"] == "maybe"]
        self.assertEqual(len(unknown), 1)
        self.assertIn("? maybe", data["html"])
        self.assertNotIn("? build ok", data["html"])

    def test_detail_is_escaped_not_raw(self):
        data = _run_driver(WITH_CHECKS)
        html = data["html"]
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_absent_cleanly_without_field(self):
        data = _run_driver(WITHOUT_CHECKS)
        self.assertEqual(data["checks"], [])
        self.assertNotIn("Visual checks", data["html"])
        self.assertNotIn("data-brief-visual-checks", data["html"])
        # The brief itself still renders: kind + normal sections.
        self.assertIn("morning", data["html"])
        self.assertIn("<summary><b>Decisions</b></summary>", data["html"])

    def test_absent_cleanly_with_empty_list(self):
        data = _run_driver(EMPTY_CHECKS)
        self.assertEqual(data["checks"], [])
        self.assertNotIn("Visual checks", data["html"])
        self.assertNotIn("data-brief-visual-checks", data["html"])

    def test_index_matches_bus_and_spec_notes_str005(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")
        self.assertIn("data-brief-visual-checks", index)
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Visual checks (STR-005", spec)


if __name__ == "__main__":
    unittest.main()
