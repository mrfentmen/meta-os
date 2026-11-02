# Cycle 001 — score

- Verdict: MATCH.
- Differing fields: none. All scored fields inside their bands:
  rmse observed=1.0994 expected=1.099 tolerance=0.05 band=[1.049, 1.149].
- Metric line: RMSE observed=1.0994 expected=1.099 tolerance=0.05 -> MATCH.
- Context (reported, not pass/fail): R2 observed=0.7248 (repo note 0.725),
  MAE observed=0.8439 (repo note 0.844), n=1128, skipped=0.
- Skipped rows: 0 (falsifier condition on silent skips: satisfied, none).
- Input freeze: inputs/delaney-processed.csv sha256
  8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f59c8be8964602f189
  matches the archived sha in gate/delaney/SOURCES.md.
- Figure: figure.png (measured-vs-predicted scatter, red diagonal),
  generating command (from labs/cycles/cycle-001):
  python3 run.py --figure figure.png --from raw/result.json
- Comparison block (independent verification):
  raw/result.json sha256 =
  06eb9b69126f91e4d4fc31f96556fe2582dd55a7f9d4d76b8f66a4cfcc332d24
  verify/rerun_result.json sha256 =
  06eb9b69126f91e4d4fc31f96556fe2582dd55a7f9d4d76b8f66a4cfcc332d24
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs).
