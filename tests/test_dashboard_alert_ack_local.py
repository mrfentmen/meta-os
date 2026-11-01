#!/usr/bin/env python3
"""HN-003 Alert Acknowledge: device-local lifecycle (DSH-014).

Acceptance: the Acknowledge button renders ENABLED whenever its
transition applies, and clicking it acknowledges the alert: the
record re-renders as acknowledged with acked_by, and the state
persists across reload. The persistence is LOCAL only (localStorage
overlay, or an injected test store): no network call, no store
write, no bus message. The LIVE write stays gated
(ALERT_WRITE_ENABLED false, clickAcknowledge returns "gated") until
Dale's viewer posting decision lands.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests. The reload proof evals the module twice in
one process with the same backing store object: eval 1 acks, eval 2
(a fresh module, as after a reload) re-feeds the same OPEN fixtures
and still reads acknowledged, because setAlerts merges the overlay
at ingest.
"""
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

NOW_MS = 1700003600 * 1000
ALERTS = [
    {"id": "alert:1", "kind": "stall", "severity": "critical",
     "subjects": ["milo"], "explanation": "OPEN-CARD",
     "suggested_fix": "fix", "created_at": 1700000000,
     "resolved_at": None},
    {"id": "alert:2", "kind": "stall", "severity": "warning",
     "subjects": ["hana"], "explanation": "ACKED-CARD",
     "suggested_fix": "fix", "created_at": 1699999000,
     "status": "acknowledged", "acknowledged_at": 1699999500,
     "acked_by": "pax", "resolved_at": None},
    {"id": "alert:3", "kind": "stall", "severity": "info",
     "subjects": ["rowan"], "explanation": "RESOLVED-CARD",
     "suggested_fix": "fix", "created_at": 1699998000,
     "resolved_at": 1699998500},
]

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const MODE = __MODE__;
const ALERTS = __ALERTS__;
const NOW_MS = __NOW_MS__;
const storeMap = {};
const store = {
  getItem: (k) => (k in storeMap ? storeMap[k] : null),
  setItem: (k, v) => { storeMap[k] = v; },
};
function stubBody() {
  return { innerHTML: "", parentNode: { open: false } };
}
function fakeEl(id) {
  const el = {
    id: id, fns: [],
    getAttribute: (n) => id,
    addEventListener: (ev, fn) => { el.fns.push(fn); },
  };
  return el;
}
let ackEls = [];
function stubBodyClick() {
  return {
    innerHTML: "",
    parentNode: { open: false },
    querySelector: () => null,
    querySelectorAll: (sel) => {
      if (sel === "[data-intel-alert-ack]") return ackEls;
      return [];
    },
  };
}
function setup() {
  global.window = {
    busUtil: {
      panel: (id) => {
        if (!bodies[id]) {
          bodies[id] = (MODE === "click") ? stubBodyClick() : stubBody();
        }
        return bodies[id];
      },
      esc: (s) => String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
      myNick: () => "hana",
      api: async () => { throw new Error("no live api in harness"); },
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
  return ip;
}
(() => {
  const out = {};
  if (MODE === "hooks") {
    const ip = setup();
    ip.setAlerts(ALERTS, NOW_MS);
    out.htmlBefore = bodies["intel-alerts"].innerHTML;
    out.ack = ip.acknowledgeAlertLocal("alert:1", 1700003700);
    out.row = ip.alertRows(NOW_MS)[0];
    out.ackAgain = ip.acknowledgeAlertLocal("alert:1", 1700003701);
    out.ackResolved = ip.acknowledgeAlertLocal("alert:3", 1700003700);
    out.ackMissing = ip.acknowledgeAlertLocal("nope", 1700003700);
    out.liveGated = ip.clickAcknowledge("alert:1", 1700003700);
    out.liveGate = ip.alertWriteGate();
    out.liveAckAfter = ip.clickAcknowledge("alert:1", 1700003700, true);
  } else if (MODE === "reload") {
    const ip1 = setup();
    ip1.setAlertLocalStore(store);
    ip1.setAlerts(ALERTS, NOW_MS);
    out.first = ip1.acknowledgeAlertLocal("alert:1", 1700003700);
    out.firstRow = ip1.alertRows(NOW_MS)[0];
    const ip2 = setup();
    ip2.setAlertLocalStore(store);
    ip2.setAlerts(ALERTS, NOW_MS);
    out.secondRow = ip2.alertRows(NOW_MS)[0];
  } else if (MODE === "click") {
    ackEls = [fakeEl("alert:1"), fakeEl("alert:2")];
    const ip = setup();
    ip.setAlerts(ALERTS, NOW_MS);
    out.htmlBefore = bodies["intel-alerts"].innerHTML;
    const fns = ackEls[0].fns;
    out.clicked = fns.length > 0;
    if (fns.length) fns[fns.length - 1]();
    out.row = ip.alertRows(NOW_MS)[0];
  }
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
              .replace("__ALERTS__", json.dumps(ALERTS))
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


class DashboardAlertAckLocalTest(unittest.TestCase):
    def test_ack_button_enabled_and_note_local(self):
        data = _run_driver("hooks")
        html = data["htmlBefore"]
        self.assertIn('data-intel-alert-ack="alert:1">Acknowledge</button>',
                      html)
        self.assertIn("Acknowledge / Resolve are stored on this device "
                      "only, not posted.", html)

    def test_local_ack_transitions_and_stamps(self):
        data = _run_driver("hooks")
        self.assertEqual(data["ack"], "acknowledged")
        row = data["row"]
        self.assertEqual(row["status"], "acknowledged")
        self.assertEqual(row["acknowledged_at"], 1700003700)
        self.assertEqual(row["acked_by"], "hana")
        self.assertEqual(data["ackAgain"], "already-acknowledged")
        self.assertEqual(data["ackResolved"], "refused-resolved")
        self.assertEqual(data["ackMissing"], "not-found")

    def test_live_write_stays_gated(self):
        data = _run_driver("hooks")
        self.assertIs(data["liveGate"], False)
        self.assertEqual(data["liveGated"], "gated")
        # Local and live paths agree after a local ack.
        self.assertEqual(data["liveAckAfter"], "already-acknowledged")

    def test_ack_persists_across_reload(self):
        data = _run_driver("reload")
        self.assertEqual(data["first"], "acknowledged")
        self.assertEqual(data["firstRow"]["status"], "acknowledged")
        row = data["secondRow"]
        self.assertEqual(row["status"], "acknowledged",
                         "overlay must survive a fresh module eval")
        self.assertEqual(row["acknowledged_at"], 1700003700)
        self.assertEqual(row["acked_by"], "hana")

    def test_live_click_handler_acks(self):
        data = _run_driver("click")
        self.assertTrue(data["clicked"],
                        "no click handler attached to ack button")
        self.assertEqual(data["row"]["status"], "acknowledged")
        self.assertEqual(data["row"]["acked_by"], "hana")


if __name__ == "__main__":
    unittest.main()
