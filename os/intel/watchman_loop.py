"""OS-122 follow-up: the service-loop caller for watchman_tick().

watchman_tick() folds one cycle's relay_watchman events per
machine and judges them, but it is a pure call: it keeps no
state between cycles, runs no watchman, and reads no stdout.
This module is the caller that will sit in the production
loop, written against the interfaces that already exist so
it can be drilled on fixtures today and wired to the real
relay_watchman CLI later without changing its judgment:

- One run per machine per cycle is a relay_watchman --once
  run (Pax OS-118): exit 0 means the run happened and its
  stdout is one JSON event object per line; anything else
  means the run failed and its stdout is unusable.
- loop_cycle() takes {machine: (ok, stdout)} for the cycle,
  plus the priors and journal the loop carries, and returns
  (records, new_journal, diagnostics).

Judgment rules, stated plainly because each one guards a
silent-failure class:

- A successful run folds through watchman_tick(), exactly
  as the bridge documents: a tick proves the watchman ran,
  a wake event proves the bell, a quiet tick keeps
  last_bell None and reads UNKNOWN, never ALIVE.
- A failed run folds NOTHING fresh. Inventing an alive
  record for a watchman that never ran would hide the
  failure; inventing a dead record for a watchman the
  caller simply could not reach would cry wolf. Instead
  the machine's last real record, when one exists, is
  carried forward unchanged into the judge, so its bell
  ages honestly: a machine that rang and then stops
  reporting goes crew-dark once its bell passes the
  stale window, and a machine that never rang stays
  UNKNOWN and yields nothing. A failed run for a machine
  with no prior record is unjudged, and the failure is
  recorded only in diagnostics, never as a watchman
  record. Diagnostics are the caller's own log, not a
  bus post and not an alert.
- A carried record drops restart_ok. A restart outcome is
  a fact of the cycle that ran it, never something carried
  forward: a prior folded with restart_ok True that goes
  dark again must read restart failed and escalate once,
  fail closed toward Dale, rather than re-spending an
  old success as proof the dead watchman revived.
- Malformed stdout lines are contained per machine: a
  junk line counts in diagnostics and never breaks the
  machine's good events or any other machine.
- Inputs are never mutated: runs, priors, and journal
  come back unchanged, and carried records are copies.

What this module does NOT claim. It runs no subprocess
itself: the caller that owns the machines supplies each
run's (ok, stdout) pair, so the judgment drills without
a booted image, a running relay-watchman.service, or
the live queue reader OS-118 still owes. It starts no
agent session (OS-119's adapter), restarts no process
(systemd under OS-034), reassigns no job (OS-125
baton), and sends no push (Hana OS-097): a failed run
here is a diagnostic line, and the escalation the judge
builds is a payload, never a send. No bus posts, no
live Redis, no network, no model calls.
"""

import copy
import json

from intel import watchman_bridge as _bridge
from intel import watchman_watch as _watchman_watch


def parse_event_lines(text):
    """Stdout text -> (events, malformed_count).

    One JSON object per non-blank line. A line that is not
    a JSON object is malformed: it is counted, skipped, and
    never breaks the good lines around it. Non-string input
    yields no events and counts as one malformed line, so a
    caller passing garbage still gets a usable answer.
    """
    if not isinstance(text, str):
        return [], 1
    events = []
    malformed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            malformed += 1
            continue
        if not isinstance(value, dict):
            malformed += 1
            continue
        events.append(value)
    return events, malformed


def loop_cycle(runs, now, priors=None, journal=None, restart_ok=None):
    """One service-loop cycle over every machine's watchman run.

    runs is {machine: (ok, stdout)}: ok True means the
    relay_watchman --once run exited 0 and stdout holds
    its event lines; ok False means the run failed and
    stdout is ignored. priors is {machine: prior record}
    carried from the previous cycle; journal is the
    caller's journal list for episode dedupe. restart_ok
    is an optional {machine: bool} of caller-supplied
    restart outcomes for machines whose runs succeeded.

    Returns (records, new_journal, diagnostics).
    records is the board's latest picture: fresh records
    for machines whose runs succeeded, carried prior
    records (restart_ok stripped, copied) for machines
    whose runs failed and that have a prior. new_journal
    holds only this cycle's new records. diagnostics is
    {"run_failures": [machine, ...], "malformed_lines":
    {machine: count, ...}} with the malformed key present
    only for machines that had malformed lines. Inputs are
    never mutated.
    """
    if not isinstance(runs, dict):
        runs = {}
    if not isinstance(priors, dict):
        priors = {}
    if not isinstance(journal, list):
        journal = []
    if not isinstance(restart_ok, dict):
        restart_ok = {}

    ok_events = {}
    ok_priors = {}
    carried = {}
    diagnostics = {"run_failures": [], "malformed_lines": {}}

    for name in sorted(runs):
        run = runs[name]
        ok = False
        stdout = ""
        if isinstance(run, (list, tuple)) and len(run) >= 2:
            ok = run[0] is True
            stdout = run[1]
        if not ok:
            diagnostics["run_failures"].append(name)
            prior = priors.get(name)
            if isinstance(prior, dict):
                record = {key: copy.deepcopy(value)
                          for key, value in prior.items()
                          if key != "restart_ok"}
                carried[name] = record
            continue
        events, malformed = parse_event_lines(stdout)
        if malformed:
            diagnostics["malformed_lines"][name] = malformed
        ok_events[name] = events
        if isinstance(priors.get(name), dict):
            ok_priors[name] = priors[name]

    fresh, journal_new = _bridge.watchman_tick(
        ok_events, now, priors=ok_priors, journal=journal,
        restart_ok=restart_ok)
    if carried:
        snapshot = _bridge.machines_snapshot(carried)
        carried_new = _watchman_watch.watchman_watch_tick(
            snapshot, journal + journal_new, now)
        journal_new = journal_new + carried_new

    records = {}
    records.update(fresh)
    records.update(carried)
    return records, journal_new, diagnostics
