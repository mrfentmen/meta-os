#!/usr/bin/env python3
"""OS-043 boot checklist view (plan/META_OS.md, spec section 8.1).

Acceptance: while services start, the dashboard shell shows bus,
queue, supervisor, watchdog, and brief flipping live as units report
ready, from real unit/ready states, with Milo's live watchdog status
line (OS-041). The driver below cycles the live renderBoot through
the harness hooks (the live collectBoot path reads /keys/ + /mget/
against the bus store, which the stub cannot serve, so the hook is
the cycle path, the same way "posted" is harness-fed for DSH-012):

- no record: supervisor + watchdog wait ("no boot status record
  yet"), brief waits ("no brief yet"), bus answers once read.
- fresh green record: the OS-041 frozen line renders verbatim,
  supervisor "3/3 units up", queue counts from the DSH-004 read,
  brief kind + age from the DSH-007 read.
- killed unit record: supervisor down naming relay-jobs, watchdog
  line names it too.
- open alert record: the frozen line names the latest open alert.
- staleness boundary (OS-041 rule, mirrored not redefined):
  fresh at exactly +30s, stale at +31s with an explicit stale mark
  and "not trusted as current health" — never a green line.
- bus read failure: the DSH-021 error row, bus line down.

Nothing here posts: the panel only reads (spec section 0 gate).
Not proven here: lines rendering from live data on a booted image
(no test image in repo) — integration-day work (INT-028).
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

T0 = 100000

GREEN = {"line": "Boot: 3/3 units up, 2 workers alive — no open alerts",
         "units_up": 3, "units_total": 3, "units_down": [],
         "workers_count": 2, "last_alert": None, "ts": T0}
KILLED = {"line": "Boot: 2/3 units up, 2 workers alive — down: relay-jobs"
          " — no open alerts",
          "units_up": 2, "units_total": 3, "units_down": ["relay-jobs"],
          "workers_count": 2, "last_alert": None, "ts": T0}
ALERT = {"line": "Boot: 3/3 units up, 2 workers alive — last alert: a-new"
         " (critical)",
         "units_up": 3, "units_total": 3, "units_down": [],
         "workers_count": 2,
         "last_alert": {"id": "a-new", "severity": "critical"}, "ts": T0}
JOBS = [{"id": "1", "title": "First", "status": "open"},
        {"id": "2", "title": "Second", "status": "claimed"},
        {"id": "3", "title": "Third", "status": "done",
         "done_at": T0}]
BRIEF = {"kind": "morning", "generated_at": T0 - 600}

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
const bootBody = () => bodies["intel-boot"]
  ? bodies["intel-boot"].innerHTML : "";
const out = {};
const ip = (() => {
  eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
  return global.window.__busTest.intelPanel;
})();
if (!ip) throw new Error("intelPanel test hook missing");
const NOW = (__T0__ + 5) * 1000;
ip.setBootStatus(null, NOW);
out.noRecord = bootBody();
ip.setJobs(__JOBS__, NOW);
ip.setBrief(__BRIEF__, NOW);
ip.setBootStatus(__GREEN__, NOW);
out.green = bootBody();
out.greenLines = ip.bootLines(NOW);
ip.setBootStatus(__KILLED__, NOW);
out.killed = bootBody();
ip.setBootStatus(__ALERT__, NOW);
out.alert = bootBody();
ip.setBootStatus(__GREEN__, NOW);
ip.renderBootAt((__T0__ + 30) * 1000);
out.freshBoundary = bootBody();
ip.renderBootAt((__T0__ + 31) * 1000);
out.staleBoundary = bootBody();
ip.setBootError("unreachable", NOW);
out.busError = bootBody();
out.snapshotBoot = ip.snapshot().boot;
out.snapshotBootLine = ip.snapshot().bootLine;
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
    driver = (NODE_DRIVER.replace("__T0__", str(T0))
              .replace("__JOBS__", json.dumps(JOBS))
              .replace("__BRIEF__", json.dumps(BRIEF))
              .replace("__GREEN__", json.dumps(GREEN))
              .replace("__KILLED__", json.dumps(KILLED))
              .replace("__ALERT__", json.dumps(ALERT)))
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


class Os043Test(unittest.TestCase):
    def test_no_record_waits_without_error(self):
        data = _run_driver()
        self.assertIn("Supervisor — waiting: no boot status record yet",
                      data["noRecord"])
        self.assertIn("Watchdog — waiting: no boot status record yet",
                      data["noRecord"])
        self.assertIn("Brief — waiting: no brief yet", data["noRecord"])
        self.assertIn("Bus — up: answering", data["noRecord"])
        self.assertNotIn("Can't reach the bus store", data["noRecord"])

    def test_fresh_green_record_renders_frozen_line_verbatim(self):
        data = _run_driver()
        self.assertIn("Boot: 3/3 units up, 2 workers alive — no open alerts",
                      data["green"])
        self.assertIn("Supervisor — up: 3/3 units up", data["green"])
        self.assertIn("Watchdog — up: Boot: 3/3 units up", data["green"])
        self.assertIn("Queue — up: 3 jobs — 1 open, 1 claimed, 1 done",
                      data["green"])
        self.assertIn("Brief — up: morning — generated 10 min ago",
                      data["green"])
        self.assertTrue(data["snapshotBoot"])
        self.assertIn("3/3 units up", data["snapshotBootLine"])

    def test_killed_unit_names_the_dead_unit(self):
        data = _run_driver()
        self.assertIn("Supervisor — down: 2/3 units up — down: relay-jobs",
                      data["killed"])
        self.assertIn("down: relay-jobs", data["killed"])

    def test_open_alert_record_names_latest_alert(self):
        data = _run_driver()
        self.assertIn("last alert: a-new (critical)", data["alert"])

    def test_staleness_boundary_30_fresh_31_stale(self):
        data = _run_driver()
        self.assertIn("Watchdog — up: Boot: 3/3 units up",
                      data["freshBoundary"])
        self.assertNotIn("stale", data["freshBoundary"])
        self.assertIn("Supervisor — stale:", data["staleBoundary"])
        self.assertIn("not trusted as current health",
                      data["staleBoundary"])
        self.assertIn("Watchdog — stale:", data["staleBoundary"])
        self.assertNotIn("Watchdog — up:", data["staleBoundary"])

    def test_bus_read_failure_banners_and_drops_bus_line(self):
        data = _run_driver()
        self.assertIn("Can&#39;t reach the bus store", data["busError"])
        self.assertIn("Bus — down: boot status read failed",
                      data["busError"])

    def test_spec_documents_boot_checklist_contract(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        section = spec.split("### 8.1 Boot checklist (OS-043)", 1)[1]
        section = section.split("## 9.", 1)[0]
        for line in ("bus", "queue", "supervisor", "watchdog", "brief"):
            self.assertIn(line, section.lower())
        self.assertIn("muse-bus:intel:wd:bootstatus:", section)
        self.assertIn("30s", section)

    def test_viewer_files_stay_identical(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")


if __name__ == "__main__":
    unittest.main()
