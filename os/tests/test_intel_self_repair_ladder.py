"""tests/test_intel_self_repair_ladder.py -- OS-095: self-repair ladder.

OS-095 puts the ladder before the report: a stall is
resolved by nudge, restart, or reassign, each rung
journaled with its reason, with zero Dale contact. The
live halves (a real nudge, a systemd restart, an overseer
reassign) belong to the test image and the watchman, so
these tests pin the decision, journal, brief, and
no-Dale-contact halves on fixtures, exactly as the OS-034
tests pinned the contract halves:

- A present registered worker with a stale job gets nudge.
- An absent registered worker holding a job gets restart.
- A claimer outside the caps registry gets reassign, with
  a baton carrying the deposited progress and files.
- A malformed stall yields no action, never a crash.
- A stall whose job is missing from the snapshot yields
  no action.
- A second tick over the same stall journals nothing new.
- The brief line names the rung, the job, and the worker.
- A ladder tick never mutates its input snapshot.
- Ladder records carry no push or announcement surface.
- The drill script exists and passes; the eval note and
  the META_OS.md spec record name OS-095.
- None of the new OS-095 files carries an em dash (the
  check.sh new-doc rule).

No bus post, no live Redis, no network, no systemd: pure
fixture calls plus file reads.
"""

import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import ladder  # noqa: E402

T0 = 100000
NEW_FILES = [
    "intel/ladder.py",
    "intel/drills/self_repair_ladder.py",
    "intel/evals/self_repair_ladder.md",
    "intel/evals/self_repair_ladder.log",
    "tests/test_intel_self_repair_ladder.py",
]


def snapshot(presence, jobs):
    return {
        "caps": {"pax": {"caps": "python"},
                 "hana": {"caps": "python"}},
        "presence": presence,
        "jobs": jobs,
        "messages": [],
    }


def job(job_id, claimer, last_progress, files=None):
    record = {"id": job_id, "title": "job %s" % job_id,
              "status": "claimed", "claim": claimer,
              "claimed_at": T0, "last_progress_at": last_progress}
    if files is not None:
        record["files"] = files
    return record


class LadderRungTest(unittest.TestCase):
    def test_present_registered_worker_gets_nudge(self):
        snap = snapshot(["pax", "hana"], [job("7", "pax", T0)])
        rung, _ = ladder.classify(
            snap, {"kind": "progress-stall", "nick": "pax",
                   "job": "7"})
        self.assertEqual(rung, "nudge")

    def test_absent_registered_worker_gets_restart(self):
        snap = snapshot(["hana"], [job("7", "pax", T0)])
        rung, _ = ladder.classify(
            snap, {"kind": "presence-stall", "nick": "pax",
                   "job": "7"})
        self.assertEqual(rung, "restart")

    def test_walk_on_claimer_gets_reassign_with_baton(self):
        files = ["a.txt", "b.txt"]
        snap = snapshot(["pax", "hana"],
                        [job("9", "ghost", T0 + 100, files)])
        records = ladder.ladder_tick(
            snap, [{"kind": "presence-stall", "nick": "ghost",
                    "job": "9"}], [], T0 + 600)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["rung"], "reassign")
        self.assertEqual(records[0]["baton"]["last_progress_at"],
                         T0 + 100)
        self.assertEqual(records[0]["baton"]["files"], files)
        self.assertEqual(records[0]["baton"]["title"], "job 9")

    def test_malformed_stall_yields_no_action(self):
        snap = snapshot(["pax"], [job("7", "pax", T0)])
        for stall in [{}, {"nick": "pax"}, {"job": "7"},
                      {"nick": "", "job": "7"}, None, "pax"]:
            self.assertIsNone(ladder.ladder_action(snap, stall, T0))

    def test_missing_job_yields_no_action(self):
        snap = snapshot(["pax"], [job("7", "pax", T0)])
        self.assertIsNone(ladder.ladder_action(
            snap, {"kind": "progress-stall", "nick": "pax",
                   "job": "99"}, T0))

    def test_second_tick_journals_nothing_new(self):
        snap = snapshot(["hana"], [job("7", "pax", T0)])
        stall = {"kind": "presence-stall", "nick": "pax", "job": "7"}
        first = ladder.ladder_tick(snap, [stall], [], T0 + 700)
        second = ladder.ladder_tick(snap, [stall], first, T0 + 700)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_brief_line_names_rung_job_worker(self):
        snap = snapshot(["pax", "hana"], [job("7", "pax", T0)])
        records = ladder.ladder_tick(
            snap, [{"kind": "progress-stall", "nick": "pax",
                    "job": "7"}], [], T0 + 700)
        lines = ladder.ladder_brief_lines(records)
        self.assertEqual(len(lines), 1)
        self.assertIn("nudge", lines[0])
        self.assertIn("7", lines[0])
        self.assertIn("pax", lines[0])

    def test_tick_never_mutates_snapshot(self):
        snap = snapshot(["hana"], [job("7", "pax", T0)])
        before = copy.deepcopy(snap)
        ladder.ladder_tick(
            snap, [{"kind": "presence-stall", "nick": "pax",
                    "job": "7"}], [], T0 + 700)
        self.assertEqual(snap, before)

    def test_records_carry_no_push_surface(self):
        snap = snapshot(["pax", "hana"], [job("7", "pax", T0)])
        records = ladder.ladder_tick(
            snap, [{"kind": "progress-stall", "nick": "pax",
                    "job": "7"}], [], T0 + 700)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["kind"], "ladder-action")
        self.assertNotIn("push", records[0])
        self.assertNotIn("announcement", records[0])
        with open("intel/ladder.py") as handle:
            source = handle.read()
        self.assertNotIn("from intel import push", source)
        self.assertNotIn("import intel.push", source)

    def test_drill_passes_and_docs_exist(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/self_repair_ladder.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ALL PHASES PASS", result.stdout)
        with open("intel/evals/self_repair_ladder.md") as handle:
            self.assertIn("OS-095", handle.read())
        with open("plan/META_OS.md") as handle:
            meta_os = handle.read()
        self.assertIn("OS-095", meta_os)
        self.assertIn("self_repair_ladder.py", meta_os)

    def test_no_em_dash_in_new_files(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
