"""tests/test_intel_e2e3.py -- INT-004 end-to-end test 3, pinned.

The scripted loop in intel/e2e3.py is the acceptance artifact;
these tests pin it inside the unit harness so a regression in
any stage (drill setup, blocked item, stall alert on a real
snapshot, fresh-nick offer, on-join brief content, no
auto-post) fails the suite, not just the standalone run. The
loop runs against its own in-memory fake surface and restores
the harness job namespace, capability namespace, and nicks, so
it never touches the live bus and never disturbs the other
tests.

The loop proves the on-join path on the real command path:
the blocked job is blocked by a real jobs.py blocked command,
the alert fires on a real ingest snapshot and is stored
through the real store path, and the brief is the template
brief the offer path generates. The brief names the blocked
job by id and title and the stored alert by id with its
explanation's first line; the blocked reason itself is not
in the brief, because real snapshot rows carry no note field
yet, and the loop asserts id and title only rather than
pretending otherwise.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from intel import brief  # noqa: E402
from intel import e2e3  # noqa: E402
from intel import thresholds  # noqa: E402
from mos import capabilities  # noqa: E402


class E2E3Test(RelayTestCase):
    def test_loop_passes_all_stages(self):
        result = e2e3.run_loop(write_log=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["drill setup", "blocked item",
                                 "stall and alert", "fresh nick joins",
                                 "on-join brief", "no auto-post"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertEqual(result["blocked_job_id"], "1")
        self.assertEqual(result["stall_job_id"], "2")
        alert = result["alert"]
        self.assertEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["nick"], "worker-a")
        self.assertEqual(alert["job"], "2")
        self.assertEqual(alert["last_progress_age_seconds"],
                         thresholds.STALL_MINUTES * 60 + 61)
        self.assertEqual(result["alert_record_id"],
                         "presence-stall:worker-a:2")
        text = result["brief_text"]
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertLessEqual(len(text.split()),
                             brief.BRIEF_BUDGETS["onjoin"])
        self.assertIn("Ship the e2e3 release note", text)
        self.assertIn("presence-stall:worker-a:2", text)
        self.assertIn("INT-004: PASS", result["transcript"])

    def test_loop_twice_isolated_and_harness_untouched(self):
        capns_before = capabilities.CAPNS
        first = e2e3.run_loop(write_log=False)
        second = e2e3.run_loop(write_log=False)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        # The loop runs on its own fake surface: the harness
        # fake holds no jobs from either run, and the harness
        # job namespace and capability namespace are restored.
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(out.strip(), "[]")
        self.assertEqual(jobs.NS, "muse-bus:tjob")
        self.assertEqual(capabilities.CAPNS, capns_before)

    def test_watch_items_falls_back_to_explanation(self):
        # The INT-004 fix, pinned without the loop: a stored
        # WDG-010 record carries explanation, not summary, and
        # the brief must still render it. A record with a real
        # summary keeps that summary, and a record with
        # neither renders empty rather than inventing one.
        snapshot = {"alerts": [
            {"id": "presence-stall:worker-a:2",
             "explanation": "worker-a went quiet on job 2\nfix: requeue it"},
            {"id": "WD-1", "summary": "kept summary",
             "explanation": "ignored explanation"},
            {"id": "WD-2"},
            {"id": "", "summary": "no id, skipped"},
        ]}
        items = brief.extract_watch_items(snapshot)
        self.assertEqual(items, [
            {"id": "presence-stall:worker-a:2",
             "summary": "worker-a went quiet on job 2"},
            {"id": "WD-1", "summary": "kept summary"},
            {"id": "WD-2", "summary": ""},
        ])


if __name__ == "__main__":
    unittest.main()
