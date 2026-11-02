# Cycle 003 — pre-registration

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: director call to Muse Spark once (model/director_prompt.txt);
  adopt/reject each line in the record; then call
  os/worlds/science-lab/compute.py run_materials once with
  {fractions: [0.6, 0.4], densities: [2.70, 8.96]} and compare the
  returned density to the band below with compute.compare_to_prereg;
  Wonder reads the output figure once; SAM segments one labs
  molecule image once; critic comes from the second model once;
  every model call is tried ONCE only, OFFLINE deterministic
  fallback on any flake, never retried.
- Inputs: inputs.json {fractions: [0.6, 0.4], densities: [2.70, 8.96],
  units: "g/cm^3"}; frozen hash in inputs.sha256.
- Method: labs/cycles/cycle-003/run.py, deterministic, seed 500003.
- Expected value: density 5.204 g/cm^3, tolerance 0.001
  (MATCH iff [5.203, 5.205]). Source of expectation: hand arithmetic
  (0.6*2.70 + 0.4*8.96 = 5.204), recorded before running.
- Headline metric: density (g/cm^3).
- Falsifier: observed density outside [5.203, 5.205] g/cm^3, runner
  exception, or input-hash mismatch.
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
