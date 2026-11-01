#!/usr/bin/env python3
"""worlds/custos/runtime/scheduler.py: the Custos patrol scheduler (RW-007).

Patrols run on a per-source cadence, not all-or-nothing. The config
carries a "cadence" map from patrol source to interval:

    {
      "cadence": {"kev": "24h", "ct": "1h", "dns": "6h",
                  "subdomain": "6h", "hosts": "15m"},
      ... the rest of the patrol config ...
    }

Intervals are seconds ("90"), or a number plus a unit: s, m, h, d.
A source with no cadence entry runs every cycle (today's behaviour);
a config with no "cadence" key at all runs every source every
cycle, so the scheduler is a drop-in replacement for the patrol:
the standing service driver invokes it exactly the way it invoked
patrol.py (`run --config --records --state`), with the scheduler
state defaulting to a scheduler.json next to the patrol seen-state
file. An installation adopts it by pointing METAOS_CUSTOS_PATROL
at scheduler.py; the driver itself is untouched.

One scheduler invocation is one unattended cycle: it loads the
last-run times, works out which sources are due, runs the patrol
with only those sources (plus dependencies — the subdomain sweep
grades this cycle's CT entries, so a due subdomain pull ct in
with it), appends the patrol records plus one scheduler-cycle
record naming what ran, what was skipped, and when each source is
next due, and persists both states. A cycle where nothing is due
writes only the cycle record and calls no patrol at all: the
record still proves the timer fired and the scheduler decided.

The scheduler never invents a run: a cadence entry it cannot parse,
or a source name it does not know, is an error before anything
runs — no patrol, no state write, a nonzero exit. The patrol's own
rules are unchanged: a signal that fails inside a run is a summary
error, never data.

CLI:
    scheduler.py run --config hosts.json --records patrol.jsonl \
        [--state patrol-state.json] [--scheduler-state sched.json] \
        [--kev-file kev.json] [--ct-file ct.json] \
        [--dns-file dns.json]

Signal functions are injectable through run_cycle so the tests run
on recorded signal shapes with no network and a fake clock.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patrol  # noqa: E402

SOURCES = patrol.SCHEDULER_SOURCES

# A due source pulls these in with it: the subdomain sweep needs
# this cycle's CT entries, so it cannot run on a stale cycle alone.
DEPENDENCIES = {"subdomain": ("ct",)}

_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(value):
    """Seconds for a cadence value: int, digit string, or N + s/m/h/d.

    Raises ValueError on anything else, including zero and
    negative intervals: a cadence that never fires, or fires in
    the past, is a config error, not a schedule.
    """
    if isinstance(value, bool):
        raise ValueError("cadence interval must be a duration, not %r"
                         % (value,))
    if isinstance(value, int):
        seconds = value
    elif isinstance(value, str):
        text = value.strip().lower()
        if not text:
            raise ValueError("cadence interval must not be empty")
        unit = _DURATION_UNITS.get(text[-1])
        if unit is not None and text[:-1].isdigit():
            seconds = int(text[:-1]) * unit
        elif text.isdigit():
            seconds = int(text)
        else:
            raise ValueError("unparseable cadence interval: %r" % (value,))
    else:
        raise ValueError("unparseable cadence interval: %r" % (value,))
    if seconds <= 0:
        raise ValueError("cadence interval must be positive: %r" % (value,))
    return seconds


def validate_cadence(config):
    """{source: seconds} for the config's cadence map.

    Unknown source names and unparseable intervals raise
    ValueError. A source with no entry defaults to every cycle
    (interval 0 in the returned map is the marker for that: the
    due check treats 0 as always due). A config with no cadence
    key runs every source every cycle.
    """
    raw = config.get("cadence") or {}
    if not isinstance(raw, dict):
        raise ValueError("cadence must be a JSON object, not %r" % (raw,))
    unknown = sorted(set(raw) - set(SOURCES))
    if unknown:
        raise ValueError("unknown cadence source(s): %s" % ", ".join(unknown))
    cadence = {source: 0 for source in SOURCES}
    for source, value in raw.items():
        cadence[source] = parse_duration(value)
    return cadence


def parse_ts(text):
    """Aware datetime for an ISO timestamp, accepting the Z form."""
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def format_ts(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_scheduler_state(path):
    """{source: last-run ISO string} from a state file, or {}."""
    if path and os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    return {}


def save_scheduler_state(path, state):
    if path:
        with open(path, "w") as f:
            json.dump(state, f, indent=1, sort_keys=True)


def due_sources(now, last_run, cadence):
    """Sources whose interval has elapsed since their last run.

    A source never run is due. Interval 0 (no cadence entry) is
    always due. Exactly at the interval counts as due: a source
    scheduled every hour runs at the hour, not after it.
    """
    due = set()
    for source in SOURCES:
        interval = cadence.get(source, 0)
        last = last_run.get(source)
        if last is None or interval == 0:
            due.add(source)
            continue
        try:
            elapsed = (now - parse_ts(last)).total_seconds()
        except ValueError:
            # An unparseable last-run stamp is not a schedule: treat
            # the source as due and let this cycle repair the stamp.
            due.add(source)
            continue
        if elapsed >= interval:
            due.add(source)
    return due


def run_cycle(config, now, sched_state, patrol_state,
              fetch_kev_fn=None, probe_cert_fn=None, probe_port_fn=None,
              fetch_ct_fn=None, fetch_headers_fn=None,
              fetch_dns_fn=None, resolve_subdomain_fn=None):
    """One unattended scheduler cycle.

    config: the patrol config (cadence read from it).
    now: aware datetime for this cycle.
    sched_state: {source: last-run ISO} — updated in place for
        sources this cycle runs, and returned.
    patrol_state: {"seen_cve": set, "seen_ct": set,
        "seen_dns": dict} — the patrol seen-state, updated in
        place by the patrol run and returned.
    Signal fns default to the patrol's live ones; tests inject
    fakes. Returns (records, sched_state, patrol_state).

    Records are the patrol's records (when anything ran) followed
    by one scheduler-cycle record. When nothing is due, records
    hold only the cycle record and the patrol is never called.
    """
    cadence = validate_cadence(config)
    due = due_sources(now, sched_state, cadence)
    run = set(due)
    for source in list(run):
        run.update(DEPENDENCIES.get(source, ()))
    now_str = format_ts(now)
    skipped = [s for s in SOURCES if s not in run]
    if run:
        records, seen_cve, seen_ct = patrol.run_patrol(
            config, now_str,
            fetch_kev_fn or patrol.fetch_kev,
            probe_cert_fn or patrol.probe_cert,
            probe_port_fn or patrol.probe_port,
            patrol_state.get("seen_cve", set()),
            fetch_ct_fn, patrol_state.get("seen_ct", set()),
            fetch_headers_fn, fetch_dns_fn,
            patrol_state.get("seen_dns", {}),
            resolve_subdomain_fn, sources=run)
        patrol_state["seen_cve"] = seen_cve
        patrol_state["seen_ct"] = seen_ct
        summary = records[-1] if records else None
        for source in run:
            sched_state[source] = now_str
    else:
        # Nothing due: the patrol is never called, neither state
        # moves, and the cycle record below is the whole output.
        records, summary = [], None
    next_due = {}
    for source in SOURCES:
        interval = cadence.get(source, 0)
        if source in run:
            base = now
        elif source in sched_state:
            try:
                base = parse_ts(sched_state[source])
            except ValueError:
                continue
        else:
            continue
        next_due[source] = format_ts(base + timedelta(seconds=interval))
    cycle = {
        "record_type": "scheduler-cycle",
        "ts": now_str,
        "sources_due": [s for s in SOURCES if s in due],
        "sources_run": [s for s in SOURCES if s in run],
        "sources_skipped": skipped,
        "patrol_summary": summary,
        "next_due": next_due,
    }
    records.append(cycle)
    return records, sched_state, patrol_state


# ---------------------------------------------------------------------
# CLI.

def default_scheduler_state(state_path):
    """Scheduler-state path next to the patrol state file.

    The driver passes only --state, so the scheduler must not need
    a second path to be a drop-in: scheduler.json sits beside
    seen.json in the same state dir.
    """
    if not state_path:
        return None
    return os.path.join(os.path.dirname(os.path.abspath(state_path)),
                         "scheduler.json")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="scheduler.py")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run one scheduler cycle")
    run.add_argument("--config", required=True)
    run.add_argument("--records", help="JSONL file to append to "
                                       "(default: print to stdout)")
    run.add_argument("--state", help="patrol seen-state JSON file")
    run.add_argument("--scheduler-state", help="scheduler last-run "
                     "JSON file (default: scheduler.json next to "
                     "--state)")
    run.add_argument("--kev-file", help="read the KEV feed from a local "
                                        "file instead of fetching it")
    run.add_argument("--ct-file", help="read the CT entries from a local "
                                       "file instead of fetching them")
    run.add_argument("--dns-file", help="read DNS snapshots from a local "
                                        "JSON file {domain: snapshot} "
                                        "instead of resolving them")
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    # Cadence errors fail before any state is read or written and
    # before any patrol runs.
    try:
        validate_cadence(config)
    except ValueError as exc:
        print("scheduler: bad cadence: %s" % exc, file=sys.stderr)
        return 2

    sched_path = args.scheduler_state or default_scheduler_state(args.state)
    sched_state = load_scheduler_state(sched_path)
    seen_cve, seen_ct, seen_dns = patrol.load_state(args.state)

    if args.kev_file:
        with open(args.kev_file) as f:
            feed = json.load(f)
        fetch_fn = lambda _url: feed.get("vulnerabilities", [])
    else:
        fetch_fn = None

    if args.ct_file:
        with open(args.ct_file) as f:
            ct_feed = json.load(f)
        fetch_ct_fn = lambda _domain, _template: ct_feed
    else:
        fetch_ct_fn = None

    if args.dns_file:
        with open(args.dns_file) as f:
            dns_feed = json.load(f)

        def fetch_dns_fn(domain, _feed=dns_feed):
            if domain not in _feed:
                raise ValueError("no dns fixture for %s" % domain)
            return _feed[domain]
    else:
        fetch_dns_fn = None

    now = datetime.now(timezone.utc)
    patrol_state = {"seen_cve": seen_cve, "seen_ct": seen_ct,
                    "seen_dns": seen_dns}
    records, sched_state, patrol_state = run_cycle(
        config, now, sched_state, patrol_state,
        fetch_kev_fn=fetch_fn, fetch_ct_fn=fetch_ct_fn,
        fetch_dns_fn=fetch_dns_fn)
    patrol.save_state(args.state, patrol_state["seen_cve"],
                      patrol_state["seen_ct"], patrol_state["seen_dns"])
    save_scheduler_state(sched_path, sched_state)

    lines = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    if args.records:
        with open(args.records, "a") as f:
            f.write(lines)
    else:
        sys.stdout.write(lines)
    cycle = records[-1]
    print("scheduler cycle complete: ran %s, skipped %s"
          % (",".join(cycle["sources_run"]) or "nothing",
             ",".join(cycle["sources_skipped"]) or "nothing"),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
