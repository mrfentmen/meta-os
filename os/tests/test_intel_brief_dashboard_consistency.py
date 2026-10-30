#!/usr/bin/env python3
"""INT-025: brief/dashboard consistency — the brief panel shows the same
brief text the CLI shows for the same id.

Three brief ids, generated as template briefs (no Spark call) through
intel/brief.py generate_brief, then checked two ways:

- CLI side: intel.py brief --show prints json.dumps(record, indent=2,
  sort_keys=True), so the CLI text for an id is the record itself.
- Panel side: the real intelPanel module from bus.html, driven with
  the DSH-030 node-driver stub, fed the same record through setBrief.

The panel must carry every section item from the CLI-shown record,
in section order, with nothing added and nothing dropped. An empty
section renders "No items." in the panel, never an invented item.
"""

import html as _html
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")

# Section order the panel renders (bus.html BRIEF_SECTIONS).
SECTION_ORDER = ("Decisions", "In flight", "Owners",
                 "Blocked and why", "Watch items")

NODE_DRIVER = r"""
const fs = require("fs");
const bodies = {};
global.window = {
  busUtil: {
    panel: (id) => {
      if (!bodies[id]) {
        bodies[id] = { innerHTML: "", parentNode: { open: false } };
      }
      return bodies[id];
    },
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;"),
    nickColor: () => "#58a6ff",
    myNick: () => "rowan",
    busKey: () => "muse-bus",
    roomName: () => "build-relay-intel",
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
ip.setBrief(__BRIEF__, __NOW__);
console.log(JSON.stringify(bodies["intel-brief"].innerHTML));
"""

QUIET_SNAPSHOT = {
    "messages": [{"nick": "pax", "text": "morning, checking in"}],
    "jobs": [],
}

BUSY_SNAPSHOT = {
    "messages": [
        {"nick": "pax", "text": "DECISION: freeze the wire format today"},
        {"nick": "milo", "text": "DONE: watchdog loop runs on the stall fixture"},
        {"nick": "rowan",
         "text": "BLOCKED: brief panel needs the frozen payload contract"},
    ],
    "jobs": [
        {"id": "3", "title": "brief panel", "status": "claimed",
         "claim": "pax", "note": "working"},
        {"id": "5", "title": "dispatch poster", "status": "open"},
        {"id": "7", "title": "spark client", "status": "blocked",
         "note": "waiting on the real Spark endpoint, not a fake one"},
        {"id": "9", "title": "watchdog loop", "status": "done",
         "note": "finished"},
    ],
}

STALL_SNAPSHOT = {
    "messages": [
        {"nick": "milo", "text": "DECISION: restart the watchdog loop"},
    ],
    "jobs": [
        {"id": "11", "title": "watchdog loop", "status": "blocked",
         "note": "no beat in 20 minutes"},
    ],
    "alerts": [
        {"id": "ALERT-STALL-1",
         "summary": "watchdog loop silent for 20 minutes"},
    ],
}


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _panel_text(record, now_ms):
    with open(BUS, encoding="utf-8") as f:
        module = _intel_module(f.read())
    driver = NODE_DRIVER \
        .replace("__BRIEF__", json.dumps(record)) \
        .replace("__NOW__", str(now_ms))
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
    assert r.returncode == 0, "node failed: %s" % r.stderr
    raw = json.loads(r.stdout)
    text = re.sub(r"<[^>]+>", "\n", raw)
    return _html.unescape(text)


def _panel_items(panel_text):
    items = []
    for line in panel_text.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:])
    return items


class BriefDashboardConsistencyTest(unittest.TestCase):
    def test_panel_matches_cli_for_three_brief_ids(self):
        cases = [
            ("quiet", QUIET_SNAPSHOT, 1793101200),
            ("busy", BUSY_SNAPSHOT, 1793104800),
            ("stall", STALL_SNAPSHOT, 1793108400),
        ]
        for name, snapshot, ts in cases:
            with self.subTest(brief=name):
                _text, record = brief.generate_brief(
                    snapshot, "build", kind="morning", now=ts,
                    dry_run=True)
                brief_id = "build:%d" % record["generated_at"]
                # CLI side: intel.py brief --show prints exactly this.
                cli_text = json.dumps(record, indent=2, sort_keys=True)
                self.assertEqual(json.loads(cli_text)["sections"],
                                 record["sections"])
                self.assertEqual(record["generated_at"], ts)
                # Panel side: the same record through intelPanel.
                panel_text = _panel_text(record, ts * 1000)
                self.assertIn("morning", panel_text)
                self.assertIn("TEMPLATE", panel_text)
                expected = []
                empty_sections = 0
                for key in SECTION_ORDER:
                    items = record["sections"][key]
                    if items:
                        expected.extend(items)
                    else:
                        empty_sections += 1
                self.assertEqual(_panel_items(panel_text), expected,
                                 "panel items differ from CLI record "
                                 "for %s" % brief_id)
                self.assertEqual(panel_text.count("No items."),
                                 empty_sections,
                                 "empty sections must read empty, "
                                 "not invented, for %s" % brief_id)
                # Every panel item is verbatim in the CLI text.
                for item in expected:
                    self.assertIn(item, cli_text)

    def test_busy_sections_are_the_fixture_values(self):
        _text, record = brief.generate_brief(
            BUSY_SNAPSHOT, "build", kind="morning", now=1793104800,
            dry_run=True)
        sections = record["sections"]
        self.assertEqual(sections["Decisions"], [
            "decision: freeze the wire format today",
            "done: watchdog loop runs on the stall fixture",
            "blocked: brief panel needs the frozen payload contract",
        ])
        self.assertEqual(sections["In flight"],
                         ["3 brief panel", "5 dispatch poster"])
        self.assertEqual(sections["Owners"], ["pax: brief panel"])
        self.assertEqual(sections["Blocked and why"], [
            "7 spark client: waiting on the real Spark endpoint, "
            "not a fake one",
        ])
        self.assertEqual(sections["Watch items"], [])

    def test_stall_watch_item_is_the_alert(self):
        _text, record = brief.generate_brief(
            STALL_SNAPSHOT, "build", kind="morning", now=1793108400,
            dry_run=True)
        self.assertEqual(record["sections"]["Watch items"],
                         ["ALERT-STALL-1: watchdog loop silent "
                          "for 20 minutes"])
        self.assertEqual(record["sections"]["Blocked and why"],
                         ["11 watchdog loop: no beat in 20 minutes"])


if __name__ == "__main__":
    unittest.main()
