#!/usr/bin/env python3
"""Stage 2d workshop memory for META OFFICINA.

The workshop record: packs plus outcomes, appended as one JSON line
per entry, that the next brief can read. Append-only, like the lab
ledger — there is deliberately no delete, clear, or rewrite API, so
the oldest entries can never be silently dropped. Readers see the
whole history (or its tail plus a count); writers only append.

Record file format (one JSON object per line, UTF-8):
  {"seq": <int, starts at 1>, "timestamp_utc": <ISO-8601>,
   "entry": {<caller-supplied dict>}}
A corrupt line is reported by read_all with its line number rather
than silently skipped.

Stdlib only. No model calls, no network. Entry payloads are plain
JSON; a corrupt line is reported by read_all with its line number
rather than silently skipped.
"""

import json
import os
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def append_entry(store_path, entry):
    """Append one entry dict to the store. Returns the stored record
    (entry plus seq + timestamp). Creates parent dirs as needed. The
    file is opened append-only; nothing here rewrites history."""
    parent = os.path.dirname(os.path.abspath(store_path))
    os.makedirs(parent, exist_ok=True)
    seq = len(read_all(store_path)) + 1
    stored = {
        "seq": seq,
        "timestamp_utc": _utcnow(),
        "entry": dict(entry),
    }
    with open(store_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(stored, sort_keys=True) + "\n")
    return stored


def read_all(store_path):
    """Read every entry, oldest first. A missing store reads as []."""
    if not os.path.isfile(store_path):
        return []
    out = []
    with open(store_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    "workshop memory line %d is corrupt: %s"
                    % (lineno, e)
                )
    return out


def recall_for_brief(store_path, limit=5):
    """What the next brief can read: the tail of the history plus the
    totals, so the reader knows how much came before. The oldest
    entries are never dropped from the store — only the window shown
    here is bounded, and its bound is reported."""
    entries = read_all(store_path)
    return {
        "total_entries": len(entries),
        "oldest_seq": entries[0]["seq"] if entries else None,
        "window": entries[-limit:] if limit else entries,
        "window_limit": limit,
        "note": "append-only: seq starts at 1 and nothing is ever "
        "removed; absence of an early seq in the window means it "
        "scrolled out of view, not out of the store",
    }


def record_outcome(rough_words, run_record, pack_check):
    """Build the entry dict for one finished brief: words in, pack
    out, outcome honest (proven or unproven, with numbers)."""
    grade = (run_record.get("final_grade") or {})
    verification = run_record.get("verification") or {}
    return {
        "kind": "brief-outcome",
        "rough_words": rough_words,
        "artefact_class": run_record["brief"]["artefact_class"],
        "final_params": run_record.get("final_params"),
        "proven": bool(run_record.get("proven")),
        "status": run_record.get("status"),
        "final_r_th_c_per_w": grade.get("r_th_c_per_w"),
        "heldout_r_th_c_per_w": verification.get(
            "heldout_r_th_c_per_w"),
        "pack_check_ok": bool(pack_check.get("ok")),
        "pack_violations": list(pack_check.get("violations", [])),
    }
