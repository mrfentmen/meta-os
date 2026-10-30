#!/usr/bin/env python3
"""DSH-038 decision pins: dispatch approve is request-only.

Acceptance: the decision plus rationale live in docs/DASHBOARD_SPEC.md
(section 5.6), and the panel implementation matches it: the live Post
button stays disabled under DISPATCH_POST_ENABLED (false), the
approve flow makes no U.api post call, and the mock note tells the
human the real post happens from the CLI. No behavior is changed by
this batch; these tests pin the decided posture so a later lane
cannot quietly re-enable a browser write path.
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Dsh038Test(unittest.TestCase):
    def setUp(self):
        self.spec = read(SPEC)
        self.bus = read(BUS)

    def test_spec_has_request_only_decision_section(self):
        self.assertIn("### 5.6 DSH-038 decision", self.spec)
        section = self.spec.split("### 5.6 DSH-038 decision", 1)[1]
        section = section.split("## 6. Alerts panel", 1)[0]
        self.assertIn("request-only", section)
        self.assertIn("the viewer never posts a dispatch plan", section)
        self.assertIn("no live", section)
        self.assertIn("no flip task", section)

    def test_spec_decision_gives_real_cli_flow(self):
        section = self.spec.split("### 5.6 DSH-038 decision", 1)[1]
        section = section.split("## 6. Alerts panel", 1)[0]
        self.assertIn("--dry-run --plan plan.json", section)
        self.assertIn("--plan plan.json --approve", section)
        self.assertIn("--secret-file", section)
        self.assertIn("--show <id>", section)
        self.assertIn("--undo <id>", section)

    def test_spec_decision_names_why_not_deferred(self):
        section = self.spec.split("### 5.6 DSH-038 decision", 1)[1]
        section = section.split("## 6. Alerts panel", 1)[0]
        self.assertIn("chmod 600", section)
        self.assertIn("secrets never reach", section)
        self.assertIn("GOV-002", section)

    def test_spec_decision_reopens_only_on_dale_plus_server(self):
        section = self.spec.split("### 5.6 DSH-038 decision", 1)[1]
        section = section.split("## 6. Alerts panel", 1)[0]
        self.assertIn("only a Dale decision", section)
        self.assertIn("server-side", section)

    def test_spec_no_longer_waits_on_viewer_posting_rule_for_dispatch(self):
        self.assertNotIn(
            "Dispatch approve) ship disabled/read-only until Dale's "
            "posting rule", self.spec)
        self.assertIn("Dispatch approve is decided, not pending", self.spec)
        self.assertIn("Dispatch approve is request-only (DSH-038",
                      self.spec)

    def test_viewer_files_stay_identical(self):
        self.assertEqual(self.bus, read(INDEX))

    def test_dispatch_post_gate_stays_off(self):
        self.assertIn("var DISPATCH_POST_ENABLED = false;", self.bus)

    def test_approve_flow_makes_no_api_post_call(self):
        start = self.bus.index("function approvePost(")
        end = self.bus.index("// --- Posted-plan tracker", start)
        self.assertNotIn("U.api", self.bus[start:end])

    def test_mock_note_names_request_only_cli_post(self):
        self.assertIn("request-only", self.bus)
        self.assertIn("intel.py dispatch --goal", self.bus)
        self.assertIn("--plan plan.json --approve", self.bus)

    def test_panel_holds_no_keyring_or_secret_file_reference(self):
        self.assertNotIn("keyring", self.bus)
        self.assertNotIn("secret-file", self.bus)


if __name__ == "__main__":
    unittest.main()
