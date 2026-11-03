# Cycle 004 — score

- Verdict: MATCH.
- Differing fields: none.
- Metric line: E_J observed=3.972892e-19 expected=3.972892e-19
  tolerance=1.0e-24 band=[3.972882e-19, 3.972902e-19] -> MATCH
  (absolute difference 0.0).
- Context (reported, not pass/fail): E_eV observed=2.479684.
- Input freeze: inputs.json sha256
  69f345dc5ecc4c2a2f7b2dfa1d2f2e39a24e92dcb4ec86d16ab9f0bba8f1c.
- Figure: figure.png (visible-spectrum bar with 500 nm marker),
  generating command (from labs/cycles/cycle-004):
  python3 run.py --figure figure.png --from raw/result.json
- Comparison block (independent verification):
  raw/result.json sha256 =
  5f358a9411819e444b3cad4c25363150a795f206fcc70249a16c84c96c98cccf
  verify/rerun_result.json sha256 =
  5f358a9411819e444b3cad4c25363150a795f206fcc70249a16c84c96c98cccf
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs).
