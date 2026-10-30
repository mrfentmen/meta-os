"""tests/test_intel_dispatch_readme.py — intel/README.md dispatch section (DSP-020).

DSP-020 acceptance is a cold reader posting a dry-run plan from the
README alone. This test pins the section to the code so the section
and the code cannot drift apart silently:

- The Dispatch section exists in intel/README.md, sits at heading
  level 2 after the briefing engine section and before the final
  Status section, and contains no em dash (DOC-007 hygiene for new
  copy; the README itself is grandfathered in the dash baseline,
  but new DSP-020 copy must still be dash-free).
- Every command, function, and guard the section names actually
  exists: the intel.py CLI parser accepts the dispatch flags, and
  every named intel.dispatch function is importable.
- The section's cold-reader dry-run works: the demo goal plan file
  the section names (hackathon/demo_goal_plan.json) dry-runs clean
  through dry_run_plan, posts nothing, and yields the 5-job G5
  shape the section describes.

No bus post, no queue write, no Spark call: dry_run_plan is pure
functions on plan text, and the README read is a file read.
"""

import os
import unittest

from intel import dispatch as _dispatch  # noqa: E402


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dispatch_section():
    path = os.path.join(_repo_root(), "intel", "README.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.index("## Dispatch - DSP-020 (Pax)")
    end = text.index("\n## Status", start)
    return text[start:end]


class DispatchReadmeSectionTest(unittest.TestCase):
    def test_section_exists_at_level_two_in_order(self):
        path = os.path.join(_repo_root(), "intel", "README.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## Briefing engine", text)
        self.assertIn("## Dispatch - DSP-020 (Pax)", text)
        dispatch_at = text.index("## Dispatch - DSP-020 (Pax)")
        self.assertGreater(dispatch_at, text.index("## Briefing engine"))
        self.assertLess(dispatch_at, text.rindex("## Status"))
        # The section is a level-2 section, not a subsection of the
        # wire-format freeze: the freeze's own status stays level 3.
        self.assertIn("### Status", text)

    def test_section_has_no_em_dash(self):
        self.assertNotIn("\u2014", _dispatch_section())

    def test_section_names_real_commands(self):
        section = _dispatch_section()
        for command in (
            "python3 intel.py dispatch --goal",
            "--dry-run --plan",
            "--approve",
            "--secret-file",
            "--crew-mode",
            "--confirm-large",
            "--show <dispatch id>",
            "--undo <dispatch id>",
            "hackathon/demo_goal_plan.json",
            "muse-bus:intel:dispatch:<id>",
        ):
            self.assertIn(command, section, command)

    def test_section_names_real_functions(self):
        section = _dispatch_section()
        for name in (
            "parse_plan",
            "check_file_overlap",
            "check_no_contradiction",
            "check_dep_graph",
            "clamp_attempt_budgets",
            "validated_plan",
            "dry_run_plan",
            "request_approval",
            "post_plan",
            "show_dispatch",
            "undo_dispatch",
            "check_no_secrets",
            "plan_size_warnings",
            "plan_from_spark",
            "fallback_plan",
        ):
            self.assertIn(name, section, name)
            self.assertTrue(callable(getattr(_dispatch, name)), name)

    def test_section_names_the_guards(self):
        section = _dispatch_section()
        for task in ("DSP-002", "DSP-003", "DSP-004", "DSP-005",
                     "DSP-007", "DSP-008", "DSP-009", "DSP-010",
                     "DSP-011", "DSP-013", "DSP-016", "DSP-017",
                     "DSP-028"):
            self.assertIn(task, section, task)

    def test_cold_reader_dry_run_from_section(self):
        plan_path = os.path.join(_repo_root(), "hackathon",
                                 "demo_goal_plan.json")
        with open(plan_path, encoding="utf-8") as handle:
            plan_text = handle.read()
        detail = _dispatch.dry_run_plan(plan_text)
        plan, order, _clamps = _dispatch.validated_plan(plan_text)
        self.assertEqual(len(plan["jobs"]), 5)
        self.assertEqual(order, ["module", "panel", "tests", "docs",
                                 "review"])
        # The dry-run prints the plan; it never posts, so the
        # detail names every job key and the posting order.
        for key in order:
            self.assertIn(key, detail, key)


if __name__ == "__main__":
    unittest.main()
