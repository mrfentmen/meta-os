"""intel/brief.py: OS-127 follow-up — with_recovery,
the boot-path caller.

Before this change no caller in the repo filled
`recovery`: a boot brief carried its one
in-flight-jobs-recovered line only when the snapshot
hand-stated a "recovery" record, and a boot snapshot
that only carried the lease sweep's own stated outcome
carried no line at all. Now the boot path fills the
record first: recovered jobs from the snapshot's own
stated sweep_recovered list (id, title, baton step
when stated), the sweep count from its own stated
sweep_count, and corrupted jobs from its own stated
sweep_corrupted list, with one as_of stamp for the
whole record. A snapshot that hand-states a record
keeps it untouched, and a snapshot that states no
sweep outcome gets no record added, so older briefs
keep their exact shape. A stated sweep count of zero
with no recovered jobs reads "0 recovered" plainly,
while a snapshot with no sweep count never reads
zero. A job listed twice is one recovery, and
malformed entries are skipped, never guessed — and
a skipped entry never reconciles into a clean count.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "sweep_recovered": [
        {"id": "5", "title": "brief panel", "baton_step": "step 2"},
        {"id": "6", "title": "dispatch poster", "baton_step": 1}],
    "sweep_count": 2,
}


class WithRecoveryTest(unittest.TestCase):
    def test_fills_recovered_and_sweep_count_with_one_stamp(self):
        filled = brief.with_recovery(SNAPSHOT, now=1793093400)
        record = filled["recovery"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["recovered"],
                         [{"id": "5", "title": "brief panel",
                           "baton_step": "step 2"},
                          {"id": "6", "title": "dispatch poster",
                           "baton_step": 1}])
        self.assertEqual(record["sweep_count"], 2)
        self.assertNotIn("corrupted", record)

    def test_filled_record_renders_recovery_line(self):
        filled = brief.with_recovery(SNAPSHOT, now=1793093400)
        line = brief.recovery_line(filled["recovery"])
        self.assertIn("2 recovered", line)
        self.assertIn("job 5 brief panel (resumed at step 2)", line)
        self.assertIn("job 6 dispatch poster (resumed at baton step 1)",
                      line)

    def test_boot_template_brief_over_filled_snapshot_carries_line(self):
        filled = brief.with_recovery(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True, boot=True)
        self.assertIn("In-flight jobs recovered at this boot: "
                      "2 recovered", text)
        self.assertIn("job 5 brief panel (resumed at step 2)", text)

    def test_clean_shutdown_reads_zero_recovered_plainly(self):
        filled = brief.with_recovery({"sweep_count": 0,
                                      "sweep_recovered": []},
                                     now=1793093400)
        self.assertEqual(filled["recovery"]["sweep_count"], 0)
        self.assertEqual(filled["recovery"]["recovered"], [])
        self.assertEqual(brief.recovery_line(filled["recovery"]),
                         "In-flight jobs recovered at this boot: "
                         "0 recovered")

    def test_no_sweep_count_never_reads_zero(self):
        filled = brief.with_recovery({"sweep_recovered": []},
                                     now=1793093400)
        self.assertNotIn("recovery", filled)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"recovered": [{"id": "5", "title": "brief panel",
                                  "baton_step": "step 2"}],
                  "sweep_count": 1, "corrupted": []}
        filled = brief.with_recovery(
            {"recovery": stated,
             "sweep_recovered": SNAPSHOT["sweep_recovered"],
             "sweep_count": 2},
            now=1793093400)
        self.assertEqual(filled["recovery"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_recovery(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("recovery", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_recovery({"messages": []},
                                     now=1793093400)
        self.assertNotIn("recovery", filled)
        filled = brief.with_recovery({"sweep_recovered": [],
                                      "sweep_corrupted": []},
                                     now=1793093400)
        self.assertNotIn("recovery", filled)

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_recovery(
            {"sweep_recovered": [
                {"title": "no id, skipped"},
                {"id": "5"},
                {"id": "5", "title": "brief panel",
                 "baton_step": "step 2"},
                {"id": "6", "title": "dispatch poster"}],
             "sweep_count": 2,
             "sweep_corrupted": [
                 {"id": "7", "title": "watchdog loop"}, "a bare name"]},
            now=1793093400)
        record = filled["recovery"]
        self.assertEqual(record["recovered"],
                         [{"id": "5", "title": "brief panel",
                           "baton_step": "step 2"},
                          {"id": "6", "title": "dispatch poster"}])
        # The skipped entries void the sweep count, so the
        # line stays incomplete instead of printing a
        # clean count over a gap.
        self.assertNotIn("sweep_count", record)
        self.assertEqual(record["corrupted"],
                         [{"id": "7", "title": "watchdog loop"},
                          "a bare name"])
        line = brief.recovery_line(record)
        self.assertIn("corrupted record", line)
        self.assertIn("job 7 watchdog loop", line)

    def test_job_listed_twice_is_one_recovery(self):
        filled = brief.with_recovery(
            {"sweep_recovered": [
                {"id": "5", "title": "brief panel",
                 "baton_step": "step 2"},
                {"id": "5", "title": "a second listing",
                 "baton_step": "step 9"}],
             "sweep_count": 1},
            now=1793093400)
        self.assertEqual(filled["recovery"]["recovered"],
                         [{"id": "5", "title": "brief panel",
                           "baton_step": "step 2"}])
        self.assertEqual(filled["recovery"]["sweep_count"], 1)
        self.assertIn("1 recovered",
                      brief.recovery_line(filled["recovery"]))

    def test_recovered_job_without_baton_step_reads_not_reported(self):
        filled = brief.with_recovery(
            {"sweep_recovered": [{"id": "5", "title": "brief panel"}],
             "sweep_count": 1},
            now=1793093400)
        self.assertIn("step not reported",
                      brief.recovery_line(filled["recovery"]))

    def test_sweep_mismatch_reads_incomplete_with_both_counts(self):
        filled = brief.with_recovery(
            {"sweep_recovered": [{"id": "5", "title": "brief panel",
                                  "baton_step": "step 2"}],
             "sweep_count": 2},
            now=1793093400)
        line = brief.recovery_line(filled["recovery"])
        self.assertIn("recovery incomplete", line)
        self.assertIn("reports 2 recovered but 1 job records", line)

    def test_recovered_jobs_without_sweep_count_read_incomplete(self):
        filled = brief.with_recovery(
            {"sweep_recovered": [{"id": "5", "title": "brief panel",
                                  "baton_step": "step 2"}]},
            now=1793093400)
        self.assertNotIn("sweep_count", filled["recovery"])
        self.assertIn("no lease sweep count",
                      brief.recovery_line(filled["recovery"]))

    def test_invalid_sweep_count_is_ignored_never_guessed(self):
        for bad in (True, -1, "2", 2.5):
            filled = brief.with_recovery(
                {"sweep_recovered": [{"id": "5", "title": "brief panel",
                                      "baton_step": "step 2"}],
                 "sweep_count": bad},
                now=1793093400)
            self.assertNotIn("sweep_count", filled["recovery"])

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_recovery(SNAPSHOT)
        self.assertIsInstance(filled["recovery"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_recovery(None), {})


if __name__ == "__main__":
    unittest.main()
