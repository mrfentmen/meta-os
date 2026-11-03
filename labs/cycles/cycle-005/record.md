# Cycle 005 — record (held-out Delaney slice, paper-anchored expectation)

- Question: does a held-out slice of the archived Delaney set
  (rows 31-130, 100 compounds never used as the cycle-001 target)
  reproduce the PAPER's own reported training error?
- Target origin: a held-out Delaney slice (rows beyond 30) of the
  archived set gate/delaney/delaney-processed.csv — the cycle-5
  brief's "held-out Delaney slice (rows beyond 30)" option.
- Source: Delaney (2004), reported training statistics n = 2874,
  se = 0.97 (gate/run_gate.py PAPER table, verified from the paper);
  archived compound set as in cycle-001 (same sha).
- Expected value (pre-registered BEFORE this run, paper-anchored):
  RMSE 0.97, tolerance 0.06, i.e. MATCH iff observed slice RMSE in
  [0.91, 1.03]. Rationale recorded honestly: the paper's se comes
  from its 2,874-compound training set with Daylight CLOGP, while
  this run uses RDKit Wildman-Crippen cLogP on 100 held-out
  compounds, so a miss is plausible and, if it occurs, is evidence
  about method scope, not an error to hide.
- Headline metric: RMSE of paper-equation predicted logS vs measured
  (log units) on the 100-row slice.
- Method: run.py (deterministic; same equation and descriptors as
  cycle-001, restricted to the frozen slice inputs/slice.csv).
- Seed: 500005 (recorded; closed-form computation, no sampling).
- Falsifier: the claim "the held-out slice reproduces the paper's
  training se within tolerance" is killed if the observed slice RMSE
  falls outside [0.91, 1.03], or if the frozen slice hash differs
  from inputs.sha256, or if any slice row is skipped silently.
- Ladder level earned: Level 2 (computationally tested): DIFFER on the pre-registered band; mismatch caps the record at 2 per the ladder mismatch rule, even though the clean-directory re-run agrees bit-for-bit.
- Ledger entry id: 1bff12098b3555c34507c4d9741033e3fe12c995626c68e262ebecf9bb6f5c15 (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; receipts: none).
