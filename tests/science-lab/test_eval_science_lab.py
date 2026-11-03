"""Tests for the Science Lab eval harness (eval/science-lab/).

Runs the real runner against the real tree. No invented expectations:
the runner itself asserts the hosted duties over a copy of the shipped
records, so these tests assert the harness is complete and green, plus
the scenario file's own shape (unique ids, known agents, known kinds).
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "eval" / "science-lab"
RUNNER = EVAL / "run.py"
SCENARIOS = EVAL / "scenarios.json"

KNOWN_KINDS = {"check", "duty", "registry", "refusal"}


class TestEvalScienceLab(unittest.TestCase):
    def test_scenarios_wellformed(self):
        doc = json.loads(SCENARIOS.read_text(encoding="utf-8"))
        ids = [s["id"] for s in doc["scenarios"]]
        self.assertEqual(len(ids), len(set(ids)), "scenario ids must be unique")
        self.assertEqual(len(ids), 28, "28 scenarios: 13 check + 13 duty + 1 registry + 1 refusal")
        for sc in doc["scenarios"]:
            self.assertIn(sc["kind"], KNOWN_KINDS)
            if sc["kind"] in ("check", "duty"):
                self.assertIn(sc["agent"], doc["agents"])
            if sc["kind"] == "duty":
                if "expected_check" in sc:
                    self.assertEqual(sc["expected_check"], doc["agents"][sc["agent"]])
                else:
                    # research-director: census rows, no check key; the
                    # expected row shape and cycle ids are asserted instead.
                    self.assertEqual(sc["agent"], "research-director")
                    self.assertTrue(sc["expected_keys"])
                    self.assertTrue(sc["expected_cycles"])
        self.assertEqual(len(doc["agents"]), 13)

    def test_runner_all_pass(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER)], capture_output=True, text=True,
            timeout=300, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-2000:])
        report = json.loads(proc.stdout)
        self.assertEqual(report["scenarios"], 28)
        self.assertEqual(report["passed"], 28)
        self.assertEqual(report["failed"], 0)
        failed = [r["id"] for r in report["results"] if not r["pass"]]
        self.assertEqual(failed, [])


if __name__ == "__main__":
    unittest.main()
