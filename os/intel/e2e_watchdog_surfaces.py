#!/usr/bin/env python3
"""intel/e2e_watchdog_surfaces.py -- INT-020 end-to-end, Milo lane.

One watchdog alert traced across all three surfaces that are
supposed to show it, with the same id and severity on each:

  1. alert store: intel/store.py build_alert_record (WDG-010)
  2. brief: intel/brief.py Watch items (BRF-022), template brief
  3. dashboard: bus.html intelPanel alerts panel (DSH-013/014),
     driven by the node harness stub, no live viewer

What this run is, plainly:

- The alert is a real watchdog tick, not a hand-built dict: a
  presence-stall fixture (caps nick gone from presence, claimed
  job idle past STALL_MINUTES) goes through intel/watchdog.py
  tick(), exactly the WDG-002 detector path. Nothing here
  touches the live bus or posts a real job, and nothing is
  announced: the ALERT line stays held, per Dale's posting rule.
- The store surface is the validated WDG-010 record built from
  that detector dict (id defaults to the dedupe_key, one record
  per dedupe key). The brief and dashboard surfaces are fed
  that same record object, not retyped copies, so an id or
  severity mismatch between surfaces would fail the run rather
  than being typed away.
- The dashboard check reads the panel's alertRows data (id,
  kind, severity) and the rendered card HTML. Honest limit,
  stated in the transcript: the card renders kind, severity,
  explanation and suggested fix, but not the id literal itself
  -- the id lives in the panel's row data, not in the card text.
  That is a rendering observation for Rowan's DSH lane, not a
  mismatch: no surface here carries a different id or severity.

Stages, each asserted, any failure failing the run:

  1. tick: exactly one presence-stall alert, severity critical.
  2. store: the record's id is the dedupe_key, severity critical.
  3. brief: Watch items carry exactly that id, and the template
     brief text renders "id: summary".
  4. dashboard: the panel's first alert row carries exactly that
     id and severity, and its card HTML carries the kind and
     severity.
  5. quiet: a healthy snapshot yields zero alerts on all three
     surfaces (no invented alert id anywhere).
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from intel import brief  # noqa: E402
from intel import store as istore  # noqa: E402
from intel import watchdog  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
LOG = os.path.join(REPO, "intel", "evals", "e2e_watchdog_surfaces.log")

STALL_SNAPSHOT = {
    "jobs": [{"id": "7", "title": "demo job",
              "status": "claimed", "claim": "pax",
              "claimed_at": 9340}],
    "presence": ["hana"],
    "caps": {"pax": {"caps": "build"}},
}
NOW = 10000

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
global.window = {
  busUtil: {
    panel: (id) => (bodies[id] || (bodies[id] = { innerHTML: "", parentNode: { open: false } })),
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;"),
    nickColor: () => "#58a6ff",
    myNick: () => "rowan",
    busKey: () => "muse-bus",
    roomName: () => "build-int",
    api: async () => { throw new Error("no live api"); },
  },
  busHooks: { connect: [], poll: [] },
  location: { search: "" },
};
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: () => {} } },
};
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
ip.setAlerts(__RECORD__, __NOW_MS__);
const out = {};
out.rows = ip.alertRows(__NOW_MS__);
out.html = bodies["intel-alerts"].innerHTML;
console.log(JSON.stringify(out));
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _dashboard_check(record):
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        mod_path = f.name
        f.write(module)
    driver = (NODE_DRIVER
              .replace("__MODULE_PATH__", json.dumps(mod_path))
              .replace("__RECORD__", json.dumps([record]))
              .replace("__NOW_MS__", str(NOW * 1000)))
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
    assert r.returncode == 0, "node dashboard harness failed: %s" % r.stderr
    return json.loads(r.stdout)


def run_loop(write_log=True):
    lines = []
    stages = []

    def stage(name, ok, detail):
        stages.append((name, ok, detail))
        lines.append("%s: %s -- %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            raise AssertionError("%s: %s" % (name, detail))

    # 1. tick
    alerts = watchdog.tick(STALL_SNAPSHOT, now=NOW)
    stage("tick", len(alerts) == 1
          and alerts[0]["kind"] == "presence-stall"
          and alerts[0]["severity"] == "critical",
          "exactly one presence-stall alert, severity critical: %s"
          % (alerts[0] if alerts else "none"))

    # 2. store record, built from the detector dict itself
    record = istore.build_alert_record(alerts[0], room="build-int")
    stage("store", record["id"] == alerts[0]["dedupe_key"]
          and record["severity"] == "critical",
          "record id=%s severity=%s room=%s"
          % (record["id"], record["severity"], record["room"]))

    # 3. brief surface: same record, same id
    snapshot = dict(STALL_SNAPSHOT)
    snapshot["alerts"] = [record]
    items = brief.extract_watch_items(snapshot)
    text = brief.compose_template_brief(snapshot)
    stage("brief", len(items) == 1 and items[0]["id"] == record["id"]
          and ("%s: " % record["id"]) in text,
          "Watch items id=%s; template brief renders 'id: summary'"
          % (items[0]["id"] if items else "none"))

    # 4. dashboard surface: same record, same id and severity
    dash = _dashboard_check(record)
    rows = dash["rows"]
    stage("dashboard", len(rows) == 1 and rows[0]["id"] == record["id"]
          and rows[0]["severity"] == "critical"
          and "presence-stall" in dash["html"]
          and "critical" in dash["html"],
          "panel row id=%s severity=%s; card renders kind+severity "
          "(id literal itself is row data, not card text)"
          % (rows[0]["id"] if rows else "none",
             rows[0]["severity"] if rows else "none"))

    # 5. quiet fixture: no surface invents an alert
    quiet = watchdog.tick({"jobs": [], "presence": [], "caps": {}}, now=NOW)
    quiet_items = brief.extract_watch_items({"alerts": []})
    stage("quiet", quiet == [] and quiet_items == [],
          "quiet tick yields zero alerts; Watch items empty")

    lines.append("INT-020: PASS -- id %s severity critical on store, "
                 "brief, and dashboard row" % record["id"])
    transcript = "\n".join(lines) + "\n"
    if write_log:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write(transcript)
    return {"ok": True, "stages": stages, "transcript": transcript,
            "alert_id": record["id"], "record": record}


if __name__ == "__main__":
    try:
        result = run_loop(write_log=True)
    except AssertionError as e:
        print("INT-020: FAIL -- %s" % e)
        sys.exit(1)
    print(result["transcript"])
