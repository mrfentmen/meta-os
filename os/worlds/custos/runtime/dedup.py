#!/usr/bin/env python3
"""worlds/custos/runtime/dedup.py: alert dedup for the Custos patrol (RW-008).

Identical alert findings inside a configured window collapse into one
record with a count. "Identical" means the same source, host, category,
and detail, byte for byte once the detail is canonicalised (sorted
keys): a finding whose detail changes — a certificate with one fewer
day left, a DNS diff with a new address — is a new finding, not a
repeat, and is never folded into the old one.

Scope, by design:

  * Only alert findings are deduped (tier yellow or red). Baseline
    normal records always pass through: per-host liveness history is
    built from those records, and collapsing them would punch holes
    in it.
  * The window is opt-in. The patrol only dedupes when the config
    sets `dedup_window_seconds` AND the caller supplies a dedup state
    dict (the CLI loads it from the patrol state file). With either
    missing, behaviour is exactly the pre-RW-008 behaviour: every
    patrol re-records what it finds.
  * The dedup state is a plain dict, updated in place like the DNS
    baseline map: key -> {"first_ts", "last_ts", "count"}. The first
    patrol in a window emits the one record; later patrols inside
    the window emit nothing for that finding, increment the count,
    and report the suppression in their patrol summary
    (`dedup_suppressed`, `dedup_counts`). After the window passes,
    the next occurrence emits a fresh record and the count resets.
  * Duplicates inside a single patrol's observation list collapse
    the same way, except the kept record carries the fold in its
    detail as "occurrences" (2 or more). A record emitted on its
    first sighting carries no occurrences field: existing record
    shapes are untouched unless a fold actually happened.
  * Suppression never invents, fixes, or escalates anything. A
    suppressed red finding produced no new escalation record because
    the first occurrence already ran the escalation chain; the
    summary still shows the finding is repeating, with its count.

Timestamps are the patrol's ISO UTC strings
("2026-11-01T05:00:00Z"). An unparseable first_ts is treated as
expired: the finding emits again rather than being suppressed on a
timestamp nobody can read.
"""

import json
from datetime import datetime, timezone


def _canonical_detail(detail):
    """Detail as a canonical string: sorted keys, compact separators."""
    try:
        return json.dumps(detail, sort_keys=True, separators=(",", ":"),
                          default=str)
    except (TypeError, ValueError):
        return json.dumps(str(detail), sort_keys=True)


def finding_key(record):
    """The identity of a finding, as a JSON string for state files.

    A list [source, host, category, canonical-detail] so the key is
    readable in the state file and unambiguous across findings.
    """
    return json.dumps([record.get("source"), record.get("host"),
                       record.get("category"),
                       _canonical_detail(record.get("detail", {}))],
                      sort_keys=True)


def parse_ts(text):
    """UTC datetime for a patrol timestamp string, or None."""
    try:
        return datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def apply_dedup(records, dedup_state, now, window_seconds):
    """Collapse identical alert findings in `records`.

    Returns (kept, collapsed, suppressed, suppressed_counts).

      kept: the observation list with folds and suppressions applied,
        in original order. Non-observation records pass through
        untouched (the patrol calls this before escalations exist,
        but the function does not assume that).
      collapsed: duplicates folded into a kept record of the same
        patrol (the kept record's detail gains "occurrences").
      suppressed: observations swallowed by an open window from an
        earlier patrol.
      suppressed_counts: state key -> running count for each finding
        suppressed this patrol (the count after this patrol's
        increment, so the summary shows the fold size, not just 1).

    `dedup_state` is updated in place. A window of None disables
    dedup entirely (records returned unchanged); a negative window
    is treated the same way, never as a crash.
    """
    if window_seconds is None:
        return list(records), 0, 0, {}
    try:
        window = float(window_seconds)
    except (TypeError, ValueError):
        return list(records), 0, 0, {}
    if window < 0:
        return list(records), 0, 0, {}

    now_dt = parse_ts(now)
    kept = []
    emitted = {}  # key -> kept record, this patrol only
    collapsed = 0
    suppressed = 0
    suppressed_counts = {}
    for record in records:
        if record.get("record_type") != "observation":
            kept.append(record)
            continue
        if record.get("tier") == "none":
            # Baseline normal is history, not an alert: never folded.
            kept.append(record)
            continue
        key = finding_key(record)
        if key in emitted:
            kept_record = emitted[key]
            detail = kept_record.setdefault("detail", {})
            detail["occurrences"] = int(detail.get("occurrences", 1)) + 1
            collapsed += 1
            continue
        entry = dedup_state.get(key)
        first_dt = parse_ts(entry.get("first_ts")) if entry else None
        if entry is not None and first_dt is not None and now_dt is not None \
                and (now_dt - first_dt).total_seconds() <= window:
            entry["count"] = int(entry.get("count", 1)) + 1
            entry["last_ts"] = now
            suppressed += 1
            suppressed_counts[key] = entry["count"]
            continue
        # First sighting, or the window has passed: emit, reset count.
        dedup_state[key] = {"first_ts": now, "last_ts": now, "count": 1}
        emitted[key] = record
        kept.append(record)
    return kept, collapsed, suppressed, suppressed_counts
