#!/usr/bin/env python3
"""INT-031: Cloudflare Pages deploy rollback path for muse-relay-live.

The platform procedure is confirmed from the official Cloudflare
Pages docs (dashboard Deployments -> All deployments -> three-dot
menu -> "Rollback to this deployment"), pinned here so a future
edit cannot silently swap it for a Workers-style wrangler rollback
or a guessed menu label. The project half is pinned just as hard
in the other direction: the previous production deployment id is
NOT recorded in the runbook (no deploy log entry exists and no
operator dashboard session is available from this VM), so the test
requires the runbook to say so explicitly instead of inventing an
id. A runbook that claimed a recorded id would pass a naive steps
check and lie to the next operator.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOK = os.path.join(REPO, "docs", "DEPLOY_RUNBOOK.md")


def read_runbook():
    with open(RUNBOOK, encoding="utf-8") as fh:
        return fh.read()


class RollbackInt031Test(unittest.TestCase):
    def test_exact_dashboard_steps(self):
        text = read_runbook()
        for step in ("Deployments", "All deployments",
                     "Rollback to this deployment",
                     "muse-relay-live"):
            self.assertIn(step, text, "missing rollback step: %s" % step)

    def test_valid_target_rules(self):
        text = read_runbook()
        self.assertIn("successfully built", text)
        self.assertIn("Preview deployments are **not** valid", text)

    def test_official_docs_source_cited(self):
        text = read_runbook()
        self.assertIn(
            "https://developers.cloudflare.com/pages/configuration/rollbacks/",
            text)

    def test_previous_deployment_id_explicitly_unrecorded(self):
        text = read_runbook()
        self.assertIn("Previous production deployment id", text)
        self.assertIn("not yet recorded", text)
        # No invented id: the acceptance field must not carry a
        # plausible-looking identifier next to it.
        field = re.search(
            r"Previous production deployment id.*?\n(.*?)\n", text, re.S)
        self.assertIsNotNone(field)
        self.assertNotRegex(field.group(0), r"\b[0-9a-f]{8,}\b")

    def test_project_restore_still_marked_unconfirmed(self):
        text = read_runbook()
        self.assertIn("INT-031", text)
        self.assertIn("unconfirmed", text)

    def test_failover_card_copy_present(self):
        text = read_runbook()
        self.assertIn("Failover-card copy", text)
        self.assertIn("https://muse-relay-live.pages.dev", text)

    def test_rollback_verified_by_previous_marker(self):
        text = read_runbook()
        self.assertIn("previous batch's marker", text)

    def test_no_credential_recorded(self):
        text = read_runbook()
        for forbidden in ("api_token", "CF_API_TOKEN", "Bearer "):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
