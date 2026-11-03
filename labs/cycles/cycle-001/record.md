# Cycle 001 — record (Delaney ESOL cross-check)

- Question: does the Delaney (2004) published ESOL equation, implemented
  from scratch with RDKit Wildman-Crippen cLogP, reproduce the
  repo-recorded error statistics on the archived 1,128-compound set?
- Target: the Delaney solubility cross-check under labs/delaney-xcheck
  (xcheck.py, selfcheck 5/5; README notes the expected systematic shift
  vs the paper's Daylight CLOGP).
- Source: Delaney, J. S. (2004). ESOL: Estimating Aqueous Solubility
  Directly from Molecular Structure. J. Chem. Inf. Comput. Sci. 44(3),
  1000-1005. doi:10.1021/ci034243x. Archived compound set:
  os/worlds/science-lab/gate/delaney/delaney-processed.csv, sha256
  8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f159c8be8964602f189
  (gate/delaney/SOURCES.md).
- Expected value (pre-registered, from repo numbers recorded in
  labs/delaney-xcheck/README.md BEFORE this run): RMSE 1.099,
  tolerance 0.05, i.e. MATCH iff observed RMSE in [1.049, 1.149].
  Context values from the same repo note: R2 0.725, MAE 0.844
  (reported alongside, scored as context, not pass/fail).
- Headline metric: RMSE of paper-equation predicted logS vs measured
  log solubility (mols per litre, log units).
- Method: run.py (deterministic; no fitting; paper coefficients
  0.16 / -0.63 / -0.0062 / +0.066 / -0.74 applied to RDKit
  descriptors MolWt, Crippen MolLogP, Lipinski RB, aromatic proportion).
- Seed: 500001 (recorded; computation is closed-form, seed governs
  no sampling and is filed for ledger completeness).
- Falsifier: the claim is killed if the observed RMSE falls outside
  [1.049, 1.149], or if the frozen input hash differs from the
  archived sha above, or if any compound row is skipped silently
  (every skipped row must be named in the raw output).
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run from frozen inputs.
- Ledger entry id: feb64da499909bad3db348d929196e9558e32e1449a70a6356f9c2277656dce9 (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; receipts: none).
