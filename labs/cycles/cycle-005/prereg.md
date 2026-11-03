# Cycle 005 — pre-registration

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: apply the Delaney (2004) published equation (same
  coefficients and RDKit descriptors as cycle-001) to every row of
  the frozen 100-row slice inputs/slice.csv (data rows 31-130 of the
  archived delaney-processed.csv) and score the slice RMSE against
  the paper-anchored band below.
- Inputs: inputs/slice.csv (exact rows 31-130 of the archived file,
  header preserved); frozen hash in inputs.sha256.
- Method: labs/cycles/cycle-005/run.py, deterministic, seed 500005.
- Expected value: RMSE 0.97, tolerance 0.06 (MATCH iff [0.91, 1.03]).
  Source of expectation: the paper's reported training se = 0.97
  (gate/run_gate.py PAPER table), recorded before running.
- Headline metric: RMSE (log units) on the slice.
- Falsifier: slice RMSE outside [0.91, 1.03], slice-hash mismatch,
  or any silently skipped row.
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
