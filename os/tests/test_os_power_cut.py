"""Power-cut drill (Milo lane, OS-040).

Pinned here: three cut/reboot/recover runs all pass with zero
manual fixes, each run's stall alert, sweep requeue, and boot
brief recovery line, and the control proving the sweep
respects an unexpired lease. A real hard kill of a booted
Meta OS image is NOT proven here: there is no test image in
this repo, so the drill proves the watchdog + sweep + brief
half on fixtures.
"""

import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import power_cut  # noqa: E402


class PowerCutDrillTest(unittest.TestCase):
    def test_three_runs_all_pass(self):
        report = power_cut.run_drill()
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["runs"]), 3)

    def test_each_run_recovers_its_job_and_reports_it(self):
        report = power_cut.run_drill()
        for run in report["runs"]:
            self.assertEqual(run["requeued"], [run["job"]])
            self.assertEqual(run["alert"]["kind"], "presence-stall")
            self.assertEqual(run["alert"]["nick"], run["nick"])
            self.assertIn(run["job"], run["recovery_line"])
            self.assertIn("1 recovered", run["recovery_line"])
            self.assertNotIn("recovery incomplete",
                             run["recovery_line"])

    def test_control_reboot_before_lease_expiry_requeues_nothing(self):
        self.assertTrue(power_cut.run_drill()["control_ok"])

    def test_drill_log_names_all_three_runs(self):
        log = "\n".join(power_cut.run_drill()["log"])
        for nick, job in power_cut.RUNS:
            self.assertIn(f"{nick}/job {job}", log)


if __name__ == "__main__":
    unittest.main()
