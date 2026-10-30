#!/usr/bin/env python3
"""tests/test_intel_brief_priority_contacts.py -- INT-027 follow-up.

Wires the last two INT-027 cold-start gaps into the template
brief, from stated snapshot records the caller supplies:
gap 1 (no priority order) via "priority_order" (a list of
job ids in priority order), and gap 5 (no ask-nick on the
blocked job) via "blocked_contacts" (a job_id -> ask nick
map). The INT-027 verdict documented both gaps as limits
because no priority field and no blocked-owner field existed
in the window; these records are those fields, supplied by
the caller the same way the daily, memory, and federation
records are, never guessed from a job title.

Both sections are additive, stated plainly: the In flight
and Blocked and why lines keep their pinned shape, because
rewriting them in place was what the BRF-019 follow-up
could not do without breaking those pins. The new sections
supply the order and the ask-nick those lines cannot carry
in place.

Still owed, stated plainly: a Spark-composed brief carrying
these lines (real Spark transport is still blocked), and an
independent lane member's cold-start re-run under the new
sections. This file pins the template renderer only.
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


class PriorityOrderLinesTest(unittest.TestCase):
    def test_order_numbers_jobs_in_record_order_with_titles(self):
        record = {"order": ["7", "6"], "as_of": 1793101200}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.priority_order_lines(record, jobs)
        self.assertEqual(len(lines), 2)
        self.assertIn("Priority 1: 7 spark client", lines[0])
        self.assertIn("Priority 2: 6 cold-start test", lines[1])
        self.assertIn("(as of ", lines[0])

    def test_unknown_and_duplicate_ids_skipped_never_invented(self):
        record = {"order": ["7", "99", "7", "6"]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.priority_order_lines(record, jobs)
        self.assertEqual(len(lines), 2)
        self.assertNotIn("99", "\n".join(lines))
        self.assertIn("Priority 1: 7 spark client", lines[0])

    def test_unlisted_job_is_not_guessed_into_order(self):
        record = {"order": ["7"]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.priority_order_lines(record, jobs)
        self.assertEqual(len(lines), 1)
        self.assertNotIn("cold-start test", lines[0])

    def test_empty_order_reads_none_reported(self):
        lines = brief.priority_order_lines({"order": []}, [])
        self.assertEqual(lines, ["Priority order: none reported"
                                 " (snapshot time not reported)"])

    def test_malformed_record_yields_no_lines(self):
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"}]
        self.assertEqual(brief.priority_order_lines(None, jobs), [])
        self.assertEqual(brief.priority_order_lines(
            {"order": "not a list"}, jobs), [])
        self.assertEqual(brief.priority_order_lines(
            {"as_of": 1793101200}, jobs), [])

    def test_lines_are_plain_not_bullets(self):
        record = {"order": ["6"]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"}]
        lines = brief.priority_order_lines(record, jobs)
        for line in lines:
            self.assertFalse(line.startswith("- "))


class BlockedContactLinesTest(unittest.TestCase):
    def test_ask_nick_named_and_missing_reads_not_reported(self):
        record = {"contacts": [{"job_id": "7", "ask": "milo"}],
                  "as_of": 1793101200}
        jobs = [{"id": "7", "title": "spark client",
                 "status": "blocked"},
                {"id": "9", "title": "brief panel",
                 "status": "blocked"}]
        lines = brief.blocked_contact_lines(record, jobs)
        self.assertEqual(len(lines), 2)
        self.assertIn("Ask milo about 7 spark client", lines[0])
        self.assertIn("9 brief panel: owner not reported "
                      "in this window", lines[1])
        self.assertIn("(as of ", lines[0])

    def test_contact_for_non_blocked_job_is_ignored(self):
        record = {"contacts": [{"job_id": "6", "ask": "pax"}]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.blocked_contact_lines(record, jobs)
        self.assertEqual(len(lines), 1)
        self.assertNotIn("pax", lines[0])
        self.assertIn("7 spark client: owner not reported "
                      "in this window", lines[0])

    def test_no_blocked_jobs_reads_none_reported(self):
        lines = brief.blocked_contact_lines(
            {"contacts": []},
            [{"id": "6", "title": "cold-start test",
             "status": "open"}])
        self.assertEqual(lines, ["Blocked contacts: none reported"
                                 " (snapshot time not reported)"])

    def test_malformed_record_yields_no_lines(self):
        jobs = [{"id": "7", "title": "spark client",
                 "status": "blocked"}]
        self.assertEqual(brief.blocked_contact_lines(None, jobs), [])
        self.assertEqual(brief.blocked_contact_lines(
            {"contacts": "not a list"}, jobs), [])
        self.assertEqual(brief.blocked_contact_lines(
            {"as_of": 1793101200}, jobs), [])

    def test_lines_are_plain_not_bullets(self):
        record = {"contacts": [{"job_id": "7", "ask": "milo"}]}
        jobs = [{"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.blocked_contact_lines(record, jobs)
        for line in lines:
            self.assertFalse(line.startswith("- "))


class PriorityContactsComposerTest(unittest.TestCase):
    def test_sections_render_after_sources_and_pinned_lines_unchanged(self):
        snapshot = _content_snapshot(
            jobs=[{"id": "6", "title": "cold-start test",
                   "status": "open"},
                  {"id": "7", "title": "spark client",
                   "status": "blocked",
                   "note": "waiting on the real Spark endpoint"}],
            source_pointers=["plan/lanes/HANA.md"],
            priority_order={"order": ["7", "6"]},
            blocked_contacts={"contacts": [{"job_id": "7",
                                            "ask": "milo"}]})
        text = brief.compose_template_brief(snapshot)
        lines = text.splitlines()
        self.assertIn("Priority order", lines)
        self.assertIn("Blocked contacts", lines)
        self.assertLess(lines.index("Sources"),
                        lines.index("Priority order"))
        self.assertLess(lines.index("Priority order"),
                        lines.index("Blocked contacts"))
        self.assertIn("Priority 1: 7 spark client", text)
        self.assertIn("Ask milo about 7 spark client", text)
        # Pinned lines keep their exact shape.
        self.assertIn("- 6 cold-start test (open)", text)
        self.assertIn("- 7 spark client: waiting on the real "
                      "Spark endpoint", text)

    def test_no_records_means_no_sections_old_shape(self):
        text = brief.compose_template_brief(_content_snapshot())
        self.assertNotIn("Priority order", text)
        self.assertNotIn("Blocked contacts", text)

    def test_malformed_records_mean_no_sections(self):
        snapshot = _content_snapshot(
            priority_order="not a record",
            blocked_contacts={"contacts": "not a list"})
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Priority order", text)
        self.assertNotIn("Blocked contacts", text)


class PriorityContactsRubricTest(unittest.TestCase):
    def test_sections_trace_to_records_only(self):
        record = {"order": ["7"]}
        jobs = [{"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked"}]
        lines = brief.priority_order_lines(record, jobs)
        self.assertEqual(len(lines), 1)
        self.assertIn("7", lines[0])
        self.assertNotIn("6", lines[0])
        contacts = brief.blocked_contact_lines(
            {"contacts": [{"job_id": "7", "ask": "milo"}]}, jobs)
        self.assertEqual(len(contacts), 1)
        self.assertIn("milo", contacts[0])
        self.assertNotIn("pax", contacts[0])


if __name__ == "__main__":
    unittest.main()
