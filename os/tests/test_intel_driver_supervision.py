"""tests/test_intel_driver_supervision.py -- OS-056: driver supervision.

OS-056 ships relay-drivers.slice with CPUQuota and MemoryMax
defaults shared with the OS-035 worker slice, records the slice in
plan/META_OS.md, and proves through the drill that driver
heartbeats feed the existing stall detectors unchanged. These
tests pin the file values and the spec record, not a live
enforcement run: a driver process in the slice on a test image
needs driver programs that are not landed yet and an image this
repo does not carry (see the drill intel/drills/driver_supervision.py
for the honest gate).

- os/services/relay-drivers.slice exists and its [Slice]
  section carries exactly CPUQuota=100% and MemoryMax=1G.
- plan/META_OS.md records the slice filename and both values
  alongside the OS-056 paragraph.
- The drill script exists and carries the file, verify,
  detector, and contract phases.
- A driver nick gone from presence with a claimed job past the
  stall window yields exactly one presence-stall alert naming
  the driver and job, severity critical; a full tick leaves the
  job claimed (OS-034: the watchdog records, systemd restarts).
- None of the new OS-056 files carries an em dash (the check.sh
  new-doc rule).

No bus post, no live Redis, no network, no systemd: pure file
reads plus the fixture detectors.
"""

import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLICE = os.path.join(ROOT, "os", "services", "relay-drivers.slice")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
DRILL = os.path.join(ROOT, "intel", "drills", "driver_supervision.py")
EVAL = os.path.join(ROOT, "intel", "evals", "driver_supervision.md")

EXPECTED = {"CPUQuota": "100%", "MemoryMax": "1G"}
DRIVER = "driver-audio"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def slice_values(text):
    values = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "Slice" and "=" in line:
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    return values


class DriverSliceTest(unittest.TestCase):
    def test_slice_values(self):
        values = slice_values(read(SLICE))
        for key, want in EXPECTED.items():
            self.assertEqual(values.get(key), want,
                             f"{key} should be {want}")

    def test_spec_records_slice_and_values(self):
        text = read(SPEC)
        self.assertIn("relay-drivers.slice", text)
        self.assertIn("OS-056", text)
        for want in EXPECTED.values():
            self.assertIn(want, text)

    def test_drill_exists_with_all_phases(self):
        text = read(DRILL)
        for phase in ("phase_file", "phase_verify", "phase_detector",
                      "phase_contract"):
            self.assertIn(phase, text)

    def test_eval_exists(self):
        self.assertTrue(os.path.exists(EVAL))

    def test_no_em_dash_in_new_files(self):
        for path in (SLICE, DRILL, EVAL):
            self.assertNotIn("\u2014", read(path), path)


class DriverDetectorTest(unittest.TestCase):
    def _snapshot(self, present):
        from intel import thresholds  # noqa: E402
        t0 = 100000
        return t0, {
            "caps": {DRIVER: {"caps": "audio"}},
            "presence": list(present),
            "jobs": [{"id": "d1", "title": "play boot sting",
                      "status": "claimed", "claim": DRIVER,
                      "claimed_at": t0, "last_progress_at": t0}],
            "messages": [],
        }

    def test_driver_presence_stall(self):
        from intel import thresholds, watchdog  # noqa: E402
        t0, snap = self._snapshot([])
        stall_at = t0 + thresholds.STALL_MINUTES * 60 + 1
        alerts = watchdog.detect_presence_stall(snap, stall_at)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "presence-stall")
        self.assertEqual(alerts[0]["nick"], DRIVER)
        self.assertEqual(alerts[0]["job"], "d1")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_tick_leaves_driver_job_claimed(self):
        from intel import thresholds, watchdog  # noqa: E402
        t0, snap = self._snapshot([])
        stall_at = t0 + thresholds.STALL_MINUTES * 60 + 1
        alerts = watchdog.tick(snap, now=stall_at)
        driver_alerts = [a for a in alerts if a.get("nick") == DRIVER]
        self.assertEqual(len(driver_alerts), 1)
        self.assertEqual(snap["jobs"][0]["status"], "claimed")
        self.assertEqual(snap["jobs"][0]["claim"], DRIVER)


if __name__ == "__main__":
    unittest.main()
