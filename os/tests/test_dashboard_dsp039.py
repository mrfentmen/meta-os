#!/usr/bin/env python3
"""DSP-039 dispatch approval affordance states (spec section 5.4).

Acceptance: the six states (idle, planning, plan-ready, posting,
posted, rejected) are listed in the dashboard spec with exact button
labels, and the panel mock cycles all six. The driver below cycles
the live renderDispatch through the harness hook setDispatchState
(planning and posting have no live path while the engine/post gate
are off, so the hook is the cycle path, the same way "posted" is
harness-fed via setPostedDispatch):

- idle: "No plan yet." + Plan button enabled
- planning: "Planning…" + goal input disabled
- plan-ready: preview + DSP-040 line + "Post N jobs" / "Reject plan"
- posting: preview frozen + "Posting…" + no "No plan yet."
- posted: tracker with the posted job id
- rejected: "Plan rejected — nothing was posted."

The posting row is the gap this batch closes: before it, the
posting state fell through to the idle branch and rendered
"No plan yet.", contradicting the spec table. Nothing here enables
a live post: the Post button stays disabled under
DISPATCH_POST_ENABLED (false), and the posting branch posts nothing.
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

PLAN = {"goal": "Cycle the six dispatch states",
        "jobs": [{"key": "A", "title": "First job",
                  "files": "a.py", "max_attempts": 3},
                 {"key": "B", "title": "Second job",
                  "files": "b.py", "max_attempts": 2}]}

POSTED = {"dispatch_id": "d1",
          "jobs": [{"key": "A", "job_id": "42"}]}

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
global.window = {
  busUtil: {
    panel: (id) => {
      if (!bodies[id]) {
        bodies[id] = { innerHTML: "", parentNode: { open: false },
                       querySelector: () => null };
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
    api: async () => ({ result: null }),
  },
  busHooks: { connect: [], poll: [] },
};
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: () => {} } },
};
const dispatchBody = () => bodies["intel-dispatch"]
  ? bodies["intel-dispatch"].innerHTML : "";
const out = {};
const ip = (() => {
  eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
  return global.window.__busTest.intelPanel;
})();
if (!ip) throw new Error("intelPanel test hook missing");
ip.setPlan(__PLAN__);
out.planReady = dispatchBody();
out.planReadyState = ip.snapshot().dispatchState;
ip.setDispatchState("posting");
out.posting = dispatchBody();
out.postingState = ip.snapshot().dispatchState;
ip.setDispatchState("planning");
out.planning = dispatchBody();
out.planningState = ip.snapshot().dispatchState;
ip.setPlan(null);
out.idle = dispatchBody();
out.idleState = ip.snapshot().dispatchState;
ip.setPlan(__PLAN__);
ip.clickReject();
out.rejected = dispatchBody();
out.rejectedState = ip.snapshot().dispatchState;
ip.setPostedDispatch(__POSTED__);
out.posted = dispatchBody();
out.postedState = ip.snapshot().dispatchState;
out.postGate = ip.dispatchPostGate();
console.log(JSON.stringify(out));
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
    driver = (NODE_DRIVER.replace("__PLAN__", json.dumps(PLAN))
              .replace("__POSTED__", json.dumps(POSTED)))
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


class Dsp039Test(unittest.TestCase):
    def test_all_six_states_render_their_spec_row(self):
        data = _run_driver()
        self.assertEqual(data["idleState"], "idle")
        self.assertIn("No plan yet.", data["idle"])
        self.assertEqual(data["planningState"], "planning")
        self.assertIn("Planning…", data["planning"])
        self.assertIn("disabled", data["planning"])
        self.assertEqual(data["planReadyState"], "plan-ready")
        self.assertIn("Post 2 jobs", data["planReady"])
        self.assertIn("Reject plan", data["planReady"])
        self.assertIn("A human approves every plan.",
                      data["planReady"])
        self.assertIn("First job", data["planReady"])
        self.assertEqual(data["postingState"], "posting")
        self.assertIn("Posting…", data["posting"])
        self.assertIn("First job", data["posting"])
        self.assertNotIn("No plan yet.", data["posting"])
        self.assertEqual(data["rejectedState"], "rejected")
        self.assertIn("Plan rejected — nothing was posted.",
                      data["rejected"])
        self.assertEqual(data["postedState"], "posted")
        self.assertIn("A job 42", data["posted"])
        self.assertFalse(data["postGate"])

    def test_spec_lists_all_six_states_with_exact_labels(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        section = spec.split("### 5.4 Approval states", 1)[1]
        section = section.split("### 5.5", 1)[0]
        for state in ("idle", "planning", "plan-ready", "posting",
                      "posted", "rejected"):
            self.assertIn(state, section)
        for label in ("`Plan`", "Planning…", "`Post N jobs`",
                      "`Reject plan`"):
            self.assertIn(label, section)

    def test_viewer_files_stay_identical(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")


if __name__ == "__main__":
    unittest.main()
