"""tests/test_intel_e2e1.py -- INT-002 end-to-end test 1, pinned.

The scripted loop in intel/e2e1.py is the acceptance artifact;
these tests pin it inside the unit harness so a regression in
any stage (dry-run, approval, poster, worker claim path, brief
digest) fails the suite, not just the standalone run. The loop
runs against its own in-memory fake surface and restores the
harness job namespace and nicks, so it never touches the live
bus and never disturbs the other tests in the file.

The loop starts from a hand-authored plan fixture, not a live
Spark call: GOV-001 leaves the live Spark transport blocked,
and the goal -> plan Spark seam belongs to DSP-017, not to
this loop. What is pinned here is the loop from a validated
plan onward, exactly what the script's docstring states.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from intel import dispatch  # noqa: E402
from intel import e2e1  # noqa: E402


class E2E1Test(RelayTestCase):
    def test_loop_passes_all_stages(self):
        result = e2e1.run_loop(write_log=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["dry-run", "approve", "post",
                                 "worker probe", "worker report",
                                 "brief"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertIn("dispatch_id", result)
        self.assertEqual(sorted(result["job_ids"]), ["probe", "report"])
        self.assertIn("INT-002: PASS", result["transcript"])
        self.assertIn("2 jobs completed", result["transcript"])
        self.assertIn("Write the e2e probe note",
                      result["transcript"])
        self.assertIn("Record the probe result in the e2e log",
                      result["transcript"])

    def test_loop_twice_isolated_and_harness_untouched(self):
        first = e2e1.run_loop(write_log=False)
        second = e2e1.run_loop(write_log=False)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        # The loop runs on its own fake surface: the harness
        # fake holds no jobs from either run, and the harness
        # job namespace is restored.
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(out.strip(), "[]")
        self.assertEqual(jobs.NS, "muse-bus:tjob")

    def test_plan_fixture_validates_clean(self):
        plan, order, clamps = dispatch.validated_plan(e2e1.PLAN_JSON)
        self.assertEqual(order, ["probe", "report"])
        self.assertEqual(clamps, [])
        detail = dispatch.dry_run_plan(e2e1.PLAN_JSON)
        self.assertIn("jobs in posting order: probe -> report", detail)

    def test_no_approval_means_no_post(self):
        plan, _order, _clamps = dispatch.validated_plan(e2e1.PLAN_JSON)
        self.assertFalse(dispatch.request_approval(plan))


if __name__ == "__main__":
    unittest.main()
