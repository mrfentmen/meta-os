"""Dead-dep drill (Milo lane, WDG-022).

Scenario, as the demo will run it live: job A is posted, job
B is posted depending on A, then A gets blocked with a
reason. B cannot proceed until a human unblocks or replaces
A, so the watchdog must raise exactly one critical dead-dep
alert naming both jobs and A's blocking reason verbatim —
and keep raising it while A stays blocked, then stop once A
is unblocked.

Runs unattended on fixtures: no network, no Redis, no bus
posts. The alert line is held, never posted (Dale's posting
rule); the drill asserts the held announcement line exists
rather than sending it.

The dead-dep detector (WDG-005) has no age gate by design:
the dep's blocked/failed-final state IS the threshold, so
the drill ages the clock between phases to show the alert
persists across ticks rather than to cross a threshold.

Usage: python3 intel/drills/dead_dep.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import watchdog  # noqa: E402

DEP_ID = "1"
JOB_ID = "2"
REASON = "needs Pax sign-off on the key shape"
NOW = 10000


def _post(snapshot, job_id, deps=None):
    job = {"id": job_id, "title": f"job {job_id}",
           "status": "open"}
    if deps is not None:
        job["deps"] = deps
    snapshot.setdefault("jobs", []).append(job)
    return job


def _block(snapshot, job_id, reason):
    for job in snapshot["jobs"]:
        if job["id"] == job_id:
            job["status"] = "blocked"
            job["note"] = reason
            return job
    raise AssertionError(f"no job {job_id} to block")


def _unblock(snapshot, job_id):
    for job in snapshot["jobs"]:
        if job["id"] == job_id:
            job["status"] = "open"
            job.pop("note", None)
            return job
    raise AssertionError(f"no job {job_id} to unblock")


def run_drill():
    """Run every phase; raise AssertionError on any failure.

    Returns a report dict (alert, phase log) so tests can
    assert on the drill's outcome without parsing stdout.
    """
    log = []
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {}}

    # Phase 1 — A and B posted, A live: B waits on a healthy
    # dep, so the watchdog has nothing to warn about.
    _post(snapshot, DEP_ID)
    _post(snapshot, JOB_ID, deps=DEP_ID)
    got = watchdog.tick(snapshot, now=NOW)
    assert got == [], f"live dep must yield zero alerts, got {got}"
    log.append("phase 1: posted A and B(deps A) with A live "
               "yield zero alerts")

    # Phase 2 — A blocked with a reason: the alert must fire
    # naming B, naming A, and carrying A's reason verbatim,
    # while B is still open and waiting.
    _block(snapshot, DEP_ID, REASON)
    got = watchdog.tick(snapshot, now=NOW + 60)
    assert len(got) == 1, (
        f"blocked dep must yield exactly one alert, "
        f"got {len(got)}: {got}")
    alert = got[0]
    assert alert["kind"] == "dead-dep", alert
    assert alert["severity"] == "critical", alert
    assert alert["job"] == JOB_ID, alert
    assert alert["dep"] == DEP_ID, alert
    assert alert["blocking_reason"] == REASON, alert
    assert REASON in alert["explanation"], alert
    assert JOB_ID in alert["explanation"], alert
    assert DEP_ID in alert["explanation"], alert
    assert alert["dedupe_key"] == f"dead-dep:{JOB_ID}:{DEP_ID}", alert
    lines = watchdog.announcements_for(got)
    assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
    log.append(f"phase 2: critical dead-dep alert names job "
               f"{JOB_ID} blocked on dep {DEP_ID} for reason "
               f"'{REASON}' verbatim; announcement line held, "
               f"not posted")

    # Phase 3 — A still blocked, clock aged: the same alert
    # (same dedupe key) must keep firing. A dead dep is not a
    # one-tick event; it stays dead until a human acts.
    got = watchdog.tick(snapshot, now=NOW + 3600)
    assert len(got) == 1, f"still-blocked dep must keep firing, got {got}"
    assert got[0]["dedupe_key"] == alert["dedupe_key"], got
    log.append("phase 3: while A stays blocked, the same "
               "dead-dep alert keeps firing (same dedupe key)")

    # Phase 4 — A unblocked: B's dep is live again, so the
    # alert stops firing. The watchdog reports the condition,
    # it does not keep a permanent record of a cleared one.
    _unblock(snapshot, DEP_ID)
    got = watchdog.tick(snapshot, now=NOW + 3660)
    assert got == [], f"unblocked dep must stop firing, got {got}"
    log.append("phase 4: after A is unblocked, the dead-dep "
               "alert stops firing")

    return {"alert": alert, "log": log}


def main(argv=None):
    try:
        report = run_drill()
    except AssertionError as exc:
        print(f"dead-dep drill: FAIL: {exc}")
        return 1
    for line in report["log"]:
        print(f"dead-dep drill: {line}")
    print("dead-dep drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
