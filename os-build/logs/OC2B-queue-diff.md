# OC2B-053 — Queue suite reconciliation vs baseline

Baseline reference in task list: "§9 baseline (296/296)". The current
tree collects **629 tests** (`tests/queue-python/`, 95 files) —
the suite GREW since that baseline was written (more validators,
edge cases, livecam/model coverage). There is no 296-test gate left
to reproduce literally; the honest reconciliation:

- Collected: 629. Passed: 629. Failed: 0. Skipped: 0.
  (`python3 -m pytest tests/queue-python/ -q`, 5.77s, build host.)
- Delta vs 296/296: +333 tests, all green — growth, not regression.
  Zero failures means zero deltas to explain per-test.
- Failing-shape coverage present and green: tampered envelopes 400'd,
  unknown products refused, no-key clean refusal, idempotent re-POST,
  health names FALLBACK honestly (see test names in suite).
- Full output: `OC2B-queue-suite.txt`.
