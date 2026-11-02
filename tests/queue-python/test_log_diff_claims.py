"""Tests for tools/log_diff_claims.py (CB2-448)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import log_diff_claims  # noqa: E402

BEFORE = """\
META OS 0.1 (K6)
META OS KERNEL - alive (K1)
Programs: hello sleeper crasher (ring 3)
INT user page-fault addr 0x0 err 0x4: task killed
"""


class LogDiffClaims(unittest.TestCase):
    def test_identical_logs_have_no_changes(self):
        self.assertEqual(log_diff_claims.diff_texts(BEFORE, BEFORE), [])
        self.assertIn("no claim checks changed", log_diff_claims.render([]))

    def test_new_panic_changes_only_panic_zero(self):
        names = log_diff_claims.diff_texts(BEFORE, BEFORE + "META OS KERNEL - panic\n")
        self.assertEqual(names, ["panic_zero"])

    def test_dropped_programs_line_changes_only_that_check(self):
        after = BEFORE.replace("Programs: hello sleeper crasher (ring 3)\n", "")
        self.assertEqual(log_diff_claims.diff_texts(BEFORE, after), ["three_programs"])

    def test_render_names_each_change(self):
        text = log_diff_claims.render(["alive", "panic_zero"])
        self.assertEqual(text.strip().splitlines(), ["changed: alive", "changed: panic_zero"])


if __name__ == "__main__":
    unittest.main()
