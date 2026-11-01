#!/usr/bin/env python3
"""DSH-034 intel panels focus mode (spec section 8).

Acceptance: in demo mode, 'i' toggles intel focus mode (chat log
hidden, panels full width); documented in DEMO.md shot notes. The
node driver stubs U.api/busHooks/document like the other dashboard
harness tests, captures the module's real keydown handler, and
drives it with fake events — so the demo-mode gate, the editable-
target guard, and the modified/other-key guards are all exercised
through the production handler, not a reimplementation. CSS rules
are asserted from the style block, not from a live browser.
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
DEMO = os.path.join(REPO, "plan", "DEMO.md")

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const bodyClasses = [];
const keyHandlers = [];
const LOC = __LOCATION__;
const NOW = 1700000000000;
function makeClassList() {
  return {
    add: (c) => { if (bodyClasses.indexOf(c) < 0) bodyClasses.push(c); },
    remove: (c) => {
      const i = bodyClasses.indexOf(c);
      if (i >= 0) bodyClasses.splice(i, 1);
    },
  };
}
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
  addEventListener: (type, fn) => {
    if (type === "keydown") keyHandlers.push(fn);
  },
};
if (LOC) global.window.location = LOC;
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: makeClassList() },
};
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
ip.setCrew([], NOW);
ip.setBrief(null, NOW);
ip.setPlan(null);
ip.setAlerts([], NOW);
const body = () => ({ tagName: "BODY" });
const steps = {};
steps.initialFocus = ip.snapshot().intelFocus;
steps.handlerRegistered = keyHandlers.length > 0;
if (keyHandlers.length > 0) {
  const h = keyHandlers[0];
  h({ key: "i", target: body() });
  steps.afterI = ip.snapshot().intelFocus;
  steps.classesAfterI = bodyClasses.slice();
  h({ key: "i", target: body() });
  steps.afterSecondI = ip.snapshot().intelFocus;
  steps.classesAfterSecondI = bodyClasses.slice();
  h({ key: "i", target: { tagName: "INPUT" } });
  steps.afterInputI = ip.snapshot().intelFocus;
  h({ key: "i", target: { tagName: "TEXTAREA" } });
  steps.afterTextareaI = ip.snapshot().intelFocus;
  h({ key: "j", target: body() });
  steps.afterJ = ip.snapshot().intelFocus;
  h({ key: "i", ctrlKey: true, target: body() });
  steps.afterCtrlI = ip.snapshot().intelFocus;
  h({ key: "i", target: { tagName: "BODY", isContentEditable: true } });
  steps.afterEditableI = ip.snapshot().intelFocus;
}
console.log(JSON.stringify(steps));
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


class DashboardIntelFocusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.demo = _run_node(cls.intel, {"search": "?demo=1"})
        cls.normal = _run_node(cls.intel, {"search": ""})

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: checks on bus.html cover index.html
        # only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_i_toggles_focus_on_and_off_in_demo_mode(self):
        self.assertTrue(self.demo["handlerRegistered"])
        self.assertFalse(self.demo["initialFocus"])
        self.assertTrue(self.demo["afterI"])
        self.assertIn("intel-focus-mode", self.demo["classesAfterI"])
        self.assertFalse(self.demo["afterSecondI"])
        self.assertNotIn("intel-focus-mode",
                         self.demo["classesAfterSecondI"])

    def test_i_is_inert_while_typing_or_modified_or_other_key(self):
        # Each inert press follows the toggle-off above, so focus
        # must stay off through all of them.
        self.assertFalse(self.demo["afterInputI"])
        self.assertFalse(self.demo["afterTextareaI"])
        self.assertFalse(self.demo["afterJ"])
        self.assertFalse(self.demo["afterCtrlI"])
        self.assertFalse(self.demo["afterEditableI"])

    def test_no_handler_and_no_focus_on_normal_url(self):
        self.assertFalse(self.normal["handlerRegistered"])
        self.assertFalse(self.normal["initialFocus"])

    def test_focus_css_hides_log_and_widens_panels(self):
        style = self.bus.split("<style>")[1].split("</style>")[0]
        self.assertIn(
            "body.demo-mode.intel-focus-mode #log { display: none; }",
            style)
        self.assertIn(
            "body.demo-mode.intel-focus-mode #panels { width: 100%;",
            style)
        self.assertIn("max-width: none; border-left: none; }", style)
        # No new colors: the focus block adds no hex value (id
        # selectors like #log are not colors, so match hex only).
        focus = style.split(
            "body.demo-mode.intel-focus-mode #log")[1].split(
                "border-left: none; }")[0]
        self.assertIsNone(
            re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", focus))

    def test_spec_and_demo_notes_document_the_shortcut(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Implemented (DSH-034)", spec)
        self.assertIn("intel-focus-mode", spec)
        with open(DEMO, encoding="utf-8") as f:
            demo = f.read()
        self.assertIn("DSH-034", demo)
        self.assertIn("Intel focus", demo)
        self.assertIn("?demo=1", demo)


if __name__ == "__main__":
    unittest.main()
