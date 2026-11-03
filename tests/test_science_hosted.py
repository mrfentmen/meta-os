"""Tests for os/worlds/science-lab/hosted.py.

Every case runs the real program against a copy of the real records, so the
duties are tested against the tree that ships rather than a fixture written
to match the program's opinion.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "os" / "worlds" / "science-lab"
HOSTED = LAB / "hosted.py"
RECORDS = LAB / "records"


def run(args, env=None):
    return subprocess.run([sys.executable, str(HOSTED)] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env)


class HostedDutyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.records = self.root / "records"
        shutil.copytree(RECORDS, self.records)
        self.env = {"METAOS_STATE": str(self.root / "state"), "PATH": "/usr/bin:/bin"}
        self.env["HOME"] = str(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_listed_agent_runs_and_writes_one_receipt(self):
        names = run(["--agent", "list"]).stdout.split()
        self.assertIn("research-archivist", names)
        for name in names:
            out = run(["--agent", name, "--records", str(self.records)], env=self.env)
            self.assertEqual(out.returncode, 0, name + ": " + out.stdout + out.stderr)
        receipts = list((self.root / "state" / "science-lab").glob("*.json"))
        self.assertEqual(len(receipts), len(names))

    def test_an_agent_with_no_duty_is_refused(self):
        # All 13 science-lab agents are hosted since the tools first slice;
        # refusal is now proven with a name that has no duty at all.
        out = run(["--agent", "no-such-agent", "--records", str(self.records)], env=self.env)
        self.assertEqual(out.returncode, 2)
        self.assertIn("stays a draft", out.stderr)

    def test_the_archivist_fails_on_a_broken_chain(self):
        ledger = self.records / "ledger.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        lines[1] = lines[1].replace('"entry_hash": "', '"entry_hash": "0', 1)
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = run(["--agent", "research-archivist", "--records", str(self.records)], env=self.env)
        self.assertEqual(out.returncode, 1)
        self.assertIn("hash-chain", out.stdout)

    def test_the_critic_names_a_dropped_claim(self):
        out = run(["--agent", "scientific-critic", "--records", str(self.records)], env=self.env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        receipts = list((self.root / "state" / "science-lab").glob("scientific-critic-*.json"))
        data = json.loads(receipts[0].read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["findings"][0]["count"], 1)

    def test_a_missing_ledger_is_an_error_not_an_empty_answer(self):
        (self.records / "ledger.jsonl").unlink()
        out = run(["--agent", "research-archivist", "--records", str(self.records)], env=self.env)
        self.assertNotEqual(out.returncode, 0)

    def test_check_mode_writes_no_receipt(self):
        out = run(["--agent", "research-director", "--check", "--records", str(self.records)],
                  env=self.env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertFalse((self.root / "state" / "science-lab").exists())


if __name__ == "__main__":
    unittest.main()
