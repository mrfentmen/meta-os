#!/usr/bin/env python3
"""DOC-017 dashboard help panel (spec section 8).

Acceptance: help text shipped in the bus.html viewer — a static
"Dashboard help" panel naming, per intel panel, what it reads and
how often it refreshes. The node driver stubs U.api/busHooks/
document like the other dashboard harness tests; the help panel
is static, so the test asserts its rendered text, not fixture
state. It also pins the two invariants the help panel must not
break: no new hex colors (DSH-018 palette) and no demo pinning
(DSH-028 pins exactly the four intel panels).
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
global.window = {
  busUtil: {
    panel: (id, title) => {
      if (!bodies[id]) {
        bodies[id] = { innerHTML: "", parentNode: { open: false },
                       title: title || "" };
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
    api: async () => { throw new Error("help panel reads nothing"); },
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
if (!ip.renderHelp) throw new Error("renderHelp hook missing");
ip.renderHelp();
const help = bodies["intel-help"] || {};
const out = {
  helpTitle: help.title || "",
  helpHTML: help.innerHTML || "",
  helpOpen: !!(help.parentNode && help.parentNode.open),
  demoPinned: ip.snapshot().demoPinned,
  bodyClasses: bodyClasses,
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


class DashboardHelpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.normal = _run_node(cls.intel, {"search": ""})
        cls.demo = _run_node(cls.intel, {"search": "?demo=1"})

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: checks on bus.html cover index.html
        # only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_help_panel_title(self):
        self.assertEqual(self.normal["helpTitle"], "Dashboard help")

    def test_help_covers_all_four_panels(self):
        html = self.normal["helpHTML"]
        for section in ("Crew Board", "Brief", "Dispatch", "Alerts"):
            self.assertIn(section, html,
                          "help text missing %s section" % section)

    def test_help_names_exact_data_sources(self):
        html = self.normal["helpHTML"]
        for key in ("muse-bus:presence:", "muse-bus:nickclaim:",
                    "muse-bus:cap:", "muse-bus:job:",
                    "muse-bus:jobindex",
                    "muse-bus:intel:brief:",
                    "muse-bus:intel:alert:",
                    "muse-bus:intel:wd:beat"):
            self.assertIn(key, html, "help text missing key %s" % key)

    def test_help_states_refresh_behavior(self):
        html = self.normal["helpHTML"]
        self.assertIn("2-second poll", html)
        self.assertIn("no timers", html)

    def test_help_states_read_only_and_posting_gate(self):
        html = self.normal["helpHTML"]
        self.assertIn("read-only", html)
        self.assertIn("posting is off", html)
        self.assertIn("never auto-posts", html)

    def test_help_states_demo_and_deep_links(self):
        html = self.normal["helpHTML"]
        self.assertIn("?demo=1", html)
        self.assertIn("#intel/brief/", html)
        self.assertIn("#intel/alert/", html)

    def test_help_adds_no_new_hex_colors(self):
        # DSH-018 palette: the help block carries no color values.
        self.assertIsNone(
            re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\\b",
                      self.normal["helpHTML"]))

    def test_help_not_demo_pinned(self):
        # DSH-028 pins exactly the four intel panels; the help
        # panel stays collapsed in demo mode.
        self.assertEqual(self.demo["demoPinned"], [])
        self.assertFalse(self.demo["helpOpen"])
        self.assertIn("demo-mode", self.demo["bodyClasses"])

    def test_spec_documents_help_panel(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("DOC-017", spec)
        self.assertIn("Dashboard help", spec)


if __name__ == "__main__":
    unittest.main()
