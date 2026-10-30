"""DSP-017: Spark dispatch failure fallback.

plan_from_spark retries one malformed JSON answer; a second
malformed answer in a row yields one FALLBACK job carrying the
raw goal as its spec, with a loud warning, and nothing
malformed is posted. A structured plan that fails a guard is
refused on the first attempt (no retry, no fallback).
INT-008 extends the fallback to a Spark transport error:
when complete raises, the same FALLBACK job is returned
with an endpoint-down warning, because the drill requires
dispatch to fall back when Spark is down. All Spark answers
here are injected callables, never a live call and never a
fake transport in the product: the product code takes the
callable from the caller.
"""

import contextlib
import io
import json
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import (  # noqa: E402
    DEFAULT_MAX_ATTEMPTS, FALLBACK_JOB_KEY, PlanError,
    fallback_plan, plan_from_spark, post_plan)
from helpers import RelayTestCase  # noqa: E402


def _valid_plan_json():
    return json.dumps({
        "summary": "Do the one job.",
        "jobs": [{
            "key": "do-it",
            "title": "Do it",
            "spec": "Goal, context, files, steps, out of scope.",
            "files": ["intel/ingest.py"],
            "deps": [],
            "max_attempts": 3,
            "accept": ["file-exists: intel/ingest.py"],
        }],
    })


class _ScriptedComplete:
    """A Spark callable returning scripted answers, counting calls."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, goal):
        self.calls += 1
        index = min(self.calls - 1, len(self.answers) - 1)
        answer = self.answers[index]
        if isinstance(answer, BaseException):
            raise answer
        return answer


class PlanFromSparkTest(unittest.TestCase):

    def test_malformed_twice_falls_back_with_raw_goal(self):
        goal = "Wire the snapshot panel\nsecond line of the goal"
        complete = _ScriptedComplete(["{not json", "still not ["])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            result = plan_from_spark(goal, complete)
        self.assertEqual(complete.calls, 2)
        self.assertTrue(result["fallback"])
        self.assertEqual(result["order"], [FALLBACK_JOB_KEY])
        self.assertEqual(result["clamps"], [])
        self.assertIn("FALLBACK", result["warning"])
        self.assertIn("FALLBACK", err.getvalue())
        plan = result["plan"]
        self.assertEqual(len(plan["jobs"]), 1)
        job = plan["jobs"][0]
        self.assertEqual(job["key"], FALLBACK_JOB_KEY)
        self.assertIn("FALLBACK", plan["summary"])
        self.assertIn("FALLBACK", job["title"])
        self.assertIn("FALLBACK", job["spec"])
        self.assertIn(goal, job["spec"])

    def test_nonstring_answers_count_as_malformed(self):
        complete = _ScriptedComplete([None, None])
        with contextlib.redirect_stderr(io.StringIO()):
            result = plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 2)
        self.assertTrue(result["fallback"])
        self.assertEqual(len(result["plan"]["jobs"]), 1)

    def test_malformed_then_valid_succeeds_without_fallback(self):
        complete = _ScriptedComplete(["{broken", _valid_plan_json()])
        result = plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 2)
        self.assertFalse(result["fallback"])
        self.assertIsNone(result["warning"])
        self.assertEqual(result["order"], ["do-it"])
        self.assertEqual(result["plan"]["jobs"][0]["title"], "Do it")

    def test_valid_first_answer_calls_once(self):
        complete = _ScriptedComplete([_valid_plan_json()])
        result = plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 1)
        self.assertFalse(result["fallback"])

    def test_structured_invalid_plan_propagates_without_retry(self):
        bad = json.dumps({
            "summary": "Bad plan.",
            "jobs": [{
                "key": "do-it",
                "title": "Do it",
                "spec": "Some spec.",
                "files": ["intel/ingest.py"],
                "deps": [],
                "max_attempts": 3,
                "accept": [],
            }],
        })
        complete = _ScriptedComplete([bad])
        with self.assertRaises(PlanError):
            plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 1)

    def test_dependency_cycle_propagates_without_fallback(self):
        cyclic = json.dumps({
            "summary": "Cyclic plan.",
            "jobs": [
                {"key": "a", "title": "Do a", "spec": "Spec a.",
                 "files": ["intel/ingest.py"], "deps": ["b"],
                 "max_attempts": 3,
                 "accept": ["file-exists: intel/ingest.py"]},
                {"key": "b", "title": "Do b", "spec": "Spec b.",
                 "files": ["intel.py"], "deps": ["a"],
                 "max_attempts": 3,
                 "accept": ["file-exists: intel.py"]},
            ],
        })
        complete = _ScriptedComplete([cyclic])
        with self.assertRaises(PlanError):
            plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 1)

    def test_transport_error_falls_back_with_endpoint_down_warning(
            self):
        complete = _ScriptedComplete([RuntimeError("spark down")])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            result = plan_from_spark("Do the thing", complete)
        self.assertEqual(complete.calls, 1)
        self.assertTrue(result["fallback"])
        self.assertEqual(result["order"], ["fallback-job"])
        self.assertIn("FALLBACK", result["plan"]["summary"])
        self.assertIn("Do the thing",
                      result["plan"]["jobs"][0]["spec"])
        self.assertIn("endpoint is down", result["warning"])
        self.assertIn("endpoint is down", err.getvalue())

    def test_empty_goal_raises_before_any_call(self):
        complete = _ScriptedComplete([_valid_plan_json()])
        with self.assertRaises(PlanError):
            plan_from_spark("   ", complete)
        self.assertEqual(complete.calls, 0)


class FallbackPlanTest(unittest.TestCase):

    def test_multiline_goal_yields_single_line_title(self):
        plan = fallback_plan("First line of the goal\nsecond line")
        job = plan["jobs"][0]
        self.assertNotIn("\n", job["title"])
        self.assertIn("First line of the goal", job["title"])
        self.assertIn("second line", job["spec"])

    def test_fallback_carries_no_invented_files_or_checks(self):
        plan = fallback_plan("Do the thing")
        job = plan["jobs"][0]
        self.assertEqual(job["files"], [])
        self.assertEqual(job["accept"], [])
        self.assertEqual(job["deps"], [])
        self.assertEqual(job["max_attempts"], DEFAULT_MAX_ATTEMPTS)

    def test_empty_goal_raises(self):
        with self.assertRaises(PlanError):
            fallback_plan("")


class FallbackPostTest(RelayTestCase):
    """The fallback plan posts through the normal poster (DSP-008).

    The poster needs no files or accept lines to post, so the
    fallback job reaches the queue only after the DSP-007
    gate — here the test itself is the approver, passing the
    plan straight to post_plan with an injected post.
    """

    def test_fallback_job_posts_one_job_with_raw_goal_spec(self):
        goal = "Wire the snapshot panel"
        with contextlib.redirect_stderr(io.StringIO()):
            result = plan_from_spark(
                goal, _ScriptedComplete(["{bad", "}also bad"]))
        self.assertTrue(result["fallback"])
        seen = {}

        def fake_post(argv):
            seen["argv"] = list(argv)
            return "42"

        record = post_plan(result["plan"], order=result["order"],
                           post_one=fake_post)
        self.assertEqual(len(record["jobs"]), 1)
        self.assertEqual(record["jobs"][0]["key"], FALLBACK_JOB_KEY)
        self.assertEqual(record["jobs"][0]["id"], "42")
        spec_arg = [a for a in seen["argv"]
                    if a.startswith("--spec=")][0]
        self.assertIn(goal, spec_arg)
        self.assertIn("FALLBACK", spec_arg)


if __name__ == "__main__":
    unittest.main()
