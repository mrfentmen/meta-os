"""Restart-ownership contract drill (Milo lane, OS-034).

Acceptance: kill -9 a worker gets a systemd restart plus a
watchdog event note and NO false stall alert; SIGSTOP a
worker gets a stall alert and no restart fight.

The contract (META_OS.md, supervision contract): systemd's
Restart= owns process death; the watchdog owns silent-but-
alive stalls; neither double-acts on the other's case.

Runs unattended on fixtures: no network, no Redis, no bus
posts, no real systemd. The systemd half is played by the
drill itself — it kills the fake worker's presence, waits
the modeled RestartSec, and restores presence with a fresh
heartbeat — because there is no test image in this repo to
kill a real relay-worker@ unit on. What the drill proves
is the watchdog's half of the contract, which is Milo's
lane: the tick output in each case, and the event note's
shape through the store's own validator.

Timeline uses a fake clock (base time T0) so the drill is
deterministic: thresholds are read from intel/thresholds.py,
never hardcoded, so a threshold retune retunes the drill.

Case A (kill -9 + systemd restart):
  T0        worker pax claims job 7, heartbeats, progresses.
  T0+300    SIGKILL: presence stops, heartbeats stop.
  T0+310    systemd RestartSec elapses: worker back, presence
            restored, heartbeat fresh. The watchdog records
            a worker-restart event note (info, never an
            announcement) and the tick at T0+310 yields zero
            alerts — no false stall alert for a handled death.
  Control: the same death with NO restart, ticked past the
  stall threshold, yields exactly one presence-stall alert
  — proving the zero in case A comes from the restart,
  not from a blind detector.

Case B (SIGSTOP, alive but wedged):
  Worker pax stays in presence (the process lives, so
  systemd has nothing to restart and does nothing) but its
  last activity freezes at T0. The tick past the progress-
  stall threshold yields exactly one progress-stall alert,
  zero presence-stall alerts, and no restart note — the
  watchdog acts, systemd does not fight it.

Usage: python3 intel/drills/restart_contract.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402

JOB_ID = "7"
NICK = "pax"
T0 = 100000
RESTART_SEC = 10  # modeled RestartSec (watchdog unit's value;
                  # the worker template's own value is Pax's
                  # unit to pin — see the eval doc's gaps)


def _snapshot(present, last_activity):
    return {
        "caps": {NICK: ["python"]},
        "presence": [NICK] if present else [],
        "jobs": [{
            "id": JOB_ID, "title": "demo job", "status": "claimed",
            "claim": NICK, "claimed_at": T0,
            "last_progress": last_activity,
            "lease": thresholds.LEASE_DEFAULT_SECONDS,
            "lease_until": T0 + thresholds.LEASE_DEFAULT_SECONDS,
        }],
        "messages": [],
    }


def _check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}: {name}"
          + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def main():
    ok = True
    stall = thresholds.STALL_MINUTES * 60
    progress = thresholds.PROGRESS_STALL_MINUTES * 60

    # --- Case A: kill -9, systemd restarts, watchdog notes, no alert.
    killed_at = T0 + 300
    back_at = killed_at + RESTART_SEC
    tick_gap = watchdog.tick(_snapshot(False, killed_at),
                             now=killed_at + RESTART_SEC // 2)
    ok &= _check("A0 mid-restart gap ticks zero alerts (age under threshold)",
                 tick_gap == [], f"got {tick_gap}")
    tick_a = watchdog.tick(_snapshot(True, back_at), now=back_at)
    ok &= _check("A1 restarted worker ticks zero alerts",
                 tick_a == [], f"got {tick_a}")
    note = watchdog.restart_event_note(NICK, JOB_ID, back_at,
                                       downtime_seconds=RESTART_SEC)
    record = istore.build_alert_record(note)
    ok &= _check("A2 restart note validates as an info record",
                 record["kind"] == "worker-restart"
                 and record["severity"] == "info"
                 and record["id"] == f"worker-restart:{NICK}:{JOB_ID}"
                 and NICK in record["explanation"]
                 and JOB_ID in record["explanation"],
                 f"got {record}")
    ok &= _check("A3 restart note never announces",
                 watchdog.announcements_for([record]) == [])
    ok &= _check("A4 note names the systemd restart, not a stall",
                 "systemd" in record["explanation"]
                 and "no stall alert" in record["explanation"])

    # --- Control: same death, no restart, past threshold -> stall.
    tick_c = watchdog.tick(_snapshot(False, killed_at),
                           now=killed_at + stall + 60)
    kinds_c = [a["kind"] for a in tick_c]
    ok &= _check("A-control un-restarted death yields one presence-stall",
                 kinds_c == ["presence-stall"], f"got {kinds_c}")

    # --- Case B: SIGSTOP, alive but wedged -> stall alert, no fight.
    tick_b = watchdog.tick(_snapshot(True, T0),
                           now=T0 + progress + 60)
    kinds_b = [a["kind"] for a in tick_b]
    ok &= _check("B1 wedged worker yields exactly one progress-stall",
                 kinds_b == ["progress-stall"], f"got {kinds_b}")
    stall_b = tick_b[0] if tick_b else {}
    ok &= _check("B2 stall alert names nick, job, and age",
                 stall_b.get("nick") == NICK
                 and stall_b.get("job") == JOB_ID
                 and stall_b.get("last_progress_age_seconds",
                                 0) > progress,
                 f"got {stall_b}")
    ok &= _check("B3 wedged case builds no restart note and "
                 "systemd takes no action (process alive)",
                 watchdog.announcements_for(tick_b) != []
                 and not any(a["kind"] == "worker-restart"
                             for a in tick_b))

    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
