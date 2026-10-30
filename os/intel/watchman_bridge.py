"""intel/watchman_bridge.py -- OS-122 follow-up to Pax OS-118.

Pax OS-118 landed the real watchman (os/watchman/relay_watchman.py):
a pure tick() over job and agent-heartbeat records that emits wake
and nudge events, plus relay-watchman.service under relay.target.
What it does NOT publish is a per-machine watchman record in the
shape Milo's OS-122 module (intel/watchman_watch.py) judges:
{watchman_alive, last_bell, last_wake}. The service file itself
names the split: systemd owns watchman process death, the watchdog
owns the watchman going silent (crew-dark). This bridge closes
that gap from Milo's side only; it edits no Pax file.

One mapping rule, nothing else:

- A tick the caller actually ran proves the watchman is alive at
  that tick's time, so fold_tick marks watchman_alive True with
  last_tick = now. Aliveness comes from the tick executing, never
  from the watchman's rung state file: that file is only written
  when new rung keys appear, so its mtime cannot prove a tick
  happened, and this bridge never reads it.
- A bell is a wake event, nothing else. last_bell and last_wake
  advance only to the latest wake event's ts in the tick; a tick
  with no wake event keeps the prior bell, and a watchman that
  has ticked but never rung carries last_bell None. Under
  watchman_watch's own rule that record reads UNKNOWN on the
  board, not ALIVE: a ticking watchman with no bell rung is not
  claimed alive until it rings once.
- An aged record needs no special case: watchman_watch judges
  it DEAD once last_bell is older than WATCHMAN_STALE_MINUTES,
  and watchman_watch_tick journals crew-dark plus the restart
  record for that episode. The bridge invents no bell, no wake,
  and no restart outcome; restart_ok stays a fixture fact the
  caller supplies, exactly as OS-122 tests already do.

No bus posts, no live Redis, no network, no model calls. The
bridge reads only the tick events the caller hands it.

The service-loop entry point is watchman_tick(): one call folds
every machine's relay_watchman events into watchman_watch records
and judges them, so the future loop (or Pax's queue reader, once
it lands) does not hand-assemble fold, snapshot, and judge per
machine. A machine missing from the events mapping is not judged
at all: silence in the input is not a dead watchman. A machine
that stops reporting must be folded explicitly with an empty
event list and its prior record, so its bell ages honestly into
crew-dark instead of vanishing from the board.
"""

from intel import watchman_watch as _watchman_watch

WAKE_KIND = "wake"


def _num(value):
    """An int/float timestamp, else None. Bools are not times."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if value != value else value
    return None


def _prior_bell(prior):
    """The prior record's last_bell, or None when unusable."""
    if not isinstance(prior, dict):
        return None
    return _num(prior.get("last_bell"))


def fold_tick(events, now, prior=None):
    """One relay_watchman tick's events -> a watchman_watch record.

    events is the (events, new_keys) tick output's event list, or
    just the list. now is the tick's time. prior is the previous
    record for the same machine, or None. The return is a fresh
    dict; inputs are never mutated.
    """
    if not isinstance(events, list):
        events = []
    bell = _prior_bell(prior)
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("kind") != WAKE_KIND:
            continue
        ts = _num(event.get("ts"))
        if ts is None:
            continue
        if bell is None or ts > bell:
            bell = ts
    record = {"watchman_alive": True, "last_tick": _num(now),
              "last_bell": bell, "last_wake": bell}
    return record


def watchman_tick(events_by_machine, now, priors=None, journal=None,
                  restart_ok=None):
    """One service-loop call over every machine's watchman events.

    events_by_machine is {machine: events} where events is a
    relay_watchman tick's event list (or just the list). priors
    is {machine: prior record} for bell carry-over; a machine
    absent from priors starts fresh. journal is the caller's
    journal list for episode dedupe; it is never mutated, and
    only the new records are returned. restart_ok is an
    optional {machine: bool} of caller-supplied restart
    outcomes: the mechanical restart is the caller's fact,
    exactly as OS-122 tests supply it, never something this
    module observes. A machine with no restart fact supplied
    carries no restart_ok key, so the judge reads a dark
    machine's restart as failed and escalates once — fail
    closed toward Dale, stated plainly, rather than
    assuming a restart the caller never ran.

    Returns (records, new_journal): records is {machine:
    record} for every machine named in events_by_machine;
    new_journal is what watchman_watch_tick judges from
    those records. Inputs are never mutated. A machine
    whose events are not a list still gets a fresh fold
    (no bell invented); a machine missing from the
    mapping entirely is absent from records and unjudged.
    Malformed input for one machine never breaks another.
    """
    if not isinstance(events_by_machine, dict):
        events_by_machine = {}
    if not isinstance(priors, dict):
        priors = {}
    if not isinstance(restart_ok, dict):
        restart_ok = {}
    records = {}
    for name in sorted(events_by_machine):
        record = fold_tick(events_by_machine[name], now,
                           prior=priors.get(name))
        outcome = restart_ok.get(name)
        if isinstance(outcome, bool):
            record["restart_ok"] = outcome
        records[name] = record
    snapshot = machines_snapshot(records)
    journal_list = journal if isinstance(journal, list) else []
    new_journal = _watchman_watch.watchman_watch_tick(
        snapshot, journal_list, now)
    return records, new_journal


def machines_snapshot(records):
    """{machine: record} -> the snapshot watchman_watch consumes.

    Non-dict records are skipped, never judged: a shape that is
    not a watchman record cannot earn a crew-dark.
    """
    machines = {}
    if not isinstance(records, dict):
        return {"machines": machines}
    for name, record in records.items():
        if isinstance(record, dict):
            machines[name] = dict(record)
    return {"machines": machines}
