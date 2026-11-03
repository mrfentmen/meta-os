# Cycle 001 — pre-registration

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: apply the Delaney (2004) published equation
  logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP
  with RDKit descriptors (Crippen MolLogP, Descriptors MolWt,
  Lipinski NumRotatableBonds, aromatic heavy atoms / heavy atoms)
  to every row of the frozen input copy of
  os/worlds/science-lab/gate/delaney/delaney-processed.csv.
- Inputs: inputs/delaney-processed.csv (byte copy of the archived
  file); frozen hashes in inputs.sha256.
- Method: labs/cycles/cycle-001/run.py, deterministic, seed 500001.
- Expected value: RMSE 1.099, tolerance 0.05 (MATCH iff [1.049, 1.149]).
  Source of expectation: labs/delaney-xcheck/README.md repo numbers
  (R2 0.725 / RMSE 1.099 / MAE 0.844), recorded before running.
- Headline metric: RMSE (log units). Context: R2, MAE.
- Falsifier: RMSE outside [1.049, 1.149], input-hash mismatch, or any
  silently skipped row.
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
