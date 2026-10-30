#!/usr/bin/env python3
"""FDNY pack runtime first light: the PAR clock (2026-10-28).

Personnel Accountability Report, made into a machine. A fire
department tracks which crews are inside a burning structure and
checks each one on a clock (a PAR check). Today that clock is a
human accountability officer's head, and the failure mode is
distraction: a PAR check slips silently while everything else is
happening. This program is the clock that never gets distracted.
That is the whole job.

It is an accountability aid, not a commander. The division of
labor is fixed and written here so nobody has to trust vibes:

    The human accountability officer tells the clock who went
    inside and when (enter), marks a completed PAR check when the
    crew answers on the radio (complete), and ends an interior
    period (exit). The clock counts each crew's interval
    individually, raises par-check-due when a check falls due,
    escalates to crew-unaccounted when the grace window passes
    with no completed check, and keeps the timeline of all of it,
    sealed in the state file at the end of the incident.

    The clock never orders crews, never dispatches anything,
    never guesses where a crew is, never marks a PAR complete on
    its own, and never invents a location. It has no radio and no
    sensors: it knows only what a human entered. Its alerts are
    advisory and fail loud; the accountability officer acts on
    them.

Alert lines follow the FND-020 freeze in intel/README.md, one
line per critical alert: ALERT:<id> <severity> <kind>, with the
id carrying no spaces and no explanation text on the line. The
explanation and the suggested fix live on the event record,
never on the line, exactly like the federal watchdog's alerts.
The two kinds this program raises are the pack's own declared
kinds from worlds/fdny/pack.json: par-check-due (warning,
urgent) and crew-unaccounted (critical, life-safety).

State lives on disk, never in a session: the state file holds
the roster, the timeline, and the dedupe ledger, so a reboot is
a shift change for the clock too. Purity contract, same as the
OS-118 watchman: tick() and the state functions never mutate
their inputs, take no counter, hold no session, and make no
model calls. The CLI is the only I/O.

CLI:

    python3 par_clock.py --file STATE.json enter --crew crew-2 \
        --entered-at 1761500000 --location "division 2 stairwell"
    python3 par_clock.py --file STATE.json complete --crew crew-2
    python3 par_clock.py --file STATE.json exit --crew crew-2
    python3 par_clock.py --file STATE.json tick --loop
    python3 par_clock.py --file STATE.json show

tick prints one JSON event record per line and, for critical
events, the frozen ALERT line on its own line. Exit codes:
0 ok, 2 bad usage or bad input.
"""

import argparse
import json
import os
import sys
import time

DEFAULT_INTERVAL_SECONDS = 600
DEFAULT_GRACE_SECONDS = 120

KIND_PAR_CHECK_DUE = "par-check-due"
KIND_CREW_UNACCOUNTED = "crew-unaccounted"

SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

TL_ENTER = "par-enter"
TL_COMPLETE = "par-complete"
TL_EXIT = "par-exit"

__all__ = [
    "new_state",
    "enter_crew",
    "exit_crew",
    "complete_par",
    "tick",
    "render_alert",
    "validated_crew_id",
    "DEFAULT_INTERVAL_SECONDS",
    "DEFAULT_GRACE_SECONDS",
]


def validated_crew_id(crew_id):
    """A crew id must be a non-empty string with no whitespace."""
    if not isinstance(crew_id, str):
        return None, "crew id must be a string"
    crew_id = crew_id.strip()
    if not crew_id:
        return None, "crew id may not be empty"
    if any(ch.isspace() for ch in crew_id):
        return None, "crew id may not contain whitespace"
    return crew_id, None


def new_state():
    """A fresh PAR clock state document."""
    return {"roster": {}, "ledger": [], "timeline": []}


def _copy_state(state):
    """A deep-enough copy so no input is ever mutated."""
    if not isinstance(state, dict):
        return new_state()
    out = {
        "roster": {},
        "ledger": list(state.get("ledger") or []),
        "timeline": list(state.get("timeline") or []),
    }
    for crew_id, record in (state.get("roster") or {}).items():
        out["roster"][crew_id] = dict(record)
    return out


def _inside_record(state, crew_id):
    roster = state.get("roster") or {}
    return roster.get(crew_id)


def enter_crew(state, crew_id, entered_at, location=None):
    """Mark a crew inside the structure. Returns (new_state, error).

    entered_at is unix seconds. A crew already inside is refused,
    never silently re-entered, so the interval can never be
    restarted by accident. The roster entry keeps an optional
    last known location, supplied by the human, never invented.
    """
    crew_id, err = validated_crew_id(crew_id)
    if err:
        return None, err
    if not isinstance(entered_at, int) or isinstance(entered_at, bool):
        return None, "entered-at must be unix seconds (an integer)"
    out = _copy_state(state)
    if crew_id in out["roster"]:
        return None, "crew %s is already inside" % crew_id
    record = {"crew_id": crew_id, "entered_at": entered_at,
              "last_par_at": None, "location": None}
    if isinstance(location, str):
        location = location.strip()
        if location:
            record["location"] = location
    out["roster"][crew_id] = record
    out["timeline"].append({
        "kind": TL_ENTER, "crew": crew_id, "ts": entered_at,
        "location": record["location"],
    })
    return out, None


def complete_par(state, crew_id, now):
    """Mark a completed PAR check. Returns (new_state, error).

    Only a human confirms a PAR: the clock never completes one
    itself, so an unanswered radio is never mistaken for an
    answer.
    """
    crew_id, err = validated_crew_id(crew_id)
    if err:
        return None, err
    if not isinstance(now, int) or isinstance(now, bool):
        return None, "completion time must be unix seconds"
    out = _copy_state(state)
    record = _inside_record(out, crew_id)
    if record is None:
        return None, "crew %s is not inside" % crew_id
    record["last_par_at"] = now
    out["timeline"].append({
        "kind": TL_COMPLETE, "crew": crew_id, "ts": now,
    })
    return out, None


def exit_crew(state, crew_id, now):
    """End an interior period. Returns (new_state, error).

    The crew leaves the roster and its dedupe keys are dropped,
    so a later re-entry starts a clean cycle. The timeline keeps
    the whole interior period; nothing is erased.
    """
    crew_id, err = validated_crew_id(crew_id)
    if err:
        return None, err
    if not isinstance(now, int) or isinstance(now, bool):
        return None, "exit time must be unix seconds"
    out = _copy_state(state)
    record = _inside_record(out, crew_id)
    if record is None:
        return None, "crew %s is not inside" % crew_id
    out["timeline"].append({
        "kind": TL_EXIT, "crew": crew_id, "ts": now,
    })
    del out["roster"][crew_id]
    prefix = "par:%s:" % crew_id
    out["ledger"] = [k for k in out["ledger"]
                     if not k.startswith(prefix)]
    return out, None


def _event(kind, severity, urgency, crew_id, due_at, now, record):
    """Build one alert event record. The line never carries the
    explanation; the record always does."""
    if kind == KIND_PAR_CHECK_DUE:
        alert_id = "par-due-%s-%d" % (crew_id, due_at)
        explanation = ("PAR check for crew %s is due now "
                       "(due %d seconds ago) and has not completed."
                       % (crew_id, now - due_at))
        fix = ("Have the accountability officer complete the PAR "
               "check with the crew, then run complete --crew %s."
               % crew_id)
    else:
        alert_id = "par-unaccounted-%s-%d" % (crew_id, due_at)
        minutes = (now - due_at) // 60
        explanation = ("No completed PAR for crew %s and the grace "
                       "window has passed (%d minutes overdue). "
                       "Treat as a mayday-standard check failure."
                       % (crew_id, minutes))
        fix = ("Escalate to the incident commander now. Do not let "
               "this clock clear itself; only a confirmed PAR "
               "check or an exit clears it.")
    event = {
        "kind": kind,
        "severity": severity,
        "urgency": urgency,
        "alert_id": alert_id,
        "crew": crew_id,
        "due_at": due_at,
        "entered_at": record.get("entered_at"),
        "ts": now,
        "explanation": explanation,
        "suggested_fix": fix,
    }
    location = record.get("location")
    if location:
        event["location"] = location
    return event


def tick(state, now, interval_seconds=DEFAULT_INTERVAL_SECONDS,
         grace_seconds=DEFAULT_GRACE_SECONDS):
    """One clock cycle. Returns (events, new_state).

    Pure: no I/O, no counter input, no mutation of the input
    state. Each inside crew counts from its own last completed
    PAR (or entry, when none is complete yet). Due raises
    par-check-due once per cycle-due moment; past the grace
    window, crew-unaccounted raises once per cycle-due moment on
    the same schedule key. Events dedupe on ledger keys the
    state carries, so a second tick over an unchanged inside
    state stays silent.
    """
    events = []
    out = _copy_state(state)
    ledger = set(out["ledger"])
    for crew_id, record in out["roster"].items():
        base = record.get("last_par_at")
        if base is None:
            base = record.get("entered_at")
        if not isinstance(base, int) or isinstance(base, bool):
            continue
        due_at = base + interval_seconds
        if now < due_at:
            continue
        prefix = "par:%s:" % crew_id
        key_due = "%sdue:%d" % (prefix, due_at)
        if key_due not in ledger:
            events.append(_event(KIND_PAR_CHECK_DUE, SEVERITY_WARNING,
                                 "urgent", crew_id, due_at, now, record))
            ledger.add(key_due)
        if now >= due_at + grace_seconds:
            key_over = "%sover:%d" % (prefix, due_at)
            if key_over not in ledger:
                events.append(_event(KIND_CREW_UNACCOUNTED,
                                     SEVERITY_CRITICAL, "life-safety",
                                     crew_id, due_at, now, record))
                ledger.add(key_over)
    out["ledger"] = sorted(ledger)
    return events, out


def render_alert(event):
    """The frozen FND-020 line for one event, exactly one line.

    ALERT:<id> <severity> <kind>, no explanation text on the
    line; readers split on spaces, not colons. Used only for
    critical events by the CLI; warnings accumulate silently on
    the record, same rule as the federal watchdog.
    """
    return "ALERT:%s %s %s" % (event["alert_id"],
                               event["severity"], event["kind"])


def _load_state(path):
    if not os.path.exists(path):
        return new_state(), None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError) as exc:
        return None, "cannot read state file %s: %s" % (path, exc)
    if not isinstance(data, dict):
        return None, "state file %s is not a JSON object" % path
    return _copy_state(data), None


def _save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="par_clock.py",
        description="FDNY PAR clock: the fire-ground accountability "
                    "timer that never gets distracted. Advisory "
                    "only; the human officer acts. No model calls, "
                    "no bus posts, no sensors.")
    parser.add_argument("--file", required=True,
                        help="JSON state file (created on first use)")
    parser.add_argument("command",
                        choices=("enter", "exit", "complete",
                                 "tick", "show"),
                        help="enter/exit mark interior periods, "
                             "complete marks a confirmed PAR, tick "
                             "runs one clock cycle, show prints state")
    parser.add_argument("--crew", default="",
                        help="crew id for enter/exit/complete")
    parser.add_argument("--entered-at", type=int, default=0,
                        help="unix seconds the crew went inside (enter)")
    parser.add_argument("--location", default="",
                        help="optional last known location (enter)")
    parser.add_argument("--interval-seconds", type=int,
                        default=DEFAULT_INTERVAL_SECONDS,
                        help="PAR interval per crew (default 600)")
    parser.add_argument("--grace-seconds", type=int,
                        default=DEFAULT_GRACE_SECONDS,
                        help="grace window before crew-unaccounted "
                             "(default 120)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cycle", action="store_true",
                      help="tick exactly once (the default)")
    mode.add_argument("--loop", action="store_true",
                      help="tick every --interval-seconds/10 seconds "
                           "until interrupted")
    parser.add_argument("--max-cycles", type=int, default=0,
                        help="loop only: stop after this many cycles")
    parser.add_argument("--now", type=int, default=0,
                        help="fake clock for tests (0 means real time)")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.interval_seconds <= 0 or args.grace_seconds < 0:
        sys.stderr.write("par_clock: interval must be positive and "
                         "grace non-negative\n")
        return 2

    state, err = _load_state(args.file)
    if err:
        sys.stderr.write("par_clock: %s\n" % err)
        return 2

    def now():
        if args.now:
            return args.now
        return int(time.time())

    def fail(message):
        sys.stderr.write("par_clock: %s\n" % message)
        return 2

    if args.command in ("enter", "exit", "complete"):
        if not args.crew:
            return fail("--crew is required for %s" % args.command)
        if args.command == "enter":
            if args.entered_at <= 0:
                return fail("--entered-at is required for enter")
            new, err = enter_crew(state, args.crew, args.entered_at,
                                  location=args.location or None)
        elif args.command == "exit":
            new, err = exit_crew(state, args.crew, now())
        else:
            new, err = complete_par(state, args.crew, now())
        if err:
            return fail(err)
        _save_state(args.file, new)
        return 0

    if args.command == "show":
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0

    if not args.loop:
        events, new = tick(state, now(),
                           interval_seconds=args.interval_seconds,
                           grace_seconds=args.grace_seconds)
        for event in events:
            print(json.dumps(event, sort_keys=True))
            if event["severity"] == SEVERITY_CRITICAL:
                print(render_alert(event), flush=True)
        _save_state(args.file, new)
        return 0

    cycles = 0
    sleep_seconds = max(1, args.interval_seconds // 10)
    try:
        while True:
            current, err = _load_state(args.file)
            if err:
                sys.stderr.write("par_clock: %s\n" % err)
                current = new_state()
            events, new = tick(current, now(),
                               interval_seconds=args.interval_seconds,
                               grace_seconds=args.grace_seconds)
            for event in events:
                print(json.dumps(event, sort_keys=True), flush=True)
                if event["severity"] == SEVERITY_CRITICAL:
                    print(render_alert(event), flush=True)
            _save_state(args.file, new)
            cycles += 1
            if args.max_cycles and cycles >= args.max_cycles:
                return 0
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
