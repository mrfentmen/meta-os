#!/usr/bin/env python3
"""BRF-010 brief announcement line, held.

Acceptance: the announcement line matches the frozen wire format
in intel/README.md (BRIEF:<room>:<ts> <kind>), or is held, if
Dale has not approved posting. Posting is held under GOV-002,
so what lands here is the line builder plus a print-only CLI
surface: intel.py brief --show --announce prints the frozen line
for a stored brief and posts nothing. There is no post call site
behind it. The builder is pure: it touches no Redis, no network,
no Spark, and no secret, so these tests assert its shape
directly.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402
from intel import store as _store  # noqa: E402


def _record(room="main", ts=1761500000, kind="morning"):
    return {"room": room, "generated_at": ts, "kind": kind,
            "sections": {"Decisions": ["ship the panel"],
                         "Blocked": ["waiting on Pax"]},
            "source_window": "last 500 messages",
            "model": "template", "spend_id": None}


class BriefAnnouncementTest(unittest.TestCase):
    def test_readme_example_renders_exactly(self):
        self.assertEqual(
            brief.format_brief_announcement(_record()),
            "BRIEF:main:1761500000 morning")

    def test_all_three_kinds_render(self):
        for kind in ("morning", "onjoin", "ondemand"):
            self.assertEqual(
                brief.format_brief_announcement(_record(kind=kind)),
                f"BRIEF:main:1761500000 {kind}")

    def test_room_is_cleaned_and_empty_room_reads_main(self):
        self.assertEqual(
            brief.format_brief_announcement(_record(room="Build")),
            "BRIEF:build:1761500000 morning")
        self.assertEqual(
            brief.format_brief_announcement(_record(room="")),
            "BRIEF:main:1761500000 morning")

    def test_line_carries_no_section_text(self):
        line = brief.format_brief_announcement(_record())
        self.assertNotIn("ship the panel", line)
        self.assertNotIn("waiting on Pax", line)
        self.assertEqual(line, "BRIEF:main:1761500000 morning")

    def test_ts_matches_the_store_key(self):
        record = _record()
        line = brief.format_brief_announcement(record)
        self.assertTrue(
            _store.brief_key(record["room"], record["generated_at"])
            .endswith(f":{record['generated_at']}"))
        self.assertIn(f":{record['generated_at']} ", line)

    def test_unusable_records_yield_no_line(self):
        bad = [None, "BRIEF:main:1 morning", [],
               _record(room=None), _record(room=7),
               _record(room="!!!"),
               _record(ts=None), _record(ts="1761500000"),
               _record(ts=1761500000.0), _record(ts=True),
               _record(kind="daily"), _record(kind=None)]
        for record in bad:
            with self.subTest(record=record):
                self.assertIsNone(brief.format_brief_announcement(record))

    def test_missing_fields_yield_no_line(self):
        for record in ({}, {"room": "main"}, {"room": "main",
                                             "generated_at": 1761500000}):
            with self.subTest(record=record):
                self.assertIsNone(brief.format_brief_announcement(record))


class CliAnnounceTest(unittest.TestCase):
    """BRF-010 CLI surface, run in-process with the store read
    mocked: the subprocess CLI tests cannot cover --show without
    a live Redis surface, so these patch the brief module's read
    and call intel.py main() directly."""

    def _load_cli(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "intel_cli", "intel.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run(self, cli, argv):
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_show_announce_prints_only_the_line(self):
        from unittest import mock
        cli = self._load_cli()
        with mock.patch.object(brief, "get_brief",
                               return_value=_record()):
            code, out, err = self._run(
                cli, ["brief", "--show", "--room", "main",
                      "--ts", "1761500000", "--announce"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "BRIEF:main:1761500000 morning\n")
        self.assertEqual(err, "")
        self.assertNotIn("ship the panel", out)

    def test_show_announce_without_show_is_a_usage_error(self):
        cli = self._load_cli()
        with self.assertRaises(SystemExit) as caught:
            self._run(cli, ["brief", "--announce"])
        self.assertEqual(caught.exception.code, 2)

    def test_show_announce_on_unusable_record_errors_without_a_line(
            self):
        from unittest import mock
        cli = self._load_cli()
        with mock.patch.object(brief, "get_brief",
                               return_value=_record(kind="daily")):
            code, out, err = self._run(
                cli, ["brief", "--show", "--room", "main",
                      "--ts", "1761500000", "--announce"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("RELAY_ERROR", err)
        self.assertNotIn("BRIEF:main:", err)


if __name__ == "__main__":
    unittest.main()
