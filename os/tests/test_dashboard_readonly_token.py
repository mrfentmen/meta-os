#!/usr/bin/env python3
"""DSH-033 read-only-safe viewer (spec section 0).

Acceptance: read-only walkthrough logged; no panel throws.

Walkthrough: the viewer is driven through its live collect path
(collectCrew / collectJobs / collectBrief / collectBeat) against a
U.api stub that behaves like a read-only Upstash token — every read
command succeeds, and any write command is rejected with HTTP 403,
exactly as a read-only token would reject it. Dispatch is fed a
plan-ready preview (harness-fed: no live preview source exists yet)
and alerts are fed via setAlerts (no live alert collect exists yet),
so all four panels render busy at once. The assertions:

- every panel body renders, non-empty, with its fixture content;
- the module attempts zero write commands, so the read-only token
  rejects nothing and no panel surfaces a token error
  (panelErrors all null);
- every write affordance renders disabled with the plain
  explanation: Brief me now, dispatch Post, alert Acknowledge and
  Resolve, each next to "Posting is off for this build.";
- the live ack/resolve drivers return "gated" and leave the alert
  untouched, so a read-only viewer never mutates state.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests. The beat ts and brief generated_at come
from the driver's own clock, so the beat reads alive and the brief
reads fresh regardless of when the test runs.
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

NOW_SEC = 1793102100

BRIEF = {
    "kind": "morning",
    "sections": {
        "decisions": ["Ship DSH-033"],
        "in_flight": ["Dashboard read-only walkthrough"],
        "owners": ["rowan"],
        "blocked": ["Nothing blocked"],
        "watch_items": ["Watch the deploy gate"],
    },
}

PLAN = {"goal": "Prove the read-only walkthrough",
        "jobs": [{"key": "A", "title": "Walk the four panels"}]}

ALERTS = [{"id": "a1", "severity": "warning", "subjects": ["pax"],
           "explanation": "Pax row is blocked by this alert",
           "suggested_fix": "Resolve it from the CLI",
           "created_at": NOW_SEC}]

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const calls = [];
let writeAttempts = 0;
let rejected = 0;
const NOW_MS = Date.now();
const NOW_SEC = Math.floor(NOW_MS / 1000);
const READ_CMDS = ["smembers", "mget", "pttl", "hgetall", "zrange", "get"];
const nicks = ["rowan", "pax"];
const presence = { rowan: "1", pax: "1" };
const status = { rowan: "working", pax: "idle" };
const claim = { rowan: "host-a", pax: "host-b" };
const caps = {
  rowan: ["caps", "spark,relay", "roles", "driver", "updated", String(NOW_SEC)],
  pax: ["caps", "spark", "roles", "boss", "updated", String(NOW_SEC)],
};
const jobs = {
  "1": ["title", "Fix relay", "status", "working", "claim", "pax",
        "claimed_at", String(NOW_SEC - 600),
        "lease_until", String(NOW_SEC + 600),
        "last_progress_at", String(NOW_SEC - 60)],
  "2": ["title", "Ship walkthrough", "status", "done", "claim", "",
        "done_at", String(NOW_SEC)],
};
const brief = __BRIEF__;
brief.generated_at = NOW_SEC - 900;
const history = [{ ts: NOW_SEC - 900, kind: "morning" }];
async function readOnlyApi(path) {
  const cmd = path.split("/")[1];
  calls.push(cmd);
  if (READ_CMDS.indexOf(cmd) < 0) {
    writeAttempts++;
    rejected++;
    throw new Error("HTTP 403");
  }
  if (cmd === "smembers") return { result: nicks.slice() };
  if (cmd === "mget") {
    const keys = path.split("/").slice(2).map(decodeURIComponent);
    return { result: keys.map((k) => {
      if (k.startsWith("muse-bus:presence:")) return presence[k.slice(18)] || null;
      if (k.startsWith("muse-bus:status:")) return status[k.slice(16)] || null;
      if (k.startsWith("muse-bus:nickclaim:")) return claim[k.slice(19)] || null;
      return null;
    }) };
  }
  if (cmd === "pttl") return { result: 60000 };
  if (cmd === "hgetall") {
    const key = decodeURIComponent(path.split("/")[2]);
    if (key.startsWith("muse-bus:cap:")) return { result: caps[key.slice(13)] || [] };
    if (key.startsWith("muse-bus:job:")) return { result: jobs[key.slice(13)] || [] };
    return { result: [] };
  }
  if (cmd === "zrange") return { result: ["1", "2"] };
  if (cmd === "get") {
    const key = decodeURIComponent(path.split("/")[2]);
    if (key.startsWith("muse-bus:intel:brief_index:")) return { result: JSON.stringify(history) };
    if (key.startsWith("muse-bus:intel:brief:")) return { result: JSON.stringify(brief) };
    if (key === "muse-bus:intel:wd:beat") return { result: JSON.stringify({ ts: NOW_SEC }) };
    return { result: null };
  }
  return { result: null };
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
    api: readOnlyApi,
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
  await ip.collectCrewForTest();
  await new Promise((r) => setTimeout(r, 20)); // collectCaps rides inside collectCrew
  await ip.collectJobsForTest();
  await ip.refreshBrief();
  await ip.refreshBeat();
  ip.setPlan(__PLAN__);
  ip.setAlerts(__ALERTS__, NOW_MS);
  const snap = ip.snapshot();
  const out = {
    bodies: {
      crew: bodies["intel-crew"] ? bodies["intel-crew"].innerHTML : "",
      brief: bodies["intel-brief"] ? bodies["intel-brief"].innerHTML : "",
      dispatch: bodies["intel-dispatch"] ? bodies["intel-dispatch"].innerHTML : "",
      alerts: bodies["intel-alerts"] ? bodies["intel-alerts"].innerHTML : "",
    },
    apiCalls: calls,
    writeAttempts: writeAttempts,
    rejected: rejected,
    panelErrors: ip.panelErrors(),
    snapshot: snap,
    gates: {
      briefMeNow: ip.briefMeNowGate(),
      dispatchPost: ip.dispatchPostGate(),
      alertWrite: ip.alertWriteGate(),
    },
    clickAck: ip.clickAcknowledge("a1", NOW_SEC),
    clickResolve: ip.clickResolve("a1", NOW_SEC),
    alertsAfter: ip.alertRows(NOW_MS).length,
  };
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
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
    driver = (NODE_DRIVER.replace("__BRIEF__", json.dumps(BRIEF))
              .replace("__PLAN__", json.dumps(PLAN))
              .replace("__ALERTS__", json.dumps(ALERTS)))
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


class DashboardReadonlyTokenTest(unittest.TestCase):
    def test_no_write_attempted_and_no_token_error(self):
        data = _run_driver()
        self.assertEqual(data["writeAttempts"], 0)
        self.assertEqual(data["rejected"], 0)
        self.assertTrue(
            set(data["apiCalls"]) <=
            {"smembers", "mget", "pttl", "hgetall", "zrange", "get"},
            "a non-read command reached the read-only api: %r"
            % (data["apiCalls"],))
        self.assertEqual(data["panelErrors"],
                         {"crew": None, "jobs": None,
                          "brief": None, "beat": None, "boot": None})

    def test_all_four_panels_render_busy(self):
        data = _run_driver()
        for panel in ("crew", "brief", "dispatch", "alerts"):
            self.assertTrue(data["bodies"][panel],
                            "%s panel rendered empty" % panel)
        self.assertIn("rowan", data["bodies"]["crew"])
        self.assertIn("pax", data["bodies"]["crew"])
        self.assertIn("Ship DSH-033", data["bodies"]["brief"])
        self.assertIn("Walk the four panels", data["bodies"]["dispatch"])
        self.assertIn("Pax row is blocked by this alert",
                      data["bodies"]["alerts"])
        snap = data["snapshot"]
        self.assertEqual((snap["crew"], snap["jobs"], snap["brief"],
                          snap["beat"], snap["alerts"]),
                         (2, 2, True, True, 1))

    def test_write_buttons_disabled_with_explanation(self):
        data = _run_driver()
        self.assertEqual(data["gates"],
                         {"briefMeNow": False, "dispatchPost": False,
                          "alertWrite": False})
        self.assertIn("<button disabled>Brief me now</button>",
                      data["bodies"]["brief"])
        self.assertIn("Posting is off for this build.",
                      data["bodies"]["brief"])
        self.assertIn("disabled", data["bodies"]["dispatch"])
        self.assertIn("Posting is off for this build.",
                      data["bodies"]["dispatch"])
        self.assertIn("<button disabled", data["bodies"]["alerts"])
        self.assertIn("Acknowledge", data["bodies"]["alerts"])
        self.assertIn("Resolve", data["bodies"]["alerts"])
        self.assertIn("Posting is off for this build.",
                      data["bodies"]["alerts"])
        self.assertEqual(data["clickAck"], "gated")
        self.assertEqual(data["clickResolve"], "gated")
        self.assertEqual(data["alertsAfter"], 1)

    def test_index_matches_bus_and_spec_notes_dsh033(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Implemented (DSH-033)", spec)


if __name__ == "__main__":
    unittest.main()
