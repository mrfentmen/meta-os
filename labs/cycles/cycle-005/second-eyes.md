# Cycle 005 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json.
- [ ] Check inputs/slice.csv holds exactly data rows 31-130 of the
  archived delaney-processed.csv (header + 100 rows).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical, DIFFER intact).
- [ ] Read failure.md and confirm the first-divergence account names
  the cLogP method shift before any other cause.
- [ ] Confirm the record is filed at ladder level 2 (DIFFER caps the
  record) and no file claims higher.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 2.
