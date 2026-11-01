#!/usr/bin/env python3
"""worlds/custos/runtime/false_positives.py: the Custos false-positive log.

RW-009. An operator who decides an alert is a false positive dismisses
it, and the dismissal lands in a review file with a reason. The next
patrol reads that file and stops re-raising the same finding.

"Same finding" is deliberately narrow, not a blanket category mute.
A dismissal matches one finding signature: (category, host, key),
where the key is the stable identifier of that finding:

  * KEV match: the CVE id
  * certificate-issued: the CT id
  * subdomain unexpected network: the unexpected addresses
  * dns drift: the added/removed diff, canonically serialized
  * security headers missing: the missing header list
  * anomalous exposure / service down / certificate state: the port

A dismissal for one host never silences the same category on another
host, and a dismissal for one CVE never silences another CVE. A
finding whose key cannot be derived is never dismissed: the patrol
would rather re-raise than guess what an entry meant.

The review file is JSONL, one dismissal per line:

    {"category": "service down", "host": "down.example",
     "key": "443", "reason": "host is decommissioned, port intentionally closed"}

A dismissal without a reason is not a dismissal: it is ignored and
reported as a review error, so a bare entry can never silently mute
an alert. A missing review file means no dismissals yet, not an
error. A malformed file is a patrol-summary error and suppresses
nothing: a corrupt review file must fail open (alerts still raised),
never fail into invented suppressions.

A suppressed finding is not silently dropped. It is written to the
patrol record as a "dismissed" record (not an observation, not
counted in the observation tallies, never escalated), carrying the
reason, so the audit trail shows both that the finding recurred and
that a human had already judged it.
"""

import json
import os


def _norm_host(host):
    if host is None:
        return None
    return str(host).strip().lower()


def dismissal_signature(category, host, key):
    """Canonical signature for one dismissal: (category, host, key)."""
    return (str(category), _norm_host(host), str(key))


def key_for_record(record):
    """Stable key for a patrol observation, or None if underivable.

    The key is taken from the record's detail, per source, so it
    survives across patrols for the same recurring finding and
    changes when the finding itself changes (a new CVE, a new
    unexpected address, a different missing-header set).
    """
    detail = record.get("detail") or {}
    source = record.get("source")
    if source == "kev":
        cve = detail.get("cve")
        return str(cve) if cve else None
    if source == "ct":
        ct_id = detail.get("ct_id")
        return str(ct_id) if ct_id is not None else None
    if source == "subdomain":
        unexpected = detail.get("unexpected_addresses") or []
        return ",".join(str(a) for a in unexpected) or None
    if source == "dns":
        return json.dumps({"added": detail.get("added", {}),
                           "removed": detail.get("removed", {})},
                          sort_keys=True)
    if source == "headers":
        missing = detail.get("missing") or []
        return ",".join(str(h) for h in missing) or None
    if source in ("exposure", "service", "cert"):
        port = detail.get("port")
        return str(port) if port is not None else None
    return json.dumps(detail, sort_keys=True) if detail else None


def build_dismissal_map(dismissals):
    """{signature: reason} for validated dismissal entries.

    Entries are assumed already validated by load_review; a later
    entry for the same signature does not overwrite the first
    reason, so the earliest human judgement is the one on record.
    """
    mapping = {}
    for entry in dismissals or []:
        sig = dismissal_signature(entry["category"], entry.get("host"),
                                  entry["key"])
        if sig not in mapping:
            mapping[sig] = entry["reason"]
    return mapping


def is_dismissed(record, dismissal_map):
    """(dismissed, reason) for one observation against the map."""
    key = key_for_record(record)
    if key is None:
        return False, None
    sig = dismissal_signature(record.get("category"), record.get("host"),
                              key)
    if sig in dismissal_map:
        return True, dismissal_map[sig]
    return False, None


def validate_entry(entry):
    """Error string for an invalid review entry, or None if valid."""
    if not isinstance(entry, dict):
        return "not an object"
    if not entry.get("category") or not isinstance(entry["category"], str):
        return "missing category"
    if not entry.get("key") or not isinstance(entry["key"], str):
        return "missing key"
    if not entry.get("reason") or not isinstance(entry["reason"], str):
        return "missing reason"
    host = entry.get("host")
    if host is not None and not isinstance(host, str):
        return "host must be a string or null"
    return None


def load_review(path):
    """(dismissals, errors) from a review file.

    Accepts a JSON list, a JSON object with a "dismissals" list, or
    JSONL (one dismissal per line). A missing file is ([], []).
    An unreadable or malformed file is ([], [error]): the patrol
    then suppresses nothing and reports the error in its summary.
    Invalid entries are skipped individually, each with an error,
    so one bad line never discards the whole review file.
    """
    if not path or not os.path.isfile(path):
        return [], []
    with open(path) as f:
        text = f.read()
    entries = []
    errors = []
    parsed = None
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = None
    if parsed is None:
        # JSONL fallback, one object per non-blank line.
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except ValueError as exc:
                errors.append("false-positive review line %d unreadable: %s"
                              % (lineno, exc))
        if errors and not entries:
            return [], errors
    elif isinstance(parsed, dict):
        # Either {"dismissals": [...]} or a single dismissal object;
        # a single object that fails validation is reported as an
        # ignored entry below, not as a whole-file error.
        if isinstance(parsed.get("dismissals"), list):
            entries = parsed["dismissals"]
        else:
            entries = [parsed]
    elif isinstance(parsed, list):
        entries = parsed
    else:
        return [], ["false-positive review is not a list, an object "
                    "with a dismissals list, or JSONL"]
    dismissals = []
    for entry in entries:
        problem = validate_entry(entry)
        if problem:
            errors.append("false-positive review entry ignored: %s"
                          % problem)
            continue
        dismissals.append({"category": entry["category"],
                           "host": entry.get("host"),
                           "key": entry["key"],
                           "reason": entry["reason"]})
    return dismissals, errors


def append_dismissal(path, category, host, key, reason):
    """Append one dismissal to the review file (JSONL)."""
    entry = {"category": category, "host": host, "key": key,
             "reason": reason}
    problem = validate_entry(entry)
    if problem:
        raise ValueError("invalid dismissal: %s" % problem)
    with open(path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def make_dismissed_record(now, record, reason):
    """Audit record for a finding suppressed by the review file."""
    return {
        "record_type": "dismissed",
        "ts": now,
        "source": record.get("source"),
        "host": record.get("host"),
        "category": record.get("category"),
        "tier": record.get("tier"),
        "key": key_for_record(record),
        "reason": reason,
    }
