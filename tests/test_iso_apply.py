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
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stderr)
        expected = [
            "usr/share/plymouth/themes/metaos/metaos.plymouth",
            "usr/share/plymouth/themes/metaos/metaos.script",
            "etc/calamares/settings.conf",
            "etc/calamares/branding/meta/branding.desc",
            "etc/calamares/modules/users.conf",
            "usr/share/applications/meta-agent-status.desktop",
            "usr/share/applications/meta-terminal.desktop",
            "usr/share/metaos/dock/meta-agent-status.dockitem",
            "usr/local/bin/meta-first-login",
            "etc/xdg/autostart/meta-first-login.desktop",
            "usr/share/metaos/theme/meta-wallpaper.png",
            "etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml",
            "etc/lightdm/lightdm-gtk-greeter.conf",
            "usr/share/metaos/theme/greeter-wallpaper.png",
            "usr/share/themes/MetaOS/index.theme",
            "usr/share/themes/MetaOS/gtk-3.0/gtk.css",
            "boot/grub/themes/metaos/theme.txt",
            "boot/grub/themes/metaos/meta-grub.png",
            "etc/default/grub.d/metaos-theme.cfg",
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


    def test_manifest_lists_what_was_installed(self):
        run(["--root", str(self.root)])
        manifest = self.root / "var/lib/metaos/apply-manifest.txt"
        self.assertTrue(manifest.is_file())
        listed = manifest.read_text(encoding="utf-8").splitlines()
        self.assertIn("/usr/share/applications/meta-files.desktop", listed)
        self.assertGreaterEqual(len(listed), 30)

    def test_revert_removes_exactly_what_it_wrote(self):
        run(["--root", str(self.root)])
        out = run(["--root", str(self.root), "--revert"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse((self.root / "usr/share/metaos/theme/meta-wallpaper.png").exists())
        self.assertFalse((self.root / "var/lib/metaos/apply-manifest.txt").exists())
        self.assertEqual([p for p in self.root.rglob("*") if p.is_file()], [])

    def test_revert_without_a_manifest_is_quiet(self):
        out = run(["--root", str(self.root), "--revert"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("nothing to revert", out.stdout)

    def test_verify_runs_the_doctor(self):
        out = run(["--root", str(self.root), "--verify"])
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("13 passed, 0 failed", out.stdout)


if __name__ == "__main__":
    unittest.main()
