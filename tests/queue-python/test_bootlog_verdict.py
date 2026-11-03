"""Tests for tools/bootlog_verdict.py (CB2-431..432)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import bootlog_parse  # noqa: E402
import bootlog_verdict  # noqa: E402

GOOD = """\
META OS 0.1 (K6)
META OS KERNEL - alive (K1)
Programs: hello sleeper crasher (ring 3)
INT user page-fault addr 0x0 err 0x4: task killed
"""


def verdict(text):
    return bootlog_verdict.evaluate(bootlog_parse.parse_log(text))


class BootlogVerdict(unittest.TestCase):
    def test_all_checks_green(self):
        result = verdict(GOOD)
        self.assertTrue(result["all_green"], result)
        self.assertEqual(set(result["checks"]), {"alive", "three_programs", "fault_isolation", "panic_zero"})

    def test_removing_the_programs_line_flips_only_that_check(self):
        before = verdict(GOOD)
        after = verdict(GOOD.replace("Programs: hello sleeper crasher (ring 3)\n", ""))
        self.assertFalse(after["all_green"])
        self.assertEqual(bootlog_verdict.changed_checks(before, after), ["three_programs"])

    def test_removing_the_alive_line_flips_only_alive(self):
        before = verdict(GOOD)
        after = verdict(GOOD.replace("META OS KERNEL - alive (K1)\n", ""))
        self.assertEqual(bootlog_verdict.changed_checks(before, after), ["alive"])

    def test_a_panic_flips_only_panic_zero(self):
        before = verdict(GOOD)
        after = verdict(GOOD + "META OS KERNEL - panic\n")
        self.assertEqual(bootlog_verdict.changed_checks(before, after), ["panic_zero"])
        self.assertFalse(after["checks"]["panic_zero"]["passed"])


if __name__ == "__main__":
    unittest.main()
