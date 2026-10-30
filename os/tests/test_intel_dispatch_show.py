"""tests/test_intel_dispatch_show.py: DSP-016 plan diff view.

show_dispatch reads the dispatch record stored by post_plan and
reports the plan as posted next to each job's current state,
read fresh from the queue: open, claimed, done, blocked,
cancelled, failed-final, or missing when the job id is no
longer in the queue. A claimed job carries its claim nick.
Showing is read-only: it never posts, claims, cancels, or
writes the dispatch record, so showing twice reports the same
plan with only the job states able to move. An unknown
dispatch id raises ShowError with nothing touched. The CLI
pins the same at the command line: --show prints the diff,
an unknown id exits 2 with nothing touched.

All plans here are literal dicts in the test, all jobs are
posted through post_plan onto FakeUpstash, and nothing here
posts to the bus, claims for real, or needs a Spark call.
"""

import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import (  # noqa: E402
    ShowError, post_plan, render_dispatch_show, show_dispatch,
    validated_plan)
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
    return {
        "key": key,
        "title": title or f"Do {key}",
        "spec": spec,
        "files": list(files),
        "deps": list(deps),
        "max_attempts": max_attempts,
        "accept": list(accept),
    }


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


class ShowTest(RelayTestCase):
    """DSP-016: show_dispatch reports posted plan vs live states."""

    def _posted(self, dispatch_id="dsp-show-1"):
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        return post_plan(plan, order=order, dispatch_id=dispatch_id)

    def _jobs_json(self):
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        return json.loads(out)

    def test_show_all_open_after_posting(self):
        record = self._posted()
        mapping = {e["key"]: e["id"] for e in record["jobs"]}
        report = show_dispatch("dsp-show-1")
        self.assertEqual(report["id"], "dsp-show-1")
        self.assertEqual(report["summary"], _golden()["summary"])
        self.assertEqual(report["order"],
                         ["base", "api", "panel", "docs"])
        self.assertIsInstance(report["latency_ms"], int)
        self.assertEqual(report["counts"], {"open": 4})
        by_key = {j["key"]: j for j in report["jobs"]}
        self.assertEqual([j["key"] for j in report["jobs"]],
                         ["base", "api", "panel", "docs"])
        self.assertTrue(all(j["status"] == "open"
                            for j in report["jobs"]))
        self.assertTrue(all(j["claim"] == ""
                            for j in report["jobs"]))
        # As-posted side: files from the plan, deps as posted ids.
        self.assertEqual(by_key["base"]["files"], ["intel/ingest.py"])
        self.assertEqual(by_key["api"]["deps"], [mapping["base"]])
        self.assertEqual(by_key["docs"]["deps"],
                         [mapping["api"], mapping["panel"]])
        self.assertEqual(by_key["docs"]["max_attempts"], 3)

    def test_show_mixed_states(self):
        record = self._posted()
        mapping = {e["key"]: e["id"] for e in record["jobs"]}
        self.run_cli(jobs.main, ["claim", mapping["api"]])
        self.run_cli(jobs.main, ["claim", mapping["base"]])
        rc, _out, err = self.run_cli(
            jobs.main, ["done", mapping["base"], "--commit", "abc"])
        self.assertEqual(rc, 0, err)
        rc, _out, err = self.run_cli(
            jobs.main, ["cancel", mapping["panel"],
                        "--reason=dsp-016 test"])
        self.assertEqual(rc, 0, err)
        report = show_dispatch("dsp-show-1")
        by_key = {j["key"]: j for j in report["jobs"]}
        self.assertEqual(by_key["base"]["status"], "done")
        self.assertEqual(by_key["api"]["status"], "claimed")
        self.assertEqual(by_key["api"]["claim"], "tester")
        self.assertEqual(by_key["panel"]["status"], "cancelled")
        self.assertEqual(by_key["docs"]["status"], "open")
        self.assertEqual(report["counts"],
                         {"done": 1, "claimed": 1,
                          "cancelled": 1, "open": 1})

    def test_show_reports_missing_job(self):
        istore.put_dispatch("dsp-ghost", {
            "id": "dsp-ghost", "summary": "", "room": "main",
            "created_at": 0, "order": ["x"], "signed": False,
            "jobs": [{"key": "x", "id": "9999", "title": "Ghost",
                      "files": [], "deps": [], "max_attempts": 3}]})
        report = show_dispatch("dsp-ghost")
        self.assertEqual(len(report["jobs"]), 1)
        self.assertEqual(report["jobs"][0]["status"], "missing")
        self.assertEqual(report["jobs"][0]["claim"], "")
        self.assertEqual(report["counts"], {"missing": 1})

    def test_show_unknown_dispatch_raises_and_touches_nothing(self):
        self._posted()
        before = self._jobs_json()
        with self.assertRaisesRegex(ShowError, "no dispatch record"):
            show_dispatch("dsp-nope")
        self.assertEqual(self._jobs_json(), before)

    def test_show_is_read_only(self):
        self._posted()
        record_before = json.dumps(istore.get_dispatch("dsp-show-1"),
                                   sort_keys=True)
        jobs_before = self._jobs_json()
        show_dispatch("dsp-show-1")
        show_dispatch("dsp-show-1")
        self.assertEqual(json.dumps(istore.get_dispatch("dsp-show-1"),
                                    sort_keys=True),
                         record_before)
        self.assertEqual(self._jobs_json(), jobs_before)

    def test_render_shows_posted_vs_current(self):
        record = self._posted()
        mapping = {e["key"]: e["id"] for e in record["jobs"]}
        text = render_dispatch_show(show_dispatch("dsp-show-1"))
        self.assertIn("dispatch dsp-show-1:", text)
        self.assertIn("summary: Build the snapshot in order", text)
        self.assertIn(f"base -> {mapping['base']}: Do base", text)
        self.assertIn("files: intel/ingest.py; deps: none", text)
        self.assertIn("deps: base", text)
        self.assertIn("now: open", text)
        self.assertIn("counts: 4 open", text)
        self.run_cli(jobs.main, ["claim", mapping["api"]])
        text = render_dispatch_show(show_dispatch("dsp-show-1"))
        self.assertIn("claimed by tester", text)
        self.assertIn("counts: 3 open, 1 claimed", text)


class ShowCliTest(RelayTestCase):
    """DSP-016 at the CLI: --show prints the diff, unknown id exits 2."""

    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        self.record = post_plan(plan, order=order,
                                dispatch_id="dsp-cli-show")

    def test_cli_show_prints_diff(self):
        code, out, err = self.run_cli(
            self.cli.main, ["dispatch", "--show", "dsp-cli-show"])
        self.assertEqual(code, 0, err)
        self.assertIn("dispatch dsp-cli-show:", out)
        for key in ("base", "api", "panel", "docs"):
            self.assertIn(f"{key} -> ", out)
        self.assertIn("now: open", out)
        self.assertIn("counts: 4 open", out)

    def test_cli_show_unknown_id_exits_2(self):
        before = self.run_cli(jobs.main, ["list", "--json"])[1]
        code, out, err = self.run_cli(
            self.cli.main, ["dispatch", "--show", "dsp-nope"])
        self.assertEqual(code, 2)
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("no dispatch record", err)
        after = self.run_cli(jobs.main, ["list", "--json"])[1]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
