"""Tests for tools/ps_rows_parse.py (CB2-443..444)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import ps_rows_parse  # noqa: E402

ROWS = """\
ps id 1 state Exited ticks_used 12 prio 3
ps id 7 state Running ticks_used 88 prio 1
ps id 9 state Wedged ticks_used 4 prio 5
"""


class PsRowsParse(unittest.TestCase):
    def test_rows_are_parsed_in_order(self):
        result = ps_rows_parse.parse_rows(ROWS)
        self.assertEqual([r["pid"] for r in result["rows"]], [1, 7, 9])
        self.assertEqual(result["rows"][1]["state"], "Running")
        self.assertEqual(result["rows"][1]["ticks_used"], 88)

    def test_unknown_state_is_kept_and_flagged(self):
        result = ps_rows_parse.parse_rows(ROWS)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual([r["pid"] for r in result["flagged"]], [9])
        self.assertEqual(result["flagged"][0]["state"], "Wedged")

    def test_non_ps_lines_are_skipped(self):
        result = ps_rows_parse.parse_rows("hello\nps table:\n")
        self.assertEqual(result["rows"], [])

    def test_render_counts_rows_and_flags(self):
        text = ps_rows_parse.render(ps_rows_parse.parse_rows(ROWS))
        self.assertIn("3 row(s), 1 flagged", text)
        self.assertIn("| 7 | Running | 88 | 1 |", text)


if __name__ == "__main__":
    unittest.main()
