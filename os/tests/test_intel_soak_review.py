"""tests/test_intel_soak_review.py -- OS-074 prep: soak journal review.

OS-074 acceptance is a seven-day soak reviewed end to
end: every silent failure in the log has an alert or a
filed bug, and zero unexplained gaps remain. The soak
itself is NOT run here: no booted Meta OS image runs
in this repo, the crew does not run on Meta OS here,
and seven days have not elapsed on any such image.
These tests pin the review half on fixtures:

- A clean 7-day journal reads clean with zero gaps,
  3 failures, 3 covered, all 7 days present.
- Bug coverage counts; alert plus bug are both listed
  for one failure; duplicate alerts still count as one
  coverage.
- Removing the one bug for a failure makes that
  failure the one unexplained gap, verdict gaps.
- A partial journal names its missing days instead of
  silently passing as a full week.
- Orphan covers (naming a failure that never appears)
  are reported, never counted as coverage.
- Malformed entries are skipped, never a crash; a
  failure without a day is listed undated and is still
  a gap when uncovered.
- An empty journal is clean with zero failures and all
  7 days missing; a non-list journal reads as empty.
- Inputs are never mutated, the report carries no push
  and no announcement field, and the module imports no
  push module.
- The drill script exists and passes; the eval note
  names OS-074.
- None of the new OS-074 files carries an em dash (the
  new-doc rule).

No bus post, no live Redis, no network, no systemd:
pure fixture calls plus file reads.
"""

import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import soak_review  # noqa: E402

NEW_FILES = [
    "intel/soak_review.py",
    "intel/drills/soak_review.py",
    "intel/evals/soak_review.md",
    "intel/evals/soak_review.log",
    "tests/test_intel_soak_review.py",
]


def clean_journal():
    return [
        {"kind": "silent_failure", "id": "f1", "day": 1},
        {"kind": "alert", "id": "a1", "failure_id": "f1", "day": 1},
        {"kind": "silent_failure", "id": "f2", "day": 3},
        {"kind": "bug", "id": "b1", "failure_id": "f2", "day": 3},
        {"kind": "silent_failure", "id": "f3", "day": 5},
        {"kind": "alert", "id": "a2", "failure_id": "f3", "day": 5},
        {"kind": "bug", "id": "b2", "failure_id": "f3", "day": 5},
        {"kind": "alert", "id": "a-day2", "failure_id": "f1", "day": 2},
        {"kind": "alert", "id": "a-day4", "failure_id": "f1", "day": 4},
        {"kind": "alert", "id": "a-day6", "failure_id": "f1", "day": 6},
        {"kind": "alert", "id": "a-day7", "failure_id": "f1", "day": 7},
    ]


class TestSoakReview(unittest.TestCase):
    def test_clean_week_reads_clean_with_zero_gaps(self):
        report = soak_review.review_journal(clean_journal())
        self.assertEqual(report["verdict"], "clean")
        self.assertEqual(report["unexplained_gaps"], [])
        self.assertEqual(report["total_failures"], 3)
        self.assertEqual(report["covered_failures"], 3)
        self.assertEqual(report["days_present"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(report["days_missing"], [])

    def test_bug_coverage_and_alert_plus_bug_listing(self):
        report = soak_review.review_journal(clean_journal())
        self.assertTrue(report["coverage"]["f2"]["covered"])
        self.assertEqual(report["coverage"]["f2"]["bugs"], ["b1"])
        self.assertEqual(report["coverage"]["f3"]["alerts"], ["a2"])
        self.assertEqual(report["coverage"]["f3"]["bugs"], ["b2"])

    def test_one_uncovered_failure_is_the_one_gap(self):
        journal = [e for e in clean_journal()
                   if not (e.get("kind") == "bug"
                           and e.get("failure_id") == "f2")]
        report = soak_review.review_journal(journal)
        self.assertEqual(report["verdict"], "gaps")
        self.assertEqual(report["unexplained_gaps"], ["f2"])
        self.assertEqual(report["covered_failures"], 2)

    def test_partial_journal_names_missing_days(self):
        journal = [e for e in clean_journal()
                   if e.get("day") in (1, 3, 5)]
        report = soak_review.review_journal(journal)
        self.assertEqual(report["days_present"], [1, 3, 5])
        self.assertEqual(report["days_missing"], [2, 4, 6, 7])

    def test_orphan_covers_reported_never_counted(self):
        journal = clean_journal() + [
            {"kind": "alert", "id": "a-orphan",
             "failure_id": "f-ghost", "day": 2},
            {"kind": "bug", "id": "b-orphan",
             "failure_id": "f-ghost", "day": 2},
        ]
        report = soak_review.review_journal(journal)
        self.assertEqual(report["total_failures"], 3)
        self.assertEqual(report["covered_failures"], 3)
        self.assertEqual(len(report["orphans"]), 2)

    def test_duplicate_alert_counts_as_one_coverage(self):
        journal = clean_journal() + [
            {"kind": "alert", "id": "a1-dup",
             "failure_id": "f1", "day": 1},
        ]
        report = soak_review.review_journal(journal)
        self.assertEqual(report["covered_failures"], 3)
        self.assertTrue(report["coverage"]["f1"]["covered"])

    def test_malformed_skipped_and_undated_still_a_gap(self):
        journal = clean_journal() + [
            "not-a-record",
            {"kind": "silent_failure"},
            {"kind": "alert", "day": 2},
            {"kind": "silent_failure", "id": "f4"},
        ]
        report = soak_review.review_journal(journal)
        self.assertEqual(report["skipped"], 3)
        self.assertEqual(report["total_failures"], 4)
        self.assertEqual(report["undated"], ["f4"])
        self.assertIn("f4", report["unexplained_gaps"])

    def test_empty_and_non_list_journals(self):
        empty = soak_review.review_journal([])
        self.assertEqual(empty["verdict"], "clean")
        self.assertEqual(empty["total_failures"], 0)
        self.assertEqual(empty["days_missing"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(soak_review.review_journal(None)
                         ["total_failures"], 0)

    def test_inputs_never_mutated_and_no_push_field(self):
        journal = clean_journal()
        original = copy.deepcopy(journal)
        report = soak_review.review_journal(journal)
        self.assertEqual(journal, original)
        self.assertNotIn("push", report)
        self.assertNotIn("announcement", report)

    def test_module_has_no_push_path(self):
        path = os.path.join("intel", "soak_review.py")
        with open(path) as handle:
            source = handle.read()
        self.assertNotIn("import push", source)
        self.assertNotIn("from intel import push", source)

    def test_brief_lines_name_gap_and_clean_week(self):
        journal = [e for e in clean_journal()
                   if not (e.get("kind") == "bug"
                           and e.get("failure_id") == "f2")]
        lines = soak_review.soak_brief_lines(
            soak_review.review_journal(journal))
        self.assertTrue(any("f2" in line for line in lines))
        self.assertTrue(any("gaps" in line for line in lines))
        clean_lines = soak_review.soak_brief_lines(
            soak_review.review_journal(clean_journal()))
        self.assertTrue(any("all 7 days present" in line
                            for line in clean_lines))

    def test_drill_passes_and_eval_names_task(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/soak_review.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 FAIL", result.stdout)
        with open(os.path.join("intel", "evals", "soak_review.md")) \
                as handle:
            self.assertIn("OS-074", handle.read())

    def test_new_files_exist_and_carry_no_em_dash(self):
        for path in NEW_FILES:
            self.assertTrue(os.path.exists(path), path)
            with open(path) as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
