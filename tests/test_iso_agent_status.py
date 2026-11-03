"""Tests for iso/apps/agent-status/meta-agent-status.py.

Every case builds a real directory tree and runs the tool against it. Nothing
is mocked: the tool's job is to read files, so the fixtures are files.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "iso" / "apps" / "agent-status" / "meta-agent-status.py"


def run(args):
    return subprocess.run(
        [sys.executable, str(TOOL)] + args,
        capture_output=True, text=True, timeout=30,
    )


class AgentStatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "agents" / "jobs").mkdir(parents=True)
        (self.root / "handsfree").mkdir()
        registry = {"agents": [
            {"name": "rowan", "lane": "kernel", "draft": True},
            {"name": "milo", "lane": "audit", "draft": False},
            {"name": "pax", "lane": "release", "draft": False, "hosted": True},
        ]}
        (self.root / "agents" / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
        (self.root / "agents" / "watchman.heartbeat.json").write_text("{}", encoding="utf-8")
        (self.root / "agents" / "jobs" / "a.json").write_text("{}", encoding="utf-8")
        (self.root / "agents" / "jobs" / "b.json").write_text("{}", encoding="utf-8")
        (self.root / "agents" / "gym-ledger.jsonl").write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_registry_counts_agents_and_drafts(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("3 agents, 1 draft, 1 hosted", out.stdout)

    def test_job_queue_counts_json_files(self):
        out = run(["--root", str(self.root)])
        self.assertIn("2 pending", out.stdout)

    def test_gym_ledger_counts_non_blank_lines(self):
        out = run(["--root", str(self.root)])
        self.assertIn("2 lines", out.stdout)

    def test_json_mode_is_machine_readable(self):
        out = run(["--root", str(self.root), "--json"])
        payload = json.loads(out.stdout)
        self.assertTrue(payload["ok"])
        keys = {row["key"]: row for row in payload["rows"]}
        self.assertEqual(keys["registry"]["value"]["agents"], 3)
        self.assertEqual(keys["jobs"]["value"], 2)

    def test_missing_required_row_fails_with_a_named_reason(self):
        (self.root / "agents" / "registry.json").unlink()
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 1)
        self.assertIn("registry", out.stdout)
        self.assertIn("not ready", out.stdout)

    def test_absent_optional_row_does_not_fail_the_run(self):
        out = run(["--root", str(self.root)])
        self.assertEqual(out.returncode, 0)
        self.assertIn("not installed", out.stdout)

    def test_stale_heartbeat_is_reported_stale(self):
        beat = self.root / "agents" / "watchman.heartbeat.json"
        old = 1_600_000_000
        os.utime(beat, (old, old))
        out = run(["--root", str(self.root)])
        self.assertIn("stale", out.stdout)

    def test_tool_writes_nothing(self):
        before = {p: p.stat().st_mtime for p in self.root.rglob("*")}
        run(["--root", str(self.root), "--json"])
        after = {p: p.stat().st_mtime for p in self.root.rglob("*")}
        self.assertEqual(before, after)

    def test_bad_usage_exits_two(self):
        out = run(["--root", str(self.root), "--nope"])
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
