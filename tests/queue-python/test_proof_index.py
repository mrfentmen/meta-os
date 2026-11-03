"""Tests for tools/proof_index.py (CB2-433..435)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import proof_index  # noqa: E402

K1 = "META OS 0.1 (K6)\nMETA OS KERNEL - alive (K1)\n"
K2 = "META OS - milestone K2\nMETA OS KERNEL - alive (K1)\nMETA OS KERNEL - panic\n"


class ProofIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "b-second.txt").write_text(K2, encoding="utf-8")
        (self.dir / "a-first.txt").write_text(K1, encoding="utf-8")
        (self.dir / "notes.md").write_text("not a log\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_logs_are_listed_and_notes_skipped(self):
        index = proof_index.scan_dir(self.dir)
        self.assertEqual([r["file"] for r in index["rows"]], ["a-first.txt", "b-second.txt"])
        self.assertEqual(index["skipped"], 1)

    def test_panic_count_and_milestone_are_per_file(self):
        rows = {r["file"]: r for r in proof_index.scan_dir(self.dir)["rows"]}
        self.assertEqual(rows["a-first.txt"]["panics"], 0)
        self.assertEqual(rows["b-second.txt"]["panics"], 1)
        self.assertIn("milestone K2", rows["b-second.txt"]["milestone"])

    def test_two_logs_with_the_same_milestone_both_appear_sorted(self):
        (self.dir / "c-third.log").write_text(K1, encoding="utf-8")
        index = proof_index.scan_dir(self.dir)
        self.assertEqual([r["file"] for r in index["rows"]], ["a-first.txt", "b-second.txt", "c-third.log"])

    def test_render_is_a_table_with_the_skip_count(self):
        text = proof_index.render(proof_index.scan_dir(self.dir))
        self.assertIn("| File | Date | Milestone | Panics |", text)
        self.assertIn("`a-first.txt`", text)
        self.assertIn("1 non-log file(s) skipped", text)


if __name__ == "__main__":
    unittest.main()
