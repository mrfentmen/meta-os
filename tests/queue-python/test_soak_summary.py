"""Tests for tools/soak_summary.py (CB2-447)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import soak_summary  # noqa: E402

LOG = """\
META OS KERNEL - alive (K1)
Uptime: 28s ticks 2875
STATUS tasks=7 ticks=3000
STATUS tasks=7 ticks=4258
META OS KERNEL - panic
"""


class SoakSummary(unittest.TestCase):
    def test_summary_has_duration_tick_range_and_panics(self):
        summary = soak_summary.summarise(LOG)
        self.assertEqual(summary["duration_seconds"], 28)
        self.assertEqual((summary["tick_first"], summary["tick_last"]), (2875, 4258))
        self.assertEqual(summary["tick_delta"], 1383)
        self.assertEqual(summary["panics"], 1)

    def test_render_is_exactly_three_lines(self):
        text = soak_summary.render(soak_summary.summarise(LOG))
        self.assertEqual(len(text.strip().splitlines()), 3, text)
        self.assertIn("duration: 28s", text)
        self.assertIn("panics: 1", text)

    def test_no_ticks_is_explicit(self):
        summary = soak_summary.summarise("hello\n")
        self.assertIsNone(summary["tick_first"])
        self.assertIn("ticks: no ticks", soak_summary.render(summary))


if __name__ == "__main__":
    unittest.main()
