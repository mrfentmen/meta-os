"""tests/test_intel_e2e2.py -- INT-003 end-to-end test 2, pinned.

The scripted loop in intel/e2e2.py is the acceptance artifact;
these tests pin it inside the unit harness so a regression in
any stage (post, worker-a claim path, watchdog alert on a real
snapshot, sweep requeue, auto-resolve, worker-b finish) fails
the suite, not just the standalone run. The loop runs against
its own in-memory fake surface and restores the harness job
namespace, capability namespace, and nicks, so it never
touches the live bus and never disturbs the other tests.

The loop proves the story on the real command path, where the
WDG-020 kill drill proves it on fixture dicts: the alert here
fires on a real ingest snapshot, which is why the watchdog
fix (last_progress_at accepted as an activity timestamp) is
pinned directly as well. The fake clock is advanced, never
the wall clock waited on; the sweep is the real jobs.py
sweep command, and the announcement line is asserted held,
never posted.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from intel import e2e2  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from mos import capabilities  # noqa: E402


class E2E2Test(RelayTestCase):
    def test_loop_passes_all_stages(self):
        result = e2e2.run_loop(write_log=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["post", "worker-a",
                                 "death and alert", "sweep requeue",
                                 "alert auto-resolves", "worker-b",
                                 "final quiet"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertEqual(result["job_id"], "1")
        alert = result["alert"]
        self.assertEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["nick"], "worker-a")
        self.assertEqual(alert["job"], "1")
        self.assertEqual(alert["last_progress_age_seconds"],
                         thresholds.STALL_MINUTES * 60 + 61)
        self.assertIn("INT-003: PASS", result["transcript"])
        self.assertIn("REQUEUED 1", result["transcript"])
        self.assertIn("worker-b", result["transcript"])

    def test_loop_twice_isolated_and_harness_untouched(self):
        capns_before = capabilities.CAPNS
        first = e2e2.run_loop(write_log=False)
        second = e2e2.run_loop(write_log=False)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        # The loop runs on its own fake surface: the harness
        # fake holds no jobs from either run, and the harness
        # job namespace and capability namespace are restored.
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(out.strip(), "[]")
        self.assertEqual(jobs.NS, "muse-bus:tjob")
        self.assertEqual(capabilities.CAPNS, capns_before)

    def test_watchdog_reads_last_progress_at(self):
        # The INT-003 fix, pinned without the loop: a real
        # snapshot row carries last_progress_at, not
        # last_progress, and the stall detector must fire on
        # it. A row with no timestamp at all still yields
        # nothing: the detector never invents an age.
        snapshot = {
            "messages": [], "presence": [],
            "caps": {"worker-a": {"caps": "python"}},
            "jobs": [{"id": "9", "title": "Stall note",
                      "status": "claimed", "claim": "worker-a",
                      "last_progress_at": 1000,
                      "lease_until": 1000 + 1800}],
        }
        got = watchdog.tick(snapshot, now=1000 + 661)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "presence-stall")
        self.assertEqual(got[0]["last_progress_age_seconds"], 661)
        snapshot["jobs"][0].pop("last_progress_at")
        self.assertEqual(watchdog.tick(snapshot, now=1000 + 661), [])


if __name__ == "__main__":
    unittest.main()
