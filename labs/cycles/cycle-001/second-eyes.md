# Cycle 001 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json
  (parent commit order; hashes in labs/cycles/ledger.jsonl).
- [ ] Recompute inputs/delaney-processed.csv sha256 against
  gate/delaney/SOURCES.md (expect 8c06a76f...).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical).
- [ ] Check the 5-molecule selfcheck in labs/delaney-xcheck/xcheck.py
  still passes 5/5 (implementation sanity, separate from this pack).
- [ ] Confirm no file in the pack claims a ladder level above 3 and
  none quotes the paper's training statistics as this run's result.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
