"""tests/test_intel_dispatch_announce.py -- DSP-010 announcement line.

The frozen wire format (FND-020, intel/README.md) is
"DISPATCH:<id> -> <n> jobs", where <id> is the dispatch
record id verbatim and <n> is the number of jobs actually
posted. This module tests the line builder and its gates,
and the opt-in announcement paths:

- format_dispatch_announcement is pure: it returns the
  exact line for a stored record, and None for a record
  that cannot carry a line (not a dict, no id, an id with
  whitespace, or no jobs list). The line carries no job
  titles, file lists, or specs.
- post_plan announces nothing by default. With an announce
  callable it calls it exactly once, after the record is
  stored, with the frozen line. A callable that raises
  never fails a post that already succeeded.
- The CLI prints no DISPATCH line without --announce, and
  prints exactly the frozen line with --announce. The CLI
  never pushes the line to the bus: it prints it, and the
  bus push stays held under GOV-002.

No bus post, no live Redis: every posting test runs on
RelayTestCase (fake Redis), and the format tests need no
queue at all.
"""

import importlib.util
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import (  # noqa: E402
    format_dispatch_announcement, post_plan, validated_plan)
import jobs  # noqa: E402
from helpers import RelayTestCase  # noqa: E402


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


def _record(record_id="dsp-1-2", n_jobs=4):
    return {
        "id": record_id,
        "summary": "A plan",
        "jobs": [{"key": f"job-{i}", "id": str(i)}
                 for i in range(n_jobs)],
    }


def _load_intel_cli():
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "intel.py")
    spec = importlib.util.spec_from_file_location(
        "intel_cli_announce_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormatDispatchAnnouncementTest(unittest.TestCase):
    def test_exact_frozen_line(self):
        line = format_dispatch_announcement(_record())
        self.assertEqual(line, "DISPATCH:dsp-1-2 -> 4 jobs")

    def test_count_is_jobs_actually_posted(self):
        line = format_dispatch_announcement(_record(n_jobs=1))
        self.assertEqual(line, "DISPATCH:dsp-1-2 -> 1 jobs")

    def test_line_carries_no_titles_files_or_specs(self):
        record = _record()
        record["jobs"][0]["title"] = "Secret Title Here"
        record["jobs"][0]["files"] = ["secret/path.py"]
        record["jobs"][0]["spec"] = "Secret spec text here"
        line = format_dispatch_announcement(record)
        self.assertEqual(line, "DISPATCH:dsp-1-2 -> 4 jobs")
        self.assertNotIn("Secret", line)

    def test_non_dict_returns_none(self):
        self.assertIsNone(format_dispatch_announcement(None))
        self.assertIsNone(format_dispatch_announcement("DISPATCH:x"))

    def test_missing_or_empty_id_returns_none(self):
        record = _record()
        del record["id"]
        self.assertIsNone(format_dispatch_announcement(record))
        record = _record(record_id="")
        self.assertIsNone(format_dispatch_announcement(record))

    def test_id_with_whitespace_returns_none(self):
        self.assertIsNone(format_dispatch_announcement(
            _record(record_id="dsp 1")))
        self.assertIsNone(format_dispatch_announcement(
            _record(record_id="dsp\n1")))

    def test_missing_or_empty_jobs_returns_none(self):
        record = _record()
        del record["jobs"]
        self.assertIsNone(format_dispatch_announcement(record))
        record = _record(n_jobs=0)
        self.assertIsNone(format_dispatch_announcement(record))
        record = _record()
        record["jobs"] = "not a list"
        self.assertIsNone(format_dispatch_announcement(record))


class PosterAnnounceTest(RelayTestCase):
    def _validated(self):
        plan, order, _clamps = validated_plan(json.dumps(_golden()))
        return plan, order

    def test_post_without_announce_calls_nothing(self):
        plan, order = self._validated()
        record = post_plan(plan, order=order)
        self.assertEqual(record["jobs"][0]["key"], "base")
        line = format_dispatch_announcement(record)
        self.assertEqual(line, f"DISPATCH:{record['id']} -> 4 jobs")

    def test_post_with_announce_calls_once_after_store(self):
        plan, order = self._validated()
        seen = []

        def announce(line):
            seen.append(line)

        record = post_plan(plan, order=order, announce=announce)
        self.assertEqual(seen, [f"DISPATCH:{record['id']} -> 4 jobs"])
        from intel import store as istore  # noqa: E402
        self.assertEqual(istore.get_dispatch(record["id"]), record)

    def test_failing_announce_never_fails_the_post(self):
        plan, order = self._validated()
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            def announce(line):
                raise RuntimeError("bus down")

            record = post_plan(plan, order=order, announce=announce)
        self.assertEqual(len(record["jobs"]), 4)
        self.assertIn("WARNING", err.getvalue())
        self.assertIn("dispatch announcement failed", err.getvalue())
        from intel import store as istore  # noqa: E402
        self.assertEqual(istore.get_dispatch(record["id"]), record)


class AnnounceCliTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        self.cli = _load_intel_cli()
        self.plan_path = os.path.join(self.tmp, "plan.json")
        with open(self.plan_path, "w") as handle:
            json.dump(_golden(), handle)

    def test_post_without_announce_prints_no_dispatch_line(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve"])
        self.assertEqual(code, 0, err)
        self.assertIn("posted dispatch", out)
        self.assertNotIn("DISPATCH:", out)

    def test_post_with_announce_prints_frozen_line(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--approve", "--announce"])
        self.assertEqual(code, 0, err)
        lines = [ln for ln in out.splitlines()
                 if ln.startswith("DISPATCH:")]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].endswith("-> 4 jobs"),
                        lines[0])
        self.assertIn("posted dispatch", out)

    def test_announce_without_approval_prints_nothing(self):
        code, out, err = self.run_cli(
            self.cli.main,
            ["dispatch", "--goal", "Add a snapshot endpoint",
             "--plan", self.plan_path, "--announce"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("DISPATCH:", out)


if __name__ == "__main__":
    unittest.main()
