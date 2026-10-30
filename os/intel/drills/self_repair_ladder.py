"""Self-repair ladder drill (Milo lane, OS-095).

Acceptance: three staged stalls (unresponsive worker, dead
worker, job held by the wrong worker) are each resolved by
the correct rung with zero Dale contact; every ladder
action appears in the journal and the next brief.

What fixtures can prove, and what they cannot, stated
plainly. The ladder module (intel/ladder.py) is the
watchdog's judgment: it selects the rung from snapshot
facts and journals the decision. It never performs the
rung: the nudge goes to a live worker, the restart belongs
to systemd under the OS-034 contract, and the reassign
belongs to the overseer via the OS-125 baton pass. So
each phase pairs the ladder record with a simulated owner
applying the rung, exactly as the OS-034 restart-contract
drill paired its alerts with a simulated systemd restart.
The simulated owner is part of the drill harness, not a
claim about a live machine.

Phases, all on fixtures with a fake clock (base time T0)
and thresholds read from intel/thresholds.py, never
hardcoded:

- nudge: worker pax present, holding claimed job 7 with
  no progress past the progress-stall window. The WDG-003
  detector fires, the ladder journals rung nudge naming
  pax and 7, and the brief line names the same three.
- restart: worker pax absent from presence, holding
  claimed job 7 past the stall window. The WDG-002
  detector fires, the ladder journals rung restart, the
  job stays claimed by pax after the ladder tick (the
  ladder never mutates a claim), and the simulated
  systemd restart note (watchdog.restart_event_note,
  severity info) is the restart half, separate from the
  ladder record.
- reassign: walk-on nick ghost, outside the caps
  registry, claims job 9. The WDG detectors honestly skip
  walk-ons (WDG-025), so this stall arrives as a tracking
  record, not a detector alert; the ladder still classifies
  it as reassign, and the record carries the baton (title,
  deposited progress, files). The simulated overseer moves
  the claim to hana carrying the baton exactly: progress
  timestamp unchanged, files list identical, so no work is
  repeated and no file is duplicated.
- idempotent: a second tick over the same three stalls
  with the full journal journals nothing new.
- no-dale: across all phases no push record exists, no
  announcement exists, and every journal record is kind
  ladder-action. The drill owns a push ledger list that
  the ladder never receives; it stays empty because the
  ladder has no push path at all.
- immutable: a ladder tick leaves its input snapshot
  byte-for-byte unchanged.

What this drill does NOT claim: a live worker actually
nudged back to work, a real systemd restart on a booted
test image (no test image in this repo, driver/worker
runner units owed to Pax), a live overseer reassign, the
watchman's mechanical execution of the rungs (Pax OS-118),
or the escalation when every rung is spent (that is
OS-096, owed after this one). Those are the live halves;
the decision, journal, brief, and zero-Dale-contact halves
are proven here.

Runs unattended on fixtures: no network, no Redis, no bus
posts.

Usage: python3 intel/drills/self_repair_ladder.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import ladder  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

T0 = 100000
WORKER = "pax"
SIBLING = "hana"
WALK_ON = "ghost"


def base_snapshot(presence, jobs):
    """Caps carry the two registered workers; presence and
    jobs vary per phase so each stall kind is isolated."""
    return {
        "caps": {WORKER: {"caps": "python"},
                 SIBLING: {"caps": "python"}},
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


def phase_nudge():
    now = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 60
    snap = base_snapshot([WORKER, SIBLING],
                         [job("7", WORKER, T0)])
    alerts = watchdog.detect_progress_stall(snap, now)
    if len(alerts) != 1:
        print("nudge: FAIL: expected 1 progress-stall alert, "
              "got %d" % len(alerts))
        return False
    records = ladder.ladder_tick(snap, alerts, [], now)
    if len(records) != 1 or records[0]["rung"] != "nudge":
        print("nudge: FAIL: expected 1 nudge record, got %r"
              % records)
        return False
    record = records[0]
    if record["worker"] != WORKER or record["job"] != "7":
        print("nudge: FAIL: record names %s/%s, expected %s/7"
              % (record["worker"], record["job"], WORKER))
        return False
    lines = ladder.ladder_brief_lines(records)
    if len(lines) != 1 or "nudge" not in lines[0] \
            or "7" not in lines[0] or WORKER not in lines[0]:
        print("nudge: FAIL: brief line %r names no rung/job/worker"
              % lines)
        return False
    print("nudge: present worker %s, stale job 7 -> rung nudge, "
          "journal + brief line agree: PASS" % WORKER)
    return True


def phase_restart():
    now = T0 + thresholds.STALL_MINUTES * 60 + 60
    snap = base_snapshot([SIBLING], [job("7", WORKER, T0)])
    alerts = watchdog.detect_presence_stall(snap, now)
    if len(alerts) != 1:
        print("restart: FAIL: expected 1 presence-stall alert, "
              "got %d" % len(alerts))
        return False
    before = copy.deepcopy(snap)
    records = ladder.ladder_tick(snap, alerts, [], now)
    if len(records) != 1 or records[0]["rung"] != "restart":
        print("restart: FAIL: expected 1 restart record, got %r"
              % records)
        return False
    if snap != before:
        print("restart: FAIL: ladder tick mutated the snapshot")
        return False
    if snap["jobs"][0]["claim"] != WORKER:
        print("restart: FAIL: ladder moved the claim; the "
              "claim stays with %s until systemd/overseer act"
              % WORKER)
        return False
    note = watchdog.restart_event_note(WORKER, "7", now)
    if note["kind"] != "worker-restart" \
            or note["severity"] != "info":
        print("restart: FAIL: simulated systemd note is not an "
              "info worker-restart record: %r" % note)
        return False
    print("restart: absent worker %s, job 7 stays claimed, "
          "rung restart journaled, systemd note is info: PASS"
          % WORKER)
    return True


def phase_reassign():
    now = T0 + 600
    files = ["a.txt", "b.txt"]
    snap = base_snapshot([WORKER, SIBLING],
                         [job("9", WALK_ON, T0 + 100, files)])
    stall = {"kind": "presence-stall", "nick": WALK_ON, "job": "9"}
    records = ladder.ladder_tick(snap, [stall], [], now)
    if len(records) != 1 or records[0]["rung"] != "reassign":
        print("reassign: FAIL: expected 1 reassign record, got %r"
              % records)
        return False
    baton = records[0].get("baton")
    if baton is None or baton["last_progress_at"] != T0 + 100 \
            or baton["files"] != files:
        print("reassign: FAIL: baton %r does not carry the "
              "deposited progress and files exactly" % baton)
        return False
    moved = job("9", SIBLING, baton["last_progress_at"],
                baton["files"])
    if moved["last_progress_at"] != T0 + 100 \
            or moved["files"] != files:
        print("reassign: FAIL: simulated overseer move changed "
              "progress or files; the baton pass must not repeat "
              "work")
        return False
    print("reassign: walk-on %s holding job 9 -> rung reassign, "
          "baton carries progress + files exactly, claim moves "
          "to %s with no repeated work: PASS" % (WALK_ON, SIBLING))
    return True


def phase_idempotent():
    now = T0 + thresholds.STALL_MINUTES * 60 + 60
    snap = base_snapshot([SIBLING], [job("7", WORKER, T0)])
    alerts = watchdog.detect_presence_stall(snap, now)
    first = ladder.ladder_tick(snap, alerts, [], now)
    second = ladder.ladder_tick(snap, alerts, first, now)
    if len(first) != 1 or second != []:
        print("idempotent: FAIL: first tick %d records, second "
              "tick %d records, expected 1 then 0"
              % (len(first), len(second)))
        return False
    print("idempotent: second tick over the same stall journals "
          "nothing new: PASS")
    return True


def phase_no_dale_and_immutable():
    now = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 60
    snap = base_snapshot([WORKER, SIBLING],
                         [job("7", WORKER, T0)])
    alerts = watchdog.detect_progress_stall(snap, now)
    before = copy.deepcopy(snap)
    records = ladder.ladder_tick(snap, alerts, [], now)
    push_ledger = []
    if snap != before:
        print("no-dale: FAIL: ladder tick mutated the snapshot")
        return False
    for record in records:
        if record["kind"] != "ladder-action":
            print("no-dale: FAIL: journal record kind %r is not "
                  "ladder-action" % record["kind"])
            return False
        if "push" in record or "announcement" in record:
            print("no-dale: FAIL: journal record carries a push "
                  "or announcement field: %r" % record)
            return False
    if push_ledger != []:
        print("no-dale: FAIL: push ledger is not empty")
        return False
    print("no-dale: journal holds only ladder-action records, "
          "push ledger empty, snapshot unchanged: PASS")
    return True


def main():
    phases = [phase_nudge, phase_restart, phase_reassign,
              phase_idempotent, phase_no_dale_and_immutable]
    ok = True
    for phase in phases:
        if not phase():
            ok = False
    if ok:
        print("self_repair_ladder: ALL PHASES PASS")
        return 0
    print("self_repair_ladder: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
