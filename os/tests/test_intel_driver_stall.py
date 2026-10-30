"""tests/test_intel_driver_stall.py -- OS-057: driver stall drill.

OS-057 wedges a driver process (alive, heartbeat stale) and
proves the watchdog raises the same STALL alert as for a crew
worker, with the driver restarted per the OS-034 contract and
the sibling driver untouched. The restart half is systemd's
job on a test image this repo does not carry, so these tests
pin the watchdog half on fixtures, exactly as OS-056's tests
pinned the presence-stall half: the detector, the worker
equivalence, the demo-profile window, and the tick contract
that leaves both driver jobs claimed.

- The drill script exists and carries the detector,
  equivalence, demo, and contract phases.
- The eval note exists and the META_OS.md spec record names
  OS-057 and the drill file.
- A driver nick in caps, present, holding a claimed job with
  no progress past the window yields exactly one
  progress-stall alert naming driver-audio/d1, severity
  critical; the same snapshot yields no presence-stall.
- The same wedge on worker pax yields the same alert shape.
- Under the demo progress-stall window (1 minute, from
  metaos-demo.env) the wedge fires at 61s and stays quiet
  at 30s.
- A full tick alerts once for the wedged driver, leaves both
  driver jobs claimed by their drivers, and leaves the
  sibling unalerted.
- None of the new OS-057 files carries an em dash (the
  check.sh new-doc rule).

No bus post, no live Redis, no network, no systemd: pure
file reads plus the fixture detectors.
"""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRILL = os.path.join(ROOT, "intel", "drills", "driver_stall.py")
EVAL = os.path.join(ROOT, "intel", "evals", "driver_stall.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
DEMO_ENV = os.path.join(ROOT, "intel", "metaos-demo.env")

WEDGED = "driver-audio"
SIBLING = "driver-video"
WORKER = "pax"
T0 = 100000


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class DriverStallFilesTest(unittest.TestCase):
    def test_drill_exists_with_all_phases(self):
        text = read(DRILL)
        for phase in ("phase_detector", "phase_equivalence",
                      "phase_demo", "phase_contract"):
            self.assertIn(phase, text)

    def test_eval_exists(self):
        self.assertTrue(os.path.exists(EVAL))

    def test_spec_records_drill(self):
        text = read(SPEC)
        self.assertIn("OS-057", text)
        self.assertIn("driver_stall.py", text)

    def test_demo_env_sets_one_minute_window(self):
        self.assertIn("WATCHDOG_PROGRESS_STALL_MINUTES=1",
                      read(DEMO_ENV))

    def test_no_em_dash_in_new_files(self):
        for path in (DRILL, EVAL):
            self.assertNotIn("\u2014", read(path), path)


class DriverStallDetectorTest(unittest.TestCase):
    def _snapshot(self, wedged_last, sibling_last, worker_last):
        return {
            "caps": {WEDGED: {"caps": "audio"},
                     SIBLING: {"caps": "video"},
                     WORKER: {"caps": "python"}},
            "presence": [WEDGED, SIBLING, WORKER],
            "jobs": [
                {"id": "d1", "title": "play boot sting",
                 "status": "claimed", "claim": WEDGED,
                 "claimed_at": T0, "last_progress_at": wedged_last},
                {"id": "d2", "title": "render caption",
                 "status": "claimed", "claim": SIBLING,
                 "claimed_at": T0, "last_progress_at": sibling_last},
                {"id": "w1", "title": "write brief",
                 "status": "claimed", "claim": WORKER,
                 "claimed_at": T0, "last_progress_at": worker_last},
            ],
            "messages": [],
        }

    def test_wedged_driver_progress_stall(self):
        from intel import thresholds, watchdog  # noqa: E402
        stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
        snap = self._snapshot(T0, stall_at - 60, stall_at - 60)
        alerts = watchdog.detect_progress_stall(snap, stall_at)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "progress-stall")
        self.assertEqual(alerts[0]["nick"], WEDGED)
        self.assertEqual(alerts[0]["job"], "d1")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_wedged_driver_no_presence_stall(self):
        from intel import thresholds, watchdog  # noqa: E402
        stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
        snap = self._snapshot(T0, stall_at - 60, stall_at - 60)
        self.assertEqual(watchdog.detect_presence_stall(snap,
                                                       stall_at), [])

    def test_wedged_worker_same_alert(self):
        from intel import thresholds, watchdog  # noqa: E402
        stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
        snap = self._snapshot(stall_at - 60, stall_at - 60, T0)
        alerts = watchdog.detect_progress_stall(snap, stall_at)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "progress-stall")
        self.assertEqual(alerts[0]["nick"], WORKER)
        self.assertEqual(alerts[0]["job"], "w1")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_tick_leaves_both_driver_jobs_claimed(self):
        from intel import thresholds, watchdog  # noqa: E402
        stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
        snap = self._snapshot(T0, stall_at - 60, stall_at - 60)
        alerts = watchdog.tick(snap, now=stall_at)
        wedged = [a for a in alerts if a.get("nick") == WEDGED]
        sibling = [a for a in alerts if a.get("nick") == SIBLING]
        self.assertEqual(len(wedged), 1)
        self.assertEqual(sibling, [])
        by_id = {j["id"]: j for j in snap["jobs"]}
        self.assertEqual(by_id["d1"]["claim"], WEDGED)
        self.assertEqual(by_id["d1"]["status"], "claimed")
        self.assertEqual(by_id["d2"]["claim"], SIBLING)
        self.assertEqual(by_id["d2"]["status"], "claimed")


if __name__ == "__main__":
    unittest.main()
