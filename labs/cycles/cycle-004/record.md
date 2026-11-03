# Cycle 004 — record (shelf target: NIST photon energy at 500 nm)

- Question: does a from-scratch implementation of E = h*c/lambda with
  exact SI/NIST constants reproduce the hand-computed photon energy
  for green light (lambda = 500 nm)?
- Target: a target chosen from the lab's repository shelf
  (os/worlds/science-lab/shelves/physics_math.json, NIST Fundamental
  Physical Constants locator https://physics.nist.gov/cuu/Constants):
  photon energy E = h*c/lambda with h = 6.62607015e-34 J/Hz (exact,
  SI defining constant), c = 299792458 m/s (exact, SI defining
  constant), lambda = 500e-9 m.
- Source: NIST SP 330 / SI Brochure (h, c exact by definition);
  shelf file above; Planck relation E = h*nu.
- Expected value (pre-registered BEFORE this run, hand arithmetic):
  E = 3.972892e-19 J, tolerance 1.0e-24 J, i.e. MATCH iff observed E
  in [3.972882e-19, 3.972902e-19] J. Context: 2.479684 eV
  (tolerance 1.0e-6 eV, reported alongside).
- Headline metric: E_joules (J).
- Method: run.py, stdlib only, deterministic single evaluation.
- Seed: 500004 (recorded; closed-form computation, no sampling).
- Falsifier: the claim is killed if the observed energy falls outside
  [3.972882e-19, 3.972902e-19] J, or if the frozen inputs hash
  differs from inputs.sha256.
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run from frozen inputs.
- Ledger entry id: 96ceecf89db0d67c13461fb0d04c00e633f783ad1b87b66f0bada02077a71726 (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; receipts: none).
