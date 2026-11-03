# Cycle 002 — pre-registration

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: call os/worlds/science-lab/compute.py run_physics once with
  {v0: 25, angle_deg: 30, g: 9.80665} and compare the returned
  range_m to the band below with compute.compare_to_prereg.
- Inputs: inputs.json {v0: 25, angle_deg: 30, g: 9.80665,
  g_source: "NIST standard gravity 9.80665 m/s^2 exact (shelf
  physics_math.json)"}; frozen hash in inputs.sha256.
- Method: labs/cycles/cycle-002/run.py, deterministic, seed 500002.
- Expected value: range 55.1938 m, tolerance 0.001 m
  (MATCH iff [55.1928, 55.1948] m). Source of expectation: hand
  arithmetic from the textbook formula, recorded before running.
- Headline metric: range_m (metres).
- Falsifier: observed range outside [55.1928, 55.1948] m, runner
  exception, or input-hash mismatch.
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
