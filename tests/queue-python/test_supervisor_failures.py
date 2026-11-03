"""Supervisor repeated-failure pins (CB2-094..095).

The supervisor records repeated job failures. It has no restart
loop and no exponential backoff — a found gap, not a feature. These
tests pin that absence so a later change has to be deliberate.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402
import supervisor  # noqa: E402

NOW = datetime(2026, 11, 2, 12, 0, 0,
               tzinfo=timezone.utc).timestamp()


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


class FailurePinTests(unittest.TestCase):
    def setUp(self):
        self.records = crew_records.CrewRecords(
            directory=tempfile.mkdtemp(prefix="supervisor-fail-"))
        for _ in range(3):
            self.records.append_event({
                "at": iso(NOW - 60), "type": "patrol-check",
                "camera_id": "cam-x", "outcome": "job-error"})

    def _run(self):
        return supervisor.Supervisor(
            records=self.records,
            guardrail_status=lambda: {
                "calls": 0, "est_cost_usd": 0.0,
                "test_budget_usd": 75.0, "remaining_usd": 75.0},
            now_epoch=lambda: NOW,
            patrol_stale_s=10 ** 9,
            incident_stuck_s=10 ** 9,
            budget_warn_fraction=2.0).run()

    def test_threshold_failure_is_recorded_once_not_restarted(self):
        first = self._run()
        findings = [f for f in first["findings"]
                    if f["detector"] == "repeated_job_failure"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["action"], "job_failure_warning")
        self.assertNotIn("restart", repr(findings).lower())
        second = self._run()
        self.assertEqual(
            [f for f in second["findings"]
             if f["detector"] == "repeated_job_failure"], [])

    def test_no_restart_or_backoff_implementation_exists(self):
        self.assertFalse(hasattr(supervisor, "backoff_delay"))
        self.assertFalse(hasattr(supervisor, "restart_sequence"))
        source = open(supervisor.__file__).read().lower()
        self.assertNotIn("restart_count", source)
        self.assertNotIn("exponential backoff", source)


if __name__ == "__main__":
    unittest.main()
