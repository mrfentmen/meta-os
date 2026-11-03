"""Tests for iso/base/meta-first-login.sh.

The script is the half of the install that cannot run in the installer: the
account does not exist until Calamares creates it. Every case here uses a real
temp home and a stub xfconf-query that records its arguments, so the backdrop
call is checked for what it says, not that it was made at all.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "iso" / "base" / "meta-first-login.sh"
FROZEN = ("files", "terminal", "settings", "browser", "agent-status")


class FirstLoginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.share = self.root / "share"
        (self.share / "dock").mkdir(parents=True)
        (self.share / "theme").mkdir(parents=True)
        for name in FROZEN:
            (self.share / "dock" / ("meta-%s.dockitem" % name)).write_text(
                "[PlankDockItemPreferences]\n", encoding="utf-8")
        (self.share / "theme" / "meta-wallpaper.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.share / "theme" / "gtk.css").write_text(
            "@define-color meta_blue #1877F2;\n", encoding="utf-8")

        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "xfconf.log"
        stub = self.bin / "xfconf-query"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'printf "%s\\n" "$*" >> "$XFCONF_LOG"\n'
            'for a in "$@"; do\n'
            '  if [ "$a" = "-l" ]; then\n'
            "    printf '/backdrop/screen0/monitorHDMI-1/workspace0/last-image\\n'\n"
            "    printf '/backdrop/screen0/monitorDP-2/workspace0/last-image\\n'\n"
            "  fi\n"
            "done\n",
            encoding="utf-8")
        stub.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args, share=None):
        env = dict(os.environ)
        env.update({
            "HOME": str(self.home),
            "METAOS_SHARE": str(share or self.share),
            "XFCONF_LOG": str(self.log),
            "PATH": "%s:%s" % (self.bin, env.get("PATH", "")),
        })
        return subprocess.run(["bash", str(SCRIPT)] + list(args),
                              capture_output=True, text=True, timeout=60, env=env)

    def home_files(self):
        return sorted(p for p in self.home.rglob("*") if p.is_file())

    def test_dry_run_writes_nothing(self):
        out = self.run_script("--dry-run")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.home_files(), [])
        self.assertIn("would install", out.stdout)

    def test_installs_the_frozen_dock_and_the_marker(self):
        out = self.run_script()
        self.assertEqual(out.returncode, 0, out.stderr)
        dock = self.home / ".config" / "plank" / "dock1" / "launchers"
        self.assertEqual(sorted(p.name for p in dock.glob("*.dockitem")),
                         sorted("meta-%s.dockitem" % n for n in FROZEN))
        self.assertTrue((self.home / ".config" / "gtk-3.0" / "gtk.css").is_file())
        self.assertTrue((self.home / ".config" / "metaos" / "first-login.done").is_file())

    def test_second_run_is_a_no_op(self):
        self.run_script()
        out = self.run_script()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("already applied", out.stdout)

    def test_backdrop_is_set_for_every_monitor(self):
        out = self.run_script()
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = [line for line in self.log.read_text(encoding="utf-8").splitlines()
                 if "last-image" in line and " -s " in line]
        self.assertEqual(len(lines), 2, self.log.read_text(encoding="utf-8"))
        for line in lines:
            self.assertIn(str(self.share / "theme" / "meta-wallpaper.png"), line)

    def test_a_users_own_stylesheet_is_kept(self):
        css = self.home / ".config" / "gtk-3.0" / "gtk.css"
        css.parent.mkdir(parents=True)
        css.write_text("/* mine */\n", encoding="utf-8")
        out = self.run_script()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(css.read_text(encoding="utf-8"), "/* mine */\n")
        self.assertIn("keeping the existing", out.stdout)

    def test_missing_install_tree_is_an_error(self):
        out = self.run_script(share=self.root / "absent")
        self.assertEqual(out.returncode, 1)
        self.assertIn("run iso/tools/apply.sh first", out.stderr)

    def test_unknown_argument_is_refused(self):
        self.assertEqual(self.run_script("--nope").returncode, 2)


if __name__ == "__main__":
    unittest.main()
