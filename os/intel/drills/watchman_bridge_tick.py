"""Watchman bridge service-loop drill (Milo lane, OS-122 follow-up).

The bridge (intel/watchman_bridge.py) already folds one
relay_watchman tick into one watchman_watch record, but a
service loop must not hand-assemble fold, snapshot, and judge
per machine. watchman_tick() is the one call: {machine:
events} in, ({machine: record}, new journal records) out.
This drill proves that call on fixtures, in five checks:

1. Two machines, one rings, one quiet: the real Pax tick
   rings for the sleeping agent's machine and stays quiet
   for the other; the ringing record reads ALIVE with its
   bell at the tick time, the quiet record reads UNKNOWN
   (ticking but never rang is not claimed alive), and the
   journal stays empty.
2. Silence then recovery: the ringing machine folded with
   no new events past the stale window (restart_ok True,
   the caller's restart fact) journals exactly one
   crew-dark plus one restart-succeeded record and nothing
   for the quiet machine; a fresh ring then journals
   exactly one recovered record.
3. Second episode re-alerts: after recovery the same
   machine goes dark again (restart_ok False, no restart
   fact invented) and journals a fresh crew-dark, a
   restart-failed record, and exactly one escalation;
   an identical second tick journals nothing new.
4. Malformed input is contained: a non-dict mapping
   yields no records and no journal, and junk events for
   one machine leave the healthy machine's record and
   journal untouched.
5. Inputs are never mutated: events, priors, and journal
   come back unchanged.

What this drill does NOT claim, stated plainly. The call
proves the record shape and the detector path, not a live
watchman: no booted test image, no relay-watchman.service
actually running, no systemd restart of a dead watchman,
and no live queue reader (OS-118's snapshot files are
still the interface until the queue reader lands). A
restart_ok value is always the caller's fact, never
something this module observes. No bus post, no live
Redis, no network.

Runs unattended: python3 intel/drills/watchman_bridge_tick.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
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
        "relay_watchman_tick", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check(name, condition, detail=""):
    print("%s %s %s" % ("PASS" if condition else "FAIL", name, detail))
    return condition


def _kinds(journal):
    return [entry["kind"] for entry in journal]


def main():
    ok = True
    watchman = _load_watchman()

    # Phase 1: one machine rings, one stays quiet.
    jobs = [{"id": "job-1", "status": "open", "addressed_to": "hana",
             "title": "Demo job"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}
    ring_events, _ = watchman.tick(jobs, agents, set(), NOW)
    quiet_events, _ = watchman.tick([], agents, set(), NOW)
    events = {"m1": ring_events, "m2": quiet_events}
    events_copy = copy.deepcopy(events)
    records, journal = bridge.watchman_tick(events, NOW)
    states = ww.current_states(
        bridge.machines_snapshot(records), NOW)
    by_machine = {state["machine"]: state["state"]
                  for state in states}
    ok &= _check("phase1-ring-and-quiet",
                 records["m1"].get("last_bell") == NOW
                 and records["m2"].get("last_bell") is None
                 and by_machine == {"m1": "alive", "m2": "unknown"}
                 and journal == []
                 and events == events_copy,
                 "records=%s states=%s journal=%s"
                 % (records, by_machine, journal))

    # Phase 2: m1 goes silent past the stale window, then rings.
    late = NOW + STALE + 60
    priors = {"m1": records["m1"], "m2": records["m2"]}
    priors_copy = copy.deepcopy(priors)
    dark_records, dark = bridge.watchman_tick(
        {"m1": [], "m2": []}, late, priors=priors,
        journal=[], restart_ok={"m1": True})
    journal = dark
    fresh_events, _ = watchman.tick(jobs, agents, set(), late + 60)
    recovered_records, recovered = bridge.watchman_tick(
        {"m1": fresh_events, "m2": []}, late + 60,
        priors=dark_records, journal=journal)
    ok &= _check("phase2-silence-and-recovery",
                 _kinds(dark) == ["crew-dark", "watchman-restart"]
                 and dark[1].get("restart_ok") is True
                 and all(entry.get("machine") == "m1" for entry in dark)
                 and _kinds(recovered) == ["watchman-recovered"]
                 and recovered[0].get("machine") == "m1"
                 and priors == priors_copy,
                 "dark=%s recovered=%s"
                 % (_kinds(dark), _kinds(recovered)))
    journal = journal + recovered

    # Phase 3: a second dark episode re-alerts, then stays quiet.
    later = late + 2 * STALE + 120
    dark2_records, dark2 = bridge.watchman_tick(
        {"m1": [], "m2": []}, later,
        priors=recovered_records, journal=journal,
        restart_ok={"m1": False})
    journal2 = journal + dark2
    again_records, again = bridge.watchman_tick(
        {"m1": [], "m2": []}, later + 60,
        priors=dark2_records, journal=journal2)
    ok &= _check("phase3-second-episode-realerts",
                 _kinds(dark2) == ["crew-dark", "watchman-restart",
                                   "escalation"]
                 and dark2[1].get("restart_ok") is False
                 and again == []
                 and all(entry.get("machine") == "m1"
                         for entry in dark2),
                 "dark2=%s again=%s" % (_kinds(dark2), again))

    # Phase 4: malformed input is contained per machine.
    bad_records, bad_journal = bridge.watchman_tick("junk", NOW)
    mixed_records, mixed_journal = bridge.watchman_tick(
        {"m1": "junk", "m2": quiet_events}, NOW)
    mixed_states = ww.current_states(
        bridge.machines_snapshot(mixed_records), NOW)
    mixed_by_machine = {state["machine"]: state["state"]
                        for state in mixed_states}
    ok &= _check("phase4-malformed-contained",
                 bad_records == {} and bad_journal == []
                 and mixed_records["m1"].get("last_bell") is None
                 and mixed_records["m2"].get("last_bell") is None
                 and mixed_by_machine == {"m1": "unknown",
                                          "m2": "unknown"}
                 and mixed_journal == [],
                 "bad=%s mixed=%s" % (bad_records, mixed_by_machine))

    # Phase 5: a machine missing from the mapping is unjudged.
    partial_records, partial_journal = bridge.watchman_tick(
        {"m2": quiet_events}, NOW)
    ok &= _check("phase5-absent-machine-unjudged",
                 list(partial_records) == ["m2"]
                 and partial_journal == [],
                 "records=%s" % (list(partial_records),))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
