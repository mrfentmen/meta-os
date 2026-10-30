"""WDG-027: watchdog tuning run — tick() over every detector fixture.

Standalone harness, deliberately NOT the unit tests: it rebuilds one
positive and one (or more) negative snapshot per detector from the
same snapshot shapes intel/brief.py documents and the suite fixtures
use, runs watchdog.tick() on each at now=10000, and tabulates
false positives (an alert kind fired that was not expected) and
false negatives (an expected kind that did not fire).

Fixture source note: there are no separate Buffy synthetic-history
files in this repo (no tests/fixtures/intel/ directory, no
synthetic-history files anywhere under tests/ or intel/); the
suite's hand-written snapshot fixtures ARE the synthetic histories
this run covers, one case per fixture class below.

Run from the repo root: python3 intel/evals/watchdog_tuning.py
Exit 0 only when every case matches its expected kinds exactly —
in particular the quiet fixture must yield zero alerts, which is
the WDG-027 pass requirement. The table it prints is the source
for intel/evals/watchdog_tuning.md.
"""

import sys

sys.path.insert(0, ".")
from intel import watchdog  # noqa: E402

NOW = 10000


def _claimed(job_id, nick, **extra):
    job = {"id": job_id, "title": "job %s" % job_id, "status": "claimed",
           "claim": nick, "claimed_at": 9990}
    job.update(extra)
    return job


def _caps(*nicks):
    return {n: {"caps": "build"} for n in nicks}


# (fixture name, detector under test, snapshot, expected kinds)
CASES = [
    # Quiet / healthy: zero alerts is the WDG-027 pass requirement.
    ("quiet-empty", "tick", {}, []),
    ("healthy-busy", "tick",
     {"messages": [{"nick": "pax", "text": "working on it"}],
      "jobs": [{"id": "1", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9900}],
      "presence": ["pax"], "caps": _caps("pax")}, []),
    # WDG-002 presence-stall.
    ("presence-stall-positive", "WDG-002",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9340}],
      "presence": ["hana"], "caps": _caps("pax")}, ["presence-stall"]),
    ("presence-stall-negative-present", "WDG-002",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9340}],
      "presence": ["pax", "hana"], "caps": _caps("pax")},
     ["progress-stall"]),  # present-but-idle is WDG-003, not WDG-002
    ("presence-stall-negative-fresh", "WDG-002",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9900}],
      "presence": ["hana"], "caps": _caps("pax")}, []),
    ("presence-stall-negative-walkon", "WDG-002/WDG-025",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9340}],
      "presence": ["hana"], "caps": {"hana": {}}}, []),
    # WDG-003 progress-stall.
    ("progress-stall-positive", "WDG-003",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9000,
                "last_progress": 9340}],
      "presence": ["pax", "hana"], "caps": _caps("pax")},
     ["progress-stall"]),
    ("progress-stall-negative-fresh", "WDG-003",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9000,
                "last_progress": 9900}],
      "presence": ["pax", "hana"], "caps": _caps("pax")}, []),
    ("progress-stall-negative-absent", "WDG-003",
     {"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                "claim": "pax", "claimed_at": 9000,
                "last_progress": 9340}],
      "presence": ["hana"], "caps": _caps("pax")}, ["presence-stall"]),
    # WDG-004 lease-risk.
    ("lease-risk-positive", "WDG-004",
     {"jobs": [{"id": "9", "title": "lease job", "status": "claimed",
                "claim": "pax", "claimed_at": 9900,
                "lease_until": 10240}],
      "presence": ["pax"], "caps": _caps("pax")}, ["lease-risk"]),
    ("lease-risk-negative-live-heartbeat", "WDG-004",
     {"jobs": [{"id": "9", "title": "lease job", "status": "claimed",
                "claim": "pax", "claimed_at": 9900,
                "lease_until": 10090, "lease": 120}],
      "presence": ["pax"], "caps": _caps("pax")}, []),
    ("lease-risk-negative-far-expiry", "WDG-004",
     {"jobs": [{"id": "9", "title": "lease job", "status": "claimed",
                "claim": "pax", "claimed_at": 9900,
                "lease_until": 11000}],
      "presence": ["pax"], "caps": _caps("pax")}, []),
    # WDG-005 dead-dep / WDG-006 missing-dep.
    ("dead-dep-positive", "WDG-005",
     {"jobs": [{"id": "2", "title": "blocked job", "status": "open",
                "deps": "1"},
               {"id": "1", "title": "dep job", "status": "blocked",
                "note": "waiting on vendor API key"}]}, ["dead-dep"]),
    ("dead-dep-negative-live-dep", "WDG-005",
     {"jobs": [{"id": "2", "title": "blocked job", "status": "open",
                "deps": "1"},
               {"id": "1", "title": "dep job", "status": "open"}]}, []),
    ("missing-dep-positive", "WDG-006",
     {"jobs": [{"id": "2", "title": "blocked job", "status": "open",
                "deps": "9"}]}, ["missing-dep"]),
    ("missing-dep-negative-existing-dep", "WDG-006",
     {"jobs": [{"id": "2", "title": "blocked job", "status": "open",
                "deps": "1"},
               {"id": "1", "title": "dep job", "status": "open"}]}, []),
    # WDG-007 file-collision.
    ("file-collision-positive", "WDG-007",
     {"jobs": [_claimed("1", "pax",
                         files="intel/watchdog.py, intel/store.py"),
                _claimed("2", "rowan",
                         files="intel/store.py, intel/brief.py")],
      "presence": ["pax", "rowan"], "caps": _caps("pax", "rowan")},
     ["file-collision"]),
    ("file-collision-negative-disjoint", "WDG-007",
     {"jobs": [_claimed("1", "pax", files="intel/watchdog.py"),
                _claimed("2", "rowan", files="intel/brief.py")],
      "presence": ["pax", "rowan"], "caps": _caps("pax", "rowan")}, []),
    ("file-collision-negative-done-no-branch", "WDG-007",
     {"jobs": [_claimed("1", "pax", files="intel/store.py"),
                {"id": "2", "title": "done job", "status": "done",
                 "files": "intel/store.py"}],
      "presence": ["pax"], "caps": _caps("pax")}, []),
    # WDG-008 attempt-exhaustion.
    ("attempt-warning-positive", "WDG-008",
     {"jobs": [{"id": "7", "title": "flaky job", "status": "open",
                "claim": "pax", "attempts": 2, "max_attempts": 3}]},
     ["attempt-warning"]),
    ("attempt-exhaustion-positive", "WDG-008",
     {"jobs": [{"id": "7", "title": "flaky job", "status": "open",
                "claim": "pax", "attempts": 3, "max_attempts": 3}]},
     ["attempt-exhaustion"]),
    ("attempt-negative-early", "WDG-008",
     {"jobs": [{"id": "7", "title": "flaky job", "status": "open",
                "claim": "pax", "attempts": 0, "max_attempts": 3}]}, []),
    ("attempt-negative-done", "WDG-008",
     {"jobs": [{"id": "7", "title": "flaky job", "status": "done",
                "claim": "pax", "attempts": 3, "max_attempts": 3}]}, []),
    # WDG-009 silent-room (info only, never an alert severity).
    ("silent-room-positive", "WDG-009",
     {"jobs": [{"id": "1", "title": "claimed job", "status": "claimed",
                "claim": "pax", "claimed_at": 1000}],
      "messages": [{"nick": "pax", "text": "starting", "ts": 1000}]},
     ["silent-room"]),
    ("silent-room-negative-fresh-message", "WDG-009",
     {"jobs": [{"id": "1", "title": "claimed job", "status": "claimed",
                "claim": "pax", "claimed_at": 1000}],
      "messages": [{"nick": "pax", "text": "update", "ts": 8200}]}, []),
    ("silent-room-negative-no-claims", "WDG-009",
     {"jobs": [{"id": "1", "title": "open job", "status": "open"}],
      "messages": [{"nick": "pax", "text": "done for now", "ts": 1000}]},
     []),
]


def main():
    print("%-38s %-14s %-22s %-22s %s" % (
        "fixture", "detector", "expected", "got", "verdict"))
    bad = 0
    for name, detector, snapshot, expected in CASES:
        got = [a["kind"] for a in watchdog.tick(snapshot, now=NOW)]
        false_pos = sorted(set(got) - set(expected))
        false_neg = sorted(set(expected) - set(got))
        verdict = "OK" if not false_pos and not false_neg else (
            "FP=%s FN=%s" % (false_pos, false_neg))
        if verdict != "OK":
            bad += 1
        print("%-38s %-14s %-22s %-22s %s" % (
            name, detector, ",".join(expected) or "-",
            ",".join(got) or "-", verdict))
    print("cases=%d mismatches=%d" % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
