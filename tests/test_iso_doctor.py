"""Tests for iso/base/meta-doctor.py.

Every case installs the lane into a real temp root with apply.sh, so the
doctor is tested against a tree the installer actually produced, not against
a fixture written to match the doctor's opinion.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ISO = Path(__file__).resolve().parents[1] / "iso"
APPLY = ISO / "tools" / "apply.sh"
DOCTOR = ISO / "base" / "meta-doctor.py"


def run(args):
    return subprocess.run([sys.executable, str(DOCTOR)] + args,
                          capture_output=True, text=True, timeout=60)


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["bash", str(APPLY), "--root", str(self.root)],
                       capture_output=True, text=True, timeout=120, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_clean_install_passes(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("FAIL", out.stdout)

    def test_a_missing_theme_file_is_named(self):
        (self.root / "usr/share/metaos/theme/gtk.css").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("desktop theme", out.stdout)
        self.assertIn("gtk.css", out.stdout)

    def test_a_missing_dock_item_is_named(self):
        (self.root / "usr/share/metaos/dock/meta-files.dockitem").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("dock items", out.stdout)
        self.assertIn("4 of 5", out.stdout)

    def test_json_reports_a_summary_and_rows(self):
        data = json.loads(run(["--root", str(self.root), "--json"]).stdout)
        self.assertEqual(data["summary"]["fail"], 0)
        self.assertGreaterEqual(data["summary"]["pass"], 10)
        self.assertTrue(any(row["check"] == "dock items" for row in data["rows"]))

    def test_first_login_is_reported_per_home(self):
        home = self.root / "home"
        home.mkdir()
        out = run(["--root", str(self.root), "--home", str(home)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("first login applied", out.stdout)
        marker = home / ".config" / "metaos" / "first-login.done"
        marker.parent.mkdir(parents=True)
        marker.write_text("", encoding="utf-8")
        self.assertEqual(run(["--root", str(self.root), "--home", str(home)]).returncode, 0)

    def test_a_root_that_does_not_exist_is_refused(self):
        self.assertEqual(run(["--root", str(self.root / "nope")]).returncode, 2)

    def test_an_unknown_argument_is_refused(self):
        self.assertEqual(run(["--nope"]).returncode, 2)


    def test_an_autostart_entry_with_no_binary_is_named(self):
        (self.root / "usr/local/bin/meta-first-login").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("autostart binaries", out.stdout)
        self.assertIn("meta-first-login", out.stdout)


if __name__ == "__main__":
    unittest.main()
