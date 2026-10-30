"""tests/test_intel_watchman_boot.py -- OS-129: watchman state after reboot.

The watchman survives the machine dying by rebuilding its
picture purely from queue claims and leases, never from a
stored message counter. These tests pin the verification
half on fixtures:

- Open jobs posted inside the downtime window ring as
  arrived_during_downtime; pre-window and post-boot open
  jobs do not ring.
- Claimed jobs whose leases died inside the window ring
  as lease_expired_during_downtime; live leases do not
  ring; done jobs never ring.
- Malformed records never ring and never crash.
- A job listed twice rings once; a second cycle with the
  first cycle's rung ids in the ledger rings nothing new.
- A corrupted stored counter value changes nothing: the
  ring set is identical with and without the junk keys,
  and no function takes a counter argument.
- Sweep reconciliation agrees when the sweep requeues
  exactly the lease-expired rings, and names the missing
  and extra ids when it does not.
- Rings and verification never mutate their inputs, and
  the note carries no push and no announcement field.
- The module carries no push path: no push import, no
  network import.
- The drill script exists and passes; the eval note
  names OS-129.
- None of the new OS-129 files carries an em dash (the
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

from intel import watchman_boot  # noqa: E402

T0 = 100000
T1 = 100600
NEW_FILES = [
    "intel/watchman_boot.py",
    "intel/drills/watchman_boot.py",
    "intel/evals/watchman_boot.md",
    "intel/evals/watchman_boot.log",
    "tests/test_intel_watchman_boot.py",
]


def base_jobs():
    return [
        {"id": "arrive-1", "status": "open", "posted_at": T0 + 100},
        {"id": "arrive-2", "status": "open", "posted_at": T0 + 500},
        {"id": "before", "status": "open", "posted_at": T0 - 50},
        {"id": "after", "status": "open", "posted_at": T1 + 10},
        {"id": "lease-dead", "status": "claimed",
         "claimed_by": "hana", "lease_expires_at": T0 + 300},
        {"id": "lease-live", "status": "claimed",
         "claimed_by": "rowan", "lease_expires_at": T1 + 900},
        {"id": "done-job", "status": "done",
         "lease_expires_at": T0 + 200},
    ]


class TestWatchmanBoot(unittest.TestCase):
    def test_arrivals_ring_and_only_arrivals_ring(self):
        rings = watchman_boot.post_boot_rings(base_jobs(), T0, T1)
        ids = [r["job_id"] for r in rings]
        self.assertEqual(ids, ["arrive-1", "arrive-2", "lease-dead"])
        reasons = {r["job_id"]: r["reason"] for r in rings}
        self.assertEqual(reasons["arrive-1"], "arrived_during_downtime")
        self.assertEqual(reasons["arrive-2"], "arrived_during_downtime")
        self.assertEqual(reasons["lease-dead"],
                         "lease_expired_during_downtime")

    def test_pre_window_post_boot_live_lease_and_done_do_not_ring(self):
        rings = watchman_boot.post_boot_rings(base_jobs(), T0, T1)
        ids = [r["job_id"] for r in rings]
        for missing in ("before", "after", "lease-live", "done-job"):
            self.assertNotIn(missing, ids)

    def test_malformed_records_never_ring_and_never_crash(self):
        jobs = base_jobs() + [
            {"status": "open", "posted_at": T0 + 10},
            {"id": "no-time", "status": "open"},
            "not-a-record",
            None,
        ]
        rings = watchman_boot.post_boot_rings(jobs, T0, T1)
        ids = [r["job_id"] for r in rings]
        self.assertEqual(ids, ["arrive-1", "arrive-2", "lease-dead"])
        self.assertNotIn("no-time", ids)

    def test_duplicate_input_rings_once(self):
        jobs = base_jobs() + [{"id": "arrive-1", "status": "open",
                               "posted_at": T0 + 100}]
        rings = watchman_boot.post_boot_rings(jobs, T0, T1)
        self.assertEqual([r["job_id"] for r in rings].count("arrive-1"), 1)

    def test_second_cycle_with_ledger_rings_nothing_new(self):
        first = watchman_boot.post_boot_rings(base_jobs(), T0, T1)
        ids = [r["job_id"] for r in first]
        second = watchman_boot.post_boot_rings(base_jobs(), T0, T1,
                                               rung_ledger=ids)
        self.assertEqual(second, [])

    def test_corrupted_counter_changes_nothing(self):
        clean = watchman_boot.post_boot_rings(base_jobs(), T0, T1)
        poisoned_jobs = []
        for job in base_jobs():
            copy_job = dict(job)
            copy_job["seen_counter"] = 999999
            poisoned_jobs.append(copy_job)
        poisoned = watchman_boot.post_boot_rings(poisoned_jobs, T0, T1)
        self.assertEqual([r["job_id"] for r in poisoned],
                         [r["job_id"] for r in clean])
        note = watchman_boot.verify_boot_cycle(
            base_jobs(), T0, T1, ["lease-dead"])
        self.assertTrue(note["counter_ignored"])

    def test_sweep_reconciliation_agrees(self):
        note = watchman_boot.verify_boot_cycle(
            base_jobs(), T0, T1, ["lease-dead"])
        self.assertTrue(note["reconciled"])
        self.assertEqual(note["total_rings"], 3)
        self.assertEqual(note["arrived_count"], 2)
        self.assertEqual(note["lease_expired_count"], 1)

    def test_sweep_mismatch_named_never_fudged(self):
        note = watchman_boot.verify_boot_cycle(
            base_jobs(), T0, T1, ["job-stranger"])
        self.assertFalse(note["reconciled"])
        self.assertEqual(note["mismatch"]["missing"], ["lease-dead"])
        self.assertEqual(note["mismatch"]["extra"], ["job-stranger"])

    def test_inputs_never_mutated(self):
        jobs = base_jobs()
        original = copy.deepcopy(jobs)
        ledger = ["arrive-1"]
        watchman_boot.post_boot_rings(jobs, T0, T1, rung_ledger=ledger)
        watchman_boot.verify_boot_cycle(jobs, T0, T1, ["lease-dead"])
        self.assertEqual(jobs, original)
        self.assertEqual(ledger, ["arrive-1"])

    def test_note_carries_no_push_or_announcement(self):
        note = watchman_boot.verify_boot_cycle(
            base_jobs(), T0, T1, ["lease-dead"])
        self.assertNotIn("push", note)
        self.assertNotIn("announcement", note)
        lines = watchman_boot.boot_brief_lines(note)
        self.assertTrue(any("arrive-1" in line for line in lines))
        self.assertTrue(any("reconciled" in line for line in lines))

    def test_module_carries_no_push_path(self):
        path = os.path.join("intel", "watchman_boot.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("import push", source)
        self.assertNotIn("socket", source)
        self.assertNotIn("urllib", source)

    def test_drill_passes(self):
        proc = subprocess.run(
            [sys.executable, "intel/drills/watchman_boot.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("15 PASS, 0 FAIL", proc.stdout)

    def test_eval_note_names_os129(self):
        with open("intel/evals/watchman_boot.md",
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("OS-129", text)
        self.assertIn("Buffy", text)

    def test_new_files_carry_no_em_dash(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("\u2014", text, path)


if __name__ == "__main__":
    unittest.main()
