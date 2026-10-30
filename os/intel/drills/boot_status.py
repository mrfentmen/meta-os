"""Boot status line drill (Milo lane, OS-041).

Acceptance: one line of live health (units up, workers alive,
last alert) exposed for Rowan's boot checklist; the line
renders from live data on the test image and goes stale
within 30s of a unit being killed.

Runs unattended on fixtures: no network, no Redis, no bus
posts, no booted image. The drill proves the record half of
the acceptance, which is Milo's lane: the line, its live-data
inputs, and the staleness rule. What the drill proves:

  green   3/3 units active, 2 workers present, no open
          alerts renders "Boot: 3/3 units up, 2 workers
          alive — no open alerts".
  stored  the green record round-trips through a store sink
          (the put/get seat intel.store.put_boot_status
          fills against real Redis) unchanged.
  kill    one unit failing re-renders the line at 2/3 units
          up naming the dead unit — the checklist line
          tracks the kill, it does not stay green.
  alert   an open alert re-renders the line naming the
          latest open alert id and severity; a resolved
          alert does not.
  stale   the pre-kill green record is fresh at +30s and
          stale at +31s, so a killed unit can hide behind
          an old green line for at most 30s; the post-kill
          record is fresh at +5s.

The line is a verdict on the fixture inputs, not on a boot:
a green line here does not prove relay-watchdog.service
renders it on a booted image (no test image in repo) or
that Rowan's boot checklist (OS-043) renders it — both are
named as not proven in the eval doc.

Usage: python3 intel/drills/boot_status.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import store as istore  # noqa: E402

T0 = 100000

UNITS = [{"unit": "relay-bus", "state": "active"},
         {"unit": "relay-jobs", "state": "active"},
         {"unit": "relay-watchdog", "state": "active"}]
WORKERS = ["milo", "rowan"]


def _check(log, name, condition, detail=""):
    log.append(("PASS" if condition else "FAIL") + ": " + name
               + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def run_drill():
    """Run every phase; returns a report dict for tests.

    The store sink is an in-memory dict standing in for
    intel.store.put_boot_status/get_boot_status: the drill
    proves the record shape survives a store round-trip,
    while the suite pins the real store keys against the
    fake Redis.
    """
    log = []
    ok = True

    record = istore.build_boot_status(UNITS, WORKERS, [], ts=T0)
    ok &= _check(log, "green line on healthy fixture",
                 record["line"] == "Boot: 3/3 units up, "
                 "2 workers alive — no open alerts",
                 str(record))
    ok &= _check(log, "green record fields",
                 record["units_up"] == 3 and record["units_total"] == 3
                 and record["workers_count"] == 2
                 and record["last_alert"] is None, str(record))

    sink = {}

    def put(room, ts, rec):
        sink[(room, ts)] = dict(rec)
        return f"muse-bus:intel:wd:bootstatus:{room}:{ts}"

    def get(room, ts):
        return sink.get((room, ts))

    put("main", T0, record)
    ok &= _check(log, "record round-trips through store sink",
                 get("main", T0) == record)

    killed = [dict(u, state="failed") if u["unit"] == "relay-jobs"
              else dict(u) for u in UNITS]
    after_kill = istore.build_boot_status(killed, WORKERS, [], ts=T0 + 5)
    ok &= _check(log, "killed unit drops the line and names it",
                 after_kill["line"] == "Boot: 2/3 units up, "
                 "2 workers alive — down: relay-jobs — no open alerts",
                 str(after_kill))

    alerts = [{"id": "a-old", "severity": "warning",
               "created_at": T0 - 100, "resolved_at": None},
              {"id": "a-new", "severity": "critical",
               "created_at": T0 - 10, "resolved_at": None},
              {"id": "a-done", "severity": "critical",
               "created_at": T0 - 1, "resolved_at": T0}]
    with_alert = istore.build_boot_status(UNITS, WORKERS, alerts, ts=T0)
    ok &= _check(log, "latest open alert named, resolved ignored",
                 with_alert["last_alert"]["id"] == "a-new"
                 and "last alert: a-new (critical)" in with_alert["line"],
                 str(with_alert))

    ok &= _check(log, "pre-kill record fresh at exactly 30s",
                 not istore.boot_status_is_stale(record, now=T0 + 30))
    ok &= _check(log, "pre-kill record stale at 31s",
                 istore.boot_status_is_stale(record, now=T0 + 31))
    ok &= _check(log, "post-kill record fresh at +5s",
                 not istore.boot_status_is_stale(after_kill, now=T0 + 10))
    return {"ok": ok, "log": log, "record": record}


def main():
    report = run_drill()
    for line in report["log"]:
        print(line)
    print("RESULT: " + ("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
