# Cycle 007 — score

- Verdict: MATCH.
- Differing fields: none. All scored fields inside their bands:
  gc_fraction observed=0.5166666667 expected=0.5166666667 (31/60)
  tolerance=1e-9; gc_count observed=31 expected=31; length
  observed=60 expected=60.
- Metric line: gc_fraction observed=0.5166666667 expected=0.5166666667
  tolerance=1e-9 -> MATCH (compare_to_prereg verdict: match).
- Context (reported, not pass/fail): base counts A14 C15 G16 T15;
  run_bio record_text "GC-content 0.516667 (31/60)".
- Skipped rows: not applicable (single frozen sequence input; falsifier
  condition on input-hash mismatch: satisfied, both frozen hashes match
  inputs.sha256).
- Input freeze: inputs/sequence.txt sha256
  649935f1de25bf7516148dd6787eb3bce132cac227161ded2b16c106275c26c8
  and inputs/plan.json sha256
  a3d5082ab971e174b573bf28d7b0eeb66fbfbeab2866b851f11aa420c882db0a
  both match inputs.sha256.
- Provenance pass (live, backend=MCP-GATEWAY, 2/2 ok, $0.00):
  pinned=YES. Pinned identifiers: organism Panthera leo, usageKey
  5219404 (raw/gateway/read.json, verbatim JSON payload; canonicalName
  Panthera leo, authorship Linnaeus 1758). Remote tools
  gbif__match_species + gbif__get_species; wire read args
  {"key": "5219404"} (string form, recorded verbatim). The gbif
  string-key gotcha was handled at call time (str() coercion in
  run.py); shared infra untouched.
- Figure: figure.png (ACGT composition bars), generating command
  (from labs/cycles/cycle-007):
  python3 run.py --figure figure.png --from raw/result.json
- Comparison block (independent verification):
  raw/result.json sha256 =
  fd63b5a2c549ccd2d21a74614966de612c3df0fc99066d39745ff47377366dd9
  verify/rerun_result.json sha256 =
  fd63b5a2c549ccd2d21a74614966de612c3df0fc99066d39745ff47377366dd9
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs;
  the re-run issued its own 2 live gateway calls to /tmp, recorded
  outside this pack).
