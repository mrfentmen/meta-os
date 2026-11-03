# Cycle 002 — score

- Verdict: MATCH.
- Differing fields: none.
- Metric line: range_m observed=55.193759 expected=55.1938
  tolerance=0.001 band=[55.1928, 55.1948] -> MATCH.
- Runner: os/worlds/science-lab/compute.py run_physics;
  compare_to_prereg verdict=match,
  detail="observed=55.193759 expected=55.1938 tolerance=0.001".
- Input freeze: inputs.json sha256
  e42bf80fb6a30ddcfb07689d185bdb7d7250a4e7488159262ebc2cdb26d37d.
- Figure: figure.png (drag-free trajectory with range marker),
  generating command (from labs/cycles/cycle-002):
  python3 run.py --figure figure.png --from raw/result.json
- Comparison block (independent verification):
  raw/result.json sha256 =
  39f96d53fc3cef76051230c0c25bdf77d2be8a9efe0845e1d86bd4758bf67b8d
  verify/rerun_result.json sha256 =
  39f96d53fc3cef76051230c0c25bdf77d2be8a9efe0845e1d86bd4758bf67b8d
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs).
