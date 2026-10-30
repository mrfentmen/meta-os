"""Unit tests for DSP-012: plan jobs carry req capability names.

A plan job may name the capabilities its worker must have. The
parser normalizes them, the poster passes them to jobs.py as
--req, the posted job stores them, and the dispatch record
carries them, all in the lowercase form mos/capabilities.py
matches. Nothing here invents a capability: a job with no req
in the plan posts with an empty req, and the parser rejects a
malformed req outright.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
from helpers import RelayTestCase
from intel.dispatch import (PlanError, check_dep_graph, parse_plan,
                            post_plan, render_plan_detail,
                            validated_plan)


def _job(key, req=None):
    job = {
        "key": key,
        "title": f"Do {key}",
        "spec": f"Goal, context, files, steps, out of scope for {key}.",
        "files": [f"src/{key}.py"],
        "deps": [],
        "max_attempts": 3,
        "accept": [f"file-exists: src/{key}.py"],
    }
    if req is not None:
        job["req"] = req
    return job


def _plan_text(jobs):
    return json.dumps({"summary": "Build it in order.", "jobs": jobs})


class ParseReqTest(unittest.TestCase):
    def test_req_normalized_and_defaulted(self):
        plan = parse_plan(_plan_text([
            _job("base", req=["Python", " python ", "GIT"]),
            _job("docs"),
        ]))
        self.assertEqual(plan["jobs"][0]["req"], ["python", "git"])
        self.assertEqual(plan["jobs"][1]["req"], [])

    def test_req_non_list_rejected(self):
        with self.assertRaisesRegex(PlanError, "base.*'req'"):
            parse_plan(_plan_text([_job("base", req="python")]))

    def test_req_empty_entry_rejected(self):
        with self.assertRaisesRegex(PlanError, "base.*'req'"):
            parse_plan(_plan_text([_job("base", req=["python", " "])]))

    def test_req_survives_validated_plan(self):
        plan, order, _clamps = validated_plan(_plan_text([
            _job("base", req=["Python"]),
        ]))
        self.assertEqual(order, ["base"])
        self.assertEqual(plan["jobs"][0]["req"], ["python"])

    def test_prompt_names_req_and_dsp012(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "intel", "prompts", "dispatch.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("`req`", text)
        self.assertIn("DSP-012", text)


class PostReqTest(RelayTestCase):
    def test_poster_passes_req_and_record_carries_it(self):
        plan, order, _clamps = validated_plan(_plan_text([
            _job("base", req=["Python", "GIT"]),
            _job("docs"),
        ]))
        order = check_dep_graph(plan)
        seen = []

        def fake_post(argv):
            seen.append(argv)
            return f"job-{len(seen)}"

        record = post_plan(plan, order=order, post_one=fake_post)
        self.assertIn("--req=python,git", seen[0])
        self.assertIn("--req=", seen[1])
        self.assertEqual(record["jobs"][0]["req"], ["python", "git"])
        self.assertEqual(record["jobs"][1]["req"], [])

    def test_render_shows_req_and_none(self):
        plan, _order, _clamps = validated_plan(_plan_text([
            _job("base", req=["Python"]),
            _job("docs"),
        ]))
        detail = render_plan_detail(plan, ["base", "docs"])
        self.assertIn("req: python", detail)
        self.assertIn("req: none", detail)


if __name__ == "__main__":
    unittest.main()
