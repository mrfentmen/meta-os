#!/usr/bin/env python3
"""DSH-032 today counters (spec section 8).

Acceptance: counters match fixture record counts. Jobs done today,
briefs generated today, and alerts fired/resolved today are counted
from the records the panels already read — no separate store, no new
timer (the strip re-renders on the core 2s poll via renderHeader).
A record with no timestamp on the relevant field is never counted,
and the current brief is deduplicated against the history window,
so a brief that is also the newest history entry counts once.

The node driver stubs U.api/busHooks/document like the other
dashboard harness tests. NOW is mid-morning (2026-10-27 07:55 EDT /
11:55 UTC), so the -1h/-2h fixtures stay on the same local day and
the -25h fixtures stay on the previous local day in either zone.
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

NOW = 1793102100000  # ms; nowSec = 1793102100
NOW_SEC = NOW // 1000
TODAY = NOW_SEC - 3600
TODAY_BRIEF = NOW_SEC - 7200
YESTERDAY = NOW_SEC - 90000

JOBS = [
    {"id": "1", "title": "done today", "status": "done",
     "done_at": TODAY},
    {"id": "2", "title": "done yesterday", "status": "done",
     "done_at": YESTERDAY},
    {"id": "3", "title": "done, no stamp", "status": "done"},
    {"id": "4", "title": "still open", "status": "open"},
]

# Oldest first, as brief.py writes the index: the today's entry is
# also the current brief below, so it must count exactly once.
HISTORY = [
    {"ts": YESTERDAY, "kind": "morning"},
    {"ts": TODAY_BRIEF, "kind": "morning"},
]

BRIEF_TODAY = {"kind": "morning", "generated_at": TODAY_BRIEF,
               "sections": {}}
BRIEF_TODAY_ONLY = {"kind": "morning", "generated_at": TODAY,
                    "sections": {}}
BRIEF_YESTERDAY = {"kind": "morning", "generated_at": YESTERDAY,
                   "sections": {}}

ALERTS = [
    # Fired today, resolved today.
    {"id": "a1", "severity": "warning", "created_at": TODAY,
     "resolved_at": TODAY},
    # Fired today, still open.
    {"id": "a2", "severity": "warning", "created_at": TODAY},
    # Fired yesterday, resolved today.
    {"id": "a3", "severity": "warning", "created_at": YESTERDAY,
     "resolved_at": TODAY},
    # Fired yesterday, still open.
    {"id": "a4", "severity": "warning", "created_at": YESTERDAY},
    # No created stamp (never counted as fired), resolved today.
    {"id": "a5", "severity": "warning", "resolved_at": TODAY},
]

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const NOW = __NOW__;
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
    api: async () => { throw new Error("no live api"); },
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
ip.setJobs(__JOBS__, NOW);
ip.setBriefHistory(__HISTORY__);
ip.setBrief(__BRIEF_TODAY__, NOW);
ip.setAlerts(__ALERTS__, NOW);
const step1 = {
  counts: ip.todayCountsAt(NOW),
  line: ip.todayLineAt(NOW),
};
ip.setBriefHistory([]);
ip.setBrief(__BRIEF_TODAY_ONLY__, NOW);
const step2 = { counts: ip.todayCountsAt(NOW) };
ip.setBrief(__BRIEF_YESTERDAY__, NOW);
const step3 = { counts: ip.todayCountsAt(NOW) };
console.log(JSON.stringify({ step1: step1, step2: step2, step3: step3 }));
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
    driver = (NODE_DRIVER.replace("__NOW__", str(NOW))
              .replace("__JOBS__", json.dumps(JOBS))
              .replace("__HISTORY__", json.dumps(HISTORY))
              .replace("__BRIEF_TODAY__", json.dumps(BRIEF_TODAY))
              .replace("__BRIEF_TODAY_ONLY__",
                       json.dumps(BRIEF_TODAY_ONLY))
              .replace("__BRIEF_YESTERDAY__", json.dumps(BRIEF_YESTERDAY))
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


class DashboardTodayCountersTest(unittest.TestCase):
    def test_counts_match_fixture_records(self):
        data = _run_driver()
        self.assertEqual(data["step1"]["counts"], {
            "jobsDoneToday": 1, "briefsToday": 1,
            "alertsFiredToday": 2, "alertsResolvedToday": 3})

    def test_line_renders_the_counts(self):
        line = _run_driver()["step1"]["line"]
        self.assertEqual(
            line,
            "today · jobs done 1 · briefs 1 · alerts fired 2 / resolved 3")

    def test_brief_outside_history_counts_once(self):
        # A current brief with no history entry still counts once.
        self.assertEqual(_run_driver()["step2"]["counts"]["briefsToday"],
                         1)

    def test_yesterday_brief_counts_zero(self):
        self.assertEqual(_run_driver()["step3"]["counts"]["briefsToday"],
                         0)

    def test_index_matches_bus_and_spec_notes_dsh032(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")
        self.assertIn("todayCounts", index)
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("Implemented (DSH-032)", spec)


if __name__ == "__main__":
    unittest.main()
