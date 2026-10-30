"""Watchman service-loop caller drill (Milo lane, OS-122 follow-up).

watchman_tick() folds one cycle's events, but a loop must
run the watchman per machine, carry priors and journal
across cycles, and survive a watchman that cannot run.
This drill proves intel/watchman_loop.py loop_cycle() on
fixtures, in five checks:

1. Two machines, real Pax tick output as stdout: the
   sleeping agent's machine rings and reads ALIVE with
   its bell at the tick time; the quiet machine reads
   UNKNOWN (ticking but never rang is not claimed alive);
   the journal stays empty.
2. Death by failed runs, honestly aged: the ringing
   machine's runs fail on later cycles, so its prior
   record is carried forward, never refreshed. Past the
   stale window it journals exactly one crew-dark, one
   restart record reading restart failed (the prior's
   restart_ok True from cycle 1 is stripped on carry,
   never re-spent), and exactly one escalation; a
   further failed cycle journals nothing new. A fresh
   successful ring then journals exactly one recovered.
3. Malformed stdout contained: one junk line in a
   successful run's stdout counts in diagnostics and
   leaves the machine's good wake event, the other
   machine, and the journal untouched.
4. No-prior failure unjudged: a machine whose run fails
   before it ever reported is absent from records and
   journal, and appears only in diagnostics.
5. Inputs are never mutated: runs, priors, and journal
   come back unchanged, and a carried record is a copy,
   not the prior object.

What this drill does NOT claim, stated plainly. The
loop proves the caller judgment, not a live service:
no booted test image, no relay-watchman.service
actually running (runs are supplied pairs, the module
starts no subprocess), no systemd restart of a dead
watchman, no agent session started (OS-119), no job
reassigned (OS-125), no push sent (Hana OS-097), and
no live queue reader (OS-118's snapshot files are
still the interface until it lands). A failed run here
is a diagnostics line, and the escalation is a payload,
never a send. No bus post, no live Redis, no network.

Runs unattended: python3 intel/drills/watchman_loop.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchman_loop as loop  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")
NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_loop_drill", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WATCHMAN = _load_watchman()
JOBS = [{"id": "j1", "status": "open", "addressed_to": "hana"}]
AGENTS = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}


def _stdout_for(at):
    events, _ = WATCHMAN.tick(JOBS, AGENTS, set(), at)
    return "".join(json.dumps(event, sort_keys=True) + "\n"
                   for event in events)


def _kinds(journal):
    return [entry["kind"] for entry in journal]


def _fail(msg):
    print("FAIL: %s" % msg)
    return 1


def main():
    journal = []

    # Phase 1: two machines, real Pax tick output as stdout.
    runs = {"alpha": (True, _stdout_for(NOW)),
            "beta": (True, "")}
    runs_before = copy.deepcopy(runs)
    records, new, diagnostics = loop.loop_cycle(
        runs, NOW, priors={}, journal=journal,
        restart_ok={"alpha": True})
    journal = journal + new
    if records["alpha"]["last_bell"] != NOW:
        return _fail("phase 1: ringing machine bell is not the tick time")
    if records["beta"]["last_bell"] is not None:
        return _fail("phase 1: quiet machine invented a bell")
    if new or diagnostics["run_failures"]:
        return _fail("phase 1: quiet cycle journaled or failed")
    if runs != runs_before:
        return _fail("phase 1: runs mutated")
    print("PASS phase 1: ring reads ALIVE bell, quiet reads UNKNOWN")
    priors = records

    # Phase 2: alpha's runs fail; its prior ages into crew-dark.
    priors_before = copy.deepcopy(priors)
    journal_before = copy.deepcopy(journal)
    records, new, diagnostics = loop.loop_cycle(
        {"alpha": (False, "unused"), "beta": (True, "")},
        NOW + STALE + 100, priors=priors, journal=journal)
    journal = journal + new
    if diagnostics["run_failures"] != ["alpha"]:
        return _fail("phase 2: failed run not in diagnostics")
    if "restart_ok" in records["alpha"]:
        return _fail("phase 2: carried record re-spent restart_ok")
    if records["alpha"]["last_bell"] != NOW:
        return _fail("phase 2: carried record refreshed its bell")
    if _kinds(new) != ["crew-dark", "watchman-restart",
                       "escalation"]:
        return _fail("phase 2: expected dark+restart+escalation, got %s"
                     % _kinds(new))
    restart = [e for e in new if e["kind"] == "watchman-restart"][0]
    if restart["restart_ok"] is not False:
        return _fail("phase 2: carried restart_ok read as success")
    if priors != priors_before or journal_before != journal[:len(journal_before)]:
        return _fail("phase 2: priors or journal mutated")
    if records["alpha"] is priors["alpha"]:
        return _fail("phase 2: carried record is the prior object")
    print("PASS phase 2: failed runs age the prior into one dark "
          "episode with one fail-closed escalation")
    priors = records

    # Phase 2b: a further failed cycle journals nothing new.
    records, new, _ = loop.loop_cycle(
        {"alpha": (False, "unused")}, NOW + STALE + 200,
        priors=priors, journal=journal)
    if new:
        return _fail("phase 2b: open episode journaled again")
    print("PASS phase 2b: open dark episode stays silent on repeat")

    # Phase 2c: a fresh successful ring recovers the machine.
    records, new, _ = loop.loop_cycle(
        {"alpha": (True, _stdout_for(NOW + STALE + 300))},
        NOW + STALE + 300, priors=priors, journal=journal)
    journal = journal + new
    if _kinds(new) != ["watchman-recovered"]:
        return _fail("phase 2c: expected one recovered, got %s"
                     % _kinds(new))
    print("PASS phase 2c: fresh ring recovers the dark machine")
    priors = records

    # Phase 3: malformed stdout line contained per machine.
    dirty = _stdout_for(NOW + STALE + 400) + "this is not json\n"
    records, new, diagnostics = loop.loop_cycle(
        {"alpha": (True, dirty), "beta": (True, "")},
        NOW + STALE + 400, priors=priors, journal=journal)
    if diagnostics["malformed_lines"] != {"alpha": 1}:
        return _fail("phase 3: malformed line not counted per machine")
    if records["alpha"]["last_bell"] != NOW + STALE + 400:
        return _fail("phase 3: junk line broke the good wake event")
    if new:
        return _fail("phase 3: contained junk journaled something")
    print("PASS phase 3: junk stdout line counted, good events kept")

    # Phase 4: no-prior failure is unjudged, diagnostics only.
    records, new, diagnostics = loop.loop_cycle(
        {"gamma": (False, "")}, NOW, priors={}, journal=[])
    if "gamma" in records or new:
        return _fail("phase 4: unseen machine earned a record")
    if diagnostics["run_failures"] != ["gamma"]:
        return _fail("phase 4: unseen failure missing from diagnostics")
    print("PASS phase 4: unseen machine's failed run is diagnostics only")

    # Phase 5: inputs never mutated across a mixed cycle.
    runs = {"alpha": (True, _stdout_for(NOW + 500)),
            "beta": (False, "")}
    runs_before = copy.deepcopy(runs)
    priors_before = copy.deepcopy(priors)
    journal_before = copy.deepcopy(journal)
    loop.loop_cycle(runs, NOW + 500, priors=priors, journal=journal)
    if (runs != runs_before or priors != priors_before
            or journal != journal_before):
        return _fail("phase 5: mixed cycle mutated its inputs")
    print("PASS phase 5: runs, priors, and journal unchanged")
    print("ALL PASS (5 phases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
