"""Tests for tools/bootlog_parse.py (CB2-426..430)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import bootlog_parse  # noqa: E402

GOOD = """\
META OS 0.1 (K6)
META OS KERNEL - alive (K1)
readkey: polling syscall 5
readkey got 30
readkey got 158
readkey got 28
readkey: enter seen, done got=3
Programs: hello sleeper crasher (ring 3)
INT user page-fault addr 0x0 err 0x4: task killed
STATUS tasks=7 ticks=805 heap_free_kb=31
tasks 8 ticks 2177
tasks 8 ticks 4258
"""


class BootlogParse(unittest.TestCase):
    def test_banner_alive_and_pass_verdict(self):
        record = bootlog_parse.parse_log(GOOD)
        self.assertEqual(record["banner"], "META OS 0.1 (K6)")
        self.assertTrue(record["alive"])
        self.assertEqual(record["panic_count"], 0)
        self.assertEqual(record["verdict"], "pass")

    def test_one_panic_yields_count_one_and_failing(self):
        record = bootlog_parse.parse_log(GOOD + "META OS KERNEL - panic\n")
        self.assertEqual(record["panic_count"], 1)
        self.assertEqual(record["verdict"], "failing")

    def test_missing_alive_line_names_the_verdict(self):
        record = bootlog_parse.parse_log("META OS 0.1 (K6)\nhello\n")
        self.assertFalse(record["alive"])
        self.assertEqual(record["verdict"], "missing-alive")

    def test_readkey_lines_are_structured(self):
        record = bootlog_parse.parse_log(GOOD)
        self.assertEqual([r["key"] for r in record["readkeys"]], [30, 158, 28])
        self.assertTrue(record["enter_seen"])
        self.assertEqual(record["enter_got"], 3)

    def test_status_ticks_are_extracted_in_order(self):
        record = bootlog_parse.parse_log(GOOD)
        self.assertEqual(record["ticks"], [805, 2177, 4258])

    def test_programs_and_fault_isolation(self):
        record = bootlog_parse.parse_log(GOOD)
        self.assertEqual(record["programs"], ["hello", "sleeper", "crasher", "(ring", "3)"])
        self.assertTrue(record["fault_isolation"])

    def test_empty_log_is_not_a_pass(self):
        record = bootlog_parse.parse_log("")
        self.assertEqual(record["panic_count"], 0)
        self.assertEqual(record["verdict"], "missing-alive")
        self.assertEqual(record["ticks"], [])


if __name__ == "__main__":
    unittest.main()
