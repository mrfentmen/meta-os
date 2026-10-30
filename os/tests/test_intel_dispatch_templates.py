"""tests/test_intel_dispatch_templates.py -- dispatch templates (DSP-018).

The templates live in intel/prompts/dispatch.md as prompt hints,
not hard code: the parser has no template check, and a plan that
follows no template still parses and dry-runs. These tests pin
both halves of that: every template name appears in the prompt,
and a hand-authored plan in each template's usual shape passes
the full dry-run pipeline (parse, guards, clamps) plus the
DSP-026 spec scorer and the DSP-027 accept scorer.

These are hand-authored plans, NOT Spark output: no Spark call
runs here, and nothing is posted, claimed, or announced.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import (  # noqa: E402
    dry_run_plan, parse_plan, score_plan_accepts,
    score_plan_specs, validated_plan,
)

TEMPLATES = ("add-endpoint", "fix-bug", "write-tests", "docs-pass")


def _prompt_text():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "intel", "prompts", "dispatch.md")
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _prompt_section():
    text = _prompt_text()
    return text.split("## Dispatch templates (DSP-018)")[1]


def _spec(files):
    return ("Goal: do this one job and nothing else. "
            "Context: the intel package area the goal names. "
            "Files: " + ", ".join(files) + ". "
            "Steps: make the change, then run the checks. "
            "Out of scope: any other job's work.")


def _job(key, title, files, accept, deps=()):
    return {"key": key, "title": title, "spec": _spec(files),
            "files": list(files), "deps": list(deps),
            "max_attempts": 3, "accept": list(accept)}


def _plan(summary, jobs):
    return json.dumps({"summary": summary, "jobs": jobs})


class PromptTemplatesTest(unittest.TestCase):
    """DSP-018: the four template names appear in the prompt file."""

    def test_section_lists_all_four_templates(self):
        section = _prompt_section()
        for name in TEMPLATES:
            self.assertIn(name, section)

    def test_section_says_hints_not_hard_code(self):
        section = _prompt_section()
        self.assertIn("not hard code", section)
        self.assertIn("hints", section)

    def test_section_says_no_template_overrides_guards(self):
        section = _prompt_section()
        self.assertIn("No template", section)
        self.assertIn("overrides", section)

    def test_template_names_absent_from_dispatch_code(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "intel", "dispatch.py")
        with open(path, "r", encoding="utf-8") as handle:
            code = handle.read()
        for name in TEMPLATES:
            self.assertNotIn(name, code,
                             "template %r leaked into code" % name)


class TemplateShapeTest(unittest.TestCase):
    """DSP-018: a goal matching each shape yields a sane dry-run plan.

    Each plan below follows the usual job shape its template
    hints at. Sane means: the full validated_plan pipeline passes
    (parse, overlap, contradiction, deps, clamps), the dry-run
    render names every job, and every job passes both scorers.
    """

    def _assert_sane(self, text):
        plan, order, clamps = validated_plan(text)
        self.assertEqual(clamps, [])
        detail = dry_run_plan(text)
        for job in plan["jobs"]:
            self.assertIn(job["key"], detail)
            self.assertIn(job["title"], detail)
        for score in score_plan_specs(plan):
            self.assertTrue(score["passes"], score)
        for score in score_plan_accepts(plan):
            self.assertTrue(score["passes"], score)
        return plan, order

    def test_add_endpoint_shape(self):
        plan_text = _plan(
            "Add a widget endpoint, then test it.",
            [_job("implement", "Add widget endpoint",
                  ["intel/widget.py"],
                  ["file-exists: intel/widget.py",
                   "tests-pass: tests.test_intel_widget"]),
             _job("tests", "Test widget endpoint",
                  ["tests/test_intel_widget.py"],
                  ["file-exists: tests/test_intel_widget.py",
                   "tests-pass: tests.test_intel_widget"],
                  deps=["implement"])])
        plan, order = self._assert_sane(plan_text)
        self.assertEqual(order, ["implement", "tests"])

    def test_fix_bug_shape(self):
        plan_text = _plan(
            "Reproduce the widget bug, fix it, add a regression test.",
            [_job("reproduce", "Reproduce widget bug",
                  ["tests/test_repro_widget.py"],
                  ["file-exists: tests/test_repro_widget.py"]),
             _job("fix", "Fix widget bug",
                  ["intel/widget.py"],
                  ["file-exists: intel/widget.py",
                   "tests-pass: tests.test_intel_widget"],
                  deps=["reproduce"]),
             _job("regression-test", "Add widget regression test",
                  ["tests/test_intel_widget.py"],
                  ["tests-pass: tests.test_intel_widget"],
                  deps=["fix"])])
        plan, order = self._assert_sane(plan_text)
        self.assertEqual(order,
                         ["reproduce", "fix", "regression-test"])

    def test_write_tests_shape(self):
        plan_text = _plan(
            "Cover the widget area with tests, changing no code.",
            [_job("tests", "Cover widget with tests",
                  ["tests/test_intel_widget.py"],
                  ["tests-pass: tests.test_intel_widget"])])
        plan, order = self._assert_sane(plan_text)
        self.assertEqual(order, ["tests"])
        self.assertNotIn("intel/widget.py", plan["jobs"][0]["files"])

    def test_docs_pass_shape(self):
        plan_text = _plan(
            "Refresh the widget docs, changing no code.",
            [_job("docs", "Refresh widget docs",
                  ["docs/widget.md"],
                  ["file-exists: docs/widget.md",
                   "contains: docs/widget.md :: widget"])])
        plan, order = self._assert_sane(plan_text)
        self.assertEqual(order, ["docs"])

    def test_no_template_plan_still_dry_runs(self):
        """Hints, not gates: an untemplated shape is still valid."""
        plan_text = _plan(
            "Refactor the widget helper without changing behavior.",
            [_job("refactor", "Refactor widget helper",
                  ["intel/widget.py"],
                  ["file-exists: intel/widget.py",
                   "tests-pass: tests.test_intel_widget"])])
        plan, order = self._assert_sane(plan_text)
        self.assertEqual(order, ["refactor"])


if __name__ == "__main__":
    unittest.main()
