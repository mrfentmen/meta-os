"""tests/test_intel_dispatch.py — intel/dispatch.py plan parser (DSP-002).

The parser validates Spark plan JSON strictly against the DSP-001
output schema: shape, types, non-empty files per job, at least one
accept line per job that parses via mos/acceptance.parse_accept,
unique plan-local keys, no unknown fields. It never posts, never
claims, never touches the bus, and never needs a Spark call: every
plan here is a literal string in the test.

Scope boundaries the tests pin down so later tasks are not
pre-empted: unknown dep keys pass here (DSP-004 owns the dep
graph); an out-of-range max_attempts passes unclamped here
(DSP-005 owns clamping); over-12-job plans pass here (DSP-013
owns the size guardrail).

DSP-003 tests below cover check_file_overlap on parsed plans: an
overlap is a hard error unless every consecutive owner pair is
shared-sequential (later job deps on the earlier job AND its spec
contains "shared-sequential" plus the shared path). The parser
itself stays shape-only: an overlapping plan still parses, and
only the guard rejects it.

DSP-004 tests below cover check_dep_graph on parsed plans: every
dep must name a plan-local key, cycles are rejected with the cycle
named, and the returned order puts every dep before its dependent
so DSP-008 can post in that order. The parser itself stays
shape-only: an unknown dep key still parses, and only the graph
check rejects it.

DSP-005 tests below cover clamp_attempt_budgets on parsed plans:
default 3, per-job overrides honored inside 1..5, out-of-range
values clamped to the bounds and reported, input plan unmutated.
The parser itself stays shape-only: an out-of-range max_attempts
still parses unclamped, and only the clamp adjusts it.

DSP-028 tests below cover check_no_secrets on goal and plan
texts: a credential-shaped string in either place is refused
with a secret warning naming the shape, never the value. The
parser itself stays shape-only here too: a plan carrying a
fake key still parses, and only the secret guard refuses it.
All keys below are repeated-character fakes, not real
credentials, and no test posts, claims, or touches the bus.

DSP-007 tests below cover request_approval: the --approve
flag approves, an interactive y/yes approves, and everything
else denies — any other answer, an EOFError from the prompt,
or no prompt at all. The gate returns a decision only; it
never posts. The CLI tests pin the same at the command line:
without approval the run exits 2 with zero jobs posted, and
with approval the DSP-008 poster posts the plan (PosterTest
pins the poster itself: topological order, plan keys rewritten
to real job ids, dispatch record stored, partial failure
leaving earlier jobs posted and no record stored).

with approval it reaches the DSP-008 poster refusal (the
poster itself is not built yet, so approval passed is never
reported as posted).

DSP-023 tests below cover the adversarial goals doc: each of
the six adversarial cases triggers its documented guard and
nothing is posted. The parser itself stays shape-only for the
contradiction case too: a create-then-delete plan still parses,
and only check_no_contradiction rejects it. The huge-scope case
pins a deliberate gap: over-12-job plans still pass parse
(DSP-013 owns the size guardrail), so the standing guard there
is the DSP-007 approval denial, and the doc says so.

DSP-009 tests below cover signing: a plan posted with a
keyring verifies OK job by job via jobs.py verify, the
record carries signed=True, and the CLI --secret-file /
--crew-mode flags wire through; crew mode without a
keyring refuses before any post with zero jobs posted and
no record stored; an unsigned post (no keyring, crew mode
off) still posts but warns loudly on stderr, records
signed=False, and verifies UNSIGNED; a bad keyring fails
at the first job under the DSP-008 partial-failure
contract. All keyring contents below are throwaway test
secrets, never real credentials.

DSP-013 tests below cover the plan-size guardrail: a plan
at exactly 12 jobs or 40 files triggers nothing, a 13-job
plan or a 41-file plan triggers one warning each naming
the count, the limit, and the split suggestion, and the
warning shows in the dry-run; a large plan needs a second
confirmation (a second y/yes at the prompts, or the
--confirm-large flag) on top of the first approval, and
the poster refuses a large plan without it before any job
is posted. The parser itself stays shape-only for size:
a 13-job plan still parses, only the guard fires.

DSP-011 tests below cover dispatch undo: undoing a posted
plan cancels every still-open job through jobs.py cancel
(status cancelled, never claimable again), leaves a claimed
job untouched and reported with its claim nick, leaves a
done job untouched and reported with its status, reports a
job id that no longer exists as missing, raises on an
unknown dispatch id with nothing touched, and cancels
nothing new on a second undo; a cancel refused at the
queue is classified by re-reading the job, not fatal.
"""

import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import (  # noqa: E402
    DEFAULT_MAX_ATTEMPTS, MAX_MAX_ATTEMPTS, MAX_PLAN_FILES,
    MAX_PLAN_JOBS, MIN_MAX_ATTEMPTS,
    PlanError, PostError, UndoError, approval_prompt,
    check_dep_graph, check_file_overlap, check_no_contradiction,
    check_no_secrets, clamp_attempt_budgets,
    dry_run_plan, large_plan_prompt, parse_plan, plan_paragraph,
    plan_size_warnings, plan_summary, post_plan,
    render_plan_detail, request_approval, score_accept_lines,
    score_plan_accepts, score_plan_specs,
    score_spec_parts, undo_dispatch, validated_plan)
from intel import store as istore  # noqa: E402
import jobs  # noqa: E402
from helpers import RelayTestCase  # noqa: E402


def _load_intel_cli():
    """Load root intel.py under a distinct name (intel/ is a package)."""
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "intel.py")
    spec = importlib.util.spec_from_file_location(
        "intel_cli_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _job(key, files=("intel/ingest.py",), deps=(), max_attempts=3,
         accept=("file-exists: intel/ingest.py",), title=None,
         spec="Goal, context, files, steps, out of scope."):
    job = {
        "key": key,
        "title": title or f"Do {key}",
        "spec": spec,
        "files": list(files),
        "deps": list(deps),
        "max_attempts": max_attempts,
        "accept": list(accept),
    }
    return job


def _golden():
    # 4-job diamond: base -> api, base -> panel, api + panel -> docs.
    return {
        "summary": "Build the snapshot in order: base, then api and "
                   "panel, then docs.",
        "jobs": [
            _job("base", files=("intel/ingest.py",),
                 accept=("file-exists: intel/ingest.py",
                         "tests-pass: tests.test_intel_snapshot",)),
            _job("api", files=("intel.py",), deps=("base",),
                 accept=("contains: intel.py :: snapshot",)),
            _job("panel", files=("bus.html",), deps=("base",),
                 accept=("file-exists: bus.html",)),
            _job("docs", files=("intel/README.md",),
                 deps=("api", "panel"),
                 accept=("contains: intel/README.md :: snapshot",)),
        ],
    }


class ParsePlanTest(unittest.TestCase):
    def test_golden_plan_accepted(self):
        plan = parse_plan(json.dumps(_golden()))
        self.assertEqual(plan["summary"], _golden()["summary"])
        self.assertEqual([j["key"] for j in plan["jobs"]],
                         ["base", "api", "panel", "docs"])
        self.assertEqual(plan["jobs"][1]["deps"], ["base"])
        self.assertEqual(plan["jobs"][3]["deps"], ["api", "panel"])
        self.assertEqual(plan["jobs"][0]["max_attempts"], 3)

    def test_not_json_rejected(self):
        with self.assertRaisesRegex(PlanError, "not valid JSON"):
            parse_plan("{oops")

    def test_top_level_not_object_rejected(self):
        with self.assertRaisesRegex(PlanError, "must be a JSON object"):
            parse_plan("[1, 2]")

    def test_missing_jobs_rejected(self):
        with self.assertRaisesRegex(PlanError, "missing.*'jobs'"):
            parse_plan(json.dumps({"summary": "No jobs here."}))

    def test_empty_files_rejected(self):
        golden = _golden()
        golden["jobs"][0]["files"] = []
        with self.assertRaisesRegex(PlanError, "base.*'files'.*non-empty"):
            parse_plan(json.dumps(golden))

    def test_bad_accept_line_rejected(self):
        golden = _golden()
        golden["jobs"][0]["accept"] = ["works correctly"]
        with self.assertRaisesRegex(PlanError, "base.*unparseable accept"):
            parse_plan(json.dumps(golden))

    def test_empty_accept_rejected(self):
        golden = _golden()
        golden["jobs"][0]["accept"] = []
        with self.assertRaisesRegex(PlanError, "base.*'accept'.*non-empty"):
            parse_plan(json.dumps(golden))

    def test_duplicate_key_rejected(self):
        golden = _golden()
        golden["jobs"][1] = _job("base", files=("intel.py",))
        with self.assertRaisesRegex(PlanError, "duplicate job key"):
            parse_plan(json.dumps(golden))

    def test_missing_title_rejected(self):
        golden = _golden()
        del golden["jobs"][0]["title"]
        with self.assertRaisesRegex(PlanError, "base.*'title'"):
            parse_plan(json.dumps(golden))

    def test_non_integer_max_attempts_rejected(self):
        golden = _golden()
        golden["jobs"][0]["max_attempts"] = "three"
        with self.assertRaisesRegex(PlanError, "base.*'max_attempts'"):
            parse_plan(json.dumps(golden))

    def test_unknown_field_rejected(self):
        golden = _golden()
        golden["jobs"][0]["surprise"] = True
        with self.assertRaisesRegex(PlanError, "unknown field"):
            parse_plan(json.dumps(golden))

    def test_defaults_applied(self):
        golden = _golden()
        del golden["jobs"][0]["deps"]
        del golden["jobs"][0]["max_attempts"]
        plan = parse_plan(json.dumps(golden))
        self.assertEqual(plan["jobs"][0]["deps"], [])
        self.assertEqual(plan["jobs"][0]["max_attempts"],
                         DEFAULT_MAX_ATTEMPTS)

    def test_unknown_dep_passes_here_dsp004_owns_graph(self):
        golden = _golden()
        golden["jobs"][0]["deps"] = ["no-such-job"]
        plan = parse_plan(json.dumps(golden))
        self.assertEqual(plan["jobs"][0]["deps"], ["no-such-job"])

    def test_out_of_range_max_attempts_passes_unclamped_dsp005(self):
        golden = _golden()
        golden["jobs"][0]["max_attempts"] = 99
        plan = parse_plan(json.dumps(golden))
        self.assertEqual(plan["jobs"][0]["max_attempts"], 99)


def _overlap_plan(second_deps=(), second_spec=None):
    # Two jobs owning intel/ingest.py; the second job is the one
    # that must carry the dep and the shared-sequential marker.
    first = _job("base", files=("intel/ingest.py",))
    second = _job("api", files=("intel/ingest.py",),
                  deps=second_deps,
                  spec=second_spec or "Goal, context, files, "
                  "steps, out of scope.")
    return {"summary": "Two jobs touch one path.",
            "jobs": [first, second]}


class FileOverlapGuardTest(unittest.TestCase):
    def test_golden_plan_has_no_overlap(self):
        plan = parse_plan(json.dumps(_golden()))
        self.assertIs(check_file_overlap(plan), plan)

    def test_overlap_passes_parser_but_fails_guard(self):
        # DSP-002 shape-only boundary: the parser accepts it.
        plan = parse_plan(json.dumps(_overlap_plan()))
        with self.assertRaisesRegex(
                PlanError, "api.*base.*intel/ingest.py"):
            check_file_overlap(plan)

    def test_overlap_with_dep_but_no_marker_rejected(self):
        plan = parse_plan(json.dumps(
            _overlap_plan(second_deps=("base",))))
        with self.assertRaisesRegex(PlanError, "shared-sequential"):
            check_file_overlap(plan)

    def test_overlap_with_marker_but_no_dep_rejected(self):
        plan = parse_plan(json.dumps(_overlap_plan(
            second_spec="Goal, context, files, steps, out of scope. "
            "shared-sequential: intel/ingest.py")))
        with self.assertRaisesRegex(PlanError, "must list.*in 'deps'"):
            check_file_overlap(plan)

    def test_shared_sequential_with_dep_and_marker_accepted(self):
        plan = parse_plan(json.dumps(_overlap_plan(
            second_deps=("base",),
            second_spec="Goal, context, files, steps, out of scope. "
            "shared-sequential: intel/ingest.py")))
        self.assertIs(check_file_overlap(plan), plan)

    def test_marker_naming_a_different_path_rejected(self):
        plan = parse_plan(json.dumps(_overlap_plan(
            second_deps=("base",),
            second_spec="Goal, context, files, steps, out of scope. "
            "shared-sequential: intel.py")))
        with self.assertRaisesRegex(PlanError, "shared-sequential"):
            check_file_overlap(plan)

    def test_marker_case_insensitive(self):
        plan = parse_plan(json.dumps(_overlap_plan(
            second_deps=("base",),
            second_spec="Goal, context, files, steps, out of scope. "
            "Shared-Sequential: intel/ingest.py")))
        self.assertIs(check_file_overlap(plan), plan)

    def test_three_job_chain_needs_every_consecutive_pair(self):
        first = _job("one", files=("intel/ingest.py",))
        marker = ("Goal, context, files, steps, out of scope. "
                  "shared-sequential: intel/ingest.py")
        second = _job("two", files=("intel/ingest.py",),
                      deps=("one",), spec=marker)
        third = _job("three", files=("intel/ingest.py",),
                     deps=("two",), spec=marker)
        plan = parse_plan(json.dumps(
            {"summary": "Three steps on one path.",
             "jobs": [first, second, third]}))
        self.assertIs(check_file_overlap(plan), plan)
        # Break the second link: third keeps its dep but loses
        # the marker, so the chain is no longer sequential.
        third_broken = _job("three", files=("intel/ingest.py",),
                            deps=("two",))
        plan = parse_plan(json.dumps(
            {"summary": "Three steps on one path.",
             "jobs": [first, second, third_broken]}))
        with self.assertRaisesRegex(PlanError, "three.*two"):
            check_file_overlap(plan)

    def test_one_bad_pair_fails_even_when_another_pair_is_clean(self):
        first = _job("base", files=("intel/ingest.py",))
        marker = ("Goal, context, files, steps, out of scope. "
                  "shared-sequential: intel/ingest.py")
        second = _job("api", files=("intel/ingest.py",),
                      deps=("base",), spec=marker)
        third = _job("panel", files=("bus.html",))
        fourth = _job("docs", files=("bus.html",))
        plan = parse_plan(json.dumps(
            {"summary": "One clean pair, one bad pair.",
             "jobs": [first, second, third, fourth]}))
        with self.assertRaisesRegex(PlanError, "docs.*panel.*bus.html"):
            check_file_overlap(plan)

    def test_same_job_listing_a_path_twice_is_not_an_overlap(self):
        job = _job("solo", files=("intel/ingest.py",
                                  "intel/ingest.py"))
        plan = parse_plan(json.dumps(
            {"summary": "One job, one path twice.",
             "jobs": [job]}))
        self.assertIs(check_file_overlap(plan), plan)


class DepGraphTest(unittest.TestCase):
    def test_golden_diamond_order(self):
        plan = parse_plan(json.dumps(_golden()))
        self.assertEqual(check_dep_graph(plan),
                         ["base", "api", "panel", "docs"])

    def test_order_is_posting_order_not_input_order(self):
        # Same diamond, jobs listed leaf-first: deps still come first.
        golden = _golden()
        jobs = list(reversed(golden["jobs"]))
        plan = parse_plan(json.dumps(
            {"summary": golden["summary"], "jobs": jobs}))
        self.assertEqual(check_dep_graph(plan),
                         ["base", "api", "panel", "docs"])

    def test_independent_jobs_keep_plan_order(self):
        jobs = [_job("one", files=("a.py",)),
                _job("two", files=("b.py",)),
                _job("three", files=("c.py",))]
        plan = parse_plan(json.dumps(
            {"summary": "Three independent jobs.", "jobs": jobs}))
        self.assertEqual(check_dep_graph(plan),
                         ["one", "two", "three"])

    def test_unknown_dep_passes_parser_but_fails_graph(self):
        # DSP-002 shape-only boundary: the parser accepts it.
        golden = _golden()
        golden["jobs"][0]["deps"] = ["no-such-job"]
        plan = parse_plan(json.dumps(golden))
        with self.assertRaisesRegex(
                PlanError, "base.*no-such-job.*not a job key"):
            check_dep_graph(plan)

    def test_unknown_dep_in_later_job_named(self):
        golden = _golden()
        golden["jobs"][3]["deps"] = ["api", "ghost"]
        plan = parse_plan(json.dumps(golden))
        with self.assertRaisesRegex(
                PlanError, "docs.*ghost.*not a job key"):
            check_dep_graph(plan)

    def test_two_job_cycle_names_the_cycle(self):
        jobs = [_job("a", files=("a.py",), deps=("b",)),
                _job("b", files=("b.py",), deps=("a",))]
        plan = parse_plan(json.dumps(
            {"summary": "A cycle of two.", "jobs": jobs}))
        with self.assertRaisesRegex(
                PlanError, "dependency cycle: a -> b -> a"):
            check_dep_graph(plan)

    def test_three_job_cycle_names_the_cycle(self):
        jobs = [_job("a", files=("a.py",), deps=("c",)),
                _job("b", files=("b.py",), deps=("a",)),
                _job("c", files=("c.py",), deps=("b",))]
        plan = parse_plan(json.dumps(
            {"summary": "A cycle of three.", "jobs": jobs}))
        with self.assertRaisesRegex(
                PlanError, "dependency cycle: a -> c -> b -> a"):
            check_dep_graph(plan)

    def test_self_dep_is_a_cycle(self):
        jobs = [_job("a", files=("a.py",), deps=("a",))]
        plan = parse_plan(json.dumps(
            {"summary": "A job depending on itself.", "jobs": jobs}))
        with self.assertRaisesRegex(
                PlanError, "dependency cycle: a -> a"):
            check_dep_graph(plan)

    def test_cycle_elsewhere_fails_even_when_a_chain_is_clean(self):
        jobs = [_job("base", files=("a.py",)),
                _job("api", files=("b.py",), deps=("base",)),
                _job("x", files=("x.py",), deps=("y",)),
                _job("y", files=("y.py",), deps=("x",))]
        plan = parse_plan(json.dumps(
            {"summary": "One clean chain, one cycle.",
             "jobs": jobs}))
        with self.assertRaisesRegex(
                PlanError, "dependency cycle: x -> y -> x"):
            check_dep_graph(plan)

    def test_duplicate_dep_entries_tolerated(self):
        jobs = [_job("base", files=("a.py",)),
                _job("api", files=("b.py",),
                     deps=("base", "base"))]
        plan = parse_plan(json.dumps(
            {"summary": "A dep listed twice.", "jobs": jobs}))
        self.assertEqual(check_dep_graph(plan), ["base", "api"])

    def test_check_does_not_mutate_the_plan(self):
        plan = parse_plan(json.dumps(_golden()))
        before = [j["key"] for j in plan["jobs"]]
        order = check_dep_graph(plan)
        self.assertEqual([j["key"] for j in plan["jobs"]], before)
        self.assertIsNot(order, plan["jobs"])
class GoalElicitationTest(unittest.TestCase):
    """DSP-021: dispatch prompt carries goal-elicitation microcopy.

    When a goal is too vague (no scope, no files hint, no done
    definition), Spark asks exactly three questions — scope, files
    hint, done definition — and produces no plan. The prompt text
    is guarded here; a real Spark run over a vague goal (which
    needs live transport and the DSP-006 dry-run) is still owed,
    so this test guards the microcopy, not a Spark verdict. The
    questions-only response is pinned unparseable as a plan:
    parse_plan raises PlanError on it, so no plan object exists
    for any poster to post.
    """

    QUESTIONS = (
        "What part of the system should this cover, and what is "
        "out of scope?",
        "Which files should this touch, or should I suggest them "
        "from the goal?",
        "How will we know it is done: what check should pass "
        "when the work is finished?",
    )

    VAGUE_GOALS = ("Improve things", "Make it better", "Fix stuff")

    def _section(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                             "intel", "prompts", "dispatch.md")
        with open(path) as handle:
            text = handle.read()
        start = text.index("## When the goal is too vague")
        rest = text[start:]
        end = rest.find("\n## ", 1)
        return rest if end < 0 else rest[:end]

    def test_section_asks_exactly_the_three_questions(self):
        import re
        section = self._section()
        found = re.findall(r"(?m)^\d+\.\s+(.*\?)\s*$", section)
        self.assertEqual(list(self.QUESTIONS), found)

    def test_section_says_no_plan_and_no_posting(self):
        section = self._section()
        self.assertIn("exactly the three questions", section)
        self.assertIn("no plan", section)
        self.assertIn("no posting", section)

    def test_questions_only_response_is_not_a_plan(self):
        response = "\n".join(
            f"{i + 1}. {q}" for i, q in enumerate(self.QUESTIONS))
        with self.assertRaises(PlanError):
            parse_plan(response)
        for goal in self.VAGUE_GOALS:
            with self.assertRaises(PlanError):
                parse_plan(goal)


class AttemptBudgetTest(unittest.TestCase):
    def _plan(self, attempts):
        golden = _golden()
        for job, value in zip(golden["jobs"], attempts):
            job["max_attempts"] = value
        return parse_plan(json.dumps(golden))

    def test_default_three_unchanged(self):
        golden = _golden()
        for job in golden["jobs"]:
            del job["max_attempts"]
        plan, clamps = clamp_attempt_budgets(
            parse_plan(json.dumps(golden)))
        self.assertEqual([j["max_attempts"] for j in plan["jobs"]],
                         [3, 3, 3, 3])
        self.assertEqual(clamps, [])

    def test_in_range_overrides_honored(self):
        plan, clamps = clamp_attempt_budgets(
            self._plan([1, 2, 4, 5]))
        self.assertEqual([j["max_attempts"] for j in plan["jobs"]],
                         [1, 2, 4, 5])
        self.assertEqual(clamps, [])

    def test_high_value_clamped_and_reported(self):
        plan, clamps = clamp_attempt_budgets(self._plan([99, 3, 3, 3]))
        self.assertEqual(plan["jobs"][0]["max_attempts"], 5)
        self.assertEqual(clamps, [{"key": "base", "requested": 99,
                                   "clamped": 5}])
        summary = plan_summary(plan, clamps)
        self.assertIn("clamped: job 'base': max_attempts 99 -> 5",
                      summary)

    def test_low_values_clamped_to_one(self):
        plan, clamps = clamp_attempt_budgets(self._plan([0, -4, 3, 3]))
        self.assertEqual([j["max_attempts"] for j in plan["jobs"]],
                         [1, 1, 3, 3])
        self.assertEqual([(c["key"], c["requested"], c["clamped"])
                          for c in clamps],
                         [("base", 0, 1), ("api", -4, 1)])

    def test_boundary_values_not_clamped(self):
        plan, clamps = clamp_attempt_budgets(self._plan([1, 5, 3, 3]))
        self.assertEqual([j["max_attempts"] for j in plan["jobs"]],
                         [1, 5, 3, 3])
        self.assertEqual(clamps, [])

    def test_input_plan_not_mutated(self):
        plan = self._plan([99, 0, 3, 3])
        before = json.dumps(plan, sort_keys=True)
        clamp_attempt_budgets(plan)
        self.assertEqual(json.dumps(plan, sort_keys=True), before)

    def test_clamps_in_plan_order(self):
        plan, clamps = clamp_attempt_budgets(
            self._plan([99, 6, 0, 3]))
        self.assertEqual([c["key"] for c in clamps],
                         ["base", "api", "panel"])
        self.assertEqual([j["max_attempts"] for j in plan["jobs"]],
                         [5, 5, 1, 3])

    def test_summary_lists_jobs_and_no_clamp_section_when_clean(self):
        plan, clamps = clamp_attempt_budgets(self._plan([3, 3, 3, 3]))
        summary = plan_summary(plan, clamps)
        self.assertIn("- base: Do base (attempts 3)", summary)
        self.assertIn("- docs: Do docs (attempts 3)", summary)
        self.assertNotIn("clamped:", summary)

    def test_clamped_plan_still_passes_later_checks(self):
        plan, clamps = clamp_attempt_budgets(self._plan([99, 3, 3, 3]))
        check_file_overlap(plan)
        self.assertEqual(check_dep_graph(plan),
                         ["base", "api", "panel", "docs"])

    def test_malformed_plan_rejected(self):
        with self.assertRaises(PlanError):
            clamp_attempt_budgets({"jobs": "not-a-list"})
        with self.assertRaises(PlanError):
            plan_summary({"summary": "x", "jobs": "not-a-list"})

    def test_constants_match_spec(self):
        self.assertEqual((MIN_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS,
                          MAX_MAX_ATTEMPTS), (1, 3, 5))


class DryRunPlanTest(unittest.TestCase):
    def test_golden_detail_prints_the_full_plan(self):
        detail = dry_run_plan(json.dumps(_golden()))
        self.assertIn(_golden()["summary"], detail)
        self.assertIn("jobs in posting order: base -> api -> panel "
                      "-> docs", detail)
        for job in _golden()["jobs"]:
            self.assertIn(job["title"], detail)
            for path in job["files"]:
                self.assertIn(path, detail)
            for line in job["accept"]:
                self.assertIn(line, detail)
        self.assertIn("deps: base", detail)
        self.assertIn("deps: api, panel", detail)
        self.assertIn("(attempts 3)", detail)
        self.assertNotIn("clamped:", detail)

    def test_detail_renders_in_posting_order_not_input_order(self):
        golden = _golden()
        jobs = list(reversed(golden["jobs"]))
        detail = dry_run_plan(json.dumps(
            {"summary": golden["summary"], "jobs": jobs}))
        self.assertLess(detail.index("- base:"),
                        detail.index("- docs:"))

    def test_clamp_is_reported_in_the_detail(self):
        golden = _golden()
        golden["jobs"][0]["max_attempts"] = 99
        detail = dry_run_plan(json.dumps(golden))
        self.assertIn("clamped: job 'base': max_attempts 99 -> 5",
                      detail)
        self.assertIn("- base: Do base (attempts 5)", detail)

    def test_invalid_plans_raise_and_print_nothing(self):
        with self.assertRaisesRegex(PlanError, "not valid JSON"):
            dry_run_plan("{oops")
        with self.assertRaisesRegex(PlanError, "intel/ingest.py"):
            dry_run_plan(json.dumps(_overlap_plan()))
        jobs = [_job("a", files=("a.py",), deps=("b",)),
                _job("b", files=("b.py",), deps=("a",))]
        with self.assertRaisesRegex(PlanError, "dependency cycle"):
            dry_run_plan(json.dumps(
                {"summary": "A cycle of two.", "jobs": jobs}))

    def test_render_with_wrong_order_is_rejected(self):
        plan = parse_plan(json.dumps(_golden()))
        with self.assertRaisesRegex(PlanError, "posting order"):
            render_plan_detail(plan, ["base", "api"])
        with self.assertRaisesRegex(PlanError, "posting order"):
            render_plan_detail(plan,
                               ["base", "api", "panel", "docs",
                                "ghost"])


class PlanParagraphTest(unittest.TestCase):
    def test_golden_plan_1_paragraph_covers_its_only_job(self):
        goal_id, section = _load_golden_sections()[0]
        self.assertEqual(goal_id, "G1")
        block = re.findall(r"```json\n(.*?)```", section, re.S)[0]
        plan = parse_plan(block)
        paragraph = plan_paragraph(plan, check_dep_graph(plan))
        self.assertNotIn("\n", paragraph)
        self.assertIn(plan["summary"], paragraph)
        job = plan["jobs"][0]
        self.assertIn(job["title"], paragraph)
        for path in job["files"]:
            self.assertIn(path, paragraph)

    def test_paragraph_follows_posting_order_not_input_order(self):
        golden = _golden()
        jobs = list(reversed(golden["jobs"]))
        plan = parse_plan(json.dumps(
            {"summary": golden["summary"], "jobs": jobs}))
        paragraph = plan_paragraph(plan, check_dep_graph(plan))
        self.assertNotIn("\n", paragraph)
        self.assertLess(paragraph.index("Do base"),
                        paragraph.index("Do docs"))
        self.assertIn("First,", paragraph)
        self.assertIn("and finally", paragraph)

    def test_partial_order_and_malformed_plan_refused(self):
        plan = parse_plan(json.dumps(_golden()))
        with self.assertRaisesRegex(PlanError, "posting order"):
            plan_paragraph(plan, ["base", "api"])
        with self.assertRaises(PlanError):
            plan_paragraph({"summary": "x", "jobs": "not-a-list"})


class DryRunCliTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        self.plan_path = os.path.join(self.tmp, "plan.json")
        with open(self.plan_path, "w") as handle:
            json.dump(_golden(), handle)

    def test_dry_run_prints_plan_and_posts_nothing(self):
        self.run_cli(jobs.main,
                     ["post", "--title", "Existing", "--spec", "s"])
        _rc, before, _err = self.run_cli(jobs.main, ["list"])
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--dry-run", "--plan", self.plan_path])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("goal: Add a snapshot endpoint", out)
        self.assertIn("jobs in posting order: base -> api -> panel "
                      "-> docs", out)
        self.assertIn("Do base", out)
        self.assertIn("intel/ingest.py", out)
        self.assertIn("file-exists: intel/ingest.py", out)
        self.assertIn("dry run: nothing posted", out)
        _rc, after, _err = self.run_cli(jobs.main, ["list"])
        self.assertEqual(after, before)

    def test_dry_run_without_plan_fails_loudly(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--dry-run"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("--plan", err)

    def test_dry_run_with_invalid_plan_prints_no_plan(self):
        with open(self.plan_path, "w") as handle:
            handle.write("{oops")
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--dry-run", "--plan", self.plan_path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)

    def test_dry_run_with_missing_plan_file_fails_loudly(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--dry-run", "--plan",
             os.path.join(self.tmp, "no-such-plan.json")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
class SecretGuardTest(unittest.TestCase):
    """DSP-028: secret-looking content is refused at parse time.

    The prompt ban (dispatch.md hard rule 2) tells Spark to
    refuse a goal carrying a secret; check_no_secrets is the
    machine enforcement, run on the goal text before the Spark
    call and on the plan text at parse time. A live Spark run
    over an adversarial goal (which needs real transport and
    the DSP-006 dry-run) is still owed, so these tests guard
    the refusal on literal goal and plan texts, not a Spark
    verdict. Every key below is a repeated-character fake.
    """

    # (label the error must name, snippet carrying the shape)
    SHAPES = (
        ("GitHub token", "ghp_" + "x" * 36),
        ("GitHub fine-grained token", "github_pat_" + "q" * 22),
        ("API key", "sk-" + "y" * 48),
        ("AWS access key id", "AKIA" + "Z" * 16),
        ("Bearer token", "Bearer " + "t" * 20),
        ("named credential assignment", "api_key=hunter2-fake"),
    )

    def test_fake_key_in_goal_text_is_refused(self):
        fake = "ghp_" + "x" * 36
        goal = ("Wire the deploy key " + fake +
                " into intel/ingest.py so the dashboard can read it.")
        with self.assertRaises(PlanError) as caught:
            check_no_secrets(goal)
        message = str(caught.exception)
        self.assertIn("secret warning", message)
        self.assertIn("GitHub token", message)
        self.assertNotIn(fake, message)

    def test_each_credential_shape_is_refused(self):
        for label, snippet in self.SHAPES:
            with self.subTest(label=label):
                with self.assertRaises(PlanError) as caught:
                    check_no_secrets("Do the thing with " + snippet)
                self.assertIn("secret warning", str(caught.exception))
                self.assertIn(label, str(caught.exception))
                self.assertNotIn(snippet, str(caught.exception))

    def test_secret_in_plan_spec_parses_but_guard_refuses(self):
        plan = _golden()
        plan["jobs"][0]["spec"] = ("Use the key sk-" + "y" * 48 +
                                   " to fetch the snapshot.")
        text = json.dumps(plan)
        # Shape-only parser: the plan is well-formed, so it parses.
        self.assertEqual(parse_plan(text)["jobs"][0]["key"], "base")
        # The guard is what refuses it, before anything is posted.
        with self.assertRaises(PlanError) as caught:
            check_no_secrets(text)
        self.assertIn("secret warning", str(caught.exception))
        self.assertIn("API key", str(caught.exception))

    def test_clean_text_passes_unchanged(self):
        text = json.dumps(_golden())
        self.assertEqual(check_no_secrets(text), text)

    def test_near_misses_pass(self):
        # A commit hash is plain hex, not a credential shape.
        self.assertEqual(
            check_no_secrets("Back out commit " + "a1b2c3d4" * 5 + "."),
            "Back out commit " + "a1b2c3d4" * 5 + ".")
        # The word "secret" with no assignment is not a credential.
        self.assertEqual(
            check_no_secrets("Keep the secret sauce out of scope."),
            "Keep the secret sauce out of scope.")
        # Naming a key field with no value assigned is not one either.
        self.assertEqual(
            check_no_secrets("Rotate the api_key after deploy."),
            "Rotate the api_key after deploy.")


class ApprovalGateTest(unittest.TestCase):
    def test_flag_approves(self):
        plan = parse_plan(json.dumps(_golden()))
        self.assertTrue(request_approval(plan, approve=True))

    def test_flag_approves_without_prompt(self):
        plan = parse_plan(json.dumps(_golden()))
        calls = []
        self.assertTrue(request_approval(
            plan, approve=True, confirm=calls.append))
        self.assertEqual(calls, [])

    def test_interactive_yes_variants_approve(self):
        plan = parse_plan(json.dumps(_golden()))
        for answer in ("y", "Y", "yes", "YES", "  y  ", "Yes"):
            with self.subTest(answer=answer):
                self.assertTrue(request_approval(
                    plan, confirm=lambda _prompt, a=answer: a))

    def test_interactive_other_answers_deny(self):
        plan = parse_plan(json.dumps(_golden()))
        for answer in ("n", "N", "no", "", "maybe", "ye", "yep"):
            with self.subTest(answer=answer):
                self.assertFalse(request_approval(
                    plan, confirm=lambda _prompt, a=answer: a))

    def test_prompt_names_the_job_count(self):
        plan = parse_plan(json.dumps(_golden()))
        seen = []
        request_approval(plan, confirm=lambda p: seen.append(p) or "n")
        self.assertEqual(len(seen), 1)
        self.assertIn("4 jobs", seen[0])
        self.assertEqual(seen[0], approval_prompt(plan))

    def test_eof_from_prompt_denies_instead_of_crashing(self):
        plan = parse_plan(json.dumps(_golden()))

        def _eof(_prompt):
            raise EOFError

        self.assertFalse(request_approval(plan, confirm=_eof))

    def test_no_prompt_and_no_flag_denies(self):
        plan = parse_plan(json.dumps(_golden()))
        self.assertFalse(request_approval(plan))
        self.assertFalse(request_approval(plan, approve=False,
                                          confirm=None))

    def test_gate_does_not_mutate_the_plan(self):
        plan = parse_plan(json.dumps(_golden()))
        before = json.dumps(plan, sort_keys=True)
        request_approval(plan, approve=True)
        request_approval(plan, confirm=lambda _prompt: "y")
        self.assertEqual(json.dumps(plan, sort_keys=True), before)

    def test_malformed_plan_rejected(self):
        with self.assertRaisesRegex(PlanError, "parsed plan dict"):
            request_approval({"jobs": "not-a-list"})
        with self.assertRaisesRegex(PlanError, "parsed plan dict"):
            approval_prompt("not-a-plan")

    def test_validated_plan_pipeline_shared_with_dry_run(self):
        plan, order, clamps = validated_plan(json.dumps(_golden()))
        self.assertEqual(order, ["base", "api", "panel", "docs"])
        self.assertEqual(clamps, [])
        self.assertEqual(dry_run_plan(json.dumps(_golden())),
                         render_plan_detail(plan, order, clamps))


class ApprovalCliTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        self.plan_path = os.path.join(self.tmp, "plan.json")
        with open(self.plan_path, "w") as handle:
            json.dump(_golden(), handle)

    def _jobs_list(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list"])
        return out

    def test_posting_without_approval_posts_nothing(self):
        self.run_cli(jobs.main,
                     ["post", "--title", "Existing", "--spec", "s"])
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("approval", err)
        self.assertEqual(self._jobs_list(), before)

    def test_posting_with_approve_posts_the_plan(self):
        # Gate passed, poster landed (DSP-008): the 4 golden
        # jobs post on top of the existing job, the CLI prints
        # the key -> id mapping, and nothing is claimed before
        # it exists.
        self.run_cli(jobs.main,
                     ["post", "--title", "Existing", "--spec", "s"])
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 0, err)
        self.assertIn("posted dispatch", out)
        for key in ("base", "api", "panel", "docs"):
            self.assertIn(f"  {key} -> ", out)
        after = self._jobs_list()
        self.assertNotEqual(after, before)
        self.assertEqual(len(after.splitlines()),
                         len(before.splitlines()) + 4)

    def test_cli_post_writes_spend_ledger_entry(self):
        # DSP-014 through the CLI posting path: the approved
        # post writes exactly one dispatch ledger entry naming
        # the posted dispatch id and its 4 jobs.
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 0, err)
        posted_id = None
        for line in out.splitlines():
            if line.startswith("posted dispatch "):
                posted_id = line[len("posted dispatch "):].rstrip(":")
        self.assertIsNotNone(posted_id)
        entries = istore.spend_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["lane_feature"], "dispatch")
        self.assertEqual(entries[0]["dispatch_id"], posted_id)
        self.assertEqual(entries[0]["jobs_posted"], 4)
        self.assertGreaterEqual(entries[0]["latency_ms"], 0)

    def test_crew_mode_without_secret_file_refuses(self):
        self.run_cli(jobs.main,
                     ["post", "--title", "Existing", "--spec", "s"])
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve", "--crew-mode"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("crew mode", err)
        self.assertEqual(self._jobs_list(), before)

    def test_signed_cli_posts_four_jobs_that_verify_ok(self):
        keyring = os.path.join(self.tmp, "keyring")
        with open(keyring, "w") as handle:
            handle.write("k1:test-crew-secret\n")
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve",
             "--secret-file", keyring])
        self.assertEqual(code, 0, err)
        self.assertIn("posted dispatch", out)
        _rc, jobs_out, _err = self.run_cli(jobs.main,
                                           ["list", "--json"])
        rows = json.loads(jobs_out)
        self.assertEqual(len(rows), 4)
        for row in rows:
            code, out, _err = self.run_cli(
                jobs.main, ["verify", row["id"],
                            "--secret-file", keyring])
            self.assertEqual(code, 0, out)
            self.assertEqual(out.strip(), "OK")

    def test_posting_without_plan_fails_loudly(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("--plan", err)

    def test_posting_with_invalid_plan_prints_no_plan(self):
        with open(self.plan_path, "w") as handle:
            handle.write("{oops")
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)

    def test_posting_with_missing_plan_file_fails_loudly(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", os.path.join(self.tmp, "no-such-plan.json"),
             "--approve"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)

    def test_posting_with_secret_plan_refused(self):
        plan = _golden()
        plan["jobs"][0]["spec"] = ("Use the key sk-" + "y" * 48 +
                                   " to fetch the snapshot.")
        with open(self.plan_path, "w") as handle:
            json.dump(plan, handle)
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("secret warning", err)
        self.assertIn("API key", err)
class PosterTest(RelayTestCase):
    """DSP-008: post_plan through jobs.py main() on the fake Redis.

    The default path posts for real (through jobs.main, against
    FakeUpstash, exactly as the CLI does); the injected-post_one
    tests pin the argv mapping and the failure contract without
    needing a queue. Every test runs on RelayTestCase so the
    dispatch record store is the fake, never a live bus.
    """

    def _validated(self):
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        return plan, order

    def _jobs_json(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        return json.loads(out)

    def test_posts_diamond_in_order_with_real_dep_ids(self):
        plan, order = self._validated()
        record = post_plan(plan, order=order)
        self.assertEqual(record["order"],
                         ["base", "api", "panel", "docs"])
        rows = self._jobs_json()
        self.assertEqual(len(rows), 4)
        mapping = {entry["key"]: entry["id"]
                   for entry in record["jobs"]}
        self.assertEqual(set(mapping.values()),
                         {row["id"] for row in rows})
        by_title = {row["title"]: row for row in rows}
        self.assertEqual(by_title["Do base"]["deps"], "")
        self.assertEqual(by_title["Do api"]["deps"], mapping["base"])
        self.assertEqual(by_title["Do panel"]["deps"], mapping["base"])
        self.assertEqual(by_title["Do docs"]["deps"],
                         mapping["api"] + "," + mapping["panel"])
        self.assertEqual(by_title["Do base"]["files"],
                         "intel/ingest.py")
        _rc, out, _err = self.run_cli(jobs.main,
                                       ["show", mapping["api"]])
        self.assertIn("Goal, context, files, steps, out of scope.",
                      out)
        self.assertIn("max_attempts: 3", out)

    def test_record_stored_and_retrievable(self):
        plan, order = self._validated()
        record = post_plan(plan, order=order,
                           dispatch_id="dsp-test-1")
        self.assertEqual(record["id"], "dsp-test-1")
        self.assertEqual(istore.get_dispatch("dsp-test-1"), record)
        self.assertIsNone(istore.get_dispatch("dsp-nope"))

    def test_default_record_id_uses_first_job_id(self):
        plan, order = self._validated()
        record = post_plan(plan, order=order)
        self.assertTrue(record["id"].startswith("dsp-"))
        self.assertTrue(record["id"].endswith(
            record["jobs"][0]["id"]))
        self.assertEqual(istore.get_dispatch(record["id"]), record)

    def test_spend_ledger_entry_per_posted_plan(self):
        # DSP-014: one ledger entry per posted plan, carrying
        # the dispatch id, the job count, and the posting
        # latency; posting makes no Spark call, so no token
        # counts and no cost, and the spend total is unchanged.
        plan, order = self._validated()
        ticks = iter([100.0, 100.25])
        record = post_plan(plan, order=order,
                           dispatch_id="dsp-ledger-1",
                           monotonic=lambda: next(ticks))
        self.assertEqual(record["latency_ms"], 250)
        self.assertEqual(istore.get_dispatch("dsp-ledger-1"),
                         record)
        entries = istore.spend_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["lane_feature"], "dispatch")
        self.assertEqual(entry["dispatch_id"], "dsp-ledger-1")
        self.assertEqual(entry["jobs_posted"], 4)
        self.assertEqual(entry["latency_ms"], 250)
        self.assertIsNone(entry["tokens_in"])
        self.assertIsNone(entry["tokens_out"])
        self.assertIsNone(entry["est_cost"])
        self.assertEqual(istore.spend_total(), 0.0)

    def test_ledger_write_failure_does_not_fail_post(self):
        # DSP-014: the ledger is observability only, so a failed
        # write is logged and the post still lands with its
        # record and latency intact.
        plan, order = self._validated()
        original = istore.record_spend

        def _boom(_entry):
            raise RuntimeError("ledger down")

        istore.record_spend = _boom
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                record = post_plan(plan, order=order,
                                   dispatch_id="dsp-ledger-2")
        finally:
            istore.record_spend = original
        self.assertEqual(record["id"], "dsp-ledger-2")
        self.assertIn("latency_ms", record)
        self.assertEqual(istore.get_dispatch("dsp-ledger-2"),
                         record)
        self.assertIn("spend ledger write failed", err.getvalue())
        self.assertEqual(istore.spend_entries(), [])

    def test_order_defaults_to_dep_graph(self):
        plan, _order = self._validated()
        record = post_plan(plan)
        self.assertEqual(record["order"],
                         ["base", "api", "panel", "docs"])

    def test_injected_poster_receives_rewritten_deps(self):
        plan, order = self._validated()
        seen = []

        def fake_post(argv):
            seen.append(argv)
            return f"job-{len(seen)}"

        record = post_plan(plan, order=order, post_one=fake_post)
        self.assertEqual([entry["id"] for entry in record["jobs"]],
                         ["job-1", "job-2", "job-3", "job-4"])
        self.assertIn("--deps=job-2,job-3", seen[3])
        self.assertIn("--files=intel/README.md", seen[3])
        self.assertIn("--max-attempts=3", seen[3])
        self.assertIn("--accept=contains: intel/README.md :: "
                      "snapshot", seen[3])
        self.assertIn("--title=Do docs", seen[3])

    def test_secret_file_passed_through(self):
        plan, order = self._validated()
        seen = []

        def fake_post(argv):
            seen.append(argv)
            return f"job-{len(seen)}"

        post_plan(plan, order=order, post_one=fake_post,
                  secret_file="/tmp/keyring")
        self.assertEqual(len(seen), 4)
        for argv in seen:
            self.assertIn("--secret-file=/tmp/keyring", argv)

    def test_partial_failure_stores_no_record_and_stops(self):
        plan, order = self._validated()
        calls = []

        def flaky(argv):
            calls.append(argv)
            return f"job-{len(calls)}" if len(calls) < 3 else None

        with self.assertRaises(PostError) as ctx:
            post_plan(plan, order=order, post_one=flaky)
        self.assertIn("'panel'", str(ctx.exception))
        self.assertIn("base -> job-1", str(ctx.exception))
        self.assertIn("no dispatch record stored", str(ctx.exception))
        self.assertEqual(len(calls), 3)
        self.assertEqual([k for k in self.fake.strings
                          if "intel:dispatch" in k], [])

    def test_order_missing_a_job_posts_nothing(self):
        plan, _order = self._validated()
        calls = []

        def counting(argv):
            calls.append(argv)
            return "job-1"

        with self.assertRaises(PlanError):
            post_plan(plan, order=["base", "api"],
                      post_one=counting)
        self.assertEqual(calls, [])

    def test_dep_not_yet_posted_raises_before_posting(self):
        plan, _order = self._validated()
        calls = []

        def counting(argv):
            calls.append(argv)
            return "job-1"

        with self.assertRaises(PostError):
            post_plan(plan, order=["api", "base", "panel", "docs"],
                      post_one=counting)
        self.assertEqual(calls, [])
        self.assertEqual([k for k in self.fake.strings
                          if "intel:dispatch" in k], [])


class SigningTest(RelayTestCase):
    """DSP-009: signed posts, crew-mode refusal, unsigned warning.

    The real-path tests post through jobs.main on FakeUpstash
    and verify through jobs.main verify, exactly as an
    operator would; the injected-poster tests pin the
    crew-mode refusal and the argv mapping without a queue.
    """

    def _validated(self):
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        return plan, order

    def _keyring(self, content="k1:test-crew-secret\n"):
        path = os.path.join(self.tmp, "keyring")
        with open(path, "w") as handle:
            handle.write(content)
        return path

    def _jobs_json(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        return json.loads(out)

    def test_signed_posts_verify_ok_via_jobs_verify(self):
        plan, order = self._validated()
        keyring = self._keyring()
        record = post_plan(plan, order=order, secret_file=keyring)
        self.assertTrue(record["signed"])
        self.assertEqual(len(record["jobs"]), 4)
        for entry in record["jobs"]:
            code, out, _err = self.run_cli(
                jobs.main, ["verify", entry["id"],
                            "--secret-file", keyring])
            self.assertEqual(code, 0, out)
            self.assertEqual(out.strip(), "OK")

    def test_crew_mode_with_keyring_passes_secret_file(self):
        plan, order = self._validated()
        seen = []

        def fake_post(argv):
            seen.append(argv)
            return f"job-{len(seen)}"

        record = post_plan(plan, order=order, post_one=fake_post,
                           secret_file="/tmp/keyring",
                           crew_mode=True)
        self.assertTrue(record["signed"])
        self.assertEqual(len(seen), 4)
        for argv in seen:
            self.assertIn("--secret-file=/tmp/keyring", argv)

    def test_crew_mode_without_keyring_posts_nothing(self):
        plan, order = self._validated()
        calls = []

        def counting(argv):
            calls.append(argv)
            return "job-1"

        with self.assertRaises(PostError) as ctx:
            post_plan(plan, order=order, post_one=counting,
                      crew_mode=True)
        self.assertIn("crew mode", str(ctx.exception))
        self.assertIn("nothing posted", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertEqual(self._jobs_json(), [])
        self.assertEqual([k for k in self.fake.strings
                          if "intel:dispatch" in k], [])

    def test_unsigned_post_warns_and_records_unsigned(self):
        plan, order = self._validated()
        keyring = self._keyring()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            record = post_plan(plan, order=order)
        self.assertIn("WARNING", err.getvalue())
        self.assertIn("unsigned", err.getvalue())
        self.assertFalse(record["signed"])
        for entry in record["jobs"]:
            code, out, _err = self.run_cli(
                jobs.main, ["verify", entry["id"],
                            "--secret-file", keyring])
            self.assertEqual(code, 1)
            self.assertEqual(out.strip(), "UNSIGNED")

    def test_bad_keyring_fails_at_first_job_with_no_record(self):
        plan, order = self._validated()
        keyring = self._keyring(content="")
        with self.assertRaises(PostError) as ctx:
            post_plan(plan, order=order, secret_file=keyring)
        self.assertIn("'base'", str(ctx.exception))
        self.assertIn("no dispatch record stored", str(ctx.exception))
        self.assertEqual([k for k in self.fake.strings
                          if "intel:dispatch" in k], [])
        # Pre-existing jobs.py shape, not a poster bug: the job
        # hash is written before the signing block, so the
        # failed first post leaves one unsigned orphan in the
        # queue. The poster never learns its id (no JOB line),
        # so no later job posts and no record is stored.
        rows = self._jobs_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Do base")
        code, out, _err = self.run_cli(
            jobs.main, ["verify", rows[0]["id"],
                        "--secret-file", self._keyring()])
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), "UNSIGNED")


def _load_golden_sections():
    """Parse intel/evals/dispatch_golden.md into G-sections.

    Returns a list of (goal_id, section_text) in file order. The
    DSP-022 test reads the doc itself, so a plan and its stated
    shape can never drift apart silently: the test asserts the
    plan against the shape the same section states.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "intel", "evals", "dispatch_golden.md")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    matches = list(re.finditer(r"^## (G\d+) — .*$", text, re.M))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) \
            else len(text)
        sections.append((match.group(1), text[match.start():end]))
    return sections


class GoldenGoalsTest(unittest.TestCase):
    def test_twelve_golden_goals(self):
        sections = _load_golden_sections()
        self.assertEqual([goal for goal, _ in sections],
                         [f"G{n}" for n in range(1, 13)])

    def test_each_golden_plan_dry_runs_inside_its_shape(self):
        for goal_id, section in _load_golden_sections():
            with self.subTest(goal=goal_id):
                self.assertIn("Goal:", section)
                blocks = re.findall(r"```json\n(.*?)```", section,
                                    re.S)
                self.assertEqual(len(blocks), 1,
                                 "one JSON plan per golden goal")
                count = re.search(r"Job count: (\d+)-(\d+)", section)
                self.assertIsNotNone(count, "job count range stated")
                low, high = int(count.group(1)), int(count.group(2))
                files_line = re.search(r"Must-own files: (.+)", section)
                self.assertIsNotNone(files_line, "must-own files stated")
                must_own = [f.strip() for f in
                            files_line.group(1).split(",")]
                deps_line = re.search(r"Must-have deps: (.+)", section)
                self.assertIsNotNone(deps_line, "must-have deps stated")
                deps_text = deps_line.group(1).strip()
                must_deps = []
                if deps_text != "none":
                    for pair in deps_text.split(", "):
                        src, _, dst = pair.partition(" -> ")
                        must_deps.append((src.strip(), dst.strip()))
                order_line = re.search(r"Dry-run posting order: (.+)",
                                        section)
                self.assertIsNotNone(order_line, "posting order stated")
                stated_order = [k.strip() for k in
                                order_line.group(1).split(" -> ")]
                # The dry-run is the whole gate chain: parse,
                # overlap, dep graph, budget clamp. It raises on
                # any failure, so reaching the asserts below is
                # itself the pass for the gates.
                dry_run_plan(blocks[0])
                plan = parse_plan(blocks[0])
                self.assertTrue(low <= len(plan["jobs"]) <= high)
                owned = set()
                for job in plan["jobs"]:
                    owned.update(job["files"])
                for path in must_own:
                    self.assertIn(path, owned)
                edges = set()
                for job in plan["jobs"]:
                    for dep in job["deps"]:
                        edges.add((dep, job["key"]))
                for edge in must_deps:
                    self.assertIn(edge, edges)
                self.assertEqual(check_dep_graph(plan), stated_order)


class SpecStandardTest(unittest.TestCase):
    """DSP-026: every generated spec carries the five parts.

    The standard lives in intel/prompts/dispatch.md; the scorer
    is intel/dispatch.py score_spec_parts. The golden-run score
    reads the DSP-022 doc itself, so the standard, the scorer,
    and the plans cannot drift apart silently. These are
    hand-authored plans, NOT Spark output: no Spark call runs
    here, and nothing is posted, claimed, or announced.
    """

    def test_prompt_defines_five_parts_in_order(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "intel", "prompts", "dispatch.md")
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        section = text.split("## Spec-writing standard (DSP-026)")[1]
        section = section.split("## Hard rules")[0]
        labels = ["Goal:", "Context:", "Files:", "Steps:",
                  "Out of scope:"]
        positions = [section.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions),
                         "five parts in standard order")

    def test_all_golden_specs_pass_scorer(self):
        total = 0
        for goal_id, section in _load_golden_sections():
            blocks = re.findall(r"```json\n(.*?)```", section, re.S)
            self.assertEqual(len(blocks), 1)
            plan = parse_plan(blocks[0])
            scores = score_plan_specs(plan)
            for job, score in zip(plan["jobs"], scores):
                with self.subTest(goal=goal_id, job=job["key"]):
                    self.assertEqual(score["key"], job["key"])
                    self.assertEqual(score["missing"], [])
                    self.assertEqual(score["empty"], [])
                    self.assertTrue(score["files_part_names_owned"])
                    self.assertTrue(score["passes"])
                total += 1
        self.assertEqual(total, 41, "12 golden plans, 41 jobs total")

    def test_missing_part_fails(self):
        spec = ("Goal: add the line. Context: the brief template. "
                "Files: intel/brief.py. Steps: add it, run tests.")
        score = score_spec_parts(spec, files=["intel/brief.py"])
        self.assertEqual(score["missing"], ["out of scope"])
        self.assertFalse(score["passes"])

    def test_out_of_order_part_fails(self):
        spec = ("Steps: add the line. Goal: add the line. "
                "Context: the brief template. Files: intel/brief.py. "
                "Out of scope: new sections.")
        score = score_spec_parts(spec, files=["intel/brief.py"])
        self.assertFalse(score["passes"])
        self.assertIn("steps", score["missing"])

    def test_empty_part_fails(self):
        spec = ("Goal: add the line. Context: . Files: intel/brief.py. "
                "Steps: add it. Out of scope: new sections.")
        score = score_spec_parts(spec, files=["intel/brief.py"])
        self.assertEqual(score["empty"], ["context"])
        self.assertFalse(score["passes"])

    def test_title_only_spec_fails(self):
        score = score_spec_parts("Add uptime line to morning brief.",
                                 files=["intel/brief.py"])
        self.assertEqual(score["missing"],
                         ["goal", "context", "files", "steps",
                          "out of scope"])
        self.assertFalse(score["passes"])

    def test_files_part_must_name_an_owned_file(self):
        spec = ("Goal: add the line. Context: the brief template. "
                "Files: intel/other.py. Steps: add it. "
                "Out of scope: new sections.")
        score = score_spec_parts(spec, files=["intel/brief.py"])
        self.assertFalse(score["files_part_names_owned"])
        self.assertFalse(score["passes"])

    def test_scorer_is_not_a_parser_gate(self):
        # A short spec still parses (shape-only parser); only the
        # scorer fails it. This pins the DSP-026 design decision
        # so a later gate change cannot silently break guard
        # fixtures that use short specs on purpose.
        plan = parse_plan(json.dumps({
            "summary": "Do one thing.",
            "jobs": [_job("one", spec="Add the line.")]}))
        self.assertEqual(plan["jobs"][0]["spec"], "Add the line.")
        self.assertFalse(score_plan_specs(plan)[0]["passes"])


class AcceptanceStandardTest(unittest.TestCase):
    """DSP-027: every job carries a machine-checkable accept line.

    The standard lives in intel/prompts/dispatch.md; the scorer
    is intel/dispatch.py score_accept_lines. The golden-run score
    reads the DSP-022 doc itself, so the standard, the scorer,
    and the plans cannot drift apart silently. These are
    hand-authored plans, NOT Spark output: no Spark call runs
    here, and nothing is posted, claimed, or announced.
    """

    def test_prompt_defines_acceptance_standard(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "intel", "prompts", "dispatch.md")
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        section = text.split(
            "## Acceptance-line standard (DSP-027)")[1]
        section = section.split("## Hard rules")[0]
        for phrase in ("at least one", "file-exists", "tests-pass",
                       "command-ok", "contains"):
            self.assertIn(phrase, section)

    def test_all_golden_jobs_pass_scorer(self):
        total = 0
        for goal_id, section in _load_golden_sections():
            blocks = re.findall(r"```json\n(.*?)```", section, re.S)
            self.assertEqual(len(blocks), 1)
            plan = parse_plan(blocks[0])
            scores = score_plan_accepts(plan)
            for job, score in zip(plan["jobs"], scores):
                with self.subTest(goal=goal_id, job=job["key"]):
                    self.assertEqual(score["key"], job["key"])
                    self.assertGreaterEqual(score["checks"], 1)
                    self.assertEqual(score["unowned"], [])
                    self.assertEqual(score["bad_lines"], [])
                    self.assertTrue(score["passes"])
                total += 1
        self.assertEqual(total, 41, "12 golden plans, 41 jobs total")

    def test_tests_pass_target_need_not_be_owned(self):
        # G1's only job owns intel/brief.py but its tests-pass
        # line names tests.test_intel_brief, which it does not
        # own: the test module is the check target, not an owned
        # file, so the scorer passes it anyway.
        goal_id, section = _load_golden_sections()[0]
        self.assertEqual(goal_id, "G1")
        block = re.findall(r"```json\n(.*?)```", section, re.S)[0]
        plan = parse_plan(block)
        job = plan["jobs"][0]
        self.assertNotIn("tests/test_intel_brief.py", job["files"])
        score = score_accept_lines(job["accept"], files=job["files"])
        self.assertTrue(score["passes"])

    def test_empty_accept_fails(self):
        score = score_accept_lines([], files=["intel/brief.py"])
        self.assertEqual(score["checks"], 0)
        self.assertFalse(score["passes"])

    def test_unparseable_line_fails(self):
        score = score_accept_lines(["works correctly"],
                                   files=["intel/brief.py"])
        self.assertEqual(score["bad_lines"], ["works correctly"])
        self.assertFalse(score["passes"])

    def test_file_exists_naming_unowned_file_fails(self):
        score = score_accept_lines(["file-exists: intel/other.py"],
                                   files=["intel/brief.py"])
        self.assertEqual(score["unowned"], ["intel/other.py"])
        self.assertFalse(score["passes"])

    def test_contains_naming_unowned_file_fails(self):
        score = score_accept_lines(
            ["contains: intel/other.py :: TEMPLATE"],
            files=["intel/brief.py"])
        self.assertEqual(score["unowned"], ["intel/other.py"])
        self.assertFalse(score["passes"])

    def test_tests_pass_naming_no_tests_module_fails(self):
        score = score_accept_lines(["tests-pass: intel.ingest"],
                                   files=["intel/ingest.py"])
        self.assertFalse(score["passes"])

    def test_command_ok_mentioning_no_owned_file_fails(self):
        score = score_accept_lines(
            ["command-ok: python3 -m py_compile intel/other.py"],
            files=["intel/brief.py"])
        self.assertEqual(score["unowned"],
                         ["python3 -m py_compile intel/other.py"])
        self.assertFalse(score["passes"])

    def test_command_ok_mentioning_owned_file_passes(self):
        score = score_accept_lines(
            ["command-ok: python3 -m py_compile intel/brief.py"],
            files=["intel/brief.py"])
        self.assertTrue(score["passes"])

    def test_scorer_is_not_a_parser_gate_for_ownership(self):
        # A plan naming an unowned file still parses (shape-only
        # parser); only the scorer fails it. This pins the
        # DSP-027 design decision so a later gate change cannot
        # silently break guard fixtures that use unowned paths
        # on purpose.
        plan = parse_plan(json.dumps({
            "summary": "Do one thing.",
            "jobs": [_job("one", files=["intel/brief.py"],
                           accept=["file-exists: intel/other.py"])]}))
        self.assertFalse(score_plan_accepts(plan)[0]["passes"])


def _load_adversarial_sections():
    """Parse intel/evals/dispatch_adversarial.md into A-sections.

    Returns a list of (goal_id, section_text) in file order. The
    DSP-023 test reads the doc itself, so a case and its stated
    guard can never drift apart silently: the test asserts each
    case against the guard the same section states.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "intel", "evals", "dispatch_adversarial.md")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    matches = list(re.finditer(r"^## (A\d+) — .*$", text, re.M))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) \
            else len(text)
        sections.append((match.group(1), text[match.start():end]))
    return sections


def _adversarial_block(section):
    blocks = re.findall(r"```json\n(.*?)```", section, re.S)
    assert len(blocks) == 1, "one JSON plan per adversarial case"
    return blocks[0]


class AdversarialGoalsTest(unittest.TestCase):
    """DSP-023: each adversarial goal triggers its documented guard.

    The cases are literal plans in intel/evals/dispatch_adversarial.md,
    NOT Spark output: no Spark call runs here, and no case posts,
    claims, or announces anything. The validated pipeline is pure
    functions on text, so a refused plan posts nothing by
    construction; the approval case asserts the denial directly.
    """

    def test_six_adversarial_goals(self):
        sections = _load_adversarial_sections()
        self.assertEqual([goal for goal, _ in sections],
                         [f"A{n}" for n in range(1, 7)])

    def test_contradiction_guard_fires_not_overlap(self):
        _, section = _load_adversarial_sections()[0]
        block = _adversarial_block(section)
        plan = parse_plan(block)
        # Isolation: shared-sequential lets this plan pass overlap,
        # so the contradiction guard must be the one that fires.
        self.assertIs(check_file_overlap(plan), plan)
        with self.assertRaises(PlanError) as caught:
            validated_plan(block)
        message = str(caught.exception)
        self.assertIn("contradicts", message)
        self.assertIn("intel/notes/scratch.md", message)
        self.assertIn("create-note", message)
        self.assertIn("delete-note", message)
        with self.assertRaises(PlanError):
            dry_run_plan(block)

    def test_overlap_guard_fires_on_collision(self):
        _, section = _load_adversarial_sections()[1]
        with self.assertRaises(PlanError) as caught:
            validated_plan(_adversarial_block(section))
        message = str(caught.exception)
        self.assertIn("overlaps", message)
        self.assertIn("intel/brief.py", message)

    def test_dep_graph_guard_fires_on_missing_key(self):
        _, section = _load_adversarial_sections()[2]
        with self.assertRaises(PlanError) as caught:
            validated_plan(_adversarial_block(section))
        message = str(caught.exception)
        self.assertIn("ghost", message)
        self.assertIn("not a job key", message)

    def test_secret_guard_fires_on_goal_and_plan(self):
        _, section = _load_adversarial_sections()[3]
        goal = re.search(r"^Goal: (.*)$", section, re.M).group(1)
        fake = re.search(r"ghp_\S+", goal).group(0)
        for text in (goal, _adversarial_block(section)):
            with self.assertRaises(PlanError) as caught:
                check_no_secrets(text)
            message = str(caught.exception)
            self.assertIn("secret warning", message)
            self.assertIn("GitHub token", message)
            self.assertNotIn(fake, message)

    def test_huge_scope_size_guard_fires_and_approval_denies(self):
        _, section = _load_adversarial_sections()[4]
        block = _adversarial_block(section)
        plan = parse_plan(block)
        self.assertEqual(len(plan["jobs"]), 13)
        # DSP-024 re-point: DSP-013 has landed, so the guard
        # that fires is the size guardrail, surfaced in the
        # dry-run detail. No parser guard fires on size, by
        # design: over-12-job plans still parse (DSP-002 pins
        # that boundary), and the approval denial still stands
        # behind the size guard.
        detail = dry_run_plan(block)
        self.assertIsInstance(detail, str)
        self.assertIn("plan size guardrail", detail)
        self.assertIn("13 jobs", detail)
        self.assertIn("12-job", detail)
        self.assertIn("second confirmation", detail)
        self.assertIn("Split suggestion", detail)
        self.assertFalse(request_approval(plan))
        self.assertIn("DSP-013", section)

    def test_empty_goal_has_no_plan(self):
        _, section = _load_adversarial_sections()[5]
        self.assertEqual(re.findall(r"```json\n(.*?)```", section,
                                    re.S), [])
        self.assertIn("elicitation", section)
        with self.assertRaises(PlanError) as caught:
            parse_plan("")
        self.assertIn("empty input", str(caught.exception))
        response = "\n".join(
            f"{i + 1}. {q}"
            for i, q in enumerate(GoalElicitationTest.QUESTIONS))
        with self.assertRaises(PlanError):
            parse_plan(response)


class DispatchPromptV2Test(unittest.TestCase):
    """DSP-024: dispatch prompt v2, tuned from eval failures only.

    v2 (intel/prompts/dispatch_v2.md) must exist, must carry
    the two eval-driven changes, and v1 (intel/prompts/
    dispatch.md) must still be the v1 text, kept for diffing:
    the new rules live in v2 only. This test reads the files,
    it does not run Spark: a Spark-generated plan scored
    against the golden shapes or the adversarial guards is
    still owed when real Spark transport lands.
    """

    def _prompt(self, name):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "intel", "prompts", name)
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()

    def test_v2_exists_and_names_its_eval_failures(self):
        v2 = self._prompt("dispatch_v2.md")
        self.assertIn("DSP-024", v2)
        self.assertIn("A5", v2)
        self.assertIn("A1", v2)

    def test_v2_carries_the_size_rule(self):
        v2 = self._prompt("dispatch_v2.md")
        self.assertIn("at most 40 distinct", v2)
        self.assertIn("Never emit more than 12 jobs", v2)
        self.assertIn("split it into smaller plans", v2)

    def test_v2_carries_the_contradiction_rule(self):
        v2 = self._prompt("dispatch_v2.md")
        self.assertIn("No contradictory plan, ever", v2)
        self.assertIn("creates a file and another job deletes", v2)
        self.assertIn("shared-sequential", v2)

    def test_v1_kept_for_diffing(self):
        v1 = self._prompt("dispatch.md")
        self.assertIn("Dispatch prompt v1", v1)
        self.assertNotIn("No contradictory plan, ever", v1)
        self.assertNotIn("Never emit more than 12 jobs", v1)
        self.assertNotIn("dispatch_v2", v1)


class ContradictionGuardTest(unittest.TestCase):
    """DSP-023: check_no_contradiction, direct unit cases.

    The guard is narrow by design: only literal file-level
    wording ("create file <path>" vs "delete file <path>" /
    "remove file <path>") on a file the job itself owns counts.
    Content edits and single-direction plans pass untouched.
    """

    def _plan(self, jobs):
        return {"summary": "Guard test plan.", "jobs": jobs}

    def test_self_contradiction_fires(self):
        plan = self._plan([_job(
            "both", files=("intel/x.py",),
            spec="Steps: create file intel/x.py, then delete file "
                 "intel/x.py.")])
        with self.assertRaises(PlanError) as caught:
            check_no_contradiction(plan)
        self.assertIn("contradicts itself", str(caught.exception))

    def test_content_edits_are_not_contradictions(self):
        plan = self._plan([_job(
            "edit", files=("intel/brief.py",),
            spec="Add a line to intel/brief.py and remove the old "
                 "helper from intel/brief.py.")])
        self.assertIs(check_no_contradiction(plan), plan)

    def test_single_direction_and_other_files_pass(self):
        plan = self._plan([
            _job("make", files=("intel/a.py",),
                 spec="Steps: create file intel/a.py."),
            _job("drop", files=("intel/b.py",),
                 spec="Steps: delete file intel/b.py."),
        ])
        self.assertIs(check_no_contradiction(plan), plan)

    def test_unowned_path_mention_does_not_fire(self):
        plan = self._plan([_job(
            "mention", files=("intel/a.py",),
            spec="Steps: create file intel/a.py. Note: delete file "
                 "intel/b.py is out of scope for this job.")])
        self.assertIs(check_no_contradiction(plan), plan)


def _big_plan(njobs):
    jobs = [_job(f"job-{i}", files=(f"job{i}.py",),
                 accept=(f"file-exists: job{i}.py",))
            for i in range(1, njobs + 1)]
    return {"summary": "Big plan.", "jobs": jobs}


def _wide_plan(nfiles):
    files = tuple(f"wide{i}.py" for i in range(nfiles))
    return {"summary": "Wide plan.",
            "jobs": [_job("wide", files=files,
                          accept=("file-exists: wide0.py",))]}


def _answers(*answers):
    state = iter(answers)

    def confirm(_prompt):
        value = next(state)
        if isinstance(value, Exception):
            raise value
        return value

    return confirm


class PlanSizeGuardTest(unittest.TestCase):
    """DSP-013: plan-size guardrail warnings and second approval."""

    def test_boundary_plans_trigger_nothing(self):
        self.assertEqual(plan_size_warnings(_big_plan(12)), [])
        self.assertEqual(plan_size_warnings(_wide_plan(40)), [])
        self.assertEqual(plan_size_warnings(_golden()), [])

    def test_thirteen_jobs_warns_with_count_limit_and_split(self):
        warnings = plan_size_warnings(_big_plan(13))
        self.assertEqual(len(warnings), 1)
        self.assertIn("13 jobs", warnings[0])
        self.assertIn("12-job", warnings[0])
        self.assertIn("second confirmation", warnings[0])
        self.assertIn("Split suggestion", warnings[0])
        self.assertIn("at most 12 jobs", warnings[0])

    def test_forty_one_files_warns_with_count_limit_and_split(self):
        warnings = plan_size_warnings(_wide_plan(41))
        self.assertEqual(len(warnings), 1)
        self.assertIn("41 files", warnings[0])
        self.assertIn("40-file", warnings[0])
        self.assertIn("second confirmation", warnings[0])
        self.assertIn("Split suggestion", warnings[0])
        self.assertIn("at most 40 files", warnings[0])

    def test_both_limits_breached_warns_twice(self):
        jobs = []
        for i in range(1, 14):
            files = tuple(f"job{i}-{k}.py" for k in range(4))
            jobs.append(_job(f"job-{i}", files=files,
                             accept=(f"file-exists: job{i}-0.py",)))
        warnings = plan_size_warnings({"summary": "Huge.",
                                       "jobs": jobs})
        self.assertEqual(len(warnings), 2)
        self.assertIn("13 jobs", warnings[0])
        self.assertIn("52 files", warnings[1])

    def test_distinct_files_counted_once(self):
        plan = _wide_plan(40)
        plan["jobs"].append(_job("wide-again",
                                 files=("wide0.py",),
                                 accept=("file-exists: wide0.py",)))
        self.assertEqual(plan_size_warnings(plan), [])

    def test_dry_run_shows_guard_and_small_plan_shows_none(self):
        detail = dry_run_plan(json.dumps(_big_plan(13)))
        self.assertIn("plan size guardrail", detail)
        self.assertIn("13 jobs", detail)
        self.assertIn("Split suggestion", detail)
        self.assertNotIn("guardrail",
                         dry_run_plan(json.dumps(_golden())))

    def test_malformed_shape_raises(self):
        with self.assertRaises(PlanError):
            plan_size_warnings({"jobs": "not-a-list"})
        with self.assertRaises(PlanError):
            large_plan_prompt({"jobs": "not-a-list"})

    def test_large_plan_prompt_names_counts_and_second(self):
        prompt = large_plan_prompt(_big_plan(13))
        self.assertIn("13 jobs", prompt)
        self.assertIn("13 files", prompt)
        self.assertIn("second confirmation", prompt)

    def test_first_approval_alone_denies_large_plan(self):
        plan = _big_plan(13)
        self.assertFalse(request_approval(plan, approve=True))
        self.assertFalse(request_approval(plan))

    def test_second_flag_approves_large_plan(self):
        plan = _big_plan(13)
        self.assertTrue(request_approval(plan, approve=True,
                                        confirm_large=True))

    def test_two_prompt_yeses_approve_large_plan(self):
        plan = _big_plan(13)
        self.assertTrue(request_approval(
            plan, confirm=_answers("y", "yes")))

    def test_second_no_or_eof_denies_large_plan(self):
        plan = _big_plan(13)
        self.assertFalse(request_approval(
            plan, confirm=_answers("y", "n")))
        self.assertFalse(request_approval(
            plan, confirm=_answers("y", EOFError())))
        self.assertFalse(request_approval(
            plan, confirm=_answers("n", "y")))

    def test_small_plan_approval_unchanged(self):
        plan = _golden()
        self.assertTrue(request_approval(plan, approve=True))
        self.assertTrue(request_approval(
            plan, confirm=_answers("y")))
        self.assertFalse(request_approval(plan))


class SizeGuardPosterTest(RelayTestCase):
    """DSP-013: the poster refuses a large plan without a second
    confirmation, before any job is posted."""

    def test_large_plan_refuses_before_any_post(self):
        plan, order, _clamps = validated_plan(
            json.dumps(_big_plan(13)))
        seen = []

        def fake_post(argv):
            seen.append(argv)
            return "99"

        with self.assertRaisesRegex(PostError,
                                    "second confirmation"):
            post_plan(plan, order=order, post_one=fake_post)
        self.assertEqual(seen, [])
        self.assertIsNone(istore.get_dispatch("dsp-nope"))

    def test_large_plan_posts_with_confirm_large(self):
        plan, order, _clamps = validated_plan(
            json.dumps(_big_plan(13)))
        counter = [0]

        def fake_post(argv):
            counter[0] += 1
            return str(counter[0])

        record = post_plan(plan, order=order, post_one=fake_post,
                           dispatch_id="dsp-big-1",
                           confirm_large=True)
        self.assertEqual(record["id"], "dsp-big-1")
        self.assertEqual(len(record["jobs"]), 13)
        self.assertEqual(istore.get_dispatch("dsp-big-1"), record)


class SizeGuardCliTest(RelayTestCase):
    """DSP-013 at the CLI: dry-run shows the guard, posting a
    large plan needs --confirm-large on top of --approve."""

    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        self.plan_path = os.path.join(self.tmp, "plan.json")
        with open(self.plan_path, "w") as handle:
            json.dump(_big_plan(13), handle)

    def _jobs_list(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list"])
        return out

    def test_dry_run_shows_guard_and_posts_nothing(self):
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Big goal",
             "--dry-run", "--plan", self.plan_path])
        self.assertEqual(code, 0, err)
        self.assertIn("plan size guardrail", out)
        self.assertIn("13 jobs", out)
        self.assertIn("second confirmation", out)
        self.assertIn("dry run: nothing posted", out)
        self.assertEqual(self._jobs_list(), before)

    def test_approve_without_confirm_large_posts_nothing(self):
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Big goal",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("second confirmation", err)
        self.assertEqual(self._jobs_list(), before)

    def test_approve_with_confirm_large_posts_thirteen(self):
        before = self._jobs_list()
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Big goal",
             "--plan", self.plan_path, "--approve",
             "--confirm-large"])
        self.assertEqual(code, 0, err)
        self.assertIn("posted dispatch", out)
        after = self._jobs_list()
        self.assertEqual(len(after.splitlines()),
                         len(before.splitlines()) + 13)


class UndoTest(RelayTestCase):
    """DSP-011: undo_dispatch cancels a plan's open jobs, leaves
    claimed and finished jobs untouched, and reports every job.

    The default path undoes for real (through jobs.main cancel
    on FakeUpstash, exactly as the CLI does); the injected
    cancel_one test pins the refused-cancel classification
    without needing a queue race.
    """

    def _posted(self):
        plan, order = self._validated()
        record = post_plan(plan, order=order,
                           dispatch_id="dsp-undo-1")
        return record

    def _validated(self):
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        return plan, order

    def _jobs_json(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        return json.loads(out)

    def test_undo_cancels_all_open_jobs(self):
        record = self._posted()
        report = undo_dispatch("dsp-undo-1")
        self.assertEqual(report["id"], "dsp-undo-1")
        self.assertEqual({e["key"] for e in report["cancelled"]},
                         {"base", "api", "panel", "docs"})
        self.assertEqual(report["untouched_claimed"], [])
        self.assertEqual(report["untouched_other"], [])
        self.assertEqual(report["missing"], [])
        rows = self._jobs_json()
        self.assertTrue(all(r["status"] == "cancelled"
                            for r in rows))
        self.assertEqual(len(rows), 4)
        stored = istore.get_dispatch("dsp-undo-1")
        self.assertEqual(stored["undo"], report)
        self.assertTrue(stored["undone_at"])

    def test_undo_leaves_claimed_job_untouched(self):
        record = self._posted()
        mapping = {e["key"]: e["id"] for e in record["jobs"]}
        rc, _out, err = self.run_cli(jobs.main,
                                     ["claim", mapping["api"]])
        self.assertEqual(rc, 0, err)
        report = undo_dispatch("dsp-undo-1")
        self.assertEqual({e["key"] for e in report["cancelled"]},
                         {"base", "panel", "docs"})
        self.assertEqual(len(report["untouched_claimed"]), 1)
        claimed = report["untouched_claimed"][0]
        self.assertEqual(claimed["key"], "api")
        self.assertEqual(claimed["claim"], "tester")
        h, _ = jobs.job_get(mapping["api"])
        self.assertEqual(h["status"], "claimed")

    def test_undo_leaves_done_job_untouched(self):
        record = self._posted()
        mapping = {e["key"]: e["id"] for e in record["jobs"]}
        self.run_cli(jobs.main, ["claim", mapping["base"]])
        rc, _out, err = self.run_cli(
            jobs.main, ["done", mapping["base"], "--commit", "abc"])
        self.assertEqual(rc, 0, err)
        report = undo_dispatch("dsp-undo-1")
        done = [e for e in report["untouched_other"]
                if e["key"] == "base"]
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]["status"], "done")
        self.assertEqual(len(report["cancelled"]), 3)

    def test_undo_reports_missing_job(self):
        istore.put_dispatch("dsp-ghost", {
            "id": "dsp-ghost", "summary": "", "room": "main",
            "created_at": 0, "order": ["x"], "signed": False,
            "jobs": [{"key": "x", "id": "9999", "title": "Ghost",
                      "files": [], "deps": [], "max_attempts": 3}]})
        report = undo_dispatch("dsp-ghost")
        self.assertEqual(len(report["missing"]), 1)
        self.assertEqual(report["missing"][0]["id"], "9999")
        self.assertEqual(report["cancelled"], [])

    def test_undo_unknown_dispatch_raises_and_touches_nothing(self):
        self._posted()
        before = self._jobs_json()
        with self.assertRaisesRegex(UndoError, "no dispatch record"):
            undo_dispatch("dsp-nope")
        self.assertEqual(self._jobs_json(), before)

    def test_second_undo_cancels_nothing_new(self):
        self._posted()
        undo_dispatch("dsp-undo-1")
        report = undo_dispatch("dsp-undo-1")
        self.assertEqual(report["cancelled"], [])
        self.assertEqual({e["key"]
                          for e in report["untouched_other"]},
                         {"base", "api", "panel", "docs"})
        self.assertTrue(all(e["status"] == "cancelled"
                            for e in report["untouched_other"]))

    def test_refused_cancel_is_classified_not_fatal(self):
        self._posted()
        seen = []

        def refuse_all(argv):
            seen.append(argv)
            return 2

        report = undo_dispatch("dsp-undo-1", cancel_one=refuse_all)
        self.assertEqual(len(seen), 4)
        self.assertEqual(report["cancelled"], [])
        self.assertEqual({e["key"]
                          for e in report["untouched_other"]},
                         {"base", "api", "panel", "docs"})
        self.assertTrue(all(e["status"] == "open"
                            for e in report["untouched_other"]))


class UndoCliTest(RelayTestCase):
    """DSP-011 at the CLI: --undo prints the report, unknown id
    exits 2 with nothing touched."""

    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        self.record = post_plan(plan, order=order,
                                dispatch_id="dsp-cli-undo")

    def test_cli_undo_prints_report(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--undo", "dsp-cli-undo"])
        self.assertEqual(code, 0, err)
        self.assertIn("undone dispatch dsp-cli-undo", out)
        for key in ("base", "api", "panel", "docs"):
            self.assertIn(f"cancelled {key} -> ", out)

    def test_cli_undo_unknown_id_exits_2(self):
        before = self.run_cli(jobs.main, ["list", "--json"])[1]
        code, out, err = self.run_cli(
            self.cli.main, ["dispatch", "--undo", "dsp-nope"])
        self.assertEqual(code, 2)
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("no dispatch record", err)
        after = self.run_cli(jobs.main, ["list", "--json"])[1]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
