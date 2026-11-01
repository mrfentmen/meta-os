#!/usr/bin/env python3
"""DOC-018 deploy runbook for muse-relay-live.

Acceptance: a runbook in docs/ covering build marker, deploy,
verify, and rollback. The test pins the runbook's presence and
its four required sections, the live URL, the smoke-checklist and
Pax-review gates, and the honest status the runbook itself
carries: no deploy command is pinned (the repo holds no wrangler
config, Cloudflare credential, or deploy workflow), and rollback
is documented but unconfirmed until INT-031. A runbook that
invented a deploy command would pass a naive section check and
lie to the next operator, so the absence statement is pinned too.
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOK = os.path.join(REPO, "docs", "DEPLOY_RUNBOOK.md")


def read_runbook():
    with open(RUNBOOK, encoding="utf-8") as fh:
        return fh.read()


class DeployRunbookTest(unittest.TestCase):
    def test_runbook_exists(self):
        self.assertTrue(os.path.isfile(RUNBOOK))

    def test_four_required_sections_present(self):
        text = read_runbook()
        for section in ("Build marker", "Deploy", "Verify", "Rollback"):
            self.assertIn(section, text, "missing section: %s" % section)

    def test_live_url_and_project_named(self):
        text = read_runbook()
        self.assertIn("https://muse-relay-live.pages.dev", text)
        self.assertIn("muse-relay-live", text)

    def test_predeploy_gates_named(self):
        text = read_runbook()
        self.assertIn("DASHBOARD_SMOKE_CHECKLIST.md", text)
        self.assertIn("cmp bus.html index.html", text)
        self.assertIn("DSH-039", text)  # Pax review gate

    def test_marker_must_be_rendered_visible(self):
        text = read_runbook()
        self.assertIn("rendered-visible", text)

    def test_no_pinned_deploy_command_claim(self):
        # The runbook must say plainly that no command is pinned,
        # rather than inventing one from no repo evidence.
        text = read_runbook()
        self.assertIn("does\n**not** pin a command", text)

    def test_rollback_marked_unconfirmed_until_int031(self):
        text = read_runbook()
        self.assertIn("INT-031", text)
        self.assertIn("unconfirmed", text)

    def test_no_credential_recorded(self):
        text = read_runbook()
        for forbidden in ("api_token", "CF_API_TOKEN", "Bearer "):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
