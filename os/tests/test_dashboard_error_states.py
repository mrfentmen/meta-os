#!/usr/bin/env python3
"""DSH-021 per-panel error states (spec section 9).

Acceptance: killing one data source degrades only its panel, in
plain words, while the panel keeps its last good render behind the
message. The node driver stubs U.api per mode: a failing source
throws (network failure = unreachable, HTTP 401/403 = token), a
healthy source answers from fixtures, and the harness drives the
panel's own collect path — the same path the live poll uses.
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
let phase = 1;
const NOW = 1700000000000;
const BRIEF_INDEX = JSON.stringify(
  [{ ts: 1700000000, kind: "morning", generated_at: 1700000000 }]);
const BRIEF_RECORD = JSON.stringify({
  kind: "morning", generated_at: 1700000000,
  sections: { decisions: ["Ship it"] } });
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
      if (dec.indexOf("/smembers/") >= 0) {
        if (MODE === "crew_unreachable") throw new Error("fetch failed");
        if (MODE === "crew_token") throw new Error("HTTP 401");
        if (MODE === "empty_room") return { result: [] };
        return { result: ["del"] };
      }
      if (dec.indexOf("/mget/") >= 0) return { result: ["1"] };
      if (dec.indexOf("/pttl/") >= 0) return { result: 60000 };
      if (dec.indexOf("/zrange/") >= 0 || dec.indexOf("/hgetall/") >= 0) {
        if (MODE === "jobs_only") throw new Error("fetch failed");
        return { result: [] };
      }
      if (dec.indexOf("/get/") >= 0) {
        if (dec.indexOf("wd:beat") >= 0) {
          if (MODE === "beat_failure") throw new Error("fetch failed");
          return { result: JSON.stringify({ ts: 1700000000 }) };
        }
        if (dec.indexOf("brief_index") >= 0) {
          if (MODE === "brief_recovery" && phase === 1) {
            throw new Error("HTTP 403");
          }
          return { result: BRIEF_INDEX };
        }
        if (dec.indexOf("brief:") >= 0) {
          if (MODE === "brief_recovery" && phase === 1) {
            throw new Error("HTTP 403");
          }
          return { result: BRIEF_RECORD };
        }
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
(async () => {
  if (MODE === "crew_unreachable" || MODE === "crew_token") {
    ip.setCrew([{ nick: "del", status: "", host: "", lastSeen: NOW }], NOW);
    await ip.collectCrewForTest();
  } else if (MODE === "jobs_only") {
    ip.setCrew([{ nick: "del", status: "", host: "", lastSeen: NOW }], NOW);
    ip.setBrief({ kind: "morning", generated_at: 1700000000,
                  sections: { decisions: ["Ship it"] } }, NOW);
    await ip.collectJobsForTest();
  } else if (MODE === "brief_recovery") {
    await ip.refreshBrief();
    out.errorsAfterFailure = ip.panelErrors();
    out.briefAfterFailure = bodies["intel-brief"].innerHTML;
    phase = 2;
    await ip.refreshBrief();
  } else if (MODE === "beat_failure") {
    ip.setCrew([{ nick: "del", status: "", host: "", lastSeen: NOW }], NOW);
    await ip.refreshBeat();
  } else if (MODE === "empty_room") {
    await ip.collectCrewForTest();
  }
  out.errors = ip.panelErrors();
  out.crewHTML = (bodies["intel-crew"] || { innerHTML: "" }).innerHTML;
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
    # The stub esc encodes apostrophes (&#39;); decode so assertions
    # read the plain spec wording, not the stub's escaping.
    for k, v in out.items():
        if isinstance(v, str):
            out[k] = v.replace("&#39;", "'")
    return out


class DashboardErrorStatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.results = {m: _run_node(cls.intel, m) for m in
                       ("crew_unreachable", "crew_token", "jobs_only",
                        "brief_recovery", "beat_failure", "empty_room")}

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: checks on bus.html cover index.html
        # only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_crew_unreachable_keeps_last_render(self):
        r = self.results["crew_unreachable"]
        self.assertEqual(r["errors"]["crew"]["kind"], "unreachable")
        self.assertIn("Can't reach the bus store", r["crewHTML"])
        self.assertIn("Crew Board is paused", r["crewHTML"])
        self.assertIn("The log above is unaffected", r["crewHTML"])
        # Last good render stays behind the banner.
        self.assertIn("del", r["crewHTML"])

    def test_crew_token_message(self):
        r = self.results["crew_token"]
        self.assertEqual(r["errors"]["crew"]["kind"], "token")
        self.assertIn("No token, or this token can't read presence",
                      r["crewHTML"])
        self.assertIn("Paste a token above to load Crew Board",
                      r["crewHTML"])
        self.assertIn("del", r["crewHTML"])

    def test_dead_jobs_degrade_only_crew(self):
        r = self.results["jobs_only"]
        self.assertEqual(r["errors"]["jobs"]["kind"], "unreachable")
        self.assertIsNone(r["errors"]["brief"])
        self.assertIn("Can't reach the bus store", r["crewHTML"])
        self.assertNotIn("Can't reach the bus store", r["briefHTML"])
        self.assertNotIn("No token", r["briefHTML"])
        self.assertIn("Ship it", r["briefHTML"])

    def test_brief_failure_then_recovery_clears(self):
        r = self.results["brief_recovery"]
        self.assertEqual(r["errorsAfterFailure"]["brief"]["kind"],
                         "token")
        self.assertIn("No token, or this token can't read brief records",
                      r["briefAfterFailure"])
        self.assertIsNone(r["errors"]["brief"])
        self.assertIn("Ship it", r["briefHTML"])
        self.assertNotIn("No token", r["briefHTML"])

    def test_dead_beat_degrades_only_alerts(self):
        r = self.results["beat_failure"]
        self.assertEqual(r["errors"]["beat"]["kind"], "unreachable")
        self.assertIn("Can't reach the bus store", r["alertsHTML"])
        self.assertIn("Alerts is paused", r["alertsHTML"])
        self.assertNotIn("Can't reach the bus store", r["crewHTML"])
        self.assertIn("del", r["crewHTML"])

    def test_empty_room_is_not_an_error(self):
        r = self.results["empty_room"]
        self.assertTrue(all(v is None for v in r["errors"].values()),
                        r["errors"])
        self.assertIn("No crew yet", r["crewHTML"])
        self.assertNotIn("Can't reach", r["crewHTML"])

    def test_spec_documents_error_states(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("is paused. The log above is unaffected.", spec)
        self.assertIn("Paste a token above to load", spec)
        self.assertIn("DSH-021", spec)


if __name__ == "__main__":
    unittest.main()
