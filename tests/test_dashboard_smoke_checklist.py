#!/usr/bin/env python3
"""DSH-029 dashboard smoke checklist (spec section 8).

Acceptance: a checklist file in repo docs/ lists 10 manual checks and
is run before every deploy. The checks that a browser viewport alone
can prove (390px scroll, tap-target geometry, live hash scroll) are
recorded in the checklist as harness-covered, not browser-verified,
on runs without a viewport; everything machine-checkable here is
asserted from the shipped files: the checklist structure, the
bus/index identity it gates on, the four panel ids, the demo and
deep-link markers, the mobile CSS, and the no-new-timer rule.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")
CHECKLIST = os.path.join(REPO, "docs", "DASHBOARD_SMOKE_CHECKLIST.md")

PANELS = ["intel-crew", "intel-brief", "intel-dispatch", "intel-alerts"]


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


class DashboardSmokeChecklistTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        with open(CHECKLIST, encoding="utf-8") as f:
            cls.checklist = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.style = cls.bus.split("<style>")[1].split("</style>")[0]

    def test_checklist_exists_with_exactly_ten_checks(self):
        heads = re.findall(r"^## Check (\d+) —", self.checklist,
                           flags=re.MULTILINE)
        self.assertEqual(heads, [str(n) for n in range(1, 11)],
                         "checklist must list checks 1-10 in order, "
                         "found %r" % heads)

    def test_every_check_names_its_pass_criteria(self):
        sections = re.split(r"^## Check \d+ —", self.checklist,
                            flags=re.MULTILINE)[1:]
        self.assertEqual(len(sections), 10)
        for i, sec in enumerate(sections, 1):
            self.assertIn("- Pass:", sec,
                          "check %d has no pass criteria" % i)

    def test_checklist_covers_the_deploy_gates(self):
        for needle in ("intel-crew", "intel-brief", "intel-dispatch",
                       "intel-alerts", "?demo=1", "#intel/brief/",
                       "#intel/alert/", "390px", "read-only",
                       "setInterval"):
            self.assertIn(needle, self.checklist,
                          "checklist never mentions %s" % needle)

    def test_checklist_has_run_procedure_and_log(self):
        self.assertIn("Run procedure", self.checklist)
        self.assertIn("Run log", self.checklist)
        self.assertIn("Any fail: stop", self.checklist)

    def test_check1_bus_and_index_identical(self):
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_check3_all_four_panel_ids_present(self):
        for panel in PANELS:
            self.assertIn(panel, self.bus,
                          "panel id %s missing from bus.html" % panel)

    def test_check8_demo_and_deep_link_markers_present(self):
        self.assertIn("body.demo-mode", self.style)
        self.assertIn("intel-alert-", self.bus)
        self.assertIn("intel-brief-", self.bus)

    def test_check9_mobile_stack_css_present(self):
        self.assertIn("390px", self.bus)
        self.assertIn("min-height: 40px", self.style)

    def test_check10_intel_module_adds_no_timers(self):
        self.assertNotIn("setInterval", self.intel)
        self.assertNotIn("setTimeout", self.intel)

    def test_spec_documents_smoke_checklist(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("DSH-029", spec)
        self.assertIn("DASHBOARD_SMOKE_CHECKLIST.md", spec)


if __name__ == "__main__":
    unittest.main()
