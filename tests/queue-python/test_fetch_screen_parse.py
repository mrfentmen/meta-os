"""Tests for tools/fetch_screen_parse.py (CB2-441..442)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import fetch_screen_parse  # noqa: E402

FULL = """\
Tasks: 8
Mem: frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K
"""


class FetchScreenParse(unittest.TestCase):
    def test_full_section_extracts_every_field(self):
        record = fetch_screen_parse.parse_section(FULL)
        self.assertEqual(record["tasks"], 8)
        self.assertEqual((record["frames_free"], record["frames_total"]), (126430, 126509))
        self.assertEqual((record["heap_free_k"], record["heap_total_k"]), (255, 512))
        self.assertEqual(record["missing"], [])

    def test_missing_memory_lines_are_named_not_zeroed(self):
        record = fetch_screen_parse.parse_section("Tasks: 8\n")
        self.assertEqual(record["tasks"], 8)
        self.assertIsNone(record["frames_free"])
        self.assertEqual(record["missing"], ["frames", "heap"])

    def test_missing_tasks_is_named(self):
        record = fetch_screen_parse.parse_section(FULL.replace("Tasks: 8\n", ""))
        self.assertIsNone(record["tasks"])
        self.assertEqual(record["missing"], ["tasks"])


if __name__ == "__main__":
    unittest.main()
