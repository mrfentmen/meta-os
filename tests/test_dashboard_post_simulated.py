#!/usr/bin/env python3
"""HN-002 Post N jobs: SIMULATED dispatch endpoint only (DSH-011).

Acceptance: the plan-ready Post button renders ENABLED, labelled
"Post N jobs (simulated)", with a tooltip stating simulated. Clicking
it asks the native confirm, then records a receipt in LOCAL panel
state only and renders it. Nothing leaves the browser: the driver
records every api call and there are none, and the receipt row states
"nothing posted to the bus". The REAL post stays gated
(DISPATCH_POST_ENABLED false, DSH-038 request-only): a real post
still happens only from the CLI.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests. The stub panel body captures querySelector
listeners, so one test invokes the exact click handler the live
button attaches (with a stubbed window.confirm).
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

NOW_SEC = 1700002000
PLAN = {"goal": "Prove the simulated post",
        "jobs": [{"key": "A", "title": "First job"},
                 {"key": "B", "title": "Second job"}]}
PLAN_ERRORS = {"goal": "Prove the error path",
               "jobs": [], "errors": ["Engine refused the plan."]}

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const handlers = {};
const calls = [];
const MODE = __MODE__;
const PLAN = __PLAN__;
const NOW_SEC = __NOW_SEC__;
async function stubApi(path) {
  calls.push(path.split("/")[1]);
  throw new Error("no live api in sim harness");
}
function stubBody() {
  return {
    innerHTML: "",
    parentNode: { open: false },
    querySelector: (sel) => {
      if (!handlers[sel]) {
        handlers[sel] = {
          addEventListener: (ev, fn) => { handlers[sel + ":fn"] = fn; },
        };
      }
      return handlers[sel];
    },
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
    api: stubApi,
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
  const out = { gate: ip.dispatchPostGate() };
  if (MODE === "notready") {
    out.post = ip.postSimulated(() => true, NOW_SEC);
    out.receipt = ip.simulatedDispatch();
    out.html = bodies["intel-dispatch"] ? bodies["intel-dispatch"].innerHTML : "";
  } else {
    ip.setPlan(PLAN);
    out.planState = ip.clickPlan();
    out.readyHtml = bodies["intel-dispatch"].innerHTML;
    if (MODE === "liveclick") {
      global.window.confirm = () => true;
      const click = handlers["#intel-post:fn"];
      out.clicked = !!click;
      if (click) click();
      out.receipt = ip.simulatedDispatch();
      out.html = bodies["intel-dispatch"].innerHTML;
    } else if (MODE === "cancel") {
      out.post = ip.postSimulated(() => false, NOW_SEC);
      out.receipt = ip.simulatedDispatch();
      out.html = bodies["intel-dispatch"].innerHTML;
    } else {
      out.post = ip.postSimulated(() => true, NOW_SEC);
      out.receipt = ip.simulatedDispatch();
      out.html = bodies["intel-dispatch"].innerHTML;
    }
  }
  out.calls = calls;
  console.log(JSON.stringify(out));
})();
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_driver(mode, plan=None):
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    driver = (NODE_DRIVER.replace("__MODE__", json.dumps(mode))
              .replace("__PLAN__", json.dumps(plan if plan is not None
                                              else PLAN))
              .replace("__NOW_SEC__", str(NOW_SEC))
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


class DashboardPostSimulatedTest(unittest.TestCase):
    def test_real_post_gate_stays_off(self):
        data = _run_driver("post")
        self.assertIs(data["gate"], False,
                      "DISPATCH_POST_ENABLED must stay false")

    def test_button_labelled_simulated_and_enabled(self):
        data = _run_driver("post")
        self.assertEqual(data["planState"], "plan-ready")
        self.assertIn("Post 2 jobs (simulated)", data["readyHtml"])
        self.assertIn("Simulated only: nothing posts to the bus",
                      data["readyHtml"])
        self.assertNotIn('id="intel-post" disabled', data["readyHtml"])

    def test_simulated_post_records_receipt_and_posts_nothing(self):
        data = _run_driver("post")
        self.assertEqual(data["post"], "posted-simulated")
        self.assertEqual(data["calls"], [],
                         "simulated post must make no api call")
        receipt = data["receipt"]
        self.assertTrue(receipt["simulated"])
        self.assertEqual(receipt["jobs"], 2)
        self.assertTrue(receipt["dispatch_id"].startswith("sim-"))
        self.assertIn("Simulated receipt:", data["html"])
        self.assertIn("nothing posted to the bus.", data["html"])
        self.assertIn("Simulated posting only:", data["html"])

    def test_live_click_handler_posts_simulated(self):
        data = _run_driver("liveclick")
        self.assertTrue(data["clicked"],
                        "no click handler attached to #intel-post")
        self.assertTrue(data["receipt"]["simulated"])
        self.assertIn("Simulated receipt:", data["html"])

    def test_cancel_posts_nothing(self):
        data = _run_driver("cancel")
        self.assertEqual(data["post"], "cancelled")
        self.assertIsNone(data["receipt"])
        self.assertNotIn("Simulated receipt:", data["html"])

    def test_not_plan_ready_posts_nothing(self):
        data = _run_driver("notready")
        self.assertEqual(data["post"], "idle")
        self.assertIsNone(data["receipt"])

    def test_plan_with_errors_posts_nothing(self):
        data = _run_driver("post", plan=PLAN_ERRORS)
        self.assertEqual(data["post"], "plan-ready")
        self.assertIsNone(data["receipt"])
        self.assertNotIn("Simulated receipt:", data["html"])


if __name__ == "__main__":
    unittest.main()
