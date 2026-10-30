"""Collision drill (Milo lane, WDG-021).

Scenario, as the demo will run it live: two fake workers claim
jobs whose files fields overlap on one path. Neither worker
has finished, neither is stalled, and neither job is done —
yet the watchdog must raise exactly one critical
file-collision alert naming both jobs and the shared path,
before either worker finishes, so the crew can coordinate
before merge time instead of after it.

Runs unattended on fixtures: no network, no Redis, no bus
posts. The alert line is held, never posted (Dale's posting
rule); the drill asserts the held announcement line exists
rather than sending it.

Usage: python3 intel/drills/collision.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import watchdog  # noqa: E402

FIRST_ID = "1"
SECOND_ID = "2"
FIRST_NICK = "pax"
SECOND_NICK = "rowan"
SHARED_PATH = "intel/store.py"
NOW = 10000


class FakeWorker:
    """A fixture worker: claims a job, stays present and fresh.

    Fresh claims with present nicks in the caps registry mean
    no stall, lease-risk, or attempt detector can fire, so any
    alert in this drill is a collision alert, or a test bug —
    the same isolation the WDG-007 suite tests use.
    """

    def __init__(self, nick):
        self.nick = nick

    def claim(self, snapshot, job_id, files):
        job = {"id": job_id, "title": f"job {job_id}",
               "status": "claimed", "claim": self.nick,
               "claimed_at": NOW - 10, "files": files}
        snapshot.setdefault("jobs", []).append(job)
        if self.nick not in snapshot.setdefault("presence", []):
            snapshot["presence"].append(self.nick)
        snapshot.setdefault("caps", {})[self.nick] = {"caps": "build"}
        return job

    def progress(self, snapshot, text="working on it"):
        snapshot.setdefault("messages", []).append(
            {"nick": self.nick, "text": text})


def run_drill():
    """Run every phase; raise AssertionError on any failure.

    Returns a report dict (alert, phase log) so tests can
    assert on the drill's outcome without parsing stdout.
    """
    log = []
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {}}
    first = FakeWorker(FIRST_NICK)
    second = FakeWorker(SECOND_NICK)

    # Phase 1 — disjoint claims: no collision, nothing to warn.
    first.claim(snapshot, FIRST_ID, "intel/watchdog.py")
    second.claim(snapshot, SECOND_ID, "intel/brief.py")
    got = watchdog.tick(snapshot, now=NOW)
    assert got == [], f"disjoint claims must yield zero alerts, got {got}"
    log.append("phase 1: disjoint claims yield zero alerts")

    # Phase 2 — the overlap: second worker's files now share
    # one path with the first worker's. The alert must fire
    # while both jobs are still claimed, before either finishes.
    for job in snapshot["jobs"]:
        if job["id"] == SECOND_ID:
            job["files"] = f"{SHARED_PATH}, intel/brief.py"
    for job in snapshot["jobs"]:
        if job["id"] == FIRST_ID:
            job["files"] = f"intel/watchdog.py, {SHARED_PATH}"
    got = watchdog.tick(snapshot, now=NOW)
    assert len(got) == 1, (
        f"overlapping claims must yield exactly one alert, "
        f"got {len(got)}: {got}")
    alert = got[0]
    assert alert["kind"] == "file-collision", alert
    assert alert["severity"] == "critical", alert
    assert alert["job"] == FIRST_ID, alert
    assert alert["other_job"] == SECOND_ID, alert
    assert alert["shared_path"] == SHARED_PATH, alert
    assert FIRST_ID in alert["explanation"], alert
    assert SECOND_ID in alert["explanation"], alert
    assert SHARED_PATH in alert["explanation"], alert
    assert alert["dedupe_key"] == (
        f"file-collision:{FIRST_ID}:{SECOND_ID}:{SHARED_PATH}"), alert
    lines = watchdog.announcements_for(got)
    assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
    log.append(f"phase 2: critical collision alert names jobs "
               f"{FIRST_ID}/{SECOND_ID} on {SHARED_PATH}; "
               f"announcement line held, not posted")

    # Phase 3 — still colliding: both workers keep working, so
    # the same alert (same dedupe key) must keep firing; the
    # drill catches the collision mid-work, not after the fact.
    first.progress(snapshot)
    second.progress(snapshot)
    got = watchdog.tick(snapshot, now=NOW + 60)
    assert len(got) == 1, f"live overlap must keep firing, got {got}"
    assert got[0]["dedupe_key"] == alert["dedupe_key"], got
    log.append("phase 3: while both jobs stay claimed, the same "
               "collision alert keeps firing (same dedupe key)")

    # Phase 4 — one job finishes: with no unmerged branch on
    # the done job, there is nothing left to collide with, so
    # the alert stops firing. The collision was a live-work
    # warning, not a permanent record.
    for job in snapshot["jobs"]:
        if job["id"] == FIRST_ID:
            job["status"] = "done"
    got = watchdog.tick(snapshot, now=NOW + 120)
    assert got == [], f"finished overlap must stop firing, got {got}"
    log.append("phase 4: after one job finishes (no branch), "
               "the collision alert stops firing")

    return {"alert": alert, "log": log}


def main(argv=None):
    try:
        report = run_drill()
    except AssertionError as exc:
        print(f"collision drill: FAIL: {exc}")
        return 1
    for line in report["log"]:
        print(f"collision drill: {line}")
    print("collision drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
