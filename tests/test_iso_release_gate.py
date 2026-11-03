"""Tests for iso/tools/release_gate.py.

The fixture is written in the shape the real checklist uses: milestone
headings, boxes that wrap onto indented lines, and a mix of open and closed.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "iso" / "tools" / "release_gate.py"
REAL = ROOT / "os-build" / "METAOS_1.0_RELEASE_CHECKLIST.md"

FIXTURE = """# A checklist

## Cut one

- [x] closed thing
- [ ] open thing that
      wraps onto a second line
## Cut two

- [ ] second open
"""


def run(*args):
    return subprocess.run([sys.executable, str(TOOL)] + list(args),
                          capture_output=True, text=True, timeout=60)


class ReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "checklist.md"
        self.path.write_text(FIXTURE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_counts_open_and_closed(self):
        out = run("--file", str(self.path))
        self.assertEqual(out.returncode, 1)
        self.assertIn("3 box(es): 1 closed, 2 open", out.stdout)
        self.assertIn("GATE: RED", out.stdout)

    def test_a_wrapped_box_is_one_box(self):
        out = run("--file", str(self.path))
        self.assertIn("open thing that wraps onto a second line", out.stdout)
        self.assertIn("3 box(es)", out.stdout)

    def test_open_boxes_carry_their_line_and_milestone(self):
        out = run("--file", str(self.path))
        self.assertIn("OPEN  line 6", out.stdout)
        self.assertIn("[Cut one]", out.stdout)
        self.assertIn("[Cut two]", out.stdout)

    def test_report_mode_exits_zero(self):
        out = run("--file", str(self.path), "--report")
        self.assertEqual(out.returncode, 0)
        self.assertIn("2 box(es) open", out.stdout)

    def test_json_matches_the_text(self):
        data = json.loads(run("--file", str(self.path), "--json").stdout)
        self.assertEqual(data["counts"], {"total": 3, "closed": 1, "open": 2})
        self.assertEqual(data["open"][0]["section"], "Cut one")
        self.assertEqual(data["open"][0]["line"], 6)

    def test_closed_boxes_are_hidden_unless_asked(self):
        self.assertNotIn("closed thing", run("--file", str(self.path)).stdout)
        self.assertIn("closed thing", run("--file", str(self.path), "--all").stdout)

    def test_the_real_checklist_parses(self):
        data = json.loads(run("--json").stdout)
        self.assertGreaterEqual(data["counts"]["total"], 20)
        self.assertTrue(any("H+2" in s["section"] for s in data["sections"]))
        self.assertTrue(REAL.is_file())

    def test_a_missing_checklist_is_refused(self):
        self.assertEqual(run("--file", str(self.path.parent / "nope.md")).returncode, 2)


if __name__ == "__main__":
    unittest.main()
