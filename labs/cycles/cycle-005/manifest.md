# Cycle 005 — pack manifest (every produced file enumerated; no layout item missing)

- record.md — question, target origin (held-out Delaney slice rows 31-130), source, expected value, falsifier, seed, level 2, ledger entry id, spend.
- prereg.md — pre-registered plan + commit-sha placeholder TO_BE_COMMITTED_BY_PARENT.
- prereg.sha256 — sha256 of prereg.md.
- inputs.sha256 — sha256 of inputs/slice.csv.
- inputs/slice.csv — frozen 100-row slice (data rows 31-130 of the archived set, header preserved).
- run.py — deterministic runner (same equation/descriptors as cycle-001, slice defaults, seed 500005).
- raw/result.json — untouched run output (n=100, rmse=1.0752, r2=0.7432, mae=0.8382, skipped=0).
- raw/result.sha256 — hash of raw/result.json.
- score.md — DIFFER (rmse observed=1.0752 vs expected=0.97 +-0.06), metric line, figure command, comparison block.
- critic.md — verbatim objection + response section.
- failure.md — REQUIRED failure analysis (this cycle DIFFERs): paper training se does not transfer to this set/method.
- verify/rerun_result.json — clean-directory re-run output (bit-for-bit agree).
- verify/rerun_result.sha256 — hash of the verify output.
- verify/result.json — working copy of the clean-directory run (same bytes).
- figure.png — slice measured-vs-predicted scatter; generating command in score.md.
- summary.md — one-paragraph plain summary.
- second-eyes.md — Bond reproduction-lane checklist.
- pack.sha256 — hash of this whole pack directory.
