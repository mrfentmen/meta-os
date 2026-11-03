"""Tests for iso/tools/boot_log_verdict.py. Logs are written to temp files."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "iso" / "tools" / "boot_log_verdict.py"

GOOD = """META OS 0.1 (K6)
META OS KERNEL - alive (K1)
mem summary: K4 up
HELLO FROM USERSPACE
user exit code 0
INT user page-fault addr 0x0 err 0x4: task killed
STATUS tasks=7 ticks=805 heap_free_kb=31
"""


def run(args):
    return subprocess.run([sys.executable, str(TOOL)] + args,
                          capture_output=True, text=True, timeout=30)


class VerdictTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_good_log_passes_every_row(self):
        out = run([self.write("good.txt", GOOD)])
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("verdict: PASS", out.stdout)

    def test_missing_ring3_names_the_row(self):
        log = GOOD.replace("HELLO FROM USERSPACE\n", "")
        out = run([self.write("no-ring3.txt", log)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL  ring3", out.stdout)
        self.assertIn("ring3", out.stdout.split("verdict: FAIL")[1])

    def test_panic_fails_even_when_every_other_marker_is_present(self):
        log = GOOD + "META OS KERNEL - panic\n"
        out = run([self.write("panic.txt", log)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL  panic", out.stdout)

    def test_loader_refusal_fails(self):
        log = GOOD + "user hello loader refused: address in use\n"
        out = run([self.write("refused.txt", log)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL  refused", out.stdout)

    def test_json_mode_reports_the_same_verdict(self):
        out = run([self.write("good.txt", GOOD), "--json"])
        payload = json.loads(out.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["rows"]), 9)

    def test_empty_log_fails_even_though_the_absence_rows_pass(self):
        # An empty log has no panic and no refusal, so those two rows pass by
        # absence. The seven present-marker rows fail, and that is the verdict.
        out = run([self.write("empty.txt", "")])
        self.assertEqual(out.returncode, 1)
        self.assertIn("2 of 9 passed", out.stdout)
        verdict = out.stdout.split("verdict: FAIL")[1]
        for key in ("banner", "alive", "memory", "ring3", "exit", "fault", "shell"):
            self.assertIn(key, verdict)

    def test_missing_file_is_a_usage_error(self):
        out = run([str(self.dir / "nope.txt")])
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
