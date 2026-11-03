"""Tests for tools/screendump_note.py (CB2-449)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import bootlog_parse  # noqa: E402
import screendump_note  # noqa: E402

LOG = "META OS 0.1 (K6)\nMETA OS KERNEL - alive (K1)\nticks 100\nticks 250\n"


class ScreendumpNote(unittest.TestCase):
    def test_note_names_the_file_and_values(self):
        text = screendump_note.note("WAVE3-w3_fetch.jpg", bootlog_parse.parse_log(LOG))
        self.assertIn("WAVE3-w3_fetch.jpg", text)
        self.assertIn("- Banner: META OS 0.1 (K6)", text)
        self.assertIn("- Alive: yes", text)
        self.assertIn("- Panics: 0", text)
        self.assertIn("- Ticks: 100..250", text)
        self.assertIn("- Verdict: pass", text)

    def test_missing_values_use_the_dash_form(self):
        text = screendump_note.note("empty.jpg", bootlog_parse.parse_log(""))
        self.assertIn("- Banner: —", text)
        self.assertIn("- Ticks: —", text)
        self.assertIn("- Alive: no", text)

    def test_a_panic_is_reported(self):
        text = screendump_note.note("p.jpg", bootlog_parse.parse_log(LOG + "META OS KERNEL - panic\n"))
        self.assertIn("- Panics: 1", text)
        self.assertIn("- Verdict: failing", text)


if __name__ == "__main__":
    unittest.main()
