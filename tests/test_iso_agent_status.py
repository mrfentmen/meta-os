"""Tests for iso/apps/agent-status/meta-agent-status.py.

Every case builds a real directory tree and runs the tool against it. Nothing
is mocked: the tool's job is to read files, so the fixtures are files.

The tree is the one an install actually produces: the relay keeps its state in
a per-user directory (`~/.local/state/oc2-agent`), not under /opt/metaos.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "iso" / "apps" / "agent-status" / "meta-agent-status.py"


def run(args, env=None):
    return subprocess.run(
        [sys.executable, str(TOOL)] + args,
        capture_output=True, text=True, timeout=30, env=env,
    )


class AgentStatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "jobs").mkdir(parents=True)
        (self.root / "runs").mkdir()
        registry = {"agents": [
            {"name": "rowan", "lane": "kernel", "draft": True},
            {"name": "aegis", "lane": "audit", "draft": False},
            {"name": "watch", "lane": "relay", "draft": False, "hosted": True},
        ]}
        (self.root / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
        (self.root / "watchman.heartbeat.json").write_text("{}", encoding="utf-8")
        (self.root / "jobs" / "a.job.json").write_text("{}", encoding="utf-8")
        (self.root / "jobs" / "b.job.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_registry_counts_agents_and_drafts(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("3 agents, 1 draft, 1 hosted", out.stdout)

    def test_job_queue_counts_json_files(self):
        out = run(["--root", str(self.root)])
        self.assertIn("2 pending", out.stdout)

    def test_json_mode_is_machine_readable(self):
        out = run(["--root", str(self.root), "--json"])
        payload = json.loads(out.stdout)
        self.assertTrue(payload["ok"])
        keys = {row["key"]: row for row in payload["rows"]}
        self.assertEqual(keys["registry"]["value"]["agents"], 3)
        self.assertEqual(keys["jobs"]["value"], 2)

    def test_the_board_separates_queued_from_done_and_refused(self):
        (self.root / "watchman.jsonl").write_text(
            json.dumps({"event": "bell", "id": "a", "run": "aegis-1"}) + "\n", encoding="utf-8")
        (self.root / "jobs" / "c.job.json").write_text("{}", encoding="utf-8")
        (self.root / "jobs" / "c.result.json").write_text(
            json.dumps({"id": "c", "code": 0, "signal": None}), encoding="utf-8")
        (self.root / "jobs" / "d.job.json").write_text("{}", encoding="utf-8")
        (self.root / "jobs" / "d.result.json").write_text(
            json.dumps({"id": "d", "refused": "draft-agent"}), encoding="utf-8")
        out = run(["--root", str(self.root), "--json"])
        keys = {row["key"]: row for row in json.loads(out.stdout)["rows"]}
        self.assertEqual(keys["board"]["value"]["queued"], 1)     # b
        self.assertEqual(keys["board"]["value"]["running"], 1)    # a, belled
        self.assertEqual(keys["board"]["value"]["done"], 1)       # c
        self.assertEqual(keys["board"]["value"]["refused"], 1)    # d

    def test_halted_agents_are_named_not_counted_as_failures(self):
        (self.root / "stop").mkdir()
        (self.root / "stop" / "watch.STOP").write_text("halt\n", encoding="utf-8")
        out = run(["--root", str(self.root), "--strict"])
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("1 halted: watch", out.stdout)
        payload = json.loads(run(["--root", str(self.root), "--json"]).stdout)
        keys = {row["key"]: row for row in payload["rows"]}
        self.assertEqual(keys["halts"]["value"]["halted"], ["watch"])

    def test_no_halt_directory_reports_absent_not_missing(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        payload = json.loads(run(["--root", str(self.root), "--json"]).stdout)
        keys = {row["key"]: row for row in payload["rows"]}
        self.assertEqual(keys["halts"]["status"], "absent")

    def test_notices_count_notes_and_alarms(self):
        (self.root / "notices.jsonl").write_text(
            json.dumps({"severity": "note", "title": "a"}) + "\n" +
            json.dumps({"severity": "alarm", "title": "b"}) + "\n" +
            json.dumps({"severity": "alarm", "title": "b", "suppressed": True}) + "\n",
            encoding="utf-8")
        out = run(["--root", str(self.root)])
        self.assertIn("2 alarm(s)", out.stdout)
        self.assertIn("1 repeated", out.stdout)

    def test_missing_required_row_fails_with_a_named_reason(self):
        (self.root / "registry.json").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("registry", out.stdout)
        self.assertIn("not ready", out.stdout)

    def test_absent_optional_row_does_not_fail_the_run(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0)
        self.assertIn("not installed", out.stdout)

    def test_stale_heartbeat_is_reported_stale(self):
        beat = self.root / "watchman.heartbeat.json"
        old = 1_600_000_000
        os.utime(beat, (old, old))
        out = run(["--root", str(self.root)])
        self.assertIn("stale", out.stdout)

    def test_tool_writes_nothing(self):
        before = {p: p.stat().st_mtime for p in self.root.rglob("*")}
        run(["--root", str(self.root), "--json"])
        after = {p: p.stat().st_mtime for p in self.root.rglob("*")}
        self.assertEqual(before, after)

    def test_strict_treats_a_stale_heartbeat_as_failure(self):
        beat = self.root / "watchman.heartbeat.json"
        old = 1_600_000_000
        os.utime(beat, (old, old))
        out = run(["--root", str(self.root), "--strict"])
        self.assertEqual(out.returncode, 1)
        self.assertIn("heartbeat", out.stdout)

    def test_bad_usage_exits_two(self):
        out = run(["--root", str(self.root), "--nope"])
        self.assertEqual(out.returncode, 2)

    def test_the_default_root_is_the_per_user_state_dir(self):
        env = {"HOME": str(self.root), "PATH": "/usr/bin:/bin",
               "XDG_STATE_HOME": str(self.root / "xdg")}
        out = run(["--json"], env=env)
        self.assertIn(str(self.root / "xdg" / "oc2-agent"), out.stdout)

    def test_a_dot_desktop_launcher_reports_instead_of_crashing(self):
        # No registry, no heartbeat: the window must still draw text, not die.
        (self.root / "registry.json").unlink()
        (self.root / "watchman.heartbeat.json").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("agent layer is not ready", out.stdout)


if __name__ == "__main__":
    unittest.main()
