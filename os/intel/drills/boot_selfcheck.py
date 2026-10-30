"""Boot self-check drill (Milo lane, OS-036).

Acceptance: at relay-ready the watchdog runs each detector once
against the seeded fixture (OS-026 stale lease) and writes a
green self-check record; breaking a detector fails the boot test.

Runs unattended on fixtures: no network, no Redis, no bus posts,
no booted image. A real boot of a Meta OS image cannot be
performed from this repo — there is no test image here — so the
drill proves the self-check half of the acceptance, which is
Milo's lane: the record, its green/red verdict, and the fail
mode. What the drill proves:

  green   the seeded fixture ticks to exactly the expected
          per-kind counts (9 detectors, 10 alerts) and the
          record is green, with every detector entry ok.
  stored  the green record round-trips through a store sink
          (the put/get seat intel.store.put_selfcheck fills
          against real Redis) unchanged.
  repeat  a second tick on the same fixture is green again:
          the self-check does not mutate the fixture and the
          record exists after every boot test, not just the
          first.
  broken  with one detector removed from the DETECTORS list,
          the record goes red and names the failing kind —
          breaking a detector fails the boot test.
  crash   with one detector raising, tick swallows it (one
          broken detector must not blind the rest) and the
          record still goes red on that kind's missing count.

The record is a verdict on the detectors, not on the boot: a
green record here does not prove relay-watchdog.service runs
at boot (OS-033's unit half) or that the seeded fixture pack
(OS-026) matches this fixture on a real image — both are
named as not proven in the eval doc.

Usage: python3 intel/drills/boot_selfcheck.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import boot_selfcheck  # noqa: E402
from intel import watchdog  # noqa: E402

T0 = 100000


def _check(log, name, condition, detail=""):
    log.append(("PASS" if condition else "FAIL") + ": " + name
               + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def run_drill():
    """Run every phase; returns a report dict for tests.

    The store sink is an in-memory dict standing in for
    intel.store.put_selfcheck/get_selfcheck: the drill proves
    the record shape survives a store round-trip, while the
    suite pins the real store keys against the fake Redis.
    """
    log = []
    ok = True
    snapshot = boot_selfcheck.seeded_fixture(T0)

    record = boot_selfcheck.run_self_check(snapshot, now=T0)
    ok &= _check(log, "green record on seeded fixture",
                 record["status"] == "green", str(record))
    ok &= _check(log, "10 alerts from 9 detectors",
                 record["alert_count"] == 10
                 and record["expected_count"] == 10, str(record))
    ok &= _check(log, "every detector entry ok",
                 all(d["ok"] for d in record["detectors"]),
                 str(record["detectors"]))

    sink = {}

    def put(room, ts, rec):
        sink[(room, ts)] = dict(rec)
        return f"muse-bus:intel:wd:selfcheck:{room}:{ts}"

    def get(room, ts):
        return sink.get((room, ts))

    put("main", T0, record)
    ok &= _check(log, "record round-trips through store sink",
                 get("main", T0) == record)

    again = boot_selfcheck.run_self_check(snapshot, now=T0)
    ok &= _check(log, "second boot test still green",
                 again["status"] == "green"
                 and again == record,
                 "fixture mutated or verdict unstable")

    saved = list(watchdog.DETECTORS)
    try:
        watchdog.DETECTORS = [d for d in saved
                              if d is not watchdog.detect_dead_dep]
        broken = boot_selfcheck.run_self_check(snapshot, now=T0)
    finally:
        watchdog.DETECTORS = saved
    failing = [d for d in broken["detectors"] if not d["ok"]]
    ok &= _check(log, "removed detector fails the boot test",
                 broken["status"] == "red"
                 and [d["kind"] for d in failing] == ["dead-dep"],
                 str(broken["detectors"]))

    def _boom(snapshot, now):
        raise RuntimeError("detector exploded")

    try:
        watchdog.DETECTORS = [_boom if d is watchdog.detect_lease_risk
                              else d for d in saved]
        crashed = boot_selfcheck.run_self_check(snapshot, now=T0)
    finally:
        watchdog.DETECTORS = saved
    failing = [d for d in crashed["detectors"] if not d["ok"]]
    ok &= _check(log, "crashing detector fails the boot test",
                 crashed["status"] == "red"
                 and [d["kind"] for d in failing] == ["lease-risk"]
                 and crashed["alert_count"] == 9,
                 str(crashed["detectors"]))
    return {"ok": ok, "log": log, "record": record}


def main():
    report = run_drill()
    for line in report["log"]:
        print(line)
    print("RESULT: " + ("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
