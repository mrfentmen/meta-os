"""tests/test_os_workers_slice.py -- OS-035: the relay worker slice.

OS-035 ships relay-workers.slice with MemoryMax and CPUQuota
defaults, and records the same values in plan/META_OS.md. These
tests pin the file values and the spec record, not a live
enforcement run: live throttling needs a test image with cgroup
controllers, and this suite runs anywhere (see the drill
intel/drills/cgroup_limits.py for the live probe and its host
gate).

- os/services/relay-workers.slice exists and its [Slice]
  section carries exactly CPUQuota=100% and MemoryMax=1G.
- plan/META_OS.md records both values alongside the OS-035
  paragraph and the slice filename.
- The drill script exists and carries both the file checks and
  the honest host gate (it reports ENVIRONMENT-BLOCKED rather
  than faking an enforcement pass where controllers are absent).
- None of the new OS-035 files carries an em dash (the check.sh
  new-doc rule).

No bus post, no live Redis, no network, no systemd: pure file
reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLICE = os.path.join(ROOT, "os", "services", "relay-workers.slice")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
DRILL = os.path.join(ROOT, "intel", "drills", "cgroup_limits.py")
EVAL = os.path.join(ROOT, "intel", "evals", "cgroup_limits.md")

EXPECTED = {"CPUQuota": "100%", "MemoryMax": "1G"}


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


class WorkersSliceTest(unittest.TestCase):
    def test_slice_values(self):
        values = slice_values(read(SLICE))
        for key, want in EXPECTED.items():
            self.assertEqual(values.get(key), want,
                             f"{key} should be {want}")

    def test_spec_records_values(self):
        spec = read(SPEC)
        self.assertIn("relay-workers.slice", spec)
        for key, want in EXPECTED.items():
            self.assertIn(f"{key}={want}", spec)

    def test_drill_exists_with_host_gate(self):
        drill = read(DRILL)
        self.assertIn("ENVIRONMENT-BLOCKED", drill)
        self.assertIn("cgroup.controllers", drill)
        self.assertIn("CPUQuota", drill)
        self.assertIn("MemoryMax", drill)

    def test_eval_note_exists(self):
        self.assertTrue(os.path.exists(EVAL))

    def test_no_em_dash_in_new_files(self):
        for path in (SLICE, DRILL, EVAL):
            self.assertNotIn("\u2014", read(path), path)


if __name__ == "__main__":
    unittest.main()
