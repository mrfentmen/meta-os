# Cycle 003 — second eyes (Bond reproduction lane)

- [ ] Confirm prereg.md + prereg.sha256 predate raw/result.json.
- [ ] Check each model receipt in model/ (director, wonder, sam,
  critic): tried once, mode OFFLINE, exactly one error line each,
  no retries in model/call_log.md.
- [ ] Confirm model/impact.md states per call what changed (nothing)
  and model/spend.json totals the transport usage honestly.
- [ ] Confirm model/sam_record.json carries box:none + overlay:no
  and model/sam_overlay.png is byte-identical to the source image.
- [ ] Run `python3 run.py --out-dir /tmp/<clean>` from the pack and
  diff against raw/result.json (expect byte-identical).
- [ ] Confirm no file in the pack claims a ladder level above 3 and
  no OFFLINE template text is presented as a live model reply.
- [ ] Confirm the ledger entry id quoted in record.md exists in
  labs/cycles/ledger.jsonl with level 3.
