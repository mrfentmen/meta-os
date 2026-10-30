#!/usr/bin/env python3
"""DSH-014 alerts panel: ack/resolve lifecycle buttons.

Acceptance: ack on a fixture alert persists and re-renders as
acknowledged; a resolved alert collapses into the resolved count.
The transitions mirror intel/store.py WDG-014 exactly (open ->
acknowledged -> resolved; acking a resolved alert is refused;
re-acking / re-resolving is idempotent), and the live viewer write
is gated off per dashboard spec section 0 (ALERT_WRITE_ENABLED):
until Dale's viewer posting decision lands, the buttons ship
disabled with the section 0 explanation and no live write path
exists — the harness drives the transitions with gateForTest,
exactly like clickPost for DSH-011.

The JS runs in node with stubbed busUtil/busHooks, the same shape
as the /tmp/intel_test.js harness used at implementation time.
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

NODE_DRIVER = r"""
const fs = require("fs");
const assert = require("assert");
const bodies = {};
global.window = {
  busUtil: {
    panel: (id) => (bodies[id] || (bodies[id] = { innerHTML: "" })),
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
    myNick: () => "rowan",
    api: async () => { throw new Error("no live api in harness"); },
  },
  busHooks: { connect: [], poll: [] },
};
global.document = { getElementById: () => null, createElement: () => ({}) };
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
assert(ip, "intelPanel test hook missing");
const out = {};
out.gate = ip.alertWriteGate();
const NOW = 1700003600 * 1000;
ip.setAlerts([
  { id: "alert:1", kind: "stall", severity: "critical",
    subjects: ["milo"], explanation: "OPEN-CARD", suggested_fix: "fix",
    created_at: 1700000000, resolved_at: null },
  { id: "alert:2", kind: "stall", severity: "warning",
    subjects: ["hana"], explanation: "ACKED-CARD", suggested_fix: "fix",
    created_at: 1699999000, status: "acknowledged",
    acknowledged_at: 1699999500, acked_by: "pax", resolved_at: null },
  { id: "alert:3", kind: "stall", severity: "info",
    subjects: ["rowan"], explanation: "RESOLVED-CARD", suggested_fix: "fix",
    created_at: 1699998000, resolved_at: 1699998500 },
], NOW);
out.rowsBefore = ip.alertRows(NOW).map((r) => r.status);
out.htmlBefore = bodies["intel-alerts"].innerHTML;
out.liveGated = ip.clickAcknowledge("alert:1");
out.ack = ip.clickAcknowledge("alert:1", 1700003700, true);
out.ackRow = ip.alertRows(NOW)[0];
out.ackAgain = ip.clickAcknowledge("alert:1", 1700003701, true);
out.ackResolved = ip.clickAcknowledge("alert:3", 1700003700, true);
out.resolveResolved = ip.clickResolve("alert:3", 1700003700, true);
out.resolveMissing = ip.clickResolve("nope", 1700003700, true);
out.resolve = ip.clickResolve("alert:1", 1700003800, true);
out.rowsAfter = ip.alertRows(NOW).map((r) => r.status);
out.htmlAfter = bodies["intel-alerts"].innerHTML;
out.critAfter = ip.headerCountsAt(NOW).criticalAlerts;
out.legacy = ip.alertLifecycleStatus(
  { acknowledged_at: 1700001000, resolved_at: null });
console.log(JSON.stringify(out));
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_node(module):
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        mod_path = f.name
        f.write(module)
    driver = NODE_DRIVER.replace("__MODULE_PATH__",
                                 json.dumps(mod_path))
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


class DashboardAlertLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.js = _run_node(_intel_module(cls.bus))

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: the lifecycle checks on bus.html cover
        # index.html only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_live_write_gate_off(self):
        self.assertIs(self.js["gate"], False,
                      "ALERT_WRITE_ENABLED must be off until Dale's "
                      "viewer posting decision lands")
        self.assertEqual(self.js["liveGated"], "gated")

    def test_feed_rows_carry_wdg014_status(self):
        self.assertEqual(self.js["rowsBefore"],
                         ["open", "acknowledged", "resolved"])

    def test_resolved_collapses_into_count(self):
        html = self.js["htmlBefore"]
        self.assertIn("OPEN-CARD", html)
        self.assertIn("ACKED-CARD", html)
        self.assertNotIn("RESOLVED-CARD", html,
                         "resolved card must collapse, not render")
        self.assertIn("1 resolved", html)

    def test_buttons_render_disabled_with_gate_note(self):
        html = self.js["htmlBefore"]
        self.assertIn("Acknowledge", html)
        self.assertIn("Resolve", html)
        self.assertIn("disabled", html)
        self.assertIn("Posting is off for this build.", html)

    def test_ack_persists_and_renders_acknowledged(self):
        self.assertEqual(self.js["ack"], "acknowledged")
        row = self.js["ackRow"]
        self.assertEqual(row["status"], "acknowledged")
        self.assertEqual(row["acknowledged_at"], 1700003700)
        self.assertEqual(row["acked_by"], "rowan")
        self.assertEqual(self.js["ackAgain"], "already-acknowledged",
                         "re-ack must be idempotent, not re-stamp")

    def test_resolved_alert_refuses_ack(self):
        self.assertEqual(self.js["ackResolved"], "refused-resolved")
        self.assertEqual(self.js["resolveResolved"], "already-resolved")
        self.assertEqual(self.js["resolveMissing"], "not-found")

    def test_resolve_collapses_and_unblocks_header(self):
        self.assertEqual(self.js["resolve"], "resolved")
        self.assertEqual(self.js["rowsAfter"],
                         ["resolved", "acknowledged", "resolved"])
        html = self.js["htmlAfter"]
        self.assertNotIn("OPEN-CARD", html)
        self.assertIn("2 resolved", html)
        self.assertEqual(self.js["critAfter"], 0,
                         "a resolved critical must leave the header count")

    def test_legacy_record_derives_status(self):
        self.assertEqual(self.js["legacy"], "acknowledged")

    def test_source_carries_gate_and_transitions(self):
        intel = _intel_module(self.bus)
        self.assertIn("var ALERT_WRITE_ENABLED = false;", intel)
        self.assertIn("function alertLifecycleStatus(a) {", intel)
        self.assertIn("function acknowledgeAlertRecord(a, nowSec, by) {",
                      intel)
        self.assertIn("function resolveAlertRecord(a, nowSec) {", intel)
        self.assertIn('data-intel-alert-ack="', intel)
        self.assertIn('data-intel-alert-resolve="', intel)


if __name__ == "__main__":
    unittest.main()
