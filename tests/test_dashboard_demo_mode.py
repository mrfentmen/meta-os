#!/usr/bin/env python3
"""DSH-028 dashboard demo mode (spec section 8).

Acceptance: ?demo=1 enlarges type, hides token/setup chrome, and pins
the four intel panels open; a normal URL is unchanged. The node
driver stubs U.api/busHooks/document like the other dashboard harness
tests; the stub panel bodies carry a parentNode so the test exercises
the same open-the-<details> path the live viewer takes, and the
snapshot carries demoMode + demoPinned as the harness-visible record.
CSS rules are asserted from the style block, not from a live browser:
the demo class, the enlarged type, and the hidden chrome are all in
bus.html itself.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const bodyClasses = [];
const LOC = __LOCATION__;
const NOW = 1700000000000;
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
    api: async (path) => {
      const dec = decodeURIComponent(path);
      if (dec.indexOf("/zrange/") >= 0 || dec.indexOf("/hgetall/") >= 0) {
        return { result: [] };
      }
      throw new Error("unexpected api path " + path);
    },
  },
  busHooks: { connect: [], poll: [] },
};
if (LOC) global.window.location = LOC;
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: (c) => bodyClasses.push(c) } },
};
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
ip.setCrew([], NOW);
ip.setBrief(null, NOW);
ip.setPlan(null);
ip.setAlerts([], NOW);
const snap = ip.snapshot();
const out = {
  demoMode: snap.demoMode,
  demoPinned: snap.demoPinned,
  bodyClasses: bodyClasses,
  crewOpen: bodies["intel-crew"].parentNode.open,
  briefOpen: bodies["intel-brief"].parentNode.open,
  dispatchOpen: bodies["intel-dispatch"].parentNode.open,
  alertsOpen: bodies["intel-alerts"].parentNode.open,
};
console.log(JSON.stringify(out));
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_node(module, location):
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        mod_path = f.name
        f.write(module)
    driver = NODE_DRIVER.replace("__MODULE_PATH__",
                                 json.dumps(mod_path))
    driver = driver.replace("__LOCATION__", json.dumps(location))
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        drv_path = f.name
        f.write(driver)
    try:
        r = subprocess.run(["node", drv_path], capture_output=True,
                           text=True, timeout=60)
    finally:
        os.unlink(mod_path)
        os.unlink(drv_path)
    assert r.returncode == 0, "node failed: %s" % r.stderr
    return json.loads(r.stdout)


PANELS = ["intel-crew", "intel-brief", "intel-dispatch", "intel-alerts"]


class DashboardDemoModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.results = {
            "demo": _run_node(cls.intel, {"search": "?demo=1"}),
            "demo_mid": _run_node(
                cls.intel, {"search": "?x=1&demo=1&y=2"}),
            "demo_trap": _run_node(cls.intel, {"search": "?demo=10"}),
            "normal": _run_node(cls.intel, {"search": ""}),
            "absent": _run_node(cls.intel, None),
        }

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: checks on bus.html cover index.html
        # only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_demo_flag_on_for_demo_query(self):
        self.assertTrue(self.results["demo"]["demoMode"])
        self.assertTrue(self.results["demo_mid"]["demoMode"])

    def test_demo_flag_off_otherwise(self):
        # demo=10 must not match (no prefix trap), nor an empty
        # query, nor a viewer with no location at all.
        self.assertFalse(self.results["demo_trap"]["demoMode"])
        self.assertFalse(self.results["normal"]["demoMode"])
        self.assertFalse(self.results["absent"]["demoMode"])

    def test_demo_pins_all_four_panels_open(self):
        r = self.results["demo"]
        self.assertEqual(r["demoPinned"], PANELS)
        self.assertTrue(r["crewOpen"])
        self.assertTrue(r["briefOpen"])
        self.assertTrue(r["dispatchOpen"])
        self.assertTrue(r["alertsOpen"])

    def test_demo_adds_body_class(self):
        self.assertEqual(self.results["demo"]["bodyClasses"],
                         ["demo-mode"])
        self.assertEqual(self.results["demo_mid"]["bodyClasses"],
                         ["demo-mode"])

    def test_normal_url_pins_nothing(self):
        for name in ("demo_trap", "normal", "absent"):
            r = self.results[name]
            self.assertEqual(r["demoPinned"], [],
                             "%s pinned %r" % (name, r["demoPinned"]))
            self.assertEqual(r["bodyClasses"], [])
            self.assertFalse(r["crewOpen"])
            self.assertFalse(r["briefOpen"])
            self.assertFalse(r["dispatchOpen"])
            self.assertFalse(r["alertsOpen"])

    def test_demo_css_enlarges_type_and_hides_setup_chrome(self):
        style = self.bus.split("<style>")[1].split("</style>")[0]
        self.assertIn("body.demo-mode { font-size: 18px; }", style)
        self.assertIn("body.demo-mode #panels { font-size: 17px; }",
                      style)
        self.assertIn("body.demo-mode header input#url", style)
        self.assertIn("body.demo-mode header input#token", style)
        self.assertIn("body.demo-mode #hint { display: none; }", style)
        # No new colors: the demo block adds no hex value (id
        # selectors like #url are not colors, so match hex only).
        demo = style.split("body.demo-mode {")[1].split(
            "display: none; }")[0]
        self.assertIsNone(
            re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", demo))

    def test_spec_documents_demo_mode(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("DSH-028", spec)
        self.assertIn("?demo=1", spec)


if __name__ == "__main__":
    unittest.main()
