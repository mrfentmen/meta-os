"""Tests for the agent layer inside an ISO root.

`agent-layer/install.sh` needs a checkout in $HOME and a running systemd.
An image has neither, so `stage.sh` writes the runtime, the units, the skel
env and the login hook into a root tree and enables the units with symlinks.
These tests run that stager into a temp root and read what it produced.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "agent-layer" / "stage.sh"
HOOK = ROOT / "agent-layer" / "meta-agent-login.sh"
PROVISION = ROOT / "os-build" / "iso" / "provision.sh"
DOCTOR = ROOT / "iso" / "base" / "meta-doctor.py"
UNITS = ("oc2-queue.service", "oc2-trio.service",
         "oc2-patrol.service", "oc2-patrol.timer")


def sh(*args, cwd=None):
    return subprocess.run(["sh", *map(str, args)], capture_output=True,
                          text=True, cwd=cwd)


class Staged(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "etc").mkdir()
        (self.root / "usr").mkdir()
        result = sh(STAGE, self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def tearDown(self):
        self.tmp.cleanup()

    def test_units_and_runtime_land(self):
        for unit in UNITS:
            self.assertTrue((self.root / "usr/lib/systemd/user" / unit).is_file(), unit)
        payload = self.root / "usr/share/metaos/agent"
        for rel in ("server/queue/queue_service.py", "server/queue/patrol.py",
                    "server/queue/trio_agent.py", "js/products.js", "js/schema.js"):
            self.assertTrue((payload / rel).is_file(), rel)

    def test_units_are_enabled_by_symlink_not_a_daemon(self):
        wants = self.root / "etc/systemd/user"
        for unit in UNITS[:3]:
            link = wants / "default.target.wants" / unit
            self.assertTrue(os.path.islink(link), link)
            self.assertEqual(os.readlink(link), "/usr/lib/systemd/user/" + unit)
        timer = wants / "timers.target.wants" / "oc2-patrol.timer"
        self.assertTrue(os.path.islink(timer))
        self.assertEqual(os.readlink(timer), "/usr/lib/systemd/user/oc2-patrol.timer")

    def test_env_pins_the_installed_payload_and_carries_no_secret(self):
        body = (self.root / "etc/skel/.config/oc2-agent/env").read_text()
        self.assertIn("OC2_CHECKOUT=/usr/share/metaos/agent", body)
        self.assertNotIn("/home/relay", body)
        for mark in ("SPARK_API_KEY", "sk-", "BEGIN PRIVATE"):
            self.assertNotIn(mark, body)

    def test_login_hook_and_autostart_entry_agree(self):
        hook = self.root / "usr/local/bin/meta-agent-login"
        self.assertTrue(hook.is_file())
        self.assertTrue(os.access(hook, os.X_OK))
        entry = (self.root / "etc/xdg/autostart/meta-agent-login.desktop").read_text()
        self.assertIn("Exec=/usr/local/bin/meta-agent-login", entry)
        self.assertIn("TryExec=/usr/local/bin/meta-agent-login", entry)

    def test_check_mode_passes_on_a_good_root(self):
        result = sh(STAGE, self.root, "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_check_mode_names_the_unit_that_is_missing(self):
        (self.root / "usr/lib/systemd/user/oc2-trio.service").unlink()
        result = sh(STAGE, self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("oc2-trio.service", result.stderr)

    def test_check_mode_catches_a_broken_enable_link(self):
        (self.root / "etc/systemd/user/default.target.wants/oc2-queue.service").unlink()
        result = sh(STAGE, self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not enabled", result.stderr)

    def test_runtime_compiles(self):
        payload = self.root / "usr/share/metaos/agent/server/queue"
        files = sorted(str(p) for p in payload.glob("*.py"))
        self.assertGreater(len(files), 10)
        result = subprocess.run([sys.executable, "-m", "py_compile", *files],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_login_hook_parses(self):
        result = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_doctor_reports_the_agent_layer(self):
        result = subprocess.run([sys.executable, str(DOCTOR), "--root", str(self.root)],
                                capture_output=True, text=True)
        names = ("agent units", "agent enabled", "agent runtime",
                 "agent env", "agent login hook")
        rows = [line for line in result.stdout.splitlines()
                if line.startswith(("PASS", "FAIL"))
                and any(name in line.lower() for name in names)]
        self.assertTrue(rows, result.stdout + result.stderr)
        for line in rows:
            self.assertTrue(line.startswith("PASS"), line)

    def test_provisioning_calls_the_stager(self):
        body = PROVISION.read_text()
        self.assertIn("agent-layer", body)
        self.assertIn("stage.sh", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
