"""Tests for the Science Lab tools first slice: the 6 researchers wired
through hosted.py + the registry.

Every case runs the real program against a copy of the real records, so
the duties are tested against the tree that ships rather than a fixture
written to match the program's opinion. No hypothesis record file ships
on disk, so the discipline duties audit cycle-level statements only;
the tests assert exactly that, and never a per-record field.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "os" / "worlds" / "science-lab"
HOSTED = LAB / "hosted.py"
RECORDS = LAB / "records"
REGISTRY = ROOT / "agents" / "registry.json"

NEW_SIX = [
    "mathematics-researcher",
    "chemistry-researcher",
    "biology-researcher",
    "physics-researcher",
    "hypothesis-generator",
    "statistician",
]

EXPECTED = {
    "mathematics-researcher": (["experiment-watch"], 3600000),
    "chemistry-researcher": (["experiment-watch"], 3600000),
    "biology-researcher": (["experiment-watch"], 3600000),
    "physics-researcher": (["experiment-watch"], 3600000),
    "hypothesis-generator": (["literature-watch", "experiment-watch"], 3600000),
    "statistician": (["experiment-watch", "verification-watch"], 3600000),
}


def run(args, env=None):
    return subprocess.run([sys.executable, str(HOSTED)] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env)


class Slice1Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.records = self.root / "records"
        shutil.copytree(RECORDS, self.records)
        self.env = {"METAOS_STATE": str(self.root / "state"),
                    "PATH": "/usr/bin:/bin", "HOME": str(self.root)}

    def tearDown(self):
        self.tmp.cleanup()

    def _receipt(self, name):
        out = run(["--agent", name, "--records", str(self.records)],
                  env=self.env)
        self.assertEqual(out.returncode, 0, name + ": " + out.stdout + out.stderr)
        receipts = list((self.root / "state" / "science-lab").glob(name + "-*.json"))
        self.assertEqual(len(receipts), 1, name)
        return json.loads(receipts[0].read_text(encoding="utf-8"))

    def test_all_six_new_duties_pass_check(self):
        for name in NEW_SIX:
            out = run(["--agent", name, "--check", "--records", str(self.records)],
                      env=self.env)
            self.assertEqual(out.returncode, 0, name + ": " + out.stdout + out.stderr)

    def test_all_thirteen_agents_are_listed(self):
        names = run(["--agent", "list"]).stdout.split()
        self.assertEqual(len(names), 13)
        for name in NEW_SIX:
            self.assertIn(name, names)

    def test_registry_shape_for_the_six(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        by_name = {a["name"]: a for a in data["agents"]}
        for name in NEW_SIX:
            entry = by_name[name]
            caps, wall = EXPECTED[name]
            self.assertTrue(entry["hosted"], name)
            self.assertNotIn("draft", entry, name)
            self.assertEqual(entry["command"],
                             ["python3", "repo:os/worlds/science-lab/hosted.py",
                              "--agent", name], name)
            self.assertEqual(entry["lane"], "Science Lab (research)", name)
            self.assertEqual(entry["owner"], "system: science-lab", name)
            self.assertEqual(entry["capabilities"], caps, name)
            self.assertEqual(entry["budget"], {"maxWallMs": wall}, name)

    def test_agent_docs_name_the_hosted_command(self):
        for name in NEW_SIX:
            text = (LAB / "agents" / (name + ".md")).read_text(encoding="utf-8")
            self.assertIn("HOSTED", text, name)
            self.assertIn("repo:os/worlds/science-lab/hosted.py", text, name)
            self.assertNotIn('["true"]', text, name)

    def test_chemistry_names_the_four_cycle_hypotheses(self):
        data = self._receipt("chemistry-researcher")
        finding = data["findings"][0]
        self.assertEqual(finding["matching_hypotheses"], 4)
        ids = [r["hypothesis"] for r in finding["hypotheses_with_design_signal"]]
        self.assertEqual(ids, ["RH1", "RH2", "RH3", "DRESS-H1"])
        self.assertTrue(all(r["has_disproof_statement"]
                            for r in finding["hypotheses_with_design_signal"]))

    def test_math_biology_physics_report_zero_without_failing(self):
        for name in ("mathematics-researcher", "biology-researcher",
                     "physics-researcher"):
            data = self._receipt(name)
            finding = data["findings"][0]
            self.assertEqual(finding["cycles_scanned"], 2, name)
            self.assertEqual(finding["matching_hypotheses"], 0, name)
            self.assertEqual(finding["hypotheses_with_design_signal"], [], name)

    def test_generator_reports_four_ids_all_with_a_statement(self):
        data = self._receipt("hypothesis-generator")
        finding = data["findings"][0]
        self.assertEqual(finding["total_ids"], 4)
        self.assertEqual(finding["with_disproof_statement"], 4)
        self.assertEqual(finding["without_disproof_statement"], 0)

    def test_statistician_audits_match_and_indeterminate(self):
        data = self._receipt("statistician")
        finding = data["findings"][0]
        by_cycle = {r["cycle"]: r for r in finding["cycles"]}
        self.assertEqual(by_cycle["CYCLE-EXAMPLE-001"]["audit"], "indeterminate")
        self.assertEqual(by_cycle["CYCLE-EXAMPLE-001"]["threshold_met"], True)
        self.assertEqual(by_cycle["DRESS-REHEARSAL-001"]["audit"], "match")
        self.assertEqual(by_cycle["DRESS-REHEARSAL-001"]["threshold"], 1.5)
        self.assertIn("EXP-DRESS-REHEARSAL-001",
                      [r["experiment_id"] for r in finding["reproduction_records"]])


if __name__ == "__main__":
    unittest.main()
