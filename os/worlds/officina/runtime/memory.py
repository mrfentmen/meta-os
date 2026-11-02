#!/usr/bin/env python3
"""Officina workshop memory (CB-084).

Append-only JSONL with a sha256 chain. Every record names the previous
hash; a rewrite of any earlier line is detectable at that line. The class
never exposes an update: the only way to change the file is to break the
chain, which verify() reports.
"""

import hashlib
import json
import os


class AppendOnlyError(ValueError):
    pass


def _digest(seq, prev, entry):
    payload = json.dumps(
        {"seq": seq, "prev": prev, "entry": entry},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class WorkshopMemory:
    def __init__(self, path):
        self.path = path
        self.records = []
        if os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    if line.strip():
                        self.records.append(json.loads(line))

    def append(self, entry):
        seq = len(self.records) + 1
        prev = self.records[-1]["hash"] if self.records else ""
        rec = {
            "seq": seq,
            "prev": prev,
            "entry": entry,
            "hash": _digest(seq, prev, entry),
        }
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self.records.append(rec)
        return rec

    def rewrite(self, seq, entry):
        raise AppendOnlyError("workshop memory is append-only; rewrite of seq %s refused" % seq)

    def verify(self):
        prev = ""
        for index, rec in enumerate(self.records, start=1):
            if rec.get("seq") != index:
                return {"ok": False, "broken_at": index, "reason": "sequence gap"}
            if rec.get("prev") != prev:
                return {"ok": False, "broken_at": index, "reason": "previous hash mismatch"}
            if rec.get("hash") != _digest(index, prev, rec.get("entry")):
                return {"ok": False, "broken_at": index, "reason": "entry hash mismatch"}
            prev = rec["hash"]
        return {"ok": True, "broken_at": None, "reason": None}
