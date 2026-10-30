"""Demo silent-failure staging (Milo lane, DEM-011).

DEMO.md Shot 7: Milo's staged worker posts one progress note —
then nothing. No error. No message. The room looks calm. This
script stages exactly that moment for rehearsal, on fixtures,
and prints the cue card the operator reads from: when the
silence starts, what has happened by then, and what the
watchdog will say about it once the stall threshold passes.

It reuses the WDG-020 kill_worker harness (same FakeWorker,
same sweep-free staging) so the demo scenario and the drill
scenario cannot drift apart: the staged worker claims, posts
one progress note, and at the cue stops everything — presence
included, the way a worker that has gone quiet stops showing
up. What this script does NOT do is DEM-012: it does not
measure the catch under the demo thresholds profile (that
profile is DEM-013, not landed), and its timings are fake-
clock seconds, not the human-paced demo run. The cue card
says so, in plain text, so nobody reads fixture seconds as
rehearsal seconds.

Timeline (fake clock, base T0; thresholds read from
intel/thresholds.py, never hardcoded):
  T0        worker claims the demo job
  T0 + 60   worker posts its one progress note
  T0 + 120  CUE: worker goes silent (presence drops, no more
            heartbeats, no more messages)
  cue + stall threshold - 60s: tick yields zero alerts —
            silence is not yet a stall, honestly
  cue + stall threshold + 1s past last progress: tick yields
            exactly one presence-stall alert naming the
            nick, the job, and the last-progress age

Usage: python3 intel/drills/demo_silent_failure.py
Exit 0 with a PASS line per phase on success, 1 on failure.
No network, no Redis, no bus posts: the critical
announcement line is held, per Dale's posting rule.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel.drills import kill_worker  # noqa: E402

JOB_ID = "7"
NICK = "milo"
T0 = 100000
PROGRESS_AT_OFFSET = 60
CUE_OFFSET = 120


def run_drill():
    """Stage the silent failure up to and past the cue.

    Returns a report dict (alert, cue card dict, phase log)
    so tests can assert on the drill's outcome without
    parsing stdout.
    """
    log = []
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {NICK: {"caps": "build"}}}
    worker = kill_worker.FakeWorker(NICK)

    # Phase 1 — the setup the audience sees: claim + one note.
    job = worker.claim(snapshot, JOB_ID, T0)
    worker.progress(snapshot, T0 + PROGRESS_AT_OFFSET, "working on it")
    worker.heartbeat(snapshot, T0 + PROGRESS_AT_OFFSET)
    progress_messages = [m for m in snapshot["messages"]
                         if m.get("nick") == NICK]
    assert len(progress_messages) == 1, (
        f"staged worker must post exactly one progress note, got "
        f"{len(progress_messages)}")
    got = watchdog.tick(snapshot, now=T0 + PROGRESS_AT_OFFSET)
    assert got == [], f"healthy staged worker must yield zero alerts, {got}"
    log.append("phase 1: worker claims job, posts exactly one progress note, "
               "zero alerts while healthy")

    # Phase 2 — THE CUE: the worker goes silent. Nothing after
    # this point comes from the worker: no heartbeat, no
    # message, no presence. The cue card records the moment.
    cue_at = T0 + CUE_OFFSET
    worker.kill(snapshot)
    assert NICK not in snapshot["presence"]
    cue = {
        "shot": 7,
        "nick": NICK,
        "job": JOB_ID,
        "claim_at": T0,
        "progress_at": T0 + PROGRESS_AT_OFFSET,
        "cue_at": cue_at,
        "claim_to_cue_seconds": CUE_OFFSET,
        "progress_notes": len(progress_messages),
        "cue_line": ("On cue, the staged worker posts one progress note, "
                     "then nothing. No error. No message."),
    }
    log.append(f"phase 2: CUE at T0+{CUE_OFFSET}s — worker silent, "
               f"presence dropped, one progress note on record")

    # Phase 3 — silence is not yet a stall: a tick inside the
    # threshold window must stay quiet, or the drill would be
    # teaching the operator to expect an alert too early.
    quiet_at = cue_at + thresholds.STALL_MINUTES * 60 - 60
    before_messages = list(snapshot["messages"])
    before_progress = job.get("last_progress")
    got = watchdog.tick(snapshot, now=quiet_at)
    assert got == [], (
        f"tick inside the stall window must yield zero alerts, got {got}")
    assert snapshot["messages"] == before_messages
    assert job.get("last_progress") == before_progress
    log.append("phase 3: tick inside the stall window yields zero alerts; "
               "no worker activity appears after the cue")

    # Phase 4 — past the threshold, the watchdog says it: one
    # presence-stall alert naming nick, job, last-progress age.
    stall_at = T0 + PROGRESS_AT_OFFSET + thresholds.STALL_MINUTES * 60 + 1
    got = watchdog.tick(snapshot, now=stall_at)
    assert len(got) == 1, (
        f"past-threshold tick must yield exactly one alert, got {len(got)}")
    alert = got[0]
    assert alert["kind"] == "presence-stall", alert
    assert alert["nick"] == NICK, alert
    assert alert["job"] == JOB_ID, alert
    expected_age = stall_at - (T0 + PROGRESS_AT_OFFSET)
    assert alert["last_progress_age_seconds"] == expected_age, alert
    lines = watchdog.announcements_for(got)
    assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
    cue["stall_at"] = stall_at
    cue["last_progress_age_seconds"] = expected_age
    cue["alert_kind"] = alert["kind"]
    log.append(f"phase 4: presence-stall alert names {NICK}/{JOB_ID}, "
               f"last progress {expected_age}s ago; announcement line "
               f"held, not posted")

    return {"alert": alert, "cue": cue, "log": log}


def main(argv=None):
    try:
        report = run_drill()
    except AssertionError as exc:
        print(f"demo_silent_failure drill: FAIL: {exc}")
        return 1
    for line in report["log"]:
        print(f"demo_silent_failure drill: {line}")
    cue = report["cue"]
    print("demo_silent_failure drill: CUE CARD — "
          f"shot {cue['shot']}: {cue['cue_line']} "
          f"(claim to cue: {cue['claim_to_cue_seconds']}s fake-clock; "
          f"progress notes: {cue['progress_notes']}; "
          f"stall alert {cue['alert_kind']} at last-progress age "
          f"{cue['last_progress_age_seconds']}s under production "
          f"thresholds — demo-profile timing is DEM-012/DEM-013, "
          f"not measured here)")
    print("demo_silent_failure drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
