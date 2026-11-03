"""Tests for iso/tools/apply.sh. Every case installs into a real temp root."""

import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "iso" / "tools" / "apply.sh"


def run(args):
    return subprocess.run(
        ["bash", str(SCRIPT)] + args, capture_output=True, text=True, timeout=60
    )


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_a_root(self):
        self.assertEqual(run([]).returncode, 2)

    def test_refuses_the_filesystem_root(self):
        out = run(["--root", "/"])
        self.assertEqual(out.returncode, 2)
        self.assertIn("refusing", out.stderr)

    def test_dry_run_writes_nothing(self):
        out = run(["--root", str(self.root), "--dry-run"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(list(self.root.rglob("*")), [])
        self.assertIn("planned", out.stdout)

    def test_installs_the_whole_lane(self):
        out = run(["--root", str(self.root), "--user", "boss"])
        self.assertEqual(out.returncode, 0, out.stderr)
        expected = [
            "usr/share/plymouth/themes/metaos/metaos.plymouth",
            "usr/share/plymouth/themes/metaos/metaos.script",
            "etc/calamares/settings.conf",
            "etc/calamares/branding/meta/branding.desc",
            "etc/calamares/modules/users.conf",
            "usr/share/applications/meta-agent-status.desktop",
            "usr/share/applications/meta-terminal.desktop",
            "home/boss/.config/plank/dock1/launchers/meta-agent-status.dockitem",
            "usr/local/bin/meta-agent-status",
            "usr/share/metaos/start/meta-start.html",
            "usr/share/metaos/start/tokens.css",
            "etc/chromium/policies/managed/metaos.json",
        ]
        for rel in expected:
            self.assertTrue((self.root / rel).is_file(), rel)

    def test_binary_is_executable(self):
        run(["--root", str(self.root)])
        mode = (self.root / "usr/local/bin/meta-agent-status").stat().st_mode
        self.assertTrue(mode & 0o111)

    def test_second_run_is_idempotent(self):
        run(["--root", str(self.root)])
        first = sorted(p for p in self.root.rglob("*") if p.is_file())
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stderr)
        second = sorted(p for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
