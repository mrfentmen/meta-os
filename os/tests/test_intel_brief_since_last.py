#!/usr/bin/env python3
"""tests/test_intel_brief_since_last.py -- BRF-019 follow-up.

Wires v2 rule 10 (the INT-027 cold-start gap 2 diff: old news
and new news look identical) into the template brief, from a
stated snapshot record the caller supplies: "previous_brief"
(the jobs and their statuses in the previous brief). The
INT-027 verdict documented gap 2 as a limit because no
previous brief was in the window to compare against; this
record is that comparison source, supplied by the caller the
same way the daily, memory, and federation records are,
never guessed from a job title.

Still owed, stated plainly: a Spark-composed brief carrying
these lines (real Spark transport is still blocked), and an
independent lane member's cold-start re-run under the new
section. This file pins the template renderer only.
"""

import os
import unittest

import sys
sys.path.insert(0, ".")
from intel import brief  # noqa: E402


def _content_snapshot(**extra):
    snapshot = {
        "source_window": "2026-10-28 08:00 ET onward, "
                         "last 24 hours",
        "messages": [{"nick": "hana",
                      "text": "DECISION: ship the brief panel first"}],
        "jobs": [{"id": "6", "title": "cold-start test",
                  "status": "open"}],
    }
    snapshot.update(extra)
    return snapshot


class SinceLastBriefLinesTest(unittest.TestCase):
    def test_changed_status_names_old_and_new_in_order(self):
        previous = {"jobs": [{"id": "6", "status": "claimed"},
                            {"id": "7", "status": "open"}],
                    "as_of": 1793101200}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        self.assertEqual(len(lines), 2)
        self.assertIn("Changed since your last brief: 6 "
                      "cold-start test: claimed -> open", lines[0])
        self.assertIn("Changed since your last brief: 7 "
                      "spark client: open -> blocked", lines[1])
        self.assertIn("(as of ", lines[0])

    def test_new_job_reads_new_and_unchanged_job_skipped(self):
        previous = {"jobs": [{"id": "6", "status": "open"}]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "8", "title": "brief panel",
                 "status": "claimed"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        self.assertEqual(len(lines), 1)
        self.assertIn("New since your last brief: 8 "
                      "brief panel (claimed)", lines[0])
        self.assertIn("(snapshot time not reported)", lines[0])

    def test_nothing_changed_reads_nothing_changed(self):
        previous = {"jobs": [{"id": "6", "status": "open"}]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        self.assertEqual(lines, ["Nothing changed since your last brief"
                                 " (snapshot time not reported)"])

    def test_idless_jobs_skipped_on_both_sides(self):
        previous = {"jobs": [{"title": "no id job",
                              "status": "open"},
                             {"id": "6", "status": "open"}]}
        jobs = [{"title": "no id job", "status": "blocked"},
                {"id": "6", "title": "cold-start test",
                 "status": "open"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        self.assertEqual(lines, ["Nothing changed since your last brief"
                                 " (snapshot time not reported)"])

    def test_malformed_record_yields_no_lines(self):
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"}]
        self.assertEqual(brief.since_last_brief_lines(None, jobs), [])
        self.assertEqual(brief.since_last_brief_lines(
            {"jobs": "not a list"}, jobs), [])
        self.assertEqual(brief.since_last_brief_lines(
            {"as_of": 1793101200}, jobs), [])

    def test_lines_are_plain_not_bullets(self):
        previous = {"jobs": [{"id": "6", "status": "claimed"}]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        for line in lines:
            self.assertFalse(line.startswith("- "))


class SinceLastBriefComposerTest(unittest.TestCase):
    def test_section_opens_brief_after_window_line(self):
        snapshot = _content_snapshot(previous_brief={
            "jobs": [{"id": "6", "status": "claimed"}],
            "as_of": 1793101200})
        text = brief.compose_template_brief(snapshot)
        lines = text.splitlines()
        self.assertIn("Since your last brief", lines)
        heading = lines.index("Since your last brief")
        self.assertLess(heading, lines.index("Decisions"))
        self.assertIn("Changed since your last brief: 6 "
                      "cold-start test: claimed -> open",
                      lines[heading + 1])

    def test_no_record_means_no_section_old_shape(self):
        text = brief.compose_template_brief(_content_snapshot())
        self.assertNotIn("Since your last brief", text)
        self.assertNotIn("since your last brief", text)

    def test_malformed_record_means_no_section(self):
        snapshot = _content_snapshot(previous_brief="not a record")
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Since your last brief", text)

    def test_nothing_changed_section_still_renders(self):
        snapshot = _content_snapshot(previous_brief={
            "jobs": [{"id": "6", "status": "open"}]})
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Since your last brief", text)
        self.assertIn("Nothing changed since your last brief", text)


class SinceLastBriefRubricTest(unittest.TestCase):
    def test_section_lines_trace_to_records_only(self):
        previous = {"jobs": [{"id": "6", "status": "claimed"},
                            {"id": "9", "status": "open"}]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "9", "title": "brief panel",
                 "status": "open"}]
        lines = brief.since_last_brief_lines(previous, jobs)
        self.assertEqual(len(lines), 1)
        self.assertIn("6", lines[0])
        self.assertNotIn("9", lines[0])


if __name__ == "__main__":
    unittest.main()
