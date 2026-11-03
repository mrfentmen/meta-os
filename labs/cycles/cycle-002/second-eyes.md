# Cycle 002 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json.
- [ ] Check inputs.json g value against the NIST standard-gravity
  definition (9.80665 m/s^2 exact).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical).
- [ ] Confirm compare_to_prereg detail in raw/result.json names the
  same band as prereg.md.
- [ ] Confirm no file in the pack claims a ladder level above 3.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
