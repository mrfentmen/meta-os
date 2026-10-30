#!/usr/bin/env python3
"""DSH-035 cross-browser check pin.

The 2026-10-27 run rendered bus.html in Chromium and in Playwright's
WebKit build (Safari engine) at desktop and 390px phone widths, with
the DSH-037 dev-pack fixtures fed through the __busTest.intelPanel
hook. This test pins the durable claims of that run's log: all four
engine x viewport runs recorded PASS, and the verdict was that no
Safari-only bug was found (so nothing was filed before demo freeze).
The screenshots and raw results JSON are run evidence in the goal
workspace's hidden_files/dsh035/, not repo files, so this test pins
the log, not the artifacts.
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(REPO, "docs", "DSH-035-CROSS-BROWSER-CHECK.md")


class CrossBrowserCheckTest(unittest.TestCase):
    def test_log_records_all_four_runs_pass(self):
        with open(LOG, encoding="utf-8") as f:
            text = f.read()
        for row in ("Chromium (Playwright, cached build) | 1280x900 | PASS",
                    "Chromium (Playwright, cached build) | 390x844 (phone) | PASS",
                    "WebKit (Playwright, Safari engine) | 1280x900 | PASS",
                    "WebKit (Playwright, Safari engine) | 390x844 (phone) | PASS"):
            self.assertIn(row, text, "check log omits run: %s" % row)

    def test_log_records_no_safari_only_bug_verdict(self):
        with open(LOG, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("No Safari-only bug found", text)
        self.assertIn("nothing to file before demo freeze", text)

    def test_log_states_ios_device_caveat_plainly(self):
        with open(LOG, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("No physical iOS device", text)
        self.assertIn("INT-030", text)


if __name__ == "__main__":
    unittest.main()
