#!/usr/bin/env python3
"""DSH-022 dashboard deep links (spec section 8).

Acceptance: #intel/brief/<id> and #intel/alert/<id> hash routes
scroll to the item and highlight it, and a brief's Watch items link
to their alert cards. The node driver stubs U.api/busHooks/document
like the other dashboard harness tests; scrolling itself is a
best-effort live-DOM effect (the stub document has no elements),
so the harness asserts the addressable markup and the highlight —
the anchor ids and the outline — that scrolling targets.
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

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const MODE = __MODE__;
const NOW = 1700000000000;
const BRIEF_INDEX = JSON.stringify(
  [{ ts: 1700000000, kind: "morning", generated_at: 1700000000 }]);
const BRIEF_RECORD = JSON.stringify({
  kind: "morning", generated_at: 1700000000,
  sections: { decisions: ["Ship it"],
    watch_items: [{ alert_id: "alert:1", summary: "Watch the stall" }] } });
global.window = {
  busUtil: {
    panel: (id) => (bodies[id] || (bodies[id] = { innerHTML: "" })),
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
    nickColor: () => "#58a6ff",
    myNick: () => "rowan",
    busKey: () => "muse-bus",
    roomName: () => "(main)",
    api: async (path) => {
      const dec = decodeURIComponent(path);
      if (dec.indexOf("wd:beat") >= 0) {
        return { result: JSON.stringify({ ts: 1700000000 }) };
      }
      if (dec.indexOf("brief_index") >= 0) return { result: BRIEF_INDEX };
      if (dec.indexOf("brief:") >= 0) return { result: BRIEF_RECORD };
      if (dec.indexOf("/smembers/") >= 0) return { result: ["del"] };
      if (dec.indexOf("/mget/") >= 0) return { result: ["1"] };
      if (dec.indexOf("/pttl/") >= 0) return { result: 60000 };
      if (dec.indexOf("/zrange/") >= 0 || dec.indexOf("/hgetall/") >= 0) {
        return { result: [] };
      }
      throw new Error("unexpected api path " + path);
    },
  },
  busHooks: { connect: [], poll: [] },
};
global.document = { getElementById: () => null, createElement: () => ({}) };
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
const out = {};
const BRIEF = { kind: "morning", generated_at: 1700000000,
  sections: { decisions: ["Ship it"],
    watch_items: [{ alert_id: "alert:1", summary: "Watch the stall" }] } };
const ALERTS = [
  { id: "alert:1", kind: "stall", severity: "critical",
    subjects: ["del"], explanation: "Stalled", created_at: 1700000000 },
  { id: "alert:2", kind: "stall", severity: "warning",
    subjects: ["del"], explanation: "Slow", created_at: 1700000000 },
];
(async () => {
  if (MODE === "brief_link") {
    ip.setBriefHistory([{ ts: 1700000000, kind: "morning" }]);
    ip.setBrief(BRIEF, NOW);
    await ip.applyDeepLink("#intel/brief/1700000000");
  } else if (MODE === "alert_link") {
    ip.setAlerts(ALERTS, NOW);
    ip.applyDeepLink("#intel/alert/alert:1");
    ip.renderAlertsAt(NOW);
  } else if (MODE === "watch_to_alert") {
    ip.setBrief(BRIEF, NOW);
    ip.setAlerts(ALERTS, NOW);
    ip.applyDeepLink("#intel/alert/alert:1");
    ip.renderAlertsAt(NOW);
  } else if (MODE === "bad_hash") {
    ip.setBriefHistory([{ ts: 1700000000, kind: "morning" }]);
    ip.setBrief(BRIEF, NOW);
    out.parsePlain = ip.parseDeepLink("#plain");
    out.parseWrongKind = ip.parseDeepLink("#intel/nope/1");
    out.parseEmpty = ip.parseDeepLink("#intel/brief/");
    await ip.applyDeepLink("#intel/brief/9999999999");
    out.deepLink = ip.deepLink();
    ip.renderBriefAt(NOW);
  } else if (MODE === "late_history") {
    // Hash arrives before history exists: stored, not selected.
    ip.applyDeepLink("#intel/brief/1700000000");
    out.deepLinkBefore = ip.deepLink();
    ip.setBriefHistory([{ ts: 1700000000, kind: "morning" }]);
    // Same hash re-applied once history exists: selects the brief.
    await ip.applyDeepLink("#intel/brief/1700000000");
  }
  out.deepLink = out.deepLink || ip.deepLink();
  out.briefHTML = (bodies["intel-brief"] || { innerHTML: "" }).innerHTML;
  out.alertsHTML = (bodies["intel-alerts"] || { innerHTML: "" }).innerHTML;
  console.log(JSON.stringify(out));
})();
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_node(module, mode):
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        mod_path = f.name
        f.write(module)
    driver = NODE_DRIVER.replace("__MODULE_PATH__",
                                 json.dumps(mod_path))
    driver = driver.replace("__MODE__", json.dumps(mode))
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
    out = json.loads(r.stdout)
    for k, v in out.items():
        if isinstance(v, str):
            out[k] = v.replace("&#39;", "'")
    return out


class DashboardDeepLinksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.results = {m: _run_node(cls.intel, m) for m in
                       ("brief_link", "alert_link", "watch_to_alert",
                        "bad_hash", "late_history")}

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: checks on bus.html cover index.html
        # only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_brief_route_highlights_brief_header(self):
        r = self.results["brief_link"]
        self.assertEqual(r["deepLink"],
                         {"kind": "brief", "id": "1700000000"})
        self.assertIn('id="intel-brief-1700000000"', r["briefHTML"])
        self.assertIn("outline:2px solid #58a6ff", r["briefHTML"])

    def test_alert_route_highlights_exactly_its_card(self):
        r = self.results["alert_link"]
        self.assertEqual(r["deepLink"],
                         {"kind": "alert", "id": "alert:1"})
        self.assertIn('id="intel-alert-alert:1"', r["alertsHTML"])
        self.assertIn('id="intel-alert-alert:2"', r["alertsHTML"])
        # Exactly one card carries the outline: the linked one.
        self.assertEqual(
            r["alertsHTML"].count("outline:2px solid #58a6ff"), 1)
        card = r["alertsHTML"].split('id="intel-alert-alert:1"')[1]
        card = card.split('id="intel-alert-alert:2"')[0]
        self.assertIn("outline:2px solid #58a6ff", card)

    def test_brief_watch_item_links_to_its_alert_card(self):
        r = self.results["watch_to_alert"]
        self.assertIn('href="#intel/alert/alert:1"', r["briefHTML"])
        self.assertIn("Watch the stall", r["briefHTML"])
        # Following that link lands on the alert card highlighted.
        self.assertIn('id="intel-alert-alert:1"', r["alertsHTML"])
        self.assertEqual(
            r["alertsHTML"].count("outline:2px solid #58a6ff"), 1)

    def test_non_intel_hashes_parse_to_nothing(self):
        r = self.results["bad_hash"]
        self.assertIsNone(r["parsePlain"])
        self.assertIsNone(r["parseWrongKind"])
        self.assertIsNone(r["parseEmpty"])
        # An unknown brief id parses but selects nothing: no
        # highlight on the brief actually on view.
        self.assertEqual(r["deepLink"],
                         {"kind": "brief", "id": "9999999999"})
        self.assertNotIn("outline:2px solid #58a6ff", r["briefHTML"])

    def test_brief_link_arriving_before_history_retries(self):
        r = self.results["late_history"]
        self.assertEqual(r["deepLinkBefore"],
                         {"kind": "brief", "id": "1700000000"})
        self.assertIn('id="intel-brief-1700000000"', r["briefHTML"])
        self.assertIn("outline:2px solid #58a6ff", r["briefHTML"])

    def test_spec_documents_deep_links(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("DSH-022", spec)
        self.assertIn("#intel/brief/", spec)
        self.assertIn("#intel/alert/", spec)


if __name__ == "__main__":
    unittest.main()
