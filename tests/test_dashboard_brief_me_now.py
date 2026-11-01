#!/usr/bin/env python3
"""HN-001 Brief me now: read-only on-demand refresh (DSH-009 gate flip).

Acceptance: the button renders ENABLED (it used to ship disabled with
"Posting is off for this build."); clicking it refreshes the latest
brief from the live store (GET the brief index, GET the latest record)
and renders it. It never posts: the driver records every api command
and the only commands are reads ("get"). GOV-002 is preserved because
no write path exists for a brief request: the send path (requesting a
newly generated brief) stays unwired pending Dale's viewer posting
decision, and this button cannot trigger one.

The node driver stubs U.api/busHooks/document like the other dashboard
harness tests. The stub panel body captures querySelector listeners,
so the test invokes the exact click handler the live button attaches.
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

NOW_MS = 1700002000000
BRIEF = {
    "kind": "ondemand",
    "generated_at": 1700001000,
    "sections": {
        "decisions": ["Ship the on-demand refresh."],
        "in_flight": ["HN-001 button work."],
        "owners": [{"nick": "hana", "job": 1, "title": "HN-001"}],
        "blocked": [],
        "watch_items": [],
    },
}

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const handlers = {};
const calls = [];
const NOW = __NOW__;
const MODE = __MODE__;
const BRIEF = __BRIEF__;
async function stubApi(path) {
  const cmd = path.split("/")[1];
  calls.push(cmd);
  if (MODE === "down") throw new Error("unreachable");
  if (cmd !== "get") throw new Error("unexpected command " + cmd);
  const key = decodeURIComponent(path.split("/")[2]);
  if (key.startsWith("muse-bus:intel:brief_index:")) {
    if (MODE === "empty") return { result: "[]" };
    return { result: JSON.stringify([{ ts: 1700001000, kind: "ondemand" }]) };
  }
  if (key.startsWith("muse-bus:intel:brief:")) {
    return { result: JSON.stringify(BRIEF) };
  }
  return { result: null };
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
(async () => {
  eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
  const ip = global.window.__busTest.intelPanel;
  if (!ip) throw new Error("intelPanel test hook missing");
  ip.setBrief(null, NOW);
  const emptyHtml = bodies["intel-brief"].innerHTML;
  const click = handlers["#intel-brief-now:fn"];
  if (click) click();
  await new Promise((r) => setTimeout(r, 100));
  const afterHtml = bodies["intel-brief"].innerHTML;
  console.log(JSON.stringify({
    gate: ip.briefMeNowGate(),
    emptyHtml: emptyHtml,
    clicked: !!click,
    afterHtml: afterHtml,
    calls: calls,
  }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
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
    driver = (NODE_DRIVER.replace("__NOW__", str(NOW_MS))
              .replace("__MODE__", json.dumps(mode))
              .replace("__BRIEF__", json.dumps(BRIEF))
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


class DashboardBriefMeNowTest(unittest.TestCase):
    def test_gate_flipped_and_button_enabled(self):
        data = _run_driver("live")
        self.assertIs(data["gate"], True,
                      "BRIEF_ME_NOW_ENABLED must be true after HN-001")
        self.assertIn('<button id="intel-brief-now">Brief me now</button>',
                      data["emptyHtml"])
        self.assertNotIn("disabled", data["emptyHtml"])
        self.assertNotIn("Posting is off for this build.",
                         data["emptyHtml"])

    def test_click_refreshes_latest_brief_from_live_store(self):
        data = _run_driver("live")
        self.assertTrue(data["clicked"],
                        "no click handler attached to #intel-brief-now")
        self.assertIn("Ship the on-demand refresh.", data["afterHtml"])
        self.assertIn('<button id="intel-brief-now">Brief me now</button>',
                      data["afterHtml"])
        self.assertEqual(data["calls"], ["get", "get"],
                         "refresh must read only (index + record)")

    def test_empty_index_stays_honest(self):
        data = _run_driver("empty")
        self.assertTrue(data["clicked"])
        self.assertIn("No brief yet", data["afterHtml"])
        self.assertIn('<button id="intel-brief-now">Brief me now</button>',
                      data["afterHtml"])

    def test_api_down_never_crashes_and_button_survives(self):
        data = _run_driver("down")
        self.assertTrue(data["clicked"])
        self.assertIn('<button id="intel-brief-now">Brief me now</button>',
                      data["afterHtml"])


if __name__ == "__main__":
    unittest.main()
