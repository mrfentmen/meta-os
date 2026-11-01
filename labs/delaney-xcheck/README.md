# labs/delaney-xcheck/ — Delaney (2004) ESOL cross-check

First paragraph, as ordered: **the gate is Milo's; this is a cross-check.**
Nothing here counts as the gate, and its numbers must never be quoted as
gate numbers.

## What it proves

That the Delaney-2004 published equation, implemented from scratch from
the paper (`logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP`),
runs correctly: `--selfcheck` verifies the descriptor math on 5
hand-computable molecules (5/5 pass), and edge cases (empty SMILES,
salts, charged species) behave explicitly (tests/edge.test.py).

## What it does not prove

- It does NOT reproduce the gate: cLogP here is RDKit Wildman–Crippen,
  not the paper's Daylight CLOGP. Expect a systematic shift vs the gate
  record (paper equation R² 0.725 / RMSE 1.099 / MAE 0.844). That
  difference is chemistry-tooling, not a solver bug.
- It does NOT validate any heatsink, molecule, or model. It validates
  arithmetic.
- The `--ols` mode is NOT Delaney: it fits measured ~ predicted on the
  input CSV and labels every output line accordingly.

## Use

    python3 xcheck.py --selfcheck          # 5 molecules, must all pass
    python3 xcheck.py --csv delaney.csv    # needs smiles,Solubility columns
    python3 xcheck.py --csv delaney.csv --ols   # NOT Delaney, labelled

No archived Delaney CSV exists in this checkout (searched; absent), so
the CSV run tasks are recorded as not-run, not skipped-silently.
