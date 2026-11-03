"""Tests for tools/gate_log_check.py (CB2-445..446)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import gate_log_check  # noqa: E402

CHECKS = ["toolchain", "userspace", "kernel", "boot", "asserts", "readkey", "fetch"]


def transcript(failing):
    lines = [f"{'FAIL' if name == failing else 'PASS'}: {name}" for name in CHECKS]
    lines.append("GATE GREEN 7/7" if failing is None else "GATE NOT GREEN")
    return "\n".join(lines) + "\n"


class GateLogCheck(unittest.TestCase):
    def test_all_seven_pass_is_green(self):
        result = gate_log_check.check_log(transcript(None))
        self.assertTrue(result["green"])
        self.assertEqual(len(result["passed"]), 7)
        self.assertEqual(result["failed"], [])

    def test_six_of_seven_names_the_failing_check(self):
        result = gate_log_check.check_log(transcript("readkey"))
        self.assertFalse(result["green"])
        self.assertEqual(result["failed"], ["readkey"])
        self.assertEqual(len(result["passed"]), 6)

    def test_missing_checks_are_counted(self):
        result = gate_log_check.check_log("PASS: toolchain\nGATE GREEN 7/7\n")
        self.assertEqual(result["missing"], 6)
        self.assertFalse(result["green"])

    def test_render_reports_counts(self):
        text = gate_log_check.render(gate_log_check.check_log(transcript("fetch")))
        self.assertIn("FAIL fetch", text)
        self.assertIn("6/7 passed", text)


if __name__ == "__main__":
    unittest.main()
