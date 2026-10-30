#!/usr/bin/env python3
"""tests/test_intel_e2e_watchdog_surfaces.py -- INT-020, pinned.

The scripted loop in intel/e2e_watchdog_surfaces.py is the
acceptance artifact; these tests pin it inside the unit harness
so a regression in any surface (store record id, brief Watch
item id, dashboard panel row id/severity) fails the suite, not
just the standalone run. The loop is pure-fixture plus the node
dashboard harness: it never touches the live bus, never posts,
and writes no log when write_log=False, so it runs twice with
the same result and leaves no state behind.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import e2e_watchdog_surfaces as e2e  # noqa: E402


class E2EWatchdogSurfacesTest(unittest.TestCase):
    def test_loop_passes_all_stages(self):
        result = e2e.run_loop(write_log=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [name for name, _ok, _d in result["stages"]]
        self.assertEqual(names, ["tick", "store", "brief",
                                 "dashboard", "quiet"])
        self.assertTrue(all(ok for _n, ok, _d in result["stages"]))
        self.assertEqual(result["alert_id"], "presence-stall:pax:7")
        self.assertEqual(result["record"]["severity"], "critical")
        self.assertEqual(result["record"]["room"], "build-int")
        self.assertIn("INT-020: PASS", result["transcript"])

    def test_loop_twice_isolated(self):
        first = e2e.run_loop(write_log=False)
        second = e2e.run_loop(write_log=False)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(first["alert_id"], second["alert_id"])
        self.assertEqual(first["transcript"], second["transcript"])
