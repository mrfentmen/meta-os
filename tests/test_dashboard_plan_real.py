#!/usr/bin/env python3
"""HN-010 Plan real data (DSH-010).

Acceptance: #intel-plan shows the ACTUAL queued plan when one exists
(the plan-ready preview with real job rows), and states plainly that
no plan exists yet when none does. The hollow text ("No plan preview
available yet — the dispatch engine has not landed") is gone: it
talked about the missing engine instead of the plan state. No
queued-plan store key exists yet (no engine), so the panel renders
the plan it is given and otherwise says none exists — it never
invents a plan.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests and drives the Plan button through the
clickPlan hook.
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

PLAN = {"goal": "Prove the real plan",
        "jobs": [{"key": "A", "title": "First job"},
                 {"key": "B", "title": "Second job"}]}

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const MODE = __MODE__;
const PLAN = __PLAN__;
function stubBody() {
  return {
    innerHTML: "",
    parentNode: { open: false },
    querySelector: (sel) => ({
      addEventListener: () => {},
    }),
    querySelectorAll: () => [],
  };
}
global.window = {
  busUtil: {
    panel: (id) => {
      if (!bodies[id]) bodies[id] = stubBody();
      return bodies[id];
    },
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
    myNick: () => "hana",
    busKey: () => "muse-bus",
    roomName: () => "(main)",
    api: async () => { throw new Error("no live api in harness"); },
  },
  busHooks: { connect: [], poll: [] },
};
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: () => {} } },
};
(() => {
  eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
  const ip = global.window.__busTest.intelPanel;
  if (!ip) throw new Error("intelPanel test hook missing");
  const out = {};
  if (MODE === "plan") {
    ip.setPlan(PLAN);
    out.state = ip.clickPlan();
  } else if (MODE === "click-empty") {
    out.state = ip.clickPlan();
  } else if (MODE === "idle") {
    ip.setPlan(null);
    out.state = "idle";
  }
  out.html = bodies["intel-dispatch"] ? bodies["intel-dispatch"].innerHTML : "";
  console.log(JSON.stringify(out));
})();
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_driver(mode):
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    driver = (NODE_DRIVER.replace("__MODE__", json.dumps(mode))
              .replace("__PLAN__", json.dumps(PLAN))
              .replace("__MODULE_PATH__", '"__MOD__"'))
    with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False) as mod:
        mod.write(module)
        mod_path = mod.name
    driver = driver.replace('"__MOD__"', json.dumps(mod_path))
    with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False) as drv:
        drv.write(driver)
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


class DashboardPlanRealTest(unittest.TestCase):
    def test_queued_plan_renders_real_rows(self):
        data = _run_driver("plan")
        self.assertEqual(data["state"], "plan-ready")
        self.assertIn("First job", data["html"])
        self.assertIn("Second job", data["html"])
        self.assertIn("Post 2 jobs (simulated)", data["html"])

    def test_no_plan_states_plainly_and_hollow_text_gone(self):
        data = _run_driver("click-empty")
        self.assertEqual(data["state"], "idle")
        self.assertIn("No plan exists yet.", data["html"])
        self.assertNotIn("dispatch engine has not landed", data["html"])
        self.assertNotIn("No plan preview available", data["html"])
        # One plain statement, not the note plus the idle line.
        self.assertNotIn("No plan yet.", data["html"])

    def test_idle_before_click_still_says_no_plan_yet(self):
        data = _run_driver("idle")
        self.assertIn("No plan yet.", data["html"])


if __name__ == "__main__":
    unittest.main()
