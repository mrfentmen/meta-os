#!/usr/bin/env python3
"""DSH-025 crew-board alert ribbon (dashboard spec section 7).

Acceptance: a job card carries a ribbon exactly when an open
critical alert record names the job in its subjects, and the ribbon
links to the alert via the section 8 hash route on the panels page
(bus.html#intel/alert/<id>). No ribbon for warning/info alerts, for
resolved alerts, or for alerts naming another job. The store
(intel/store.py _alert_subjects) names jobs bare ("7") and the spec
section 6 example names them "job 42", so both subject forms match.
An acknowledged alert is still outstanding (only resolved collapses,
DSH-014), so it keeps its ribbon. The node driver stubs document
like the other board harness tests; cardHTML / detailHTML are pure
renderers, so the driver calls them directly with fixture alert
records — no Upstash, no DOM. The ribbon text always reads
"critical alert", so the state is never carried by color alone.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "crew-board.html")

NODE_DRIVER = r"""
function elStub() {
  return { addEventListener: function () {}, hidden: false,
    textContent: "", innerHTML: "", value: "", className: "",
    focus: function () {}, querySelector: function () { return null; },
    querySelectorAll: function () { return []; } };
}
global.document = { getElementById: function () { return elStub(); },
  addEventListener: function () {}, querySelectorAll: function () { return []; } };
const out = {};
out.critBare = cardHTML("42", { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:1", kind: "stall", severity: "critical",
     subjects: ["milo", "42"] }]);
out.critJobForm = cardHTML("42", { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:2", kind: "stall", severity: "critical",
     subjects: ["Job 42"] }]);
out.critNumericJid = cardHTML(42, { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:3", kind: "stall", severity: "CRITICAL",
     subjects: ["42"] }]);
out.warn = cardHTML("42", { title: "Slow", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:4", kind: "stall", severity: "warning",
     subjects: ["42"] }]);
out.info = cardHTML("42", { title: "Note", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:5", kind: "note", severity: "info",
     subjects: ["42"] }]);
out.resolved = cardHTML("42", { title: "Fixed", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:6", kind: "stall", severity: "critical",
     status: "resolved", subjects: ["42"] }]);
out.resolvedLegacy = cardHTML("42", { title: "Fixed", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:7", kind: "stall", severity: "critical",
     resolved_at: 1700000100, subjects: ["42"] }]);
out.acked = cardHTML("42", { title: "Seen", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:8", kind: "stall", severity: "critical",
     status: "acknowledged", subjects: ["42"] }]);
out.otherJob = cardHTML("42", { title: "Fine", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:9", kind: "stall", severity: "critical",
     subjects: ["7"] }]);
out.noAlerts = cardHTML("42", { title: "Fine", status: "claimed",
  created_at: 1700000000 });
out.noId = cardHTML("42", { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ kind: "stall", severity: "critical", subjects: ["42"] }]);
out.escaped = cardHTML("42", { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:<x>", kind: "<b>", severity: "critical",
     subjects: ["42"] }]);
out.twoCrit = cardHTML("42", { title: "Stalled", status: "claimed",
  created_at: 1700000000 },
  [{ id: "alert:10", kind: "stall", severity: "critical",
     subjects: ["42"] },
   { id: "alert:11", kind: "collision", severity: "critical",
     subjects: ["42"] }]);
out.detailCrit = detailHTML("42", { title: "Stalled", status: "claimed" },
  "(spec)",
  [{ id: "alert:1", kind: "stall", severity: "critical",
     subjects: ["42"] }]);
out.detailClean = detailHTML("42", { title: "Fine", status: "claimed" },
  "(spec)", []);
console.log(JSON.stringify(out));
"""


def _script():
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    assert m, "no script block in crew-board.html"
    return m.group(1)


def _run_node():
    script = _script()
    # The page script runs DOM lookups at load; the driver stubs document
    # BEFORE those lookups run, so the stub must precede the script.
    prelude = NODE_DRIVER.split("const out = {};")[0]
    driver = NODE_DRIVER.split("const out = {};")[1]
    src = prelude + script + "\nconst out = {};" + driver
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        f.write(src)
        path = f.name
    try:
        res = subprocess.run(["node", path], capture_output=True,
                             text=True, timeout=30)
    finally:
        os.unlink(path)
    assert res.returncode == 0, f"node failed: {res.stderr}"
    return json.loads(res.stdout)


class TestCrewboardAlertRibbon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = _run_node()

    def test_bare_subject_ribbon_links_to_alert(self):
        card = self.out["critBare"]
        self.assertIn('class="ribbon"', card)
        self.assertIn('href="bus.html#intel/alert/alert%3A1"', card)
        self.assertIn("critical alert: stall", card)

    def test_job_form_subject_matches_case_insensitively(self):
        card = self.out["critJobForm"]
        self.assertIn('href="bus.html#intel/alert/alert%3A2"', card)
        self.assertIn("critical alert: stall", card)

    def test_numeric_jid_and_uppercase_severity_match(self):
        card = self.out["critNumericJid"]
        self.assertIn('href="bus.html#intel/alert/alert%3A3"', card)

    def test_warning_and_info_get_no_ribbon(self):
        self.assertNotIn("ribbon", self.out["warn"])
        self.assertNotIn("ribbon", self.out["info"])

    def test_resolved_gets_no_ribbon(self):
        self.assertNotIn("ribbon", self.out["resolved"])
        self.assertNotIn("ribbon", self.out["resolvedLegacy"])

    def test_acknowledged_keeps_ribbon(self):
        card = self.out["acked"]
        self.assertIn('href="bus.html#intel/alert/alert%3A8"', card)

    def test_alert_for_another_job_gets_no_ribbon(self):
        self.assertNotIn("ribbon", self.out["otherJob"])

    def test_no_alert_list_gets_no_ribbon(self):
        self.assertNotIn("ribbon", self.out["noAlerts"])

    def test_alert_without_id_renders_ribbon_without_link(self):
        card = self.out["noId"]
        self.assertIn('class="ribbon"', card)
        self.assertIn("critical alert: stall", card)
        self.assertNotIn("<a ", card)

    def test_kind_and_id_are_escaped(self):
        card = self.out["escaped"]
        self.assertIn("critical alert: &lt;b&gt;", card)
        self.assertNotIn("<b>", card)
        self.assertIn("alert%3A%3Cx%3E", card)

    def test_first_matching_critical_alert_wins(self):
        card = self.out["twoCrit"]
        self.assertEqual(card.count('class="ribbon"'), 1)
        self.assertIn("critical alert: stall", card)
        self.assertNotIn("collision", card)

    def test_detail_shows_ribbon_and_clean_detail_has_none(self):
        self.assertIn('href="bus.html#intel/alert/alert%3A1"',
                      self.out["detailCrit"])
        self.assertNotIn("ribbon", self.out["detailClean"])


if __name__ == "__main__":
    unittest.main()
