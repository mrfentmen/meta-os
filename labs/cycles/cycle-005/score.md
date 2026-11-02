# Cycle 005 — score

- Verdict: DIFFER.
- Differing fields: rmse (only scored field). R2/MAE reported as context.
- Metric line: RMSE observed=1.0752 expected=0.97 tolerance=0.06
  band=[0.91, 1.03] -> DIFFER (observed exceeds band top by 0.0452).
- Context (reported, not pass/fail): R2 observed=0.7432 on the slice
  (paper training R2 0.72), MAE observed=0.8382, n=100, skipped=0.
- Input freeze: inputs/slice.csv sha256
  e211a475b56df3f0a4b2b91fd8dc9f68ca4ea1d3fa3e3c5dc8c10d38bda1.
- Figure: figure.png (slice measured-vs-predicted scatter, red diagonal),
  generating command (from labs/cycles/cycle-005):
  python3 run.py --figure figure.png --from raw/result.json
- Comparison block (independent verification):
  raw/result.json sha256 =
  9ca7d5856839c4d4396e470ee7f3c94385e74f2488bed7397a073ae9873c449a
  verify/rerun_result.json sha256 =
  9ca7d5856839c4d4396e470ee7f3c94385e74f2488bed7397a073ae9873c449a
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs;
  the DIFFER reproduces exactly, so it is a stable finding, not noise).
- Failure analysis: see failure.md. Not-applicable line is NOT used;
  this cycle DIFFERs.
