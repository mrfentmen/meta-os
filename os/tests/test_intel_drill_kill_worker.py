"""WDG-020: the kill-a-worker drill passes unattended on fixtures.

The drill script itself (intel/drills/kill_worker.py) is the
acceptance artifact — a fake worker claims a job, posts one
progress note, dies mid-job, the watchdog raises exactly one
presence-stall alert, and the lease sweep requeues the job.
These tests pin the drill into the suite so a detector or
threshold change that breaks the demo scenario breaks the
suite too, and they cover the sweep rule's negative case
directly: an unexpired lease is never requeued early.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import kill_worker  # noqa: E402


class KillWorkerDrillTest(unittest.TestCase):
    def test_drill_passes_and_reports_the_stall_alert(self):
        report = kill_worker.run_drill()
        alert = report["alert"]
        self.assertEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["nick"], "pax")
        self.assertEqual(alert["job"], "7")
        self.assertEqual(report["requeued"], ["7"])
        self.assertEqual(len(report["log"]), 4)

    def test_sweep_leaves_unexpired_and_open_jobs_alone(self):
        snapshot = {"jobs": [
            {"id": "1", "status": "claimed", "claim": "pax",
             "lease_until": 2000},
            {"id": "2", "status": "open"},
            {"id": "3", "status": "claimed"},
        ]}
        self.assertEqual(kill_worker.sweep_expired_leases(snapshot, 1500),
                         [])
        self.assertEqual(snapshot["jobs"][0]["status"], "claimed")
        self.assertEqual(kill_worker.sweep_expired_leases(snapshot, 2000),
                         ["1"])
        self.assertEqual(snapshot["jobs"][0]["status"], "open")
        self.assertNotIn("claim", snapshot["jobs"][0])
        self.assertNotIn("lease_until", snapshot["jobs"][0])
        # The open job and the leaseless claimed job are untouched.
        self.assertEqual(snapshot["jobs"][1]["status"], "open")
        self.assertEqual(snapshot["jobs"][2]["status"], "claimed")

    def test_cli_main_exits_zero_and_prints_pass(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kill_worker.main([])
        self.assertEqual(code, 0)
        self.assertIn("kill_worker drill: PASS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
