"""tests/test_intel_load.py -- INT-006 load check, pinned.

The scripted run in intel/load_check.py is the acceptance
artifact; these tests pin it inside the unit harness so a
regression in any stage (queue shape, room shape, snapshot
counts, brief budget, tick silence, adopted time budgets)
fails the suite, not just the standalone run. The check
runs against its own in-memory fake surface and restores
the harness job namespace, capability namespace, and
nicks, so it never touches the live bus and never
disturbs the other tests.

The check proves the read path at scale on the fake
backend: a snapshot reads 2,000 messages and 200 jobs, a
morning template brief stays inside its 220-word budget,
and a tick over the healthy load state yields zero
alerts, each operation inside its adopted 5 second
budget. The 2,000-message room is a beyond-cap stress
state, not a live-reachable room: every jobs
announcement runs bus_trim to the newest 500 messages,
so the room list is seeded directly after the queue.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from intel import brief  # noqa: E402
from intel import load_check  # noqa: E402
from mos import capabilities  # noqa: E402


class LoadCheckTest(RelayTestCase):
    def test_check_passes_with_exact_counts(self):
        result = load_check.run_check(write_files=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["seed queue", "seed room",
                                 "snapshot", "brief", "tick",
                                 "budgets"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertEqual(result["message_count"], 2000)
        self.assertEqual(result["job_count"], 200)
        self.assertEqual(result["claimed_count"], 10)
        self.assertEqual(result["alert_count"], 0)
        self.assertLessEqual(result["brief_words"],
                             brief.BRIEF_BUDGETS["morning"])
        self.assertTrue(result["brief_text"].startswith("TEMPLATE"))
        for name in ("snapshot", "brief", "tick", "total"):
            self.assertLess(result["timings"][name],
                            result["budgets"][name])
        self.assertIn("INT-006: PASS", result["transcript"])

    def test_check_twice_isolated_and_harness_untouched(self):
        old_ns = jobs.NS
        old_capns = capabilities.CAPNS
        first = load_check.run_check(write_files=False)
        second = load_check.run_check(write_files=False)
        self.assertTrue(first["ok"], first["transcript"])
        self.assertTrue(second["ok"], second["transcript"])
        self.assertEqual(first["message_count"],
                         second["message_count"])
        self.assertEqual(first["job_count"], second["job_count"])
        self.assertEqual(jobs.NS, old_ns)
        self.assertEqual(capabilities.CAPNS, old_capns)

    def test_table_renders_counts_and_budgets(self):
        result = load_check.run_check(write_files=False)
        self.assertTrue(result["ok"], result["transcript"])
        table = load_check.render_load_md(result)
        self.assertIn("| snapshot |", table)
        self.assertIn("| brief |", table)
        self.assertIn("| tick |", table)
        self.assertIn("2000", table)
        self.assertIn("200", table)
        self.assertIn("5.0", table)
        self.assertIn("PASS", table)


if __name__ == "__main__":
    unittest.main()
