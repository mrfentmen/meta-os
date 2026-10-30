#!/usr/bin/env python3
"""tests/test_intel_demo_goal.py -- DSP-015 demo goal script.

The demo goal script (hackathon/demo_goal.py) must prove the
demo plan is stable: 5 dry-runs, same job count, same file
ownership per job, same posting order, G5 shape held, DSP-026
spec and DSP-027 acceptance standards passing. These tests run
the script as a subprocess (like test_intel_cli.py) and also
exercise its run_stability/check_shape functions directly, so a
drift between the script, the plan file, and the G5 golden plan
fails here, not on demo day.

The tests write no files into the repo: reports and bad plans
go to a temp dir. They post nothing, claim nothing, and touch
no job state: the script only runs the pure dry-run pipeline.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "hackathon", "demo_goal.py")
PLAN = os.path.join(REPO, "hackathon", "demo_goal_plan.json")
INTEL_PY = os.path.join(REPO, "intel.py")

SPEC = importlib.util.spec_from_file_location("demo_goal", SCRIPT)
demo_goal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo_goal)


def run_script(*argv):
    """Run hackathon/demo_goal.py; return (rc, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, *argv],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


class DemoGoalTest(unittest.TestCase):
    def test_goal_constant_is_the_demo_goal(self):
        self.assertEqual(
            demo_goal.DEMO_GOAL,
            "Build a small status page feature for the relay repo: "
            "an intel status module with tests, a viewer panel stub, "
            "docs for both, and a review pass -- each as separate "
            "jobs with clear file ownership.")

    def test_run_stability_fingerprint(self):
        with open(PLAN) as handle:
            plan_text = handle.read()
        result = demo_goal.run_stability(plan_text, runs=5)
        self.assertTrue(result["stable"])
        self.assertEqual(result["job_count"], 5)
        self.assertEqual(
            result["order"],
            ["module", "panel", "tests", "docs", "review"])
        self.assertEqual(result["files_by_job"], {
            "module": ["intel/status.py"],
            "panel": ["bus.html"],
            "tests": ["tests/test_intel_status.py"],
            "docs": ["docs/status-page.md"],
            "review": ["intel/notes/status-review.md"],
        })
        self.assertEqual(result["shape_failures"], [])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(all(s["passes"]
                            for s in result["spec_scores"]))
        self.assertTrue(all(s["passes"]
                            for s in result["accept_scores"]))

    def test_check_shape_catches_wrong_order(self):
        with open(PLAN) as handle:
            plan_text = handle.read()
        plan, _order, _clamps = demo_goal._dispatch.validated_plan(
            plan_text)
        bad_order = ["panel", "module", "tests", "docs", "review"]
        failures = demo_goal.check_shape(plan, bad_order)
        self.assertTrue(failures)
        self.assertTrue(any("module" in f and "panel" in f
                            for f in failures))

    def test_script_writes_stability_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "stability.md")
            code, out, _err = run_script("--report", report)
            self.assertEqual(code, 0)
            self.assertIn("demo goal stable: 5 runs, 5 jobs", out)
            self.assertIn("module -> panel -> tests -> docs -> review",
                          out)
            with open(report) as handle:
                text = handle.read()
            self.assertIn("Stable: yes", text)
            self.assertIn("G5 shape holds", text)
            self.assertIn("not Spark", text)
            self.assertNotIn("\u2014", text)

    def test_script_refuses_a_bad_plan(self):
        bad = {
            "summary": "Two jobs, one file.",
            "jobs": [
                {"key": "one", "title": "One",
                 "spec": "Goal: one. Context: x. Files: a.py. "
                 "Steps: do it. Out of scope: none.",
                 "files": ["a.py"], "deps": [], "max_attempts": 3,
                 "accept": ["file-exists: a.py"]},
                {"key": "two", "title": "Two",
                 "spec": "Goal: two. Context: x. Files: a.py. "
                 "Steps: do it. Out of scope: none.",
                 "files": ["a.py"], "deps": [], "max_attempts": 3,
                 "accept": ["file-exists: a.py"]},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            bad_plan = os.path.join(tmp, "bad.json")
            with open(bad_plan, "w") as handle:
                json.dump(bad, handle)
            code, _out, err = run_script(
                "--plan", bad_plan, "--report",
                os.path.join(tmp, "report.md"))
            self.assertEqual(code, 2)
            self.assertIn("failed a gate", err)

    def test_cli_dry_run_on_demo_plan(self):
        proc = subprocess.run(
            [sys.executable, INTEL_PY, "dispatch",
             "--goal", demo_goal.DEMO_GOAL, "--dry-run",
             "--plan", PLAN],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("module -> panel -> tests -> docs -> review",
                      proc.stdout)
        self.assertIn("nothing posted", proc.stdout)


if __name__ == "__main__":
    unittest.main()
