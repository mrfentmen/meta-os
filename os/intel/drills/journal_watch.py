"""Journal watch drill (Milo lane, OS-037).

Acceptance: force-failing a unit produces a SYSTEM alert in the
alert store and the dashboard feed within one watchdog loop.

Runs unattended on fixtures: no network, no Redis, no bus
posts, no real systemd. The force-fail is played by fixture
journal lines — relay-jobs.service failing with systemd's own
"Failed with result" phrasing — because there is no test image
in this repo to kill a real relay unit on. What the drill
proves is the watchdog's half, which is Milo's lane: one
journal_watch_tick over the fixture yields exactly one SYSTEM
alert, the alert validates through the store's own writer
shape (build_alert_record, no network needed), and it is
distinguishable from every job alert (kind system-failure,
subjects the unit, no nick, no job). The store half (write +
query) is proven on the fake store in
tests/test_os_journal_watch.py; the dashboard feed reads that
same alert store, so a record that queries back is a record
the dashboard can render.

Fixture journal (journalctl -o json shapes):
  1. relay-jobs.service: "Failed with result 'exit-code'."
     (priority 3) — the forced failure.
  2. relay-jobs.service: "Main process exited, code=exited,
     status=1/FAILURE" — same unit, second line: still one
     alert (grouped by unit, failure_count 2), not a storm.
  3. relay-bus.service: "Started." (priority 6) — healthy
     relay unit, must stay silent.
  4. sshd.service: "Failed with result 'exit-code'." — a
     non-relay failure, the host's business, must stay silent.

Usage: python3 intel/drills/journal_watch.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402

T0 = 100000
UNIT = "relay-jobs.service"


def _line(unit, message, priority):
    return json.dumps({"_SYSTEMD_UNIT": unit, "MESSAGE": message,
                       "PRIORITY": str(priority)})


FIXTURE = "\n".join([
    _line(UNIT, "relay-jobs.service: Failed with result 'exit-code'.", 3),
    _line(UNIT, "relay-jobs.service: Main process exited, "
                "code=exited, status=1/FAILURE", 3),
    _line("relay-bus.service", "Started relay-bus.service.", 6),
    _line("sshd.service", "sshd.service: Failed with result 'exit-code'.", 3),
    "",
    "this line is not json and must be skipped, not fatal",
])


def _check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + ("" if ok else f" — {detail}"))
    return ok


def main():
    ok = True
    # One journal_watch_tick = one watchdog loop iteration.
    collected = []
    alerts = watchdog.journal_watch_tick(FIXTURE, now=T0, emit=collected.append)
    ok &= _check("1 forced failure yields exactly one SYSTEM alert",
                 len(alerts) == 1, f"got {len(alerts)}: {alerts}")
    alert = alerts[0] if alerts else {}
    ok &= _check("2 alert kind is system-failure, severity critical",
                 alert.get("kind") == "system-failure"
                 and alert.get("severity") == "critical",
                 f"got {alert}")
    ok &= _check("3 alert is SYSTEM, not a job alert: subjects the unit,"
                 " no nick, no job",
                 alert.get("subjects") == [UNIT]
                 and alert.get("system_alert") is True
                 and "nick" not in alert and "job" not in alert,
                 f"got {alert}")
    ok &= _check("4 same unit's two failure lines group into one alert"
                 " with failure_count 2",
                 alert.get("failure_count") == 2, f"got {alert}")
    ok &= _check("5 explanation quotes the failure and names the unit",
                 UNIT in alert.get("explanation", "")
                 and "Failed with result" in alert.get("explanation", ""),
                 f"got {alert.get('explanation')}")
    ok &= _check("6 suggested fix points at journalctl -u and an operator"
                 " restart, never a watchdog restart",
                 "journalctl -u " + UNIT in alert.get("suggested_fix", "")
                 and "never restarts units itself"
                 in alert.get("suggested_fix", ""),
                 f"got {alert.get('suggested_fix')}")
    ok &= _check("7 emit received the alert (the store-writer seat)",
                 collected == alerts, f"got {collected}")
    try:
        record = istore.build_alert_record(alert, room="main")
        built = True
    except ValueError as exc:
        record = {}
        built = False
        detail = str(exc)
    else:
        detail = ""
    ok &= _check("8 alert validates as a WDG-010 store record",
                 built and record.get("id") == "system-failure:" + UNIT,
                 detail or f"got {record}")
    ok &= _check("9 system-failure severity is critical in the alert"
                 " itself (not via the snapshot-detector table:"
                 " journal watch is not a DETECTORS member, so the"
                 " WDG-024 table lock in test_intel_watchdog.py"
                 " must keep covering exactly the snapshot kinds)",
                 alert.get("severity") == "critical",
                 f"got {alert.get('severity')}")
    # Dedupe seat: a second tick for the same unit re-fires the
    # same dedupe key, so the dashboard shows one row per
    # incident (WDG-013), not one row per journal line.
    again = watchdog.journal_watch_tick(FIXTURE, now=T0 + 60)
    ok &= _check("10 re-tick re-fires the same dedupe key only",
                 len(again) == 1
                 and again[0].get("dedupe_key") == alert.get("dedupe_key"),
                 f"got {again}")

    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
