# Cycle 007 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json
  (parent commit order; hashes in labs/cycles/ledger.jsonl).
- [ ] Recompute inputs/sequence.txt and inputs/plan.json sha256
  against inputs.sha256 (expect 649935f1... and a3d5082a...).
- [ ] Hand-count the GC letters of inputs/sequence.txt (expect 31/60).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical; the re-run
  issues its own 2 live gateway calls, recorded under /tmp, not here).
- [ ] Confirm both entries in raw/gateway-calls.jsonl carry
  backend=MCP-GATEWAY, status ok, cost 0.0, cycle_id cycle-007, and the
  read entry's wire args show the key in string form.
- [ ] Confirm raw/gateway/read.json payload carries usageKey 5219404
  with canonicalName Panthera leo and raw/gateway/pin.json shows
  pinned=true with key_sent_as_string=true.
- [ ] Confirm no file in the pack claims a ladder level above 3.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
