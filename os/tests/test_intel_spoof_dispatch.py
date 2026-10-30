"""INT-010: spoofed dispatch (BAD signature), drill pinned.

The drill script itself (intel/spoof_dispatch_drill.py) is the
acceptance artifact; these tests pin it in the suite so a later
change that breaks the refusal chain breaks the suite too.
The store is the suite's in-memory fake, the keyring holds a
drill-only dummy secret, and the BAD verdict comes from the
shipped verifier recomputing the HMAC after a real spec
tamper, never a hand-written verdict. No network, no live
Redis, no bus posts, no Spark calls.
"""

import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

from intel import spoof_dispatch_drill as drill  # noqa: E402
from intel import watchdog  # noqa: E402


class SpoofDispatchDrillTest(unittest.TestCase):

    def test_drill_passes_all_stages(self):
        result = drill.run_drill(write_log=False)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["stages"]), 6)
        for name, passed, detail in result["stages"]:
            self.assertTrue(passed, f"stage {name} failed: {detail}")

    def test_detector_notes_refusal_without_a_secret(self):
        snapshot = {
            "messages": ["worker: REJECTED:9 BAD "
                         "signed_by=overseer rejected_by=worker"],
            "jobs": [{"id": "9", "status": "open"}],
        }
        got = watchdog.detect_rejected_dispatch(snapshot, drill.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "rejected-dispatch")
        self.assertEqual(got[0]["severity"], "critical")
        self.assertEqual(got[0]["dedupe_key"],
                         "rejected-dispatch:9:BAD")

    def test_detector_ignores_unsigned_jobs(self):
        snapshot = {
            "messages": ["worker: CLAIM:9 by worker"],
            "jobs": [{"id": "9", "status": "claimed",
                      "claim": "worker"}],
        }
        got = watchdog.detect_rejected_dispatch(snapshot, drill.NOW)
        self.assertEqual(got, [])


if __name__ == "__main__":
    unittest.main()
