# Cycle 004 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json.
- [ ] Check inputs.json constants against the SI Brochure / NIST
  (h = 6.62607015e-34 exact, c = 299792458 exact).
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical).
- [ ] Confirm no file in the pack claims a ladder level above 3.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
