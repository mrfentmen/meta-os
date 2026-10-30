"""intel/watchman_watch.py -- who watches the watchman (OS-122, Milo).

The watchdog treats a dead watchman as a first-class
failure. Crew-dark is the name for it: the machine's
agents are asleep, its jobs are invisible to them, and
no bell will ring for new work until the watchman is
back. A dead watchman is not a job alert and not a
worker stall; it is the failure of the thing that was
supposed to notice failures, so it gets its own
detector, its own journal records, and its own
escalation rule.

The rule is the OS-095 ladder's rule, applied one
level up, with the OS-096 gate at the end of it:

- a dead watchman earns a crew-dark record and a
  restart attempt, exactly as a dead worker earns a
  restart under OS-034 (systemd owns process death;
  the watchdog owns the judgement, never the process).
- if the restart revives it, the next tick journals a
  recovered record, and Dale hears nothing at any
  point: a revived watchman is crew business, settled
  by the crew.
- if the restart cannot revive it, the machine earns
  exactly one blocked push (OS-097): the payload is
  built here through intel/push.py, never sent.
  Sending belongs to the Web Push worker
  (muse-relay-push, outside this repo), so this
  module has no network, no bus post, and no secret,
  and nothing in it can ring a phone on its own.
  A second tick over the same dark episode journals
  nothing new: no loop, no duplicate push, ever.

What counts as dead is a pure function of the
machine's watchman record and the tick time:

- watchman_alive False: dead, whatever the bell says.
  A killed watchman is dead even if its last bell
  looks recent.
- watchman_alive True with a bell older than the
  stale window (intel/thresholds.py
  WATCHMAN_STALE_MINUTES, default 5): dead. A flag
  that says alive while the bell has gone quiet is
  a stale flag, not a live watchman.
- watchman_alive True with a fresh bell: alive.
- anything else (no flag, no bell, a malformed
  record): unknown. An absent signal is not a dead
  watchman, and the watchdog never claims crew-dark
  from missing evidence. Unknown machines yield no
  records and no escalation, only a board line that
  says unknown.

Episodes, not globals: a machine that recovers and
then dies again earns a fresh crew-dark record and,
if its restart fails again, a fresh escalation.
Dedupe is per dark episode: a crew-dark record is
open until a recovered record closes it, and an
escalation counts only inside its own episode. A
global dedupe key would silence the second death,
which is exactly the failure this module exists to
catch.

Per-machine state for the board (OS-111): the board
does not read the journal to learn whether a
watchman is alive; current_states() returns one
state record per machine (machine, state, last bell,
last wake, as of the tick time), and board_lines()
renders those records for the machine groups. The
board's group for a dark machine reads
watchman-dead while the darkness lasts, because
the state record says dead on every tick until
recovery, not just on the tick the darkness began.

The mechanical half is not here: the resident
watchman program that actually rings (Pax OS-118)
and the systemd unit that actually restarts it
(OS-034) are live-machine halves. This module
judges fixture watchman records, the drill's
simulated owner applies the restart, and a live
kill on a booted test image is not claimed here,
because no test image runs in this repo.

Inputs are never mutated: the snapshot and the
journal come back unchanged, and the tick returns
only new journal records.

Usage: watchman_watch_tick(snapshot, journal, now)
returns the new records; current_states(snapshot,
now) returns the board state records;
watchman_brief_lines(records) renders journal
records and board_lines(states) renders state
records for the next brief.
"""

from intel import push as push_module
from intel import thresholds as thresholds_module

__all__ = ["ALIVE", "DEAD", "UNKNOWN", "machine_state",
           "current_states", "watchman_watch_tick",
           "watchman_brief_lines", "board_lines"]

ALIVE = "alive"
DEAD = "dead"
UNKNOWN = "unknown"


def _num(value):
    """An int/float timestamp, else None. Bools are not times."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _machines(snapshot):
    """The machines mapping; a missing or malformed
    mapping reads as empty, so no machine is judged
    from a shape that is not a machines record."""
    if not isinstance(snapshot, dict):
        return {}
    machines = snapshot.get("machines")
    return machines if isinstance(machines, dict) else {}


def machine_state(record, now, stale_minutes=None):
    """Alive, dead, or unknown for one watchman record.

    stale_minutes overrides the thresholds default for
    the call; None reads intel/thresholds.py at call
    time, so an env-overridden demo profile changes
    detector behavior with no code edit (WDG-018).
    """
    if not isinstance(record, dict):
        return UNKNOWN
    alive_flag = record.get("watchman_alive")
    if alive_flag is False:
        return DEAD
    if alive_flag is not True:
        return UNKNOWN
    bell = _num(record.get("last_bell"))
    if bell is None:
        return UNKNOWN
    if stale_minutes is None:
        stale_minutes = thresholds_module.WATCHMAN_STALE_MINUTES
    try:
        window = float(stale_minutes) * 60.0
    except (TypeError, ValueError):
        return UNKNOWN
    if now - bell > window:
        return DEAD
    return ALIVE


def current_states(snapshot, now):
    """One board state record per machine, in name
    order. A state record is a publication, not a
    journal event: the board renders the latest set
    on every tick, so a dark machine reads dead on
    every tick until it recovers."""
    states = []
    for name in sorted(_machines(snapshot)):
        record = _machines(snapshot).get(name)
        state = machine_state(record, now)
        bell = None
        wake = None
        if isinstance(record, dict):
            bell = _num(record.get("last_bell"))
            wake = _num(record.get("last_wake"))
        states.append({"machine": name, "state": state,
                       "last_bell": bell, "last_wake": wake,
                       "as_of": now})
    return states


def _episode_open(journal, machine):
    """True when the machine's latest crew-dark record
    has no recovered record after it. Journal order is
    episode order: a recovered record closes the
    episode it follows, and a later crew-dark opens
    a new one."""
    if not isinstance(journal, list):
        return False
    open_dark = False
    for entry in journal:
        if not isinstance(entry, dict):
            continue
        if entry.get("machine") != machine:
            continue
        if entry.get("kind") == "crew-dark":
            open_dark = True
        elif entry.get("kind") == "watchman-recovered":
            open_dark = False
    return open_dark


def _escalated_this_episode(journal, machine):
    """True when an escalation record for this machine
    appears after its latest crew-dark record. An
    escalation from a closed episode does not count:
    a machine that dies again earns a new one."""
    if not isinstance(journal, list):
        return False
    last_dark = -1
    for index, entry in enumerate(journal):
        if not isinstance(entry, dict):
            continue
        if entry.get("machine") != machine:
            continue
        if entry.get("kind") == "crew-dark":
            last_dark = index
    if last_dark < 0:
        return False
    for entry in journal[last_dark + 1:]:
        if isinstance(entry, dict) and entry.get("kind") == "escalation":
            return True
    return False


def _escalation_for(machine, now):
    """The one blocked-push payload for an unrevivable
    watchman, or None when no valid payload builds.
    The question names the machine and the crew-dark
    fact; nothing here invents a reason the record
    does not carry. The payload is built, never sent."""
    question = ("The watchman on machine %s is dead and "
                "its restart failed; the machine's agents "
                "are asleep and its jobs are invisible to "
                "them. Dale's call is needed." % machine)
    parked = {"id": "watchman:%s" % machine,
              "title": "Watchman on machine %s" % machine,
              "status": "blocked", "note": question}
    payload = push_module.build_blocked_push(parked, question)
    if payload is None or not push_module.validate_push(payload):
        return None
    return {"kind": "escalation", "machine": machine,
            "reason": "watchman dead, restart failed",
            "question": question, "push": payload,
            "escalated_at": now,
            "dedupe_key": "watchdark-escalate:%s" % machine}


def watchman_watch_tick(snapshot, journal, now):
    """New journal records for this tick's machines.

    A dead machine with no open dark episode yields a
    crew-dark record and a restart record; when the
    fixture record says the restart cannot revive it
    (restart_ok not True), the same tick also yields
    the episode's one escalation record. A dead machine
    with an open episode yields nothing new. An alive
    machine with an open episode yields a recovered
    record. Unknown machines yield nothing. Inputs are
    never mutated; the return holds only new records,
    never a push send or an announcement."""
    journal = journal if isinstance(journal, list) else []
    records = []
    machines = _machines(snapshot)
    for name in sorted(machines):
        record = machines.get(name)
        state = machine_state(record, now)
        if state == UNKNOWN:
            continue
        if state == ALIVE:
            if _episode_open(journal + records, name):
                records.append(
                    {"kind": "watchman-recovered",
                     "machine": name, "state": ALIVE,
                     "recovered_at": now,
                     "dedupe_key": "watchrecovered:%s" % name})
            continue
        if _episode_open(journal + records, name):
            continue
        records.append({"kind": "crew-dark", "machine": name,
                        "state": DEAD,
                        "reason": "watchman dead: agents asleep, "
                                  "jobs invisible",
                        "created_at": now,
                        "dedupe_key": "watchdark:%s" % name})
        restart_ok = (isinstance(record, dict)
                      and record.get("restart_ok") is True)
        records.append({"kind": "watchman-restart",
                        "machine": name,
                        "restart_ok": restart_ok,
                        "attempted_at": now,
                        "dedupe_key": "watchrestart:%s" % name})
        if not restart_ok and not _escalated_this_episode(
                journal + records, name):
            escalation = _escalation_for(name, now)
            if escalation is not None:
                records.append(escalation)
    return records


def watchman_brief_lines(records):
    """One frozen line per watchman journal record for
    the next brief. Other records render nothing, so a
    mixed journal can never print a half line."""
    lines = []
    records = records if isinstance(records, list) else []
    for record in records:
        if not isinstance(record, dict):
            continue
        kind = record.get("kind")
        machine = record.get("machine")
        if kind == "crew-dark":
            lines.append("Crew-dark on machine %s: watchman dead, "
                         "agents asleep, jobs invisible."
                         % machine)
        elif kind == "watchman-restart":
            if record.get("restart_ok"):
                lines.append("Watchman restart attempted on machine "
                             "%s: restart succeeded." % machine)
            else:
                lines.append("Watchman restart attempted on machine "
                             "%s: restart failed." % machine)
        elif kind == "escalation":
            lines.append("Escalated machine %s: one blocked push "
                         "queued (watchman dead, restart failed)."
                         % machine)
        elif kind == "watchman-recovered":
            lines.append("Watchman recovered on machine %s."
                         % machine)
    return lines


def board_lines(states):
    """One line per board state record for the machine
    groups. A dead machine reads watchman-dead while
    the darkness lasts; an unknown machine reads
    unknown, never alive and never dead."""
    lines = []
    states = states if isinstance(states, list) else []
    for state in states:
        if not isinstance(state, dict):
            continue
        machine = state.get("machine")
        value = state.get("state")
        if value == DEAD:
            lines.append("Machine %s: watchman dead (crew-dark)."
                         % machine)
        elif value == ALIVE:
            lines.append("Machine %s: watchman alive." % machine)
        elif value == UNKNOWN:
            lines.append("Machine %s: watchman state unknown."
                         % machine)
    return lines
