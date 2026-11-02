# Cycle 002 — record (physics department: drag-free projectile range)

- Question: does the lab's physics runner reproduce the hand-computed
  textbook range for a drag-free projectile at the NIST standard
  gravity?
- Target: a published computational result from a DIFFERENT department
  than cycle 1 (physics, not chemistry): R = v0^2 * sin(2*theta) / g
  for v0 = 25 m/s, theta = 30 deg, g = 9.80665 m/s^2 (NIST standard
  gravity), computed via os/worlds/science-lab/compute.py run_physics.
- Source: NIST Fundamental Physical Constants / SI (standard gravity
  gn = 9.80665 m/s^2 exact by definition since 1901; shelf locator
  https://physics.nist.gov/cuu/Constants in
  os/worlds/science-lab/shelves/physics_math.json); projectile-motion
  textbook formula (no drag).
- Expected value (pre-registered BEFORE this run, hand arithmetic):
  range 55.1938 m, tolerance 0.001 m, i.e. MATCH iff observed range
  in [55.1928, 55.1948] m.
- Headline metric: range_m (metres).
- Method: run.py calls compute.run_physics once, deterministically,
  then compute.compare_to_prereg against the prereg band.
- Seed: 500002 (recorded; closed-form computation, no sampling).
- Falsifier: the claim is killed if the observed range falls outside
  [55.1928, 55.1948] m, or if run_physics raises, or if the frozen
  inputs hash differs from inputs.sha256.
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run from frozen inputs.
- Ledger entry id: d51e60f431871a50f5619e2d83dcfa5e05ef6eb6d6b7d1a2d819b4d9021ff425 (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; receipts: none).
