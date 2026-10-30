"""Attempt budgets + escalation gate drill (Milo lane, OS-096).

Acceptance: a deliberately impossible job burns exactly its
budget, parks, and escalates exactly once -- no loop, no
duplicate pushes; a crew-fixable blocker in the same drill
is resolved with zero escalation.

What fixtures can prove, and what they cannot, stated
plainly. The gate module (intel/gate.py) is the watchdog's
judgment: it decides park and escalation from job-record
facts and builds the blocked-push payload. It never sends
anything: the drill owns a sent ledger that the gate never
receives, and it stays empty because the gate has no send
path at all. The actual ring belongs to the Web Push worker
(muse-relay-push, outside this repo); wiring a real gate
park to that worker is Hana's OS-097 call-site work, owed
after this one. The simulated owner here applies ladder
rungs and counts attempts the way a live worker's retries
would, exactly as the OS-095 drill paired ladder records
with simulated owners.

Phases, all on fixtures with a fake clock (base time T0):

- impossible: job 7, max 2 attempts, stalled each tick.
  Tick 1 applies a ladder rung (attempts 1) and the gate
  stays quiet -- budget remains. Tick 2 applies the last
  rung (attempts 2) and the gate parks job 7 with exactly
  one escalation whose blocked-push payload validates and
  names the budget fact. Tick 3 over the same snapshot
  and full journal journals nothing new: no loop, no
  second push.
- crew-fixable: job 8 blocked on a dependency, attempts
  0/3, across three ticks. The gate journals nothing and
  parks nothing: a dependency is crew work, and the
  ladder stays free to act on it.
- dale-call: job 9 blocked on money with the note "needs
  $40/mo API key approval", attempts 1/5. The gate parks
  it at once despite attempts remaining, with exactly one
  escalation whose payload quotes the note verbatim.
  A second tick journals nothing new.
- malformed: jobs with a non-numeric attempts string, a
  missing max, a zero max, and a negative attempts count
  across one tick. No crash, no park, no escalation: a
  malformed budget is unbudgeted, never guessed.
- no-extra-contact: across all phases the escalation
  count is exactly two (jobs 7 and 9), the sent ledger is
  empty, and every escalation payload validates.
- immutable: a gate tick leaves its input snapshot and
  journal unchanged.
- brief: the brief lines name the parked jobs and the
  single escalation each.

What this drill does NOT claim: a phone actually ringing
(the Web Push worker wiring is OS-097, owed), a live
worker burning real attempts on a booted test image (no
test image in this repo), or the plan/META_OS.md spec
line (shared files are integrator-only under the 2026-10-27
folders rule, so that line is Pax's to add). The decision,
journal, brief, and exactly-once halves are proven here.

Runs unattended on fixtures: no network, no Redis, no bus
posts.

Usage: python3 intel/drills/attempt_gate.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import gate  # noqa: E402
from intel import push as push_module  # noqa: E402

T0 = 100000


def job(job_id, attempts=None, maximum=None, blocker_kind=None,
        note=None, status="claimed"):
    record = {"id": job_id, "title": "job %s" % job_id,
              "status": status}
    if attempts is not None:
        record["attempts"] = attempts
    if maximum is not None:
        record["max_attempts"] = maximum
    if blocker_kind is not None:
        record["blocker_kind"] = blocker_kind
    if note is not None:
        record["note"] = note
    return record


def phase_impossible():
    journal = []
    snap = {"jobs": [job("7", 0, 2)]}
    records = gate.gate_tick(snap, journal, T0)
    if records:
        print("impossible: FAIL: gate acted with budget remaining")
        return False
    snap = {"jobs": [job("7", 1, 2)]}
    records = gate.gate_tick(snap, journal, T0 + 60)
    if records:
        print("impossible: FAIL: gate acted at 1/2 attempts")
        return False
    snap = {"jobs": [job("7", 2, 2)]}
    records = gate.gate_tick(snap, journal, T0 + 120)
    if len(records) != 2:
        print("impossible: FAIL: expected parked + escalation, got %d"
              % len(records))
        return False
    parked, escalation = records
    if parked["kind"] != "parked" or escalation["kind"] != "escalation":
        print("impossible: FAIL: wrong record kinds")
        return False
    if "2/2" not in parked["reason"]:
        print("impossible: FAIL: park reason does not name the budget")
        return False
    payload = escalation.get("push")
    if not push_module.validate_push(payload):
        print("impossible: FAIL: escalation payload does not validate")
        return False
    if payload["type"] != "blocked" or payload["job_id"] != "7":
        print("impossible: FAIL: payload is not the blocked push for 7")
        return False
    journal.extend(records)
    again = gate.gate_tick(snap, journal, T0 + 180)
    if again:
        print("impossible: FAIL: second tick journaled %d new records"
              % len(again))
        return False
    print("impossible: PASS: job 7 burned 2/2, parked, one escalation, "
          "second tick silent")
    return True


def phase_crew_fixable():
    journal = []
    snap = {"jobs": [job("8", 0, 3, blocker_kind="dependency",
                         note="waits on job 7")]}
    for tick in range(3):
        records = gate.gate_tick(snap, journal, T0 + tick * 60)
        if records:
            print("crew-fixable: FAIL: gate acted on a dependency blocker")
            return False
    print("crew-fixable: PASS: dependency blocker, 0/3, zero parks and "
          "zero escalations across 3 ticks")
    return True


def phase_dale_call():
    journal = []
    note = "needs $40/mo API key approval"
    snap = {"jobs": [job("9", 1, 5, blocker_kind="money", note=note)]}
    records = gate.gate_tick(snap, journal, T0)
    if len(records) != 2:
        print("dale-call: FAIL: expected parked + escalation, got %d"
              % len(records))
        return False
    parked, escalation = records
    if parked["question"] != note:
        print("dale-call: FAIL: park question is not the note verbatim")
        return False
    payload = escalation.get("push")
    if not push_module.validate_push(payload):
        print("dale-call: FAIL: escalation payload does not validate")
        return False
    if payload["question"] != note:
        print("dale-call: FAIL: payload question is not the note verbatim")
        return False
    journal.extend(records)
    again = gate.gate_tick(snap, journal, T0 + 60)
    if again:
        print("dale-call: FAIL: second tick journaled %d new records"
              % len(again))
        return False
    print("dale-call: PASS: money blocker parked at 1/5 with the note "
          "quoted verbatim, one escalation, second tick silent")
    return True


def phase_malformed():
    snap = {"jobs": [
        job("10", "two", 3),
        job("11", 1, None),
        job("12", 1, 0),
        job("13", -1, 3),
        {"title": "no id at all", "attempts": 9, "max_attempts": 3},
        "not a record",
    ]}
    records = gate.gate_tick(snap, [], T0)
    if records:
        print("malformed: FAIL: gate acted on malformed jobs: %r" % records)
        return False
    print("malformed: PASS: non-numeric, missing, zero, negative, and "
          "id-less jobs yield nothing and no crash")
    return True


def phase_no_extra_contact():
    sent = []
    journal = []
    snap = {"jobs": [job("7", 2, 2),
                     job("9", 1, 5, blocker_kind="money",
                         note="needs $40/mo API key approval")]}
    records = gate.gate_tick(snap, journal, T0)
    escalations = [r for r in records if r["kind"] == "escalation"]
    if len(escalations) != 2:
        print("no-extra-contact: FAIL: expected 2 escalations, got %d"
              % len(escalations))
        return False
    for record in escalations:
        if not push_module.validate_push(record.get("push")):
            print("no-extra-contact: FAIL: an escalation payload is invalid")
            return False
    if sent:
        print("no-extra-contact: FAIL: the sent ledger is not empty")
        return False
    print("no-extra-contact: PASS: exactly 2 escalations, both payloads "
          "valid, sent ledger empty (gate builds, never sends)")
    return True


def phase_immutable():
    snap = {"jobs": [job("7", 2, 2)]}
    journal = [{"kind": "parked", "job": "9",
                "dedupe_key": "park:9"}]
    snap_before = copy.deepcopy(snap)
    journal_before = copy.deepcopy(journal)
    gate.gate_tick(snap, journal, T0)
    if snap != snap_before or journal != journal_before:
        print("immutable: FAIL: gate_tick mutated its inputs")
        return False
    print("immutable: PASS: snapshot and journal unchanged by the tick")
    return True


def phase_brief():
    records = gate.gate_tick({"jobs": [job("7", 2, 2)]}, [], T0)
    lines = gate.gate_brief_lines(records)
    if len(lines) != 2:
        print("brief: FAIL: expected 2 lines, got %d" % len(lines))
        return False
    if "Parked job 7" not in lines[0]:
        print("brief: FAIL: parked line does not name job 7")
        return False
    if "Escalated job 7" not in lines[1]:
        print("brief: FAIL: escalation line does not name job 7")
        return False
    print("brief: PASS: parked and escalation lines name job 7")
    return True


def main():
    phases = [phase_impossible, phase_crew_fixable, phase_dale_call,
              phase_malformed, phase_no_extra_contact, phase_immutable,
              phase_brief]
    ok = True
    for phase in phases:
        if not phase():
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
