"""tests/test_intel_timer_sweep.py -- OS-121: timer fallback sweep.

The timer sweep is the safety net under the bell: with
the watchman dead, a posted job is claimed within one
sweep interval by the timer path alone; with the
watchman healthy, sweeps produce zero duplicate claims.
These tests pin the decision layer on fixtures:

- Dead watchman: a job posted at 100 is claimed at the
  300 tick and a job posted at 550 at the 600 tick, so
  no claim waits longer than one interval (300).
- Healthy watchman: the sweep runs but claims nothing,
  across repeated ticks, so zero duplicate claims.
- Unknown watchman: the sweep holds and claims nothing,
  because missing evidence is never read as dead.
- Lease discipline: claimed and done jobs are never
  claimed, and a job already in the sweep ledger is
  never claimed again.
- Addressing: outsider-addressed and unaddressed jobs
  are never claimed; both are reported in skipped.
- Cadence: a tick before last sweep plus interval does
  not run; a future job is never claimed early; a
  duplicate input is claimed once.
- Malformed records never claim and never crash.
- Inputs are never mutated, the note carries no push
  and no announcement field, and the module imports no
  push module.
- The drill script exists and passes; the eval note
  names OS-121.
- None of the new OS-121 files carries an em dash (the
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

from intel import timer_sweep  # noqa: E402

INTERVAL = 300
ROSTER = ["milo", "hana", "rowan"]
NEW_FILES = [
    "intel/timer_sweep.py",
    "intel/drills/timer_sweep.py",
    "intel/evals/timer_sweep.md",
    "intel/evals/timer_sweep.log",
    "tests/test_intel_timer_sweep.py",
]


def base_jobs():
    return [
        {"id": "job-early", "status": "open", "posted_at": 100,
         "addressed_to": "milo"},
        {"id": "job-late", "status": "open", "posted_at": 550,
         "addressed_to": "hana"},
        {"id": "job-future", "status": "open", "posted_at": 950,
         "addressed_to": "rowan"},
        {"id": "job-claimed", "status": "claimed",
         "claimed_by": "rowan", "posted_at": 50,
         "addressed_to": "rowan"},
        {"id": "job-done", "status": "done", "posted_at": 50,
         "addressed_to": "milo"},
        {"id": "job-outsider", "status": "open", "posted_at": 100,
         "addressed_to": "outsider"},
        {"id": "job-unaddressed", "status": "open", "posted_at": 100},
    ]


def tick(jobs, now, alive, last=None, ledger=None):
    return timer_sweep.sweep_cycle(
        jobs, now, alive, sweep_interval_seconds=INTERVAL,
        last_sweep_at=last, sweep_ledger=ledger, local_agents=ROSTER)


class TestTimerSweep(unittest.TestCase):
    def test_dead_watchman_claims_within_one_interval(self):
        first = tick(base_jobs(), 0, False)
        self.assertTrue(first["ran"])
        self.assertEqual(first["claims"], [])
        second = tick(base_jobs(), 300, False, last=0,
                      ledger=first["sweep_ledger_after"])
        self.assertEqual([c["job_id"] for c in second["claims"]],
                         ["job-early"])
        self.assertEqual(second["claims"][0]["claimed_by"], "milo")
        self.assertEqual(second["claims"][0]["via"], "timer_sweep")
        self.assertLessEqual(second["claims"][0]["claimed_at"] - 100,
                             INTERVAL)
        third = tick(base_jobs(), 600, False, last=300,
                     ledger=second["sweep_ledger_after"])
        self.assertEqual([c["job_id"] for c in third["claims"]],
                         ["job-late"])
        self.assertLessEqual(third["claims"][0]["claimed_at"] - 550,
                             INTERVAL)

    def test_healthy_watchman_claims_nothing_across_ticks(self):
        first = tick(base_jobs(), 300, True)
        self.assertTrue(first["ran"])
        self.assertEqual(first["claims"], [])
        second = tick(base_jobs(), 600, True, last=300,
                      ledger=first["sweep_ledger_after"])
        self.assertEqual(second["claims"], [])
        self.assertEqual(second["sweep_ledger_after"], [])

    def test_unknown_watchman_holds(self):
        note = tick(base_jobs(), 300, None)
        self.assertEqual(note["claims"], [])
        self.assertIn("unknown", note["reason"])

    def test_claimed_and_done_jobs_never_claimed(self):
        note = tick(base_jobs(), 600, False, last=300)
        skipped = {s["job_id"]: s["reason"] for s in note["skipped"]}
        self.assertIn("not open", skipped["job-claimed"])
        self.assertIn("not open", skipped["job-done"])
        self.assertNotIn("job-claimed",
                         [c["job_id"] for c in note["claims"]])

    def test_sweep_ledger_prevents_duplicate_claims(self):
        first = tick(base_jobs(), 300, False)
        second = tick(base_jobs(), 600, False, last=300,
                      ledger=first["sweep_ledger_after"])
        self.assertNotIn("job-early",
                         [c["job_id"] for c in second["claims"]])
        third = tick(base_jobs(), 900, False, last=600,
                     ledger=second["sweep_ledger_after"])
        self.assertEqual(third["claims"], [])

    def test_addressing_rules(self):
        note = tick(base_jobs(), 600, False, last=300)
        skipped = {s["job_id"]: s["reason"] for s in note["skipped"]}
        self.assertEqual(skipped["job-outsider"],
                         "addressed elsewhere")
        self.assertIn("unaddressed", skipped["job-unaddressed"])

    def test_cadence_and_future_jobs(self):
        early = tick(base_jobs(), 150, False, last=0)
        self.assertFalse(early["ran"])
        self.assertEqual(early["claims"], [])
        self.assertEqual(early["next_sweep_at"], 300)
        note = tick(base_jobs(), 600, False, last=300)
        self.assertNotIn("job-future",
                         [c["job_id"] for c in note["claims"]])

    def test_duplicate_input_claimed_once(self):
        jobs = base_jobs() + [{"id": "job-early", "status": "open",
                               "posted_at": 100, "addressed_to": "milo"}]
        note = tick(jobs, 300, False)
        self.assertEqual(
            [c["job_id"] for c in note["claims"]].count("job-early"), 1)

    def test_malformed_records_never_claim_or_crash(self):
        jobs = base_jobs() + ["not-a-record",
                              {"status": "open", "posted_at": 100,
                               "addressed_to": "milo"}]
        note = tick(jobs, 300, False)
        self.assertEqual([c["job_id"] for c in note["claims"]],
                         ["job-early"])

    def test_no_roster_claims_nothing(self):
        note = timer_sweep.sweep_cycle(
            base_jobs(), 300, False,
            sweep_interval_seconds=INTERVAL, local_agents=None)
        self.assertEqual(note["claims"], [])

    def test_inputs_never_mutated_and_no_push_field(self):
        jobs = base_jobs()
        original = copy.deepcopy(jobs)
        ledger = ["job-early"]
        note = tick(jobs, 600, False, last=300, ledger=ledger)
        self.assertEqual(jobs, original)
        self.assertEqual(ledger, ["job-early"])
        self.assertNotIn("push", note)
        self.assertNotIn("announcement", note)

    def test_module_has_no_push_path(self):
        path = os.path.join("intel", "timer_sweep.py")
        with open(path) as handle:
            source = handle.read()
        self.assertNotIn("import push", source)
        self.assertNotIn("from intel import push", source)

    def test_drill_passes_and_eval_names_task(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/timer_sweep.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 FAIL", result.stdout)
        with open(os.path.join("intel", "evals", "timer_sweep.md")) \
                as handle:
            self.assertIn("OS-121", handle.read())

    def test_new_files_exist_and_carry_no_em_dash(self):
        for path in NEW_FILES:
            self.assertTrue(os.path.exists(path), path)
            with open(path) as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
