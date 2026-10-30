"""DEM-012/DEM-013: the demo catch lands under 90 seconds, 3/3.

DEM-012's acceptance is a measured catch time across three
rehearsals, in demo configuration; DEM-013's is a demo
thresholds profile file, separate from production defaults.
These tests pin both into the suite by running the
measurement script (intel/drills/demo_catch_time.py) as a
subprocess — never imported in-process, because the script
applies the demo profile to the environment before importing
intel.thresholds, and importing it here would leak demo
thresholds into every other test in the process.

The three rehearsals differ only in tick-grid phase, so a
pass here means the catch holds for any loop alignment, not
one lucky phase. Production separation is pinned by reading
the files: the profile says stall 1 min, and
intel/thresholds.py still carries its production default
of 10 min — the demo profile overrides through the
environment only and never edits the production module.
"""

import re
import subprocess
import sys
import unittest

sys.path.insert(0, ".")


def run_measurement():
    return subprocess.run(
        [sys.executable, "intel/drills/demo_catch_time.py"],
        capture_output=True, text=True, timeout=120)


class DemoCatchTimeTest(unittest.TestCase):
    def test_script_exits_zero_and_passes(self):
        result = run_measurement()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("demo_catch_time measurement: PASS", result.stdout)

    def test_three_rehearsals_all_under_90s(self):
        result = run_measurement()
        catches = [int(m) for m in re.findall(
            r"catch (\d+)s after cue", result.stdout)]
        self.assertEqual(len(catches), 3, result.stdout)
        for catch in catches:
            self.assertLess(catch, 90, result.stdout)
        self.assertIn("presence-stall milo/7", result.stdout)

    def test_demo_profile_separate_from_production_defaults(self):
        with open("intel/metaos-demo.env") as handle:
            profile = handle.read()
        self.assertIn("WATCHDOG_STALL_MINUTES=1", profile)
        with open("intel/thresholds.py") as handle:
            production = handle.read()
        self.assertIn('STALL_MINUTES = _env_int("WATCHDOG_STALL_MINUTES", 10, 0)',
                      production)


if __name__ == "__main__":
    unittest.main()
