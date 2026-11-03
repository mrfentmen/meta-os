"""Tests for agent-layer/meta-agent-health.py.

Every case runs the real probe as a child process against a real staged root
and a real loopback socket. Nothing is mocked; the only stand-in is a socket
this test opens or closes to decide whether the queue "answers".
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "agent-layer" / "meta-agent-health.py"
STAGE = REPO / "agent-layer" / "stage.sh"
PROBE_IN_IMAGE = Path("usr/local/lib/metaos/meta-agent-health.py")
UNITS = Path("usr/lib/systemd/user")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Health(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="meta-health-"))
        cls.root = cls.tmp / "root"
        (cls.root / "etc").mkdir(parents=True)
        (cls.root / "usr").mkdir()
        subprocess.run(["sh", str(STAGE), str(cls.root)], check=True,
                       capture_output=True, timeout=120)
        cls.listener = socket.socket()
        cls.listener.bind(("127.0.0.1", 0))
        cls.listener.listen(8)
        cls.port = cls.listener.getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        cls.listener.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="home-", dir=self.tmp))

    def run_probe(self, root=None, port=None, *extra, env=None, write=False):
        cmd = [sys.executable, str(TOOL),
               "--root", str(root or self.root),
               "--home", str(self.home),
               "--port", str(port if port is not None else self.port),
               "--json"]
        if not write:
            cmd.append("--no-write")
        cmd.extend(extra)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                              env={**os.environ, **(env or {})})

    def verdict(self, result):
        return json.loads(result.stdout)

    def rows(self, result):
        return {r["name"]: r for r in self.verdict(result)["rows"]}

    def test_clean_tree_and_live_queue_pass(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        rows = self.rows(result)
        self.assertEqual(rows["units"]["state"], "pass")
        self.assertEqual(rows["units"]["detail"], "7 units")
        self.assertEqual(rows["enabled"]["state"], "pass")
        self.assertEqual(rows["enabled"]["detail"], "6 links")
        self.assertEqual(rows["queue"]["state"], "pass")
        self.assertEqual(rows["watchman"]["state"], "absent")

    def test_dead_port_fails(self):
        result = self.run_probe(None, free_port())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.rows(result)["queue"]["state"], "fail")
        self.assertIn("refused", self.rows(result)["queue"]["detail"])

    def test_missing_unit_fails(self):
        root = self.clone_root("missing-unit")
        (root / UNITS / "oc2-queue.service").unlink()
        result = self.run_probe(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("oc2-queue.service", self.rows(result)["units"]["detail"])

    def test_torn_enable_link_fails(self):
        root = self.clone_root("torn-link")
        (root / "etc/systemd/user/timers.target.wants/oc2-health.timer").unlink()
        result = self.run_probe(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("oc2-health.timer", self.rows(result)["enabled"]["detail"])

    def test_stale_heartbeat_fails(self):
        beat = self.home / ".local/state/oc2-agent/watchman.heartbeat.json"
        beat.parent.mkdir(parents=True)
        beat.write_text(json.dumps({"ts": int((time.time() - 600) * 1000)}))
        result = self.run_probe(None, None, "--stale-after", "60")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.rows(result)["watchman"]["state"], "fail")

    def test_fresh_heartbeat_passes(self):
        beat = self.home / ".local/state/oc2-agent/watchman.heartbeat.json"
        beat.parent.mkdir(parents=True)
        beat.write_text(json.dumps({"ts": int(time.time() * 1000)}))
        result = self.run_probe()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.rows(result)["watchman"]["state"], "pass")

    def test_unreadable_heartbeat_fails(self):
        beat = self.home / ".local/state/oc2-agent/watchman.heartbeat.json"
        beat.parent.mkdir(parents=True)
        beat.write_text("{not json")
        result = self.run_probe()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.rows(result)["watchman"]["state"], "fail")

    def test_state_file_and_jsonl_are_written(self):
        result = self.run_probe(write=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.home / ".local/state/oc2-agent"
        verdict = json.loads((state / "health.json").read_text())
        self.assertTrue(verdict["ok"])
        lines = (state / "health.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["rows"], verdict["rows"])

    def test_no_write_leaves_no_state(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local/state/oc2-agent/health.json").exists())

    def test_restart_hook_runs_on_a_dead_queue(self):
        marker = self.tmp / "restart-marker"
        result = self.run_probe(None, free_port(),
                                env={"META_AGENT_RESTART": "printf ran > %s" % marker})
        self.assertEqual(self.rows(result)["restart"]["state"], "pass")
        self.assertEqual(marker.read_text(), "ran")

    def test_restart_hook_stays_quiet_when_queue_answers(self):
        marker = self.tmp / "no-restart-marker"
        result = self.run_probe(None, None,
                                env={"META_AGENT_RESTART": "printf ran > %s" % marker})
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("restart", self.rows(result))
        self.assertFalse(marker.exists())

    def test_stage_installs_the_probe_and_timer(self):
        self.assertTrue((self.root / PROBE_IN_IMAGE).is_file())
        self.assertTrue((self.root / UNITS / "oc2-health.service").is_file())
        self.assertTrue((self.root / UNITS / "oc2-health.timer").is_file())
        link = self.root / "etc/systemd/user/timers.target.wants/oc2-health.timer"
        self.assertTrue(link.is_symlink() or link.is_file())
        check = subprocess.run(["sh", str(STAGE), str(self.root), "--check"],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("PASS", check.stdout)
        self.assertIn("health cadence", check.stdout)

    def clone_root(self, name):
        root = self.tmp / name
        shutil.copytree(self.root, root, symlinks=True)
        return root

class WatchmanRestart(unittest.TestCase):
    """A stale beat is a failed row; the restart only runs when asked."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="home-"))
        self.beat = self.home / ".local/state/oc2-agent/watchman.heartbeat.json"
        self.beat.parent.mkdir(parents=True)

    def run_probe(self, *extra, env=None):
        cmd = [sys.executable, str(TOOL), "--home", str(self.home),
               "--port", str(free_port()), "--json", "--no-write"]
        cmd.extend(extra)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                              env={**os.environ, **(env or {})})

    def test_a_stale_beat_restarts_the_watchman_when_a_command_is_set(self):
        self.beat.write_text(json.dumps({"ts": int((time.time() - 600) * 1000)}))
        marker = self.home / "restarted"
        result = self.run_probe("--stale-after", "60",
                                env={"META_AGENT_WATCHMAN_RESTART": "printf wm > %s" % marker})
        rows = {r["name"]: r for r in json.loads(result.stdout)["rows"]}
        self.assertEqual(rows["watchman"]["state"], "fail")
        self.assertEqual(rows["restart-watchman"]["state"], "pass")
        self.assertEqual(marker.read_text(), "wm")

    def test_a_healthy_beat_does_not_restart_anything(self):
        self.beat.write_text(json.dumps({"ts": int(time.time() * 1000)}))
        marker = self.home / "not-restarted"
        result = self.run_probe(env={"META_AGENT_WATCHMAN_RESTART": "printf wm > %s" % marker})
        rows = {r["name"]: r for r in json.loads(result.stdout)["rows"]}
        self.assertEqual(rows["watchman"]["state"], "pass")
        self.assertNotIn("restart-watchman", rows)
        self.assertFalse(marker.exists())


class LoginHook(unittest.TestCase):
    """The autostart hook must start the timer, or the cadence never runs."""

    def test_hook_starts_all_four_units(self):
        tmp = Path(tempfile.mkdtemp(prefix="hook-"))
        try:
            bindir = tmp / "bin"
            bindir.mkdir()
            calls = tmp / "calls"
            fake = bindir / "systemctl"
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "' + str(calls) + '"\n')
            fake.chmod(0o755)
            home = tmp / "home"
            (home / ".config").mkdir(parents=True)
            env = {**os.environ, "PATH": "%s:%s" % (bindir, os.environ["PATH"]),
                   "HOME": str(home)}
            env.pop("SPARK_API_KEY", None)
            result = subprocess.run(["bash", str(REPO / "agent-layer/meta-agent-login.sh")],
                                    capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            started = calls.read_text().splitlines()
            for unit in ("oc2-queue.service", "oc2-trio.service",
                         "oc2-patrol.timer", "oc2-health.timer"):
                self.assertIn("--user start " + unit, started)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
