#!/usr/bin/env python3
"""OS-084 capability refusal banner (banner part only).

Acceptance, banner part: a capability refusal renders as a
visible banner tied to Milo's alert record. The record is the
OS-081 shape: intel/capability.refusal_alert builds kind
"capability-refusal", severity warning, id = dedupe_key
"capability-refusal:<identity>:<action>:<subject>", explanation
naming identity, action, and missing capability, persisted open
by intel/store.build_alert_record. The driver cycles the live
renderAlerts through the harness hooks (setAlerts + the
refusalBannerRows hook):

- no refusal: a stall alert banners nothing.
- open refusal: one banner line at the top of the panel, with
  the record's explanation verbatim.
- acknowledged refusal: still banners (unresolved).
- resolved refusal: banners nothing, collapses into the
  resolved count (DSH-014).
- mixed feed: only the refusal banners, exactly once.
- live OS-081 module: the refusal_alert it builds really has
  the kind/severity/id shape the banner keys off.

Nothing here posts: the panel only reads (spec section 0 gate).
Not shipped here: per-process capability summaries (need the
OS-080 grant files, not landed) and artifact links (need the
OS-083 store, not landed). Not proven here: the banner
rendering from live data on a booted image (no test image in
repo) — integration-day work (INT-028).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")

T0 = 100000

REFUSAL = {"id": "capability-refusal:milo:bus_post:-",
           "kind": "capability-refusal", "severity": "warning",
           "subjects": ["milo"],
           "explanation": "milo tried bus_post but lacks bus_post",
           "suggested_fix": "Grant bus_post or stop posting",
           "created_at": T0, "resolved_at": None, "status": "open"}
STALL = {"id": "alert:stall-1", "kind": "stall",
         "severity": "critical", "subjects": ["milo"],
         "explanation": "milo stalled on job 1",
         "suggested_fix": "Check the worker",
         "created_at": T0 - 10, "resolved_at": None,
         "status": "open"}
ACKED = dict(REFUSAL, status="acknowledged",
             acknowledged_at=T0)
RESOLVED = dict(REFUSAL, status="resolved",
                resolved_at=T0 + 5)

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
const alertsBody = () => bodies["intel-alerts"]
  ? bodies["intel-alerts"].innerHTML : "";
const out = {};
const ip = (() => {
  eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
  return global.window.__busTest.intelPanel;
})();
if (!ip) throw new Error("intelPanel test hook missing");
const NOW = (__T0__ + 5) * 1000;
ip.setAlerts([__STALL__], NOW);
out.noRefusal = alertsBody();
out.noRefusalRows = ip.refusalBannerRows(NOW);
ip.setAlerts([__REFUSAL__], NOW);
out.openRefusal = alertsBody();
out.openRefusalRows = ip.refusalBannerRows(NOW);
ip.setAlerts([__ACKED__], NOW);
out.ackedRefusal = alertsBody();
ip.setAlerts([__RESOLVED__], NOW);
out.resolvedRefusal = alertsBody();
out.resolvedRefusalRows = ip.refusalBannerRows(NOW);
ip.setAlerts([__STALL__, __REFUSAL__], NOW);
out.mixed = alertsBody();
out.mixedRows = ip.refusalBannerRows(NOW);
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
              .replace("__STALL__", json.dumps(STALL))
              .replace("__REFUSAL__", json.dumps(REFUSAL))
              .replace("__ACKED__", json.dumps(ACKED))
              .replace("__RESOLVED__", json.dumps(RESOLVED)))
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


class Os084Test(unittest.TestCase):
    def test_no_refusal_banners_nothing(self):
        data = _run_driver()
        self.assertNotIn("Capability refusal", data["noRefusal"])
        self.assertEqual(data["noRefusalRows"], [])

    def test_open_refusal_banners_explanation_verbatim(self):
        data = _run_driver()
        self.assertIn("Capability refusal: milo tried bus_post "
                      "but lacks bus_post", data["openRefusal"])
        self.assertEqual(len(data["openRefusalRows"]), 1)
        self.assertEqual(data["openRefusalRows"][0]["kind"],
                         "capability-refusal")
        # Banner sits above the feed cards: its text precedes the
        # card's identical explanation only via the banner marker.
        self.assertLess(data["openRefusal"].index("Capability refusal:"),
                        data["openRefusal"].index("Subjects:"))

    def test_acknowledged_refusal_still_banners(self):
        data = _run_driver()
        self.assertIn("Capability refusal: milo tried bus_post "
                      "but lacks bus_post", data["ackedRefusal"])

    def test_resolved_refusal_banners_nothing_and_collapses(self):
        data = _run_driver()
        self.assertNotIn("Capability refusal", data["resolvedRefusal"])
        self.assertEqual(data["resolvedRefusalRows"], [])
        self.assertIn("1 resolved", data["resolvedRefusal"])

    def test_mixed_feed_banners_only_the_refusal_once(self):
        data = _run_driver()
        self.assertEqual(data["mixed"].count("Capability refusal:"), 1)
        self.assertEqual(len(data["mixedRows"]), 1)

    def test_live_os081_module_builds_the_banner_shape(self):
        sys.path.insert(0, REPO)
        from intel import capability
        grant = {"identity": "milo", "bus_post": False,
                 "spend": False, "network": True,
                 "write_paths": ["crew/milo/"]}
        decision = capability.check_action(grant, "bus_post")
        self.assertFalse(decision["allowed"])
        alert = capability.refusal_alert(decision, now=T0)
        self.assertEqual(alert["kind"], "capability-refusal")
        self.assertEqual(alert["severity"], "warning")
        self.assertEqual(alert["dedupe_key"],
                         "capability-refusal:milo:bus_post:-")
        self.assertIn("milo", alert["explanation"])
        self.assertIn("bus_post", alert["explanation"])

    def test_spec_documents_refusal_banner_contract(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        section = spec.split("### 8.2 Capability refusal banner", 1)[1]
        section = section.split("## 9.", 1)[0]
        self.assertIn("capability-refusal", section)
        self.assertIn("OS-081", section)
        self.assertIn("OS-080", section)
        self.assertIn("OS-083", section)

    def test_viewer_files_stay_identical(self):
        with open(BUS, encoding="utf-8") as f:
            bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            index = f.read()
        self.assertEqual(bus, index, "bus.html and index.html differ")


if __name__ == "__main__":
    unittest.main()
