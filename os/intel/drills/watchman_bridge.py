"""Watchman bridge drill (Milo lane, OS-122 follow-up to Pax OS-118).

OS-118 landed the thing OS-122 was waiting on: a real watchman
program (os/watchman/relay_watchman.py) with a pure tick(). This
drill closes the bridge between that tick and the watchdog's
who-watches-the-watchman detector, on fixtures, in four checks:

1. Real tick: relay_watchman.tick() over one open job addressed
   to a sleeping agent yields exactly one wake event.
2. Bridge: folding that tick yields a record with watchman_alive
   True and last_bell equal to the tick time; the watchman_watch
   board reads ALIVE and its tick journals nothing new.
3. Silence: the same record aged past WATCHMAN_STALE_MINUTES
   (restart_ok True, the revivable case) yields exactly one
   crew-dark record plus one restart-succeeded record and no
   escalation; a fresh fold after the dark episode yields a
   watchman-recovered record.
4. No-bell honesty: a tick with no wake event yields a record
   whose last_bell stays None, and the board reads UNKNOWN, not
   ALIVE: a ticking watchman that never rang is not claimed
   alive. The rung state file is never read as liveness proof,
   because OS-118 writes it only when new rung keys appear.

What this drill does NOT claim, stated plainly. The bridge
proves the record shape and the detector path, not a live
watchman: no booted test image, no relay-watchman.service
actually running, no systemd restart of a dead watchman, and
no live queue reader (OS-118's snapshot files are still the
interface until the queue reader lands). A live wake on a
booted image remains owed, exactly as OS-118 recorded.
No bus post, no live Redis, no network.

Runs unattended: python3 intel/drills/watchman_bridge.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchman_bridge as bridge  # noqa: E402
from intel import watchman_watch as ww  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")

NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check(name, condition, detail=""):
    print("%s %s %s" % ("PASS" if condition else "FAIL", name, detail))
    return condition


def main():
    ok = True
    watchman = _load_watchman()

    # Phase 1: the real Pax tick rings once for a sleeping agent.
    jobs = [{"id": "job-1", "status": "open", "addressed_to": "hana",
             "title": "Demo job"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}
    events, _keys = watchman.tick(jobs, agents, set(), NOW)
    ok &= _check("phase1-real-tick-wake",
                 len(events) == 1 and events[0]["kind"] == "wake"
                 and events[0]["job_id"] == "job-1"
                 and events[0]["ts"] == NOW,
                 "events=%s" % (events,))

    # Phase 2: the bridge record reads ALIVE, journals nothing.
    record = bridge.fold_tick(events, NOW)
    snapshot = bridge.machines_snapshot({"m1": record})
    states = ww.current_states(snapshot, NOW)
    journal = ww.watchman_watch_tick(snapshot, [], NOW)
    ok &= _check("phase2-bridge-alive",
                 record.get("watchman_alive") is True
                 and record.get("last_bell") == NOW
                 and len(states) == 1 and states[0]["state"] == "alive"
                 and journal == [],
                 "record=%s states=%s journal=%s"
                 % (record, states, journal))

    # Phase 3: aged past the stale window, revivable restart.
    aged = dict(record, restart_ok=True)
    late = NOW + STALE + 60
    aged_snapshot = bridge.machines_snapshot({"m1": aged})
    dark = ww.watchman_watch_tick(aged_snapshot, [], late)
    kinds = [entry["kind"] for entry in dark]
    fresh_events, _ = watchman.tick(jobs, agents, set(), late + 60)
    fresh = bridge.fold_tick(fresh_events, late + 60, prior=record)
    recovered = ww.watchman_watch_tick(
        bridge.machines_snapshot({"m1": fresh}), dark, late + 60)
    ok &= _check("phase3-aged-crew-dark-and-recover",
                 kinds == ["crew-dark", "watchman-restart"]
                 and dark[1].get("restart_ok") is True
                 and len(recovered) == 1
                 and recovered[0]["kind"] == "watchman-recovered",
                 "dark=%s recovered=%s" % (kinds, recovered))

    # Phase 4: a tick with no wake event never invents a bell.
    quiet_events, _ = watchman.tick([], agents, set(), NOW)
    quiet = bridge.fold_tick(quiet_events, NOW)
    quiet_states = ww.current_states(
        bridge.machines_snapshot({"m1": quiet}), NOW)
    ok &= _check("phase4-no-bell-unknown",
                 quiet.get("last_bell") is None
                 and len(quiet_states) == 1
                 and quiet_states[0]["state"] == "unknown",
                 "quiet=%s states=%s" % (quiet, quiet_states))

    print("watchman_bridge drill: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
