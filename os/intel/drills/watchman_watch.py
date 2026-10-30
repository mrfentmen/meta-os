"""Watchman-watch drill (Milo lane, OS-122).

Acceptance: kill the watchman on the fixture machine
and the watchdog flags crew-dark within one detector
cycle, the restart revives it, and no Dale push fires;
kill it beyond the restart's power and exactly one
blocked-push fires naming the machine; the board's
group for that machine reads watchman-dead while it
lasts.

What fixtures can prove, and what they cannot, stated
plainly. The module (intel/watchman_watch.py) judges
fixture watchman records; it never touches a process,
rings a bell, or sends a push. The drill's simulated
owner applies each restart, so the restart half is
simulated, not a systemd restart on a live machine.
The resident watchman program that actually rings is
Pax OS-118, and a live kill on a booted test image
is not claimed here, because no test image runs in
this repo.

Phases, all on fixtures with a fake clock (base time T0):

- kill-and-revive: watchman on machine milo-box is
  killed (alive flag False). One tick yields a
  crew-dark record and a restart record, and no
  escalation and no push payload anywhere. The
  simulated owner applies the restart (alive flag
  True, fresh bell). The next tick yields a recovered
  record, and still no escalation. The board reads
  watchman-dead while dark and watchman alive after.
- kill-beyond-repair: watchman on machine rowan-box
  is killed with restart_ok False. One tick yields
  crew-dark, a failed restart record, and exactly one
  escalation whose push payload validates and names
  the machine. Two further unchanged ticks yield
  zero new records: no loop, no duplicate push. The
  drill's sent ledger stays empty throughout, because
  nothing here sends.
- revive-then-die-again: after a recovery, the same
  machine dies again with restart_ok False. The new
  episode yields a fresh crew-dark record and a fresh
  escalation: dedupe is per episode, so a second
  death is never silenced by the first one's records.
- alive-and-unknown: a live machine and an unknown
  machine (no flag, no bell) yield no records at all,
  and the board lines say alive and unknown, never
  dead. Malformed machine entries (a non-record, a
  missing machines mapping) yield no records and no
  crash.
- stale-bell: a watchman whose flag says alive but
  whose bell is older than the stale window reads
  dead and earns a crew-dark record; a fresh bell
  reads alive. The stale window is overridable per
  call, and the default equals the thresholds value.
- no-dale-and-immutable: journal records carry no
  announcement field, the module imports no socket,
  bus, or network module, and the tick leaves the
  snapshot and the journal byte-for-byte unchanged.

What this drill does NOT claim: a live watchman
actually killed and restarted, a real systemd
restart on a booted test image, the watchman's
mechanical ringing (Pax OS-118), or a phone
actually ringing (the Web Push worker wiring is
Hana OS-097). The escalation here is a built
payload, never a sent push.

Runs unattended on fixtures: no network, no Redis,
no bus posts.

Usage: python3 intel/drills/watchman_watch.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import push as push_module  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchman_watch as ww  # noqa: E402

T0 = 100000
SENT = []


def check(name, ok, detail=""):
    """One phase line; False fails the drill."""
    if ok:
        print("%s: PASS" % name)
    else:
        print("%s: FAIL: %s" % (name, detail))
    return ok


def phase_kill_and_revive():
    snap = {"machines": {"milo-box": {
        "watchman_alive": False, "last_bell": T0 - 600,
        "last_wake": T0 - 600, "restart_ok": True}}}
    journal = []
    new = ww.watchman_watch_tick(snap, journal, T0)
    kinds = [r["kind"] for r in new]
    if kinds != ["crew-dark", "watchman-restart"]:
        return check("kill-and-revive", False,
                     "first tick kinds %s" % kinds)
    if any("push" in r for r in new):
        return check("kill-and-revive", False,
                     "revivable death carried a push")
    if ww.board_lines(ww.current_states(snap, T0)) != [
            "Machine milo-box: watchman dead (crew-dark)."]:
        return check("kill-and-revive", False,
                     "board did not read dead while dark")
    journal = journal + new
    snap["machines"]["milo-box"] = {
        "watchman_alive": True, "last_bell": T0,
        "last_wake": T0, "restart_ok": True}
    new = ww.watchman_watch_tick(snap, journal, T0 + 60)
    if [r["kind"] for r in new] != ["watchman-recovered"]:
        return check("kill-and-revive", False,
                     "recovery tick kinds %s"
                     % [r["kind"] for r in new])
    if any("push" in r for r in new):
        return check("kill-and-revive", False,
                     "recovery carried a push")
    if ww.board_lines(ww.current_states(snap, T0 + 60)) != [
            "Machine milo-box: watchman alive."]:
        return check("kill-and-revive", False,
                     "board did not read alive after recovery")
    lines = ww.watchman_brief_lines(journal + new)
    if not any("Crew-dark on machine milo-box" in line
               for line in lines):
        return check("kill-and-revive", False,
                     "brief lost the crew-dark line")
    return check("kill-and-revive", True)


def phase_kill_beyond_repair():
    snap = {"machines": {"rowan-box": {
        "watchman_alive": False, "last_bell": T0 - 600,
        "last_wake": T0 - 600, "restart_ok": False}}}
    journal = []
    new = ww.watchman_watch_tick(snap, journal, T0)
    kinds = [r["kind"] for r in new]
    if kinds != ["crew-dark", "watchman-restart", "escalation"]:
        return check("kill-beyond-repair", False,
                     "first tick kinds %s" % kinds)
    escalation = new[2]
    if not push_module.validate_push(escalation.get("push")):
        return check("kill-beyond-repair", False,
                     "escalation push did not validate")
    if "rowan-box" not in escalation.get("question", ""):
        return check("kill-beyond-repair", False,
                     "escalation question did not name the machine")
    if SENT:
        return check("kill-beyond-repair", False,
                     "sent ledger is not empty")
    journal = journal + new
    for tick in (T0 + 60, T0 + 120):
        new = ww.watchman_watch_tick(snap, journal, tick)
        if new:
            return check("kill-beyond-repair", False,
                         "re-tick at %s yielded %s" % (tick, new))
        journal = journal + new
    if len([r for r in journal if r["kind"] == "escalation"]) != 1:
        return check("kill-beyond-repair", False,
                     "escalation count is not exactly one")
    return check("kill-beyond-repair", True)


def phase_revive_then_die_again():
    snap = {"machines": {"milo-box": {
        "watchman_alive": False, "last_bell": T0 - 600,
        "last_wake": T0 - 600, "restart_ok": True}}}
    journal = ww.watchman_watch_tick(snap, [], T0)
    snap["machines"]["milo-box"] = {
        "watchman_alive": True, "last_bell": T0,
        "last_wake": T0, "restart_ok": False}
    journal = journal + ww.watchman_watch_tick(snap, journal, T0 + 60)
    snap["machines"]["milo-box"] = {
        "watchman_alive": False, "last_bell": T0 + 60,
        "last_wake": T0 + 60, "restart_ok": False}
    new = ww.watchman_watch_tick(snap, journal, T0 + 120)
    kinds = [r["kind"] for r in new]
    if kinds != ["crew-dark", "watchman-restart", "escalation"]:
        return check("revive-then-die-again", False,
                     "second death kinds %s" % kinds)
    if len([r for r in journal + new
            if r["kind"] == "crew-dark"]) != 2:
        return check("revive-then-die-again", False,
                     "second death did not re-alert")
    return check("revive-then-die-again", True)


def phase_alive_and_unknown():
    snap = {"machines": {
        "live-box": {"watchman_alive": True, "last_bell": T0,
                     "last_wake": T0, "restart_ok": True},
        "quiet-box": {"last_bell": None, "last_wake": None},
        "broken-box": "not a record"}}
    new = ww.watchman_watch_tick(snap, [], T0)
    if new:
        return check("alive-and-unknown", False,
                     "live/unknown machines yielded %s" % new)
    lines = ww.board_lines(ww.current_states(snap, T0))
    if lines != ["Machine broken-box: watchman state unknown.",
                 "Machine live-box: watchman alive.",
                 "Machine quiet-box: watchman state unknown."]:
        return check("alive-and-unknown", False,
                     "board lines %s" % lines)
    if ww.watchman_watch_tick({}, [], T0) != []:
        return check("alive-and-unknown", False,
                     "missing machines mapping was not empty")
    if ww.watchman_watch_tick({"machines": "not a mapping"},
                              [], T0) != []:
        return check("alive-and-unknown", False,
                     "malformed machines mapping was not empty")
    return check("alive-and-unknown", True)


def phase_stale_bell():
    stale = {"watchman_alive": True, "last_bell": T0 - 301,
             "last_wake": T0 - 301, "restart_ok": False}
    if ww.machine_state(stale, T0, stale_minutes=5) != ww.DEAD:
        return check("stale-bell", False,
                     "bell 301s old did not read dead at 5 min")
    fresh = {"watchman_alive": True, "last_bell": T0 - 60,
             "last_wake": T0 - 60, "restart_ok": True}
    if ww.machine_state(fresh, T0, stale_minutes=5) != ww.ALIVE:
        return check("stale-bell", False,
                     "bell 60s old did not read alive at 5 min")
    if ww.machine_state(fresh, T0) != ww.ALIVE:
        return check("stale-bell", False,
                     "default window did not read a fresh bell alive")
    if thresholds.WATCHMAN_STALE_MINUTES != 5:
        return check("stale-bell", False,
                     "thresholds default is not 5 minutes")
    snap = {"machines": {"stale-box": stale}}
    new = ww.watchman_watch_tick(snap, [], T0)
    if [r["kind"] for r in new] != ["crew-dark", "watchman-restart",
                                   "escalation"]:
        return check("stale-bell", False,
                     "stale-bell tick kinds %s"
                     % [r["kind"] for r in new])
    return check("stale-bell", True)


def phase_no_dale_and_immutable():
    snap = {"machines": {"rowan-box": {
        "watchman_alive": False, "last_bell": T0 - 600,
        "last_wake": T0 - 600, "restart_ok": False}}}
    journal = []
    snap_before = copy.deepcopy(snap)
    journal_before = copy.deepcopy(journal)
    new = ww.watchman_watch_tick(snap, journal, T0)
    if snap != snap_before or journal != journal_before:
        return check("no-dale-and-immutable", False,
                     "tick mutated its inputs")
    if any("announce" in key for r in new for key in r):
        return check("no-dale-and-immutable", False,
                     "a record carried an announcement field")
    path = os.path.abspath(__file__)
    module_path = path.replace("drills/watchman_watch.py",
                               "watchman_watch.py")
    with open(module_path) as handle:
        source = handle.read()
    for banned in ("import socket", "import urllib",
                   "import requests", "bus_post", "redis"):
        if banned in source:
            return check("no-dale-and-immutable", False,
                         "module carries %s" % banned)
    if SENT:
        return check("no-dale-and-immutable", False,
                     "sent ledger is not empty")
    return check("no-dale-and-immutable", True)


def main():
    phases = [phase_kill_and_revive,
              phase_kill_beyond_repair,
              phase_revive_then_die_again,
              phase_alive_and_unknown,
              phase_stale_bell,
              phase_no_dale_and_immutable]
    results = [phase() for phase in phases]
    print("%d/%d phases PASS" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
