"""Watchdog boot self-check (Milo lane, OS-036).

Acceptance: at relay-ready the watchdog runs each detector once
against the seeded fixture (OS-026 stale lease) and writes a green
self-check record; breaking a detector fails the boot test.

OS-026 (Buffy's boot fixture pack) has not landed yet, so the
seeded fixture here is built to the OS-026 spec, not loaded from
it: jobs in 4 states (open, claimed, blocked, done), presence
for 4 nicks, one stale lease. When OS-026 lands, seeded_fixture
should be replaced by a loader over that pack and this module's
expected counts re-pinned — until then the fixture below IS the
spec the self-check asserts on, and the eval doc says so plainly.

How it works: run_self_check ticks the snapshot through
intel.watchdog.tick — one pass over the DETECTORS list, so every
detector runs exactly once — and compares the alerts found, per
kind, against EXPECTED, the counts the fixture is built to
produce. The record is green only when every kind matches; a
detector that stops firing (removed, crashing, or retuned past
the fixture) turns the record red and names the failing kind,
so a red self-check fails the boot test honestly instead of
pretending the watchdog is healthy.

The self-check never posts anywhere and never mutates the
snapshot: tick only reads, and the record goes to the caller,
which stores it via intel.store.put_selfcheck. A green record
means the detectors behaved on the fixture; it does not prove
the watchdog loop runs on a booted image (OS-033's unit owns
that half) or that live ingest stamps server_time (FND-014).

Usage: python3 intel/drills/boot_selfcheck.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

try:
    from intel import thresholds
    from intel import watchdog
except ImportError:  # direct module load, not via the intel package
    import thresholds  # noqa: F401
    import watchdog  # noqa: F401


# Expected alert counts per kind on the seeded fixture. The
# attempt detector is one detector with two kinds (warning at
# max-1, critical at max), so 9 detectors yield 10 alerts.
EXPECTED = {
    "presence-stall": 1,
    "progress-stall": 1,
    "lease-risk": 1,
    "dead-dep": 1,
    "missing-dep": 1,
    "file-collision": 1,
    "attempt-warning": 1,
    "attempt-exhaustion": 1,
    "silent-room": 1,
    "rejected-dispatch": 1,
}


def seeded_fixture(now):
    """The OS-026-shaped fixture, built to spec (see module doc).

    now is the fake boot clock. Ages are derived from thresholds,
    never hardcoded, so a threshold retune retunes the fixture —
    except the stale lease, which is stale by construction (its
    lease_until is in the past, so the lease-risk detector
    correctly skips it: an expired lease is the sweep's job).

    Jobs, by state (4 states, OS-026 spec):
      claimed  1  presence-stall nick, absent from presence,
                 last progress 20 min ago, lease expired (the
                 one stale lease), no files, no deps.
      claimed  2  progress-stall nick, present, last progress
                 20 min ago, no lease, no files, no deps.
      claimed  3  lease-risk nick, present, heartbeat 3 min ago
                 (past the 2-min quiet window, inside the
                 10-min progress window so no stall fires),
                 progress 1 min ago, lease expires in 3 min
                 (inside the 5-min risk window).
      claimed  4,5  collision pair, both present and fresh,
                 far-future leases, one shared file.
      open     21 dead-dep subject, deps on blocked job 20.
      blocked  20 blocked with a verbatim note (the dep).
      open     22 missing-dep subject, deps on id 999, which
                 exists nowhere in the snapshot.
      open     23 attempt-warning: attempts 2 of max 3.
      open     24 attempt-exhaustion: attempts 3 of max 3.
      done     30 finished work, no branch, no deps — the
                 fourth state, silent for every detector.
    Presence holds 4 nicks (OS-026 spec); the presence-stall
    nick is in caps but absent, which is exactly its stall.
    Messages: one timestamped message 70 min old (past the
    60-min silent-room window) plus one REJECTED dispatch line
    with no timestamp (so it cannot move the silence clock).
    """
    stall_ago = now - (thresholds.STALL_MINUTES + 10) * 60
    return {
        "room": "main",
        "messages": [
            {"nick": "pax", "text": "working on it",
             "ts": now - (thresholds.SILENT_ROOM_MINUTES + 10) * 60},
            "REJECTED:42 BAD signed_by=pax rejected_by=rowan",
        ],
        "jobs": [
            {"id": "1", "title": "stale lease job",
             "status": "claimed", "claim": "gone",
             "last_progress": stall_ago,
             "lease_until": now - 60},
            {"id": "2", "title": "stuck job",
             "status": "claimed", "claim": "stuck",
             "last_progress": stall_ago},
            {"id": "3", "title": "expiring job",
             "status": "claimed", "claim": "leasey",
             "last_progress": now - 60,
             "last_heartbeat": now - 3 * 60,
             "lease_until": now + 3 * 60,
             "lease": thresholds.LEASE_DEFAULT_SECONDS},
            {"id": "4", "title": "collision job A",
             "status": "claimed", "claim": "colla",
             "last_progress": now - 60,
             "last_heartbeat": now - 60,
             "lease_until": now + 3600,
             "files": "intel/store.py"},
            {"id": "5", "title": "collision job B",
             "status": "claimed", "claim": "collb",
             "last_progress": now - 60,
             "last_heartbeat": now - 60,
             "lease_until": now + 3600,
             "files": "intel/store.py"},
            {"id": "20", "title": "blocked dep",
             "status": "blocked", "note": "waiting on review"},
            {"id": "21", "title": "waits on blocked dep",
             "status": "open", "deps": "20"},
            {"id": "22", "title": "waits on missing dep",
             "status": "open", "deps": "999"},
            {"id": "23", "title": "one attempt left",
             "status": "open", "attempts": 2, "max_attempts": 3},
            {"id": "24", "title": "budget spent",
             "status": "open", "attempts": 3, "max_attempts": 3},
            {"id": "30", "title": "finished job",
             "status": "done"},
        ],
        "presence": ["stuck", "leasey", "colla", "collb"],
        "caps": {nick: {"caps": "build"} for nick in
                 ("gone", "stuck", "leasey", "colla", "collb")},
    }


def run_self_check(snapshot, now=None, room="main",
                   expected=None):
    """Tick once, compare per-kind counts, return the record.

    The record is {status, room, ts, detectors, alert_count,
    expected_count}: status is "green" only when every expected
    kind matched exactly; detectors lists one entry per kind
    {kind, expected, found, ok} so a red record names what
    broke. A detector that raises is swallowed by tick (one
    broken detector must not blind the rest), so it shows up
    here as found 0 against its expected count — red, named,
    honest. Extra kinds not in expected are reported as
    unexpected entries and also turn the record red: a
    self-check that ignores a new alert kind would bless a
    watchdog it does not understand.
    """
    now = int(now) if now is not None else None
    expected = dict(EXPECTED if expected is None else expected)
    alerts = watchdog.tick(snapshot, now=now)
    found = {}
    for alert in alerts:
        if isinstance(alert, dict):
            kind = alert.get("kind")
            if isinstance(kind, str):
                found[kind] = found.get(kind, 0) + 1
    detectors = []
    ok = True
    for kind in sorted(set(expected) | set(found)):
        want = expected.get(kind, 0)
        got = found.get(kind, 0)
        entry = {"kind": kind, "expected": want, "found": got,
                 "ok": want == got}
        if not entry["ok"]:
            ok = False
        detectors.append(entry)
    return {
        "status": "green" if ok else "red",
        "room": room,
        "ts": now,
        "detectors": detectors,
        "alert_count": len(alerts),
        "expected_count": sum(expected.values()),
    }
