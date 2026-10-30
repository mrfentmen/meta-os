"""tests/test_intel_attempt_gate.py -- OS-096: attempt budgets +
the escalation gate.

OS-096 ends a job's repair life exactly once: a spent
attempt budget parks the job and fires one blocked push,
and a blocker that is genuinely Dale's call (money,
permission, direction) parks it the same way. Everything
else -- a crew-fixable blocker, an unbudgeted job, a
malformed budget -- stays quiet, and a second tick over a
parked job journals nothing new. The gate builds the push
payload; it never sends it (the Web Push worker sends,
OS-097 wiring owed), so these tests pin the decision,
journal, brief, and exactly-once halves on fixtures:

- A spent budget parks with one escalation whose payload
  validates and names the job.
- A second tick over the parked job journals nothing.
- A Dale-call blocker parks with attempts remaining, and
  its payload quotes the stored note verbatim.
- A Dale-call blocker with no note derives its question
  from the kind in the record, never from nowhere.
- Crew-fixable kinds (dependency, collision, unknown,
  missing) park nothing and escalate nothing.
- An unbudgeted job never parks on attempts; malformed
  figures (non-numeric, negative, zero max) never park
  and never crash.
- A done job never parks, however its figures read.
- Records without an id and non-record entries are
  skipped, never crashed on.
- The brief lines name the parked job and the single
  escalation.
- A gate tick never mutates its input snapshot or journal.
- The gate module carries no send path: no requests, no
  urllib, no socket import.
- The drill script exists and passes; the eval note names
  OS-096.
- None of the new OS-096 files carries an em dash (the
  new-doc rule).

No bus post, no live Redis, no network, no systemd: pure
fixture calls plus file reads.
"""

import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import gate  # noqa: E402
from intel import push as push_module  # noqa: E402

T0 = 100000
NEW_FILES = [
    "intel/gate.py",
    "intel/drills/attempt_gate.py",
    "intel/evals/attempt_gate.md",
    "intel/evals/attempt_gate.log",
    "tests/test_intel_attempt_gate.py",
]


def job(job_id, attempts=None, maximum=None, blocker_kind=None,
        note=None, status="claimed"):
    record = {"id": job_id, "title": "job %s" % job_id, "status": status}
    if attempts is not None:
        record["attempts"] = attempts
    if maximum is not None:
        record["max_attempts"] = maximum
    if blocker_kind is not None:
        record["blocker_kind"] = blocker_kind
    if note is not None:
        record["note"] = note
    return record


class GateTest(unittest.TestCase):
    def test_spent_budget_parks_with_one_valid_escalation(self):
        records = gate.gate_tick({"jobs": [job("7", 2, 2)]}, [], T0)
        self.assertEqual(len(records), 2)
        parked, escalation = records
        self.assertEqual(parked["kind"], "parked")
        self.assertEqual(parked["dedupe_key"], "park:7")
        self.assertIn("2/2", parked["reason"])
        self.assertEqual(escalation["kind"], "escalation")
        self.assertEqual(escalation["dedupe_key"], "escalate:7")
        payload = escalation["push"]
        self.assertTrue(push_module.validate_push(payload))
        self.assertEqual(payload["type"], "blocked")
        self.assertEqual(payload["job_id"], "7")

    def test_second_tick_over_parked_job_is_silent(self):
        first = gate.gate_tick({"jobs": [job("7", 2, 2)]}, [], T0)
        again = gate.gate_tick({"jobs": [job("7", 2, 2)]}, first, T0 + 60)
        self.assertEqual(again, [])

    def test_dale_call_parks_with_attempts_remaining(self):
        note = "needs $40/mo API key approval"
        records = gate.gate_tick(
            {"jobs": [job("9", 1, 5, blocker_kind="money", note=note)]},
            [], T0)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["question"], note)
        self.assertEqual(records[1]["push"]["question"], note)

    def test_dale_call_without_note_derives_question_from_kind(self):
        records = gate.gate_tick(
            {"jobs": [job("9", 1, 5, blocker_kind="permission")]}, [], T0)
        self.assertEqual(len(records), 2)
        self.assertIn("permission", records[0]["question"])
        self.assertTrue(push_module.validate_push(records[1]["push"]))

    def test_crew_fixable_blockers_stay_quiet(self):
        for kind in ("dependency", "collision", "unknown", None):
            records = gate.gate_tick(
                {"jobs": [job("8", 0, 3, blocker_kind=kind)]}, [], T0)
            self.assertEqual(records, [], "kind %r parked" % (kind,))

    def test_unbudgeted_and_malformed_never_park(self):
        cases = [
            job("10", 1, None),
            job("11", "two", 3),
            job("12", 1, 0),
            job("13", -1, 3),
            job("14", 9, 3, status="done"),
        ]
        for case in cases:
            records = gate.gate_tick({"jobs": [case]}, [], T0)
            self.assertEqual(records, [], "job %r parked" % (case,))

    def test_id_less_and_non_record_entries_skipped(self):
        snap = {"jobs": [
            {"title": "no id", "attempts": 9, "max_attempts": 3},
            "not a record",
            None,
        ]}
        self.assertEqual(gate.gate_tick(snap, [], T0), [])
        self.assertEqual(gate.gate_tick({}, [], T0), [])
        self.assertEqual(gate.gate_tick({"jobs": "not a list"}, [], T0), [])

    def test_attempts_left_and_budget_exhausted(self):
        self.assertEqual(gate.attempts_left(job("7", 1, 3)), 2)
        self.assertEqual(gate.attempts_left(job("7", 3, 3)), 0)
        self.assertTrue(gate.budget_exhausted(job("7", 3, 3)))
        self.assertTrue(gate.budget_exhausted(job("7", 4, 3)))
        self.assertFalse(gate.budget_exhausted(job("7", 1, 3)))
        self.assertIsNone(gate.attempts_left(job("7", 1, None)))
        self.assertIsNone(gate.attempts_left(job("7", "two", 3)))
        self.assertIsNone(gate.attempts_left(job("7", True, 3)))

    def test_brief_lines(self):
        records = gate.gate_tick({"jobs": [job("7", 2, 2)]}, [], T0)
        lines = gate.gate_brief_lines(records)
        self.assertEqual(len(lines), 2)
        self.assertIn("Parked job 7", lines[0])
        self.assertIn("Escalated job 7", lines[1])
        self.assertEqual(gate.gate_brief_lines([{"kind": "other"}]), [])

    def test_tick_never_mutates_inputs(self):
        snap = {"jobs": [job("7", 2, 2)]}
        journal = [{"kind": "parked", "job": "9",
                    "dedupe_key": "park:9"}]
        snap_before = copy.deepcopy(snap)
        journal_before = copy.deepcopy(journal)
        gate.gate_tick(snap, journal, T0)
        self.assertEqual(snap, snap_before)
        self.assertEqual(journal, journal_before)

    def test_gate_module_has_no_send_path(self):
        with open("intel/gate.py") as handle:
            source = handle.read()
        for banned in ("import requests", "import urllib", "import socket",
                       "urlopen", ".post("):
            self.assertNotIn(banned, source)

    def test_drill_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/attempt_gate.py"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("impossible: PASS", result.stdout)
        self.assertIn("dale-call: PASS", result.stdout)
        self.assertIn("no-extra-contact: PASS", result.stdout)

    def test_eval_note_names_os096(self):
        with open("intel/evals/attempt_gate.md") as handle:
            text = handle.read()
        self.assertIn("OS-096", text)
        self.assertIn("attempt_gate.log", text)

    def test_new_files_have_no_em_dash(self):
        for path in NEW_FILES:
            with open(path) as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
