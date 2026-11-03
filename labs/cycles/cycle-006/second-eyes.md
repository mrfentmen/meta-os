# Cycle 006 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json
  (parent commit order; hashes in labs/cycles/ledger.jsonl).
- [ ] Recompute inputs/delaney-processed.csv sha256 against
  gate/delaney/SOURCES.md (expect 8c06a76f...).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical; the re-run
  issues its own 2 live gateway calls, recorded under /tmp, not here).
- [ ] Confirm both entries in raw/gateway-calls.jsonl carry
  backend=MCP-GATEWAY, status ok, cost 0.0, cycle_id cycle-006.
- [ ] Confirm raw/gateway/read.json payload contains the prereg DOI
  10.1021/ci034243x and raw/gateway/pin.json shows pinned=true.
- [ ] Check figure.png is byte-identical to cycle-001's figure
  (7e8f2a50...; same frozen inputs and implementation).
- [ ] Confirm no file in the pack claims a ladder level above 3 and
  none quotes the paper's training statistics as this run's result.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
