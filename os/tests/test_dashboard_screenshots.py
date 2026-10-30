#!/usr/bin/env python3
"""DSH-030 screenshot set for submission (hackathon/.../submission-assets/).

Pins the eight shots: every file present, a real PNG of sane size, and
named in the set's README. The node-driver test pins the claim behind
the shots: the current intelPanel module, fed the DSH-037 dev-pack
payloads, still renders crew 3 / brief template / plan-ready with 5
jobs / 5 critical alerts — so a panel change that alters a shot's
content fails the suite instead of silently dating the set.
"""
import json
import os
import struct
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "hackathon", "relay-intelligence",
                       "submission-assets")
BUS = os.path.join(REPO, "bus.html")

SHOTS = ["crew-board-desktop.png", "crew-board-phone.png",
         "brief-panel-desktop.png", "brief-panel-phone.png",
         "dispatch-preview-desktop.png", "dispatch-preview-phone.png",
         "alerts-firing-desktop.png", "alerts-firing-phone.png"]

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
const LOC = "?demo=1";
const NOW = 1793102100000;
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
    roomName: () => "build-relay-intel",
    api: async () => { throw new Error("no live api"); },
  },
  busHooks: { connect: [], poll: [] },
  location: { search: LOC },
};
global.document = {
  getElementById: () => null, createElement: () => ({}),
  body: { classList: { add: () => {} } },
};
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
if (!ip) throw new Error("intelPanel test hook missing");
ip.setCrew(__CREW__, 1793101200000);
ip.setJobs(__JOBS__, 1793101200000);
ip.setCaps(__CAPS__, 1793101200000);
ip.setBrief(__BRIEF__, NOW);
ip.setGoalDraft(__GOAL__);
ip.setPlan(__PLAN__);
ip.setAlerts(__ALERTS__, NOW);
console.log(JSON.stringify(ip.snapshot()));
"""


def _load_pack(name):
    with open(os.path.join(REPO, "intel", "devpack", name),
              encoding="utf-8") as f:
        return json.load(f)


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG: %s" % path
    width, height = struct.unpack(">II", head[16:24])
    return width, height


class DashboardScreenshotsTest(unittest.TestCase):
    def test_all_eight_shots_present_and_valid_png(self):
        for shot in SHOTS:
            path = os.path.join(ASSETS, shot)
            self.assertTrue(os.path.exists(path), "missing shot: %s" % shot)
            width, height = _png_size(path)
            self.assertGreater(width, 100, shot)
            self.assertGreater(height, 100, shot)
            self.assertGreater(os.path.getsize(path), 10000, shot)

    def test_readme_names_every_shot(self):
        with open(os.path.join(ASSETS, "README.md"),
                  encoding="utf-8") as f:
            readme = f.read()
        for shot in SHOTS:
            self.assertIn(shot, readme, "README omits %s" % shot)

    def test_devpack_renders_match_the_shots(self):
        with open(BUS, encoding="utf-8") as f:
            module = _intel_module(f.read())
        crew_pack = _load_pack("crew_board.json")
        brief_pack = _load_pack("brief.json")
        plan_pack = _load_pack("plan_preview.json")
        alerts_pack = _load_pack("alerts.json")
        crew_rows = [{"nick": n,
                      "host": crew_pack["caps"][n]["host"],
                      "lastSeen": 1793101200 * 1000}
                     for n in crew_pack["presence"]]
        cap_rows = [{"nick": n, "caps": c["caps"], "roles": c["roles"],
                     "updated": int(c["updated"])}
                    for n, c in sorted(crew_pack["caps"].items())]
        driver = NODE_DRIVER \
            .replace("__CREW__", json.dumps(crew_rows)) \
            .replace("__JOBS__", json.dumps(crew_pack["jobs"])) \
            .replace("__CAPS__", json.dumps(cap_rows)) \
            .replace("__BRIEF__", json.dumps(brief_pack["fresh"])) \
            .replace("__GOAL__", json.dumps(plan_pack["summary"])) \
            .replace("__PLAN__", json.dumps(plan_pack)) \
            .replace("__ALERTS__", json.dumps(alerts_pack["alerts"]))
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False) as f:
            mod_path = f.name
            f.write(module)
        driver = driver.replace("__MODULE_PATH__", json.dumps(mod_path))
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
        self.assertEqual(r.returncode, 0, "node failed: %s" % r.stderr)
        snap = json.loads(r.stdout)
        self.assertEqual(snap["crew"], 3)
        self.assertEqual(snap["jobs"], 3)
        self.assertEqual(snap["caps"], 3)
        self.assertTrue(snap["brief"])
        self.assertEqual(snap["briefKind"], "morning")
        self.assertTrue(snap["briefTemplate"])
        self.assertTrue(snap["plan"])
        self.assertEqual(snap["dispatchState"], "plan-ready")
        self.assertEqual(snap["alerts"], 5)
        self.assertEqual(snap["header"]["criticalAlerts"], 5)
        self.assertEqual(snap["header"]["agentsOnline"], 3)


if __name__ == "__main__":
    unittest.main()
