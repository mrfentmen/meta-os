"""Kill-a-worker drill (Milo lane, WDG-020).

Scenario, as the demo will run it live: a fake worker claims a
job, posts one progress note, keeps heartbeating — then dies
mid-job. The watchdog must raise exactly one presence-stall
alert naming the nick, the job, and the last-progress age, and
once the job's lease expires the sweep must requeue the job so
the stall alert stops firing and another worker can claim it.

Runs unattended on fixtures: no network, no Redis, no bus
posts. The sweep half mirrors the rule jobs.py already ships
(_claim_or_requeue: a claimed job whose lease has expired
reopens — status back to open, claim fields cleared). The
watchdog itself never touches job state (v1 alerts only), so
the drill applies the sweep rule to the fixture snapshot and
then re-ticks to prove the alert auto-resolves; it does not
claim the watchdog performed the requeue.

Timeline uses a fake clock (base time T0) so the drill is
deterministic: thresholds are read from intel/thresholds.py,
never hardcoded, so a threshold retune retunes the drill.

Usage: python3 intel/drills/kill_worker.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

JOB_ID = "7"
NICK = "pax"
T0 = 100000


class FakeWorker:
    """A fixture worker: claims, heartbeats, posts progress, dies.

    It edits the snapshot dict in place, the way the real
    worker's actions would change the live snapshot the next
    tick reads. Killing it means exactly one thing: presence
    stops and heartbeats stop. It never deletes its own job —
    a dead worker's job is the sweep's problem, not its own.
    """

    def __init__(self, nick):
        self.nick = nick
        self.alive = True

    def claim(self, snapshot, job_id, now):
        job = {"id": job_id, "title": "demo job",
               "status": "claimed", "claim": self.nick,
               "claimed_at": now,
               "lease": thresholds.LEASE_DEFAULT_SECONDS,
               "lease_until": now + thresholds.LEASE_DEFAULT_SECONDS}
        snapshot.setdefault("jobs", []).append(job)
        self.heartbeat(snapshot, now)
        return job

    def heartbeat(self, snapshot, now):
        if self.nick not in snapshot.setdefault("presence", []):
            snapshot["presence"].append(self.nick)
        for job in snapshot.get("jobs", []):
            if job.get("claim") == self.nick:
                job["last_heartbeat"] = now

    def progress(self, snapshot, now, text="working on it"):
        for job in snapshot.get("jobs", []):
            if job.get("claim") == self.nick:
                job["last_progress"] = now
        snapshot.setdefault("messages", []).append(
            {"nick": self.nick, "text": text})

    def kill(self, snapshot):
        """Stop heartbeats and drop out of presence, mid-job."""
        self.alive = False
        presence = snapshot.get("presence", [])
        if self.nick in presence:
            presence.remove(self.nick)


def sweep_expired_leases(snapshot, now):
    """Fixture mirror of jobs.py _claim_or_requeue's requeue rule.

    A claimed job whose lease_until has passed reopens: status
    back to open, claim fields cleared (claim, claim_host,
    claimed_at, lease_until — exactly the fields jobs.py
    _requeue_fields deletes). A claimed job whose lease still
    holds is left untouched. Returns the requeued job ids.
    """
    requeued = []
    for job in snapshot.get("jobs", []):
        if job.get("status") != "claimed":
            continue
        lease_until = job.get("lease_until")
        if not isinstance(lease_until, (int, float)):
            continue
        if int(now) < int(lease_until):
            continue
        for field in ("claim", "claim_host", "claimed_at",
                      "lease_until"):
            job.pop(field, None)
        job["status"] = "open"
        requeued.append(str(job.get("id", "")))
    return requeued


def run_drill():
    """Run every phase; raise AssertionError on any failure.

    Returns a report dict (alert, requeued ids, phase log) so
    tests can assert on the drill's outcome without parsing
    stdout. All ages are computed from thresholds, not fixed.
    """
    log = []
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {NICK: {"caps": "build"}}}
    worker = FakeWorker(NICK)

    # Phase 1 — healthy worker: claim, one progress note, beats.
    job = worker.claim(snapshot, JOB_ID, T0)
    worker.progress(snapshot, T0 + 120, "working on it")
    worker.heartbeat(snapshot, T0 + 300)
    got = watchdog.tick(snapshot, now=T0 + 300)
    assert got == [], f"healthy worker must yield zero alerts, got {got}"
    log.append("phase 1: healthy worker yields zero alerts")

    # Phase 2 — the kill: heartbeats stop, presence goes dark.
    worker.kill(snapshot)
    assert NICK not in snapshot["presence"]
    stall_at = T0 + 300 + thresholds.STALL_MINUTES * 60 + 61
    got = watchdog.tick(snapshot, now=stall_at)
    assert len(got) == 1, (
        f"dead worker must yield exactly one alert, got {len(got)}: {got}")
    alert = got[0]
    assert alert["kind"] == "presence-stall", alert
    assert alert["nick"] == NICK, alert
    assert alert["job"] == JOB_ID, alert
    expected_age = stall_at - (T0 + 120)
    assert alert["last_progress_age_seconds"] == expected_age, alert
    lines = watchdog.announcements_for(got)
    assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
    log.append(f"phase 2: presence-stall alert names {NICK}/{JOB_ID}, "
               f"age {expected_age}s; announcement line held, not posted")

    # Phase 3 — the sweep must NOT requeue before the lease ends.
    assert sweep_expired_leases(snapshot, stall_at) == []
    assert job["status"] == "claimed"
    log.append("phase 3: unexpired lease stays claimed (no early requeue)")

    # Phase 4 — lease expires, sweep requeues, alert auto-resolves.
    requeue_at = T0 + thresholds.LEASE_DEFAULT_SECONDS + 1
    requeued = sweep_expired_leases(snapshot, requeue_at)
    assert requeued == [JOB_ID], requeued
    assert job["status"] == "open"
    assert "claim" not in job and "lease_until" not in job
    got = watchdog.tick(snapshot, now=requeue_at)
    assert got == [], f"requeued job must stop firing, got {got}"
    log.append("phase 4: lease expiry requeues job; re-tick yields zero "
               "alerts, job open for the next worker")

    return {"alert": alert, "requeued": requeued, "log": log}


def main(argv=None):
    try:
        report = run_drill()
    except AssertionError as exc:
        print(f"kill_worker drill: FAIL: {exc}")
        return 1
    for line in report["log"]:
        print(f"kill_worker drill: {line}")
    print("kill_worker drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
