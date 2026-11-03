"""General lab ledger: append-only JSONL experiment log with hash chain.

This is the LAB ledger, not the Hortus breeding log (see hortus/records.py,
which stays the source of truth for breeding runs and is NOT touched here).
Every discovery-cycle transition files exactly one entry here (see cycle.py).

Schema field map against schemas/experiment.schema.json (source of truth):
  Task-5 record field  -> schema field
  question             -> research_question
  method               -> software + model + parameters (jointly)
  data hash            -> input_hash
  result (hash)        -> output_hash
  seed                 -> random_seed
  result evidence      -> evidence_level
  verification         -> verification_status
  logs                 -> execution_logs
  hypothesis link      -> hypothesis_id + hypothesis_version
  provenance           -> data_source + original_data

UNIMPLEMENTED gaps (schema is source of truth; DO NOT extend it here):
  - Task-5 "code hash": UNIMPLEMENTED. Schema has software/model/parameters
    but no standalone code_hash field. Record software versions instead.
  - Task-5 "environment": UNIMPLEMENTED. No environment field in schema;
    note runtime in execution_logs as free text only.
  - Task-5 "agent": UNIMPLEMENTED. Schema has no filed_by/agent field;
    attribute via the ledger entry's `agent` key (ledger-level, not schema).
  - Task-5 "timestamps": UNIMPLEMENTED in schema. Ledger adds `recorded_at`
    (ISO-8601 UTC) at the ledger layer; schema itself carries no timestamp.
  - Levels 4-6: UNIMPLEMENTED by design. Schema caps automated records at
    level 3; wet-lab/publication levels are human-gated (see cycle.py).

Chain rule: entry_hash = sha256(canonical_json(body) + prev_hash) where
body is the entry without entry_hash, canonical_json uses sort_keys and
compact separators. First entry uses prev_hash "GENESIS".
"""

import hashlib
import json
import os
from datetime import datetime, timezone

GENESIS_HASH = "GENESIS"


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_all(path):
    """Read all ledger entries from a JSONL file. Missing file -> []."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def validate_entry(record, require_timestamp=True):
    """Validate one ledger entry before it is written.

    Every entry must be a dict; with require_timestamp (the strict
    write path) it must already carry a recorded_at timestamp.
    """
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")
    if require_timestamp and not record.get("recorded_at"):
        raise ValueError(
            "ledger entry refused: required timestamp 'recorded_at' is missing")
    return dict(record)


def append_record(path, record, require_timestamp=False):
    """Append one record to the JSONL ledger with hash-chain fields.

    Adds `prev_hash`, `entry_hash`, and `recorded_at` (if missing).
    With require_timestamp=True the entry is refused unless recorded_at
    is already present. Never rewrites existing lines. Returns the
    filed entry dict.
    """
    validate_entry(record, require_timestamp=require_timestamp)
    entries = read_all(path)
    prev_hash = entries[-1]["entry_hash"] if entries else GENESIS_HASH
    entry = dict(record)
    if "recorded_at" not in entry:
        entry["recorded_at"] = _utcnow()
    entry["prev_hash"] = prev_hash
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    entry["entry_hash"] = hashlib.sha256(
        _canonical(body) + prev_hash.encode("utf-8")
    ).hexdigest()
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify_chain(path):
    """Verify hash linkage of a ledger file. Returns (ok: bool, msg: str)."""
    entries = read_all(path)
    prev = GENESIS_HASH
    for i, entry in enumerate(entries):
        if entry.get("prev_hash") != prev:
            return (False, "break at line %d: prev_hash mismatch" % (i + 1))
        body = {k: v for k, v in entry.items() if k != "entry_hash"}
        expect = hashlib.sha256(
            _canonical(body) + entry["prev_hash"].encode("utf-8")
        ).hexdigest()
        if entry.get("entry_hash") != expect:
            return (False, "break at line %d: entry_hash mismatch" % (i + 1))
        prev = entry["entry_hash"]
    return (True, "ok: %d entries verified" % len(entries))
