# Stage-1 gate (Delaney ESOL reproduction) — PREPARATION

**Status: READY-TO-RUN, and RAN-AS-PREP (2026-11-01).** A prep run is
not the gate. The gate itself additionally requires the Independent
Verifier to re-run from these archived inputs as a separate step and
confirm the aggregate error lands within a stated tolerance of the
paper's reported figure. No evidence level has been earned by anything
in this directory yet. When the gate is run and verified, it earns
exactly ladder level 3 for the reproduction, and no discovery claim.

## Inputs (archived)

- `delaney/delaney-processed.csv` — 1,128 compounds, measured log
  solubilities, SMILES. Source, hash, and provenance: see
  `delaney/SOURCES.md`. The runner refuses no input other than this
  file; its SHA-256 is re-checked by `--selfcheck`.

## Tooling

- RDKit **2026.09.1** in a worktree-local venv:
  `.venv-rdkit/` (pip-installed 2026-11-01; the sandbox's system
  Python has no RDKit). Run everything with
  `.venv-rdkit/bin/python os/worlds/science-lab/gate/run_gate.py`.
- Descriptors: MolWt (`Descriptors.MolWt`), MolLogP (RDKit
  Wildman–Crippen — the paper used Daylight CLOGP 4.72; this is the
  one known method difference and it is recorded in every result),
  NumRotatableBonds (`Lipinski.NumRotatableBonds`), AromaticProportion
  (aromatic heavy atoms / heavy atoms).

## The model

- **Paper equation** (Delaney 2004; coefficients verified from the
  paper's own text, opened 2026-11-01):
  logSw = 0.16 − 0.63·clogP − 0.0062·MWT + 0.066·RB − 0.74·AP
- **Fitted model** (secondary): OLS of measured log solubility on the
  same four RDKit descriptors, fit on this set. Its coefficients are
  ours, fitted here, and are labelled `FITTED — NOT Delaney` in code,
  output, and results. Never present them as the paper's.

## Prep-run results (2026-11-01, `prep_results.json`)

All 1,128 compounds processed, 0 unparseable, ~1 s wall time.

| model | R² | RMSE | MAE |
|---|---|---|---|
| Paper equation (RDKit descriptors), this set | 0.725 | 1.099 | 0.844 |
| Fitted OLS (not Delaney), this set | 0.768 | 1.009 | 0.777 |
| Paper's own report — training set (n=2,874) | 0.72 | SE 0.97 | — |
| Paper's own report — blind test (n=528) | 0.55 | SE 0.96 | AAE 0.83 |

Honest reading: the reproduced R² (0.725) sits at the paper's training
R² (0.72); the reproduced RMSE (1.099) is above the paper's reported
standard errors (0.96–0.97), and the reproduced MAE (0.844) is close
to the paper's blind-test AAE (0.83). The gaps are consistent with the
two known differences — RDKit Crippen vs Daylight CLOGP, and a
different (smaller, processed) compound set — but consistency is not
proof: attributing the gap is the Verifier's job at gate time, against
a tolerance stated before the gate run, not after.

## Commands

```
.venv-rdkit/bin/python run_gate.py --selfcheck   # dataset integrity: PASS/FAIL
.venv-rdkit/bin/python run_gate.py --limit 50    # smoke test
.venv-rdkit/bin/python run_gate.py               # full prep run -> prep_results.json
```

## What remains for the actual gate (not done here, by design)

1. A stated tolerance for the aggregate error vs the paper's figure,
   fixed before the run.
2. The Independent Verifier re-running from the archived CSV alone
   (fresh process, no prep outputs) and confirming within tolerance.
3. Filing the full experiment record, worst misses included
   (`prep_results.json` already lists the 10 worst paper-equation
   misses), through the lab's normal record path.
