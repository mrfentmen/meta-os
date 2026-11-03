# Cycle 004 — pre-registration

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: evaluate E = h*c/lambda once, stdlib only, with
  h = 6.62607015e-34, c = 299792458, lambda = 500e-9, and compare to
  the band below by absolute difference.
- Inputs: inputs.json {h: 6.62607015e-34, c: 299792458,
  lambda_m: 5.0e-07, eV: 1.602176634e-19}; frozen hash in
  inputs.sha256.
- Method: labs/cycles/cycle-004/run.py, deterministic, seed 500004.
- Expected value: E = 3.972892e-19 J, tolerance 1.0e-24 J
  (MATCH iff in [3.972882e-19, 3.972902e-19] J). Source of
  expectation: hand arithmetic from exact constants, before running.
- Headline metric: E_joules (J). Context: E_eV.
- Falsifier: observed E outside the band, or input-hash mismatch.
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
