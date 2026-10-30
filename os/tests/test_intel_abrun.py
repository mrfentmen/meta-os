"""tests/test_intel_abrun.py -- OS-106: measured A/B run + attribution.

OS-106 records the demo's one comparison (bare launch
vs mind image) with times and acceptance outcomes per
job per version, and attributes each observed stall
from its journal evidence as an image defect or a
worker failure. These tests pin the comparison, the
attribution rules, the revision note, and the
zero-send halves on fixtures:

- The comparison records the same jobs under both
  versions with seconds and an outcome per row.
- Mind-v1 totals faster and passes more than bare.
- A stall naming a skill the image lacks is a
  missing-skill image defect with the skill in the
  evidence.
- A stall naming a skill the image carries is no
  defect.
- A thin-brief stall under a thin brief is a
  thin-brief defect; under a full brief it is not.
- A bad-instruction stall is a defect only when the
  image carries that instruction.
- A dead worker is a worker failure under both
  versions, never an image defect.
- A stall naming neither an image layer nor a
  worker cause is unattributed, never guessed.
- A job with no run under a version reads missing,
  never a pass.
- The comparison never mutates its inputs.
- Malformed inputs yield no result and no crash.
- The revision note proposes one change per defect,
  deduped, and applies nothing.
- The drill script exists and passes.
- The module imports no banned module and none of
  the new OS-106 files carries an em dash.

No bus post, no live agent, no network, no systemd:
the OS-105 harness has not landed, so the
comparison runs on fixtures in its shape.
"""

import ast
import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import abrun  # noqa: E402

BARE = {"name": "bare", "version": "bare",
        "skills": [], "instructions": [], "brief": "thin"}
MIND = {"name": "mind", "version": "mind-v1",
        "skills": ["git-review"],
        "instructions": ["verify acceptance before closing"],
        "brief": "full"}

RUNS = {
    "bare": {
        "job-a": {"job": "job-a", "seconds": 420, "outcome": "fail",
                  "stalls": [{"job": "job-a",
                              "journal": ["worker stalled: needs skill "
                                          "git-review"],
                              "missing_skill": "git-review"}]},
        "job-b": {"job": "job-b", "seconds": 60, "outcome": "pass",
                  "stalls": []},
    },
    "mind-v1": {
        "job-a": {"job": "job-a", "seconds": 120, "outcome": "pass",
                  "stalls": []},
        "job-b": {"job": "job-b", "seconds": 60, "outcome": "pass",
                  "stalls": []},
    },
}
IMAGES = {"bare": BARE, "mind-v1": MIND}
NEW_FILES = ["intel/abrun.py", "intel/drills/ab_run.py",
             "intel/evals/ab_run.md", "tests/test_intel_abrun.py"]


class ComparisonTest(unittest.TestCase):
    """The comparison table and totals."""

    def test_same_jobs_both_versions_with_times_and_outcomes(self):
        result = abrun.run_comparison(["job-a", "job-b"], RUNS, IMAGES)
        self.assertEqual(result["jobs"], ["job-a", "job-b"])
        self.assertEqual(result["versions"], ["bare", "mind-v1"])
        self.assertEqual(len(result["measurements"]), 4)
        for row in result["table"]:
            for version in ("bare", "mind-v1"):
                entry = row["versions"][version]
                self.assertIsNotNone(entry["seconds"])
                self.assertNotEqual(entry["outcome"], "missing")

    def test_mind_totals_faster_and_more_passes(self):
        result = abrun.run_comparison(["job-a", "job-b"], RUNS, IMAGES)
        self.assertEqual(result["totals"]["bare"]["seconds"], 480)
        self.assertEqual(result["totals"]["mind-v1"]["seconds"], 180)
        self.assertEqual(result["totals"]["bare"]["passed"], 1)
        self.assertEqual(result["totals"]["mind-v1"]["passed"], 2)


class AttributionTest(unittest.TestCase):
    """The attribution rules, one per kind."""

    def test_missing_skill_defect_with_evidence(self):
        stall = {"job": "job-a",
                 "journal": ["worker stalled: needs skill git-review"],
                 "missing_skill": "git-review"}
        kind, detail, evidence = abrun.attribute_stall(stall, BARE)
        self.assertEqual((kind, detail), ("image-defect", "missing-skill"))
        self.assertTrue(any("git-review" in line for line in evidence))

    def test_carried_skill_is_no_defect(self):
        stall = {"job": "job-a",
                 "journal": ["worker stalled: needs skill git-review"],
                 "missing_skill": "git-review"}
        kind, _, _ = abrun.attribute_stall(stall, MIND)
        self.assertNotEqual(kind, "image-defect")

    def test_thin_brief_defect_only_under_thin_brief(self):
        stall = {"job": "job-b",
                 "journal": ["worker stalled: no repo context"],
                 "thin_brief": True}
        kind, detail, _ = abrun.attribute_stall(stall, BARE)
        self.assertEqual((kind, detail), ("image-defect", "thin-brief"))
        kind, _, _ = abrun.attribute_stall(stall, MIND)
        self.assertNotEqual(kind, "image-defect")

    def test_bad_instruction_defect_only_when_carried(self):
        bad_image = {"name": "mind", "version": "mind-v0",
                     "skills": [], "instructions": ["skip checks"],
                     "brief": "full"}
        stall = {"job": "job-x", "journal": ["followed skip checks"],
                 "bad_instruction": "skip checks"}
        kind, detail, _ = abrun.attribute_stall(stall, bad_image)
        self.assertEqual((kind, detail), ("image-defect", "bad-instruction"))
        stranger = dict(stall)
        stranger["bad_instruction"] = "not in this image"
        kind, _, _ = abrun.attribute_stall(stranger, bad_image)
        self.assertNotEqual(kind, "image-defect")

    def test_dead_worker_is_worker_failure_not_defect(self):
        stall = {"job": "job-c", "journal": ["worker process died"],
                 "worker_cause": "worker died"}
        for image in (BARE, MIND):
            kind, detail, _ = abrun.attribute_stall(stall, image)
            self.assertEqual((kind, detail), ("worker-failure", "worker died"))

    def test_unattributed_when_evidence_names_neither(self):
        stall = {"job": "job-z", "journal": ["something went wrong"],
                 "reason": "unknown"}
        kind, detail, _ = abrun.attribute_stall(stall, BARE)
        self.assertEqual((kind, detail), ("unattributed", None))


class SafetyTest(unittest.TestCase):
    """Missing runs, immutability, malformed input, revision note."""

    def test_missing_run_reads_missing_never_pass(self):
        runs = {"bare": {}, "mind-v1": {}}
        result = abrun.run_comparison(["job-a"], runs, IMAGES)
        for version in ("bare", "mind-v1"):
            entry = result["table"][0]["versions"][version]
            self.assertEqual(entry["outcome"], "missing")
            self.assertIsNone(entry["seconds"])
        self.assertEqual(result["totals"]["bare"]["passed"], 0)

    def test_comparison_never_mutates_inputs(self):
        jobs = ["job-a", "job-b"]
        runs = copy.deepcopy(RUNS)
        images = copy.deepcopy(IMAGES)
        abrun.run_comparison(jobs, runs, images)
        self.assertEqual(runs, RUNS)
        self.assertEqual(images, IMAGES)

    def test_malformed_inputs_yield_no_result_no_crash(self):
        result = abrun.run_comparison(None, None, None)
        self.assertEqual(result["jobs"], [])
        self.assertEqual(result["defects"], [])
        self.assertEqual(abrun.attribute_stall("nope", BARE)[0],
                         "unattributed")
        self.assertEqual(abrun.revision_note("nope")["next_version_changes"],
                         [])

    def test_revision_note_proposes_deduped_applies_nothing(self):
        defects = [
            {"job": "job-a", "version": "bare", "kind": "missing-skill",
             "evidence": ["worker stalled: needs skill git-review"]},
            {"job": "job-a", "version": "bare", "kind": "missing-skill",
             "evidence": ["worker stalled: needs skill git-review"]},
            {"job": "job-b", "version": "bare", "kind": "thin-brief",
             "evidence": ["worker stalled: no repo context"]},
        ]
        note = abrun.revision_note(defects)
        self.assertEqual(len(note["next_version_changes"]), 2)
        self.assertTrue(any("git-review" in c
                            for c in note["next_version_changes"]))
        self.assertTrue(any("brief" in c
                            for c in note["next_version_changes"]))
        self.assertIn("nothing auto-applies", note["note"])


class DrillAndHygieneTest(unittest.TestCase):
    """The drill passes and the new files stay clean."""

    def test_drill_passes(self):
        proc = subprocess.run(
            [sys.executable, "intel/drills/ab_run.py"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("6/6 phases PASS", proc.stdout)

    def test_no_banned_imports_no_em_dash(self):
        banned = {"socket", "urllib", "requests", "redis", "subprocess"}
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("\u2014", text, path)
        for path in ("intel/abrun.py", "intel/drills/ab_run.py"):
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = {a.name.split(".")[0] for a in node.names}
                    self.assertFalse(names & banned, path)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], banned,
                                     path)


if __name__ == "__main__":
    unittest.main()
