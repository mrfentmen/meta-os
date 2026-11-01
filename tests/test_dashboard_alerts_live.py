#!/usr/bin/env python3
"""HN-009 Alerts panel live data (DSH-013).

Acceptance: the panel reads the REAL alerts store: a keys scan for
muse-bus:intel:alert:* plus mget of the records, the same shape
collectBoot already uses. No alert index key exists yet, so the scan
is the read. With zero alerts the panel shows the honest beat-driven
empty state, not harness data. Unparseable records and records
without an id are skipped. A failed read keeps the last good alerts.
The device-local lifecycle overlay (HN-003/004) still applies to
live reads, not just harness-fed ones.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests and drives collectAlertsForTest.
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

NOW_MS = 1700003600 * 1000
LIVE1 = {"id": "live1", "kind": "stall", "severity": "critical",
         "subjects": ["milo"], "explanation": "LIVE-ONE",
         "suggested_fix": "fix", "created_at": 1700000000,
         "resolved_at": None}
LIVE2 = {"id": "live2", "kind": "stall", "severity": "warning",
         "subjects": ["hana"], "explanation": "LIVE-TWO",
         "suggested_fix": "fix", "created_at": 1700001000,
         "resolved_at": None}
FIXTURE = [{"id": "fix1", "kind": "stall", "severity": "info",
            "subjects": ["rowan"], "explanation": "FIXTURE-CARD",
            "suggested_fix": "fix", "created_at": 1700000000,
            "resolved_at": None}]

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const MODE = __MODE__;
const LIVE1 = __LIVE1__;
const LIVE2 = __LIVE2__;
const FIXTURE = __FIXTURE__;
const NOW_MS = __NOW_MS__;
const calls = [];
const storeMap = {};
const store = {
  getItem: (k) => (k in storeMap ? storeMap[k] : null),
  setItem: (k, v) => { storeMap[k] = v; },
};
async function stubApi(path) {
  const cmd = path.split("/")[1];
  calls.push(cmd);
  if (MODE === "down") throw new Error("unreachable");
  if (cmd === "keys") {
    if (MODE === "empty") return { result: [] };
    if (MODE === "mixed") {
      return { result: ["muse-bus:intel:alert:good",
                        "muse-bus:intel:alert:bad",
                        "muse-bus:intel:alert:noid"] };
    }
    if (MODE === "overlay" || MODE === "live") {
      return { result: ["muse-bus:intel:alert:live1",
                        "muse-bus:intel:alert:live2"] };
    }
    return { result: [] };
  }
  if (cmd === "mget") {
    if (MODE === "mixed") {
      return { result: [JSON.stringify({
        id: "good", kind: "stall", severity: "info", subjects: ["pax"],
        explanation: "GOOD-CARD", suggested_fix: "fix",
        created_at: 1700000000, resolved_at: null }),
        "not-json{",
        JSON.stringify({ kind: "stall", severity: "info" })] };
    }
    return { result: [JSON.stringify(LIVE1), JSON.stringify(LIVE2)] };
  }
  throw new Error("unexpected command " + cmd);
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
  const out = {};
  if (MODE === "down") {
    ip.setAlerts(FIXTURE, NOW_MS);
  }
  if (MODE === "overlay") {
    storeMap["intel-alert-lifecycle-local"] = JSON.stringify({
      live1: { status: "acknowledged", acknowledged_at: 1700003700,
               acked_by: "hana", resolved_at: null } });
    ip.setAlertLocalStore(store);
  }
  await ip.collectAlertsForTest();
  out.rows = ip.alertRows(NOW_MS);
  out.html = bodies["intel-alerts"] ? bodies["intel-alerts"].innerHTML : "";
  out.calls = calls;
  console.log(JSON.stringify(out));
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
    driver = (NODE_DRIVER.replace("__MODE__", json.dumps(mode))
              .replace("__LIVE1__", json.dumps(LIVE1))
              .replace("__LIVE2__", json.dumps(LIVE2))
              .replace("__FIXTURE__", json.dumps(FIXTURE))
              .replace("__NOW_MS__", str(NOW_MS))
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


class DashboardAlertsLiveTest(unittest.TestCase):
    def test_live_read_renders_newest_first(self):
        data = _run_driver("live")
        self.assertEqual(data["calls"], ["keys", "mget"])
        rows = data["rows"]
        self.assertEqual([r["id"] for r in rows], ["live2", "live1"])
        self.assertIn("LIVE-ONE", data["html"])
        self.assertIn("LIVE-TWO", data["html"])

    def test_zero_alerts_honest_empty_state(self):
        data = _run_driver("empty")
        self.assertEqual(data["calls"], ["keys"])
        self.assertEqual(data["rows"], [])
        self.assertIn("No alerts. Watchdog status has not been read yet.",
                      data["html"])

    def test_bad_records_skipped(self):
        data = _run_driver("mixed")
        rows = data["rows"]
        self.assertEqual([r["id"] for r in rows], ["good"])
        self.assertIn("GOOD-CARD", data["html"])

    def test_failed_read_keeps_last_good(self):
        data = _run_driver("down")
        rows = data["rows"]
        self.assertEqual([r["id"] for r in rows], ["fix1"])
        self.assertIn("FIXTURE-CARD", data["html"])

    def test_local_overlay_applies_to_live_read(self):
        data = _run_driver("overlay")
        rows = data["rows"]
        live1 = [r for r in rows if r["id"] == "live1"][0]
        self.assertEqual(live1["status"], "acknowledged")
        self.assertEqual(live1["acked_by"], "hana")
        self.assertEqual(live1["acknowledged_at"], 1700003700)


if __name__ == "__main__":
    unittest.main()
