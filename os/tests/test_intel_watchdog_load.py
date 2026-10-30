"""tests/test_intel_watchdog_load.py -- INT-023 watchdog under load, pinned.

The scripted run in intel/watchdog_load_check.py is the
acceptance artifact; these tests pin it inside the unit
harness so a regression in any stage (queue shape, tick-1
alert counts, tick-2 dedupe, tick-3 silence, adopted time
budgets) fails the suite, not just the standalone run.
The check runs against its own in-memory fake surface
and restores the harness job namespace, capability
namespace, and nicks, so it never touches the live bus
and never disturbs the other tests.

The check proves the watchdog at scale on the fake
backend: 50 stalled jobs in a 200-job queue yield
exactly 50 alerts (25 presence-stall, 25
progress-stall) and no more despite 2,000 room
messages; a second tick inside the 30-minute dedupe
cooldown leaves the store at 50 records with
last_seen advanced and created_at unchanged; and a
third tick after both workers recover yields zero
alerts. The 2,000-message room is a beyond-cap stress
state, not a live-reachable room: every jobs
announcement runs bus_trim to the newest 500 messages,
so the room list is seeded directly after the queue.
Tick silence on recovery is not store resolution: the
50 tick-1 records stay standing, and the check asserts
exactly that.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from intel import watchdog_load_check  # noqa: E402
from mos import capabilities  # noqa: E402


class WatchdogLoadCheckTest(RelayTestCase):
    def test_check_passes_with_exact_counts(self):
        result = watchdog_load_check.run_check(write_files=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["seed queue", "seed room",
                                 "tick 1 stalled load",
                                 "tick 2 dedupe", "tick 3 cleared",
                                 "budgets"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertEqual(result["message_count"], 2000)
        self.assertEqual(result["job_count"], 200)
        self.assertEqual(result["claimed_count"], 50)
        ticks = result["ticks"]
        self.assertEqual(ticks[0]["alerts"], 50)
        self.assertEqual(ticks[0]["stored"], 50)
        self.assertEqual(ticks[1]["alerts"], 50)
        self.assertEqual(ticks[1]["stored"], 50)
        self.assertEqual(ticks[2]["alerts"], 0)
        self.assertEqual(ticks[2]["stored"], 50)
        for tick in ticks:
            self.assertLess(tick["seconds"], 5.0)
        self.assertLess(result["timings"]["total"], 15.0)
        self.assertIn("INT-023: PASS", result["transcript"])

    def test_check_twice_isolated_and_harness_untouched(self):
        old_ns = jobs.NS
        old_capns = capabilities.CAPNS
        first = watchdog_load_check.run_check(write_files=False)
        second = watchdog_load_check.run_check(write_files=False)
        self.assertTrue(first["ok"], first["transcript"])
        self.assertTrue(second["ok"], second["transcript"])
        self.assertEqual(first["message_count"],
                         second["message_count"])
        self.assertEqual(first["job_count"], second["job_count"])
        self.assertEqual(first["ticks"][0]["alerts"],
                         second["ticks"][0]["alerts"])
        self.assertEqual(jobs.NS, old_ns)
        self.assertEqual(capabilities.CAPNS, old_capns)

    def test_table_renders_counts_and_budgets(self):
        result = watchdog_load_check.run_check(write_files=False)
        self.assertTrue(result["ok"], result["transcript"])
        table = watchdog_load_check.render_watchdog_load_md(result)
        self.assertIn("INT-023", table)
        self.assertIn("presence-stall", table)
        self.assertIn("progress-stall", table)
        self.assertIn("50", table)
        self.assertIn("5.0", table)
        self.assertIn("PASS", table)


if __name__ == "__main__":
    unittest.main()
