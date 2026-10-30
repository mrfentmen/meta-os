#!/usr/bin/env python3
"""OS-118: relay-watchman, the resident bell for one Meta OS machine.

A small CLI program, not an agent. It watches the job queue for
work addressed to this machine's agents, watches those agents'
heartbeats once they are working, and rings the bell: it emits
wake events for sleeping agents with newly posted jobs, and nudge
events for workers whose heartbeat has gone stale on a claimed
job. That is the whole job of this program.

Source of truth, stated first because Dale already lives the
failure mode: job state only. tick() reads job records (id,
status, addressee, claim, lease) and agent heartbeat records.
It takes no bus message counter, reads no message list, and
counts no messages, so replaying bus messages, skipping them,
or corrupting a stored counter changes nothing: a job that
exists and is unclaimed is a fact, not a count. The acceptance
test for this is test_no_counter_input: tick has no counter
parameter at all, and varying a stray counter field carried on
a job record yields identical events.

What this program is not:

- It makes no model calls and holds no session of its own.
  Waking means emitting the wake event naming job + agent;
  starting the agent's session with the job as its brief is
  the OS-119 wake adapter's work, not this program's.
- It posts nothing to the bus and moves no claim. A wake event
  is a record printed by the caller-facing CLI, not an
  announcement.
- It does not restart processes and does not reassign jobs.
  Those mechanical rungs belong to systemd under the OS-034
  contract (restart) and to the overseer via the OS-125 baton
  pass (reassign); this first light covers the two behaviors
  the OS-118 acceptance pins (wake within one poll cycle,
  nudge on the same watch cycle) and records the other two
  rungs as owed follow-up, not as silently present behavior.
- It does not invent addressees. A job rings only when its
  addressed_to (or legacy to) field names a local agent nick.
  An unaddressed open job is not this machine's to wake:
  ringing for it on every machine would wake the whole crew
  for one job. Unaddressed jobs wait for a claim, or for the
  OS-121 timer sweep.

Inputs (pure functions; the CLI loads them from JSON files):

- jobs: a list of job dicts. Fields read: id (required),
  status, addressed_to / to, claim, title (for the event
  record only, never invented when absent).
- agents: a mapping nick -> agent dict, or a list of agent
  dicts with a nick field. Fields read: nick, heartbeat_at
  (unix seconds, or None when never seen), registered
  (default True; an unregistered nick is not local).
- rung_ledger: a set of rung keys the caller owns. tick()
  never mutates its inputs; it returns (events, new_keys)
  and the caller owns merging new_keys into the ledger.
  Wake dedupes per job id: a job rings once. Nudge dedupes
  per (job id, heartbeat value that went stale): the same
  stale heartbeat never re-nudges, but a worker that comes
  back and stalls again on the same job earns a fresh nudge.

Statuses that never ring: anything but open (wake) and
claimed (nudge). Done, cancelled, blocked, and failed-final
jobs are silent, as are malformed records (not a dict, no
id) and jobs addressed to agents this machine does not know.

CLI: --once reads one jobs file and one agents file, prints
one JSON event per line, and updates the state file with the
new rung keys. --loop repeats that read every --interval
seconds, re-reading the files each cycle, until interrupted
(or --max-cycles for tests and debugging). A missing input
file reads as an empty snapshot with a stderr note, never a
crash: no snapshot yet means nothing to wake. A malformed
JSON file exits 2 under --once and is skipped (with a
stderr note) for that cycle under --loop. Exit codes: 0 ok,
2 bad input or usage.
"""

import argparse
import json
import os
import sys
import time

DEFAULT_INTERVAL_SECONDS = 10
DEFAULT_HEARTBEAT_STALE_SECONDS = 300

WAKE = "wake"
NUDGE = "nudge"

_RING_STATUSES = ("open",)
_NUDGE_STATUSES = ("claimed",)
_SILENT_STATUSES = ("done", "cancelled", "blocked", "failed-final",
                    "failed", "open-cancelled")

__all__ = [
    "addressed_to",
    "tick",
    "normalize_agents",
    "is_sleeping",
    "DEFAULT_INTERVAL_SECONDS",
    "DEFAULT_HEARTBEAT_STALE_SECONDS",
]


def _text(value):
    """A stripped string, or None for anything else."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _num(value):
    """An int/float timestamp, else None. Bools are not times."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def addressed_to(job):
    """Who a job is addressed to, from addressed_to, then to.

    Mirrors intel/wake.py's rule so the watchman and the wake
    adapter agree on addressing. Missing or empty fields mean
    unaddressed, never a guess.
    """
    if not isinstance(job, dict):
        return None
    for field in ("addressed_to", "to"):
        found = _text(job.get(field))
        if found is not None:
            return found
    return None


def normalize_agents(agents):
    """Agents input -> {nick: record}. Accepts a dict or a list.

    Unregistered agents (registered False) are dropped: they
    are not this machine's to wake. Records without a nick are
    dropped. Input is never mutated.
    """
    out = {}
    if isinstance(agents, dict):
        items = [(nick, rec) for nick, rec in agents.items()]
    elif isinstance(agents, list):
        items = []
        for rec in agents:
            if isinstance(rec, dict):
                items.append((rec.get("nick"), rec))
    else:
        return out
    for nick, rec in items:
        nick = _text(nick)
        if nick is None or not isinstance(rec, dict):
            continue
        record = dict(rec)
        record["nick"] = nick
        if record.get("registered", True) is False:
            continue
        out[nick] = record
    return out


def is_sleeping(agent, now, stale_seconds):
    """True when an agent has no heartbeat or a stale one."""
    heartbeat = _num(agent.get("heartbeat_at"))
    if heartbeat is None:
        return True
    return (now - heartbeat) > stale_seconds


def _wake_key(job_id):
    return "wake:%s" % job_id


def _nudge_key(job_id, heartbeat):
    return "nudge:%s:%s" % (job_id, heartbeat)


def tick(jobs, agents, rung_ledger, now,
         heartbeat_stale_seconds=DEFAULT_HEARTBEAT_STALE_SECONDS):
    """One watch cycle. Returns (events, new_rung_keys).

    Pure: no I/O, no counter input, no mutation of jobs,
    agents, or the ledger. Events are dicts with kind,
    job_id, agent, title (or None), ts, and, for nudges,
    heartbeat_age_seconds. The caller merges new_rung_keys
    into its ledger; a second tick over the same state with
    the merged ledger yields no repeat events.
    """
    local = normalize_agents(agents)
    ledger = set(rung_ledger or ())
    events = []
    new_keys = []
    if not isinstance(jobs, list):
        return events, new_keys
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_id = _text(job.get("id"))
        if job_id is None:
            continue
        status = _text(job.get("status"))
        if status in _RING_STATUSES:
            nick = addressed_to(job)
            if nick is None or nick not in local:
                continue
            if not is_sleeping(local[nick], now, heartbeat_stale_seconds):
                continue
            key = _wake_key(job_id)
            if key in ledger:
                continue
            events.append({
                "kind": WAKE,
                "job_id": job_id,
                "agent": nick,
                "title": _text(job.get("title")),
                "ts": now,
            })
            new_keys.append(key)
        elif status in _NUDGE_STATUSES:
            claimer = _text(job.get("claim"))
            if claimer is None or claimer not in local:
                continue
            heartbeat = _num(local[claimer].get("heartbeat_at"))
            if heartbeat is None:
                continue
            age = now - heartbeat
            if age <= heartbeat_stale_seconds:
                continue
            key = _nudge_key(job_id, heartbeat)
            if key in ledger:
                continue
            events.append({
                "kind": NUDGE,
                "job_id": job_id,
                "agent": claimer,
                "heartbeat_age_seconds": age,
                "title": _text(job.get("title")),
                "ts": now,
            })
            new_keys.append(key)
        else:
            # Silent statuses and unknown statuses never ring.
            continue
    return events, new_keys


def _load_json_file(path, what):
    """Load a JSON file. Missing file -> (None, note); bad JSON
    -> raises ValueError with a message naming the file."""
    if not os.path.exists(path):
        sys.stderr.write("watchman: %s file missing, "
                         "reading as empty: %s\n" % (what, path))
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, OSError) as exc:
        raise ValueError("watchman: cannot read %s file %s: %s"
                         % (what, path, exc))


def _run_once(jobs_path, agents_path, state_path, now,
              stale_seconds):
    """One cycle from files. Returns (events, wrote_state).

    Raises ValueError on malformed input files.
    """
    jobs = _load_json_file(jobs_path, "jobs")
    agents = _load_json_file(agents_path, "agents")
    if jobs is None:
        jobs = []
    if agents is None:
        agents = {}
    ledger = set()
    if state_path and os.path.exists(state_path):
        state = _load_json_file(state_path, "state")
        if isinstance(state, dict):
            raw = state.get("rung", [])
            if isinstance(raw, list):
                ledger = {k for k in raw if isinstance(k, str)}
    events, new_keys = tick(jobs, agents, ledger, now,
                            heartbeat_stale_seconds=stale_seconds)
    if state_path and new_keys:
        merged = sorted(ledger | set(new_keys))
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"rung": merged}, handle)
        os.replace(tmp, state_path)
    return events


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="relay_watchman.py",
        description="OS-118: watch the job queue and ring the "
                    "bell for sleeping agents (wake) and stale "
                    "workers (nudge). No model calls, no bus posts.")
    parser.add_argument("--jobs-file", required=True,
                        help="JSON file holding a list of job records")
    parser.add_argument("--agents-file", required=True,
                        help="JSON file holding agent heartbeat records")
    parser.add_argument("--state-file", default="",
                        help="JSON file holding the rung ledger "
                             "(created/updated when events fire)")
    parser.add_argument("--interval", type=int,
                        default=DEFAULT_INTERVAL_SECONDS,
                        help="seconds between loop cycles (default 10)")
    parser.add_argument("--heartbeat-stale-seconds", type=int,
                        default=DEFAULT_HEARTBEAT_STALE_SECONDS,
                        help="heartbeat age that counts as stale "
                             "(default 300)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true",
                      help="run exactly one watch cycle")
    mode.add_argument("--loop", action="store_true",
                      help="repeat cycles until interrupted")
    parser.add_argument("--max-cycles", type=int, default=0,
                        help="loop only: stop after this many cycles "
                             "(0 means run until interrupted)")
    parser.add_argument("--now", type=int, default=0,
                        help="loop/once only: fake clock for tests "
                             "(0 means real time)")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.interval <= 0 or args.heartbeat_stale_seconds < 0:
        sys.stderr.write("watchman: --interval must be positive "
                         "and --heartbeat-stale-seconds non-negative\n")
        return 2

    def now():
        if args.now:
            return args.now
        return int(time.time())

    def cycle():
        try:
            return _run_once(args.jobs_file, args.agents_file,
                             args.state_file or None, now(),
                             args.heartbeat_stale_seconds)
        except ValueError as exc:
            if args.loop:
                sys.stderr.write("%s\n" % exc)
                return []
            sys.stderr.write("%s\n" % exc)
            raise

    if args.once:
        try:
            events = cycle()
        except ValueError:
            return 2
        for event in events:
            print(json.dumps(event, sort_keys=True))
        return 0

    cycles = 0
    try:
        while True:
            try:
                events = cycle()
            except ValueError:
                events = []
            for event in events:
                print(json.dumps(event, sort_keys=True), flush=True)
            cycles += 1
            if args.max_cycles and cycles >= args.max_cycles:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
