#!/usr/bin/env python3
"""Delaney (2004) ESOL cross-check runner — labs only, NOT the gate.

Implements the paper's published equation from scratch:
    logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP
(J. Chem. Inf. Comput. Sci. 2004, Delaney "ESOL: Estimating Aqueous
Solubility Directly from Molecular Structure".)

cLogP here is RDKit Wildman-Crippen, NOT the paper's Daylight CLOGP —
expect a systematic shift vs the gate numbers (see README). Written
without reading any gate code.

Usage:
  python3 xcheck.py --selfcheck        # 5 hand-computable molecules
  python3 xcheck.py --csv file.csv     # run over a CSV (needs smiles,Solubility columns)
  python3 xcheck.py --csv file.csv --ols   # fitted-OLS mode (NOT Delaney)
"""
import csv
import math
import sys

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski
except ImportError:
    print("xcheck needs RDKit (pip install rdkit)", file=sys.stderr)
    sys.exit(2)

C0, C_LOGP, C_MW, C_RB, C_AP = 0.16, -0.63, -0.0062, 0.066, -0.74


def descriptors(mol):
    """Return (cLogP, MWT, RB, AP) for a molecule."""
    clogp = Descriptors.MolLogP(mol)
    mwt = Descriptors.MolWt(mol)
    rb = Lipinski.NumRotatableBonds(mol)
    heavy = mol.GetNumHeavyAtoms()
    arom = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic())
    ap = arom / heavy if heavy else 0.0
    return clogp, mwt, rb, ap


def delaney_logS(clogp, mwt, rb, ap):
    return C0 + C_LOGP * clogp + C_MW * mwt + C_RB * rb + C_AP * ap


def predict(smiles):
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("empty SMILES")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("unparseable SMILES: %r" % smiles)
    return delaney_logS(*descriptors(mol))


# Hand-computed expectations (independently calculated, see README for
# the arithmetic). Tolerance covers RDKit-version float wobble only.
SELFCHECK = [
    # (name, smiles, expected_logS)
    ("benzene", "c1ccccc1", -2.13),
    ("toluene", "Cc1ccccc1", -2.30),
    ("phenol", "Oc1ccccc1", -1.94),
    ("aniline", "Nc1ccccc1", -1.85),
    ("benzoic-acid", "O=C(O)c1ccccc1", -1.90),
]
SELFCHECK_TOL = 0.05


def selfcheck():
    ok = True
    for name, smi, exp in SELFCHECK:
        try:
            got = predict(smi)
        except Exception as e:  # noqa: BLE001 - report, don't crash
            print("FAIL %s: %s" % (name, e))
            ok = False
            continue
        err = abs(got - exp)
        status = "ok" if err <= SELFCHECK_TOL else "FAIL"
        if err > SELFCHECK_TOL:
            ok = False
        print("%s %-13s got=%+.3f exp=%+.3f |err|=%.3f" % (status, name, got, exp, err))
    return ok


def run_csv(path, ols=False):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            smi = row.get("smiles") or row.get("SMILES")
            sol = row.get("Solubility") or row.get("solubility") or row.get("logS")
            if not smi or sol is None:
                continue
            try:
                rows.append((predict(smi), float(sol)))
            except ValueError:
                continue
    if not rows:
        print("no usable rows in %s" % path)
        return False
    if ols:
        # NOT Delaney: ordinary least squares of measured ~ predicted.
        n = len(rows)
        mx = sum(p for p, _ in rows) / n
        my = sum(m for _, m in rows) / n
        num = sum((p - mx) * (m - my) for p, m in rows)
        den = sum((p - mx) ** 2 for p, _ in rows)
        b = num / den if den else 0.0
        a = my - b * mx
        preds = [a + b * p for p, _ in rows]
        tag = "OLS-fit (NOT Delaney)"
    else:
        preds = [p for p, _ in rows]
        tag = "Delaney-2004"
    meas = [m for _, m in rows]
    n = len(rows)
    mean = sum(meas) / n
    ss_res = sum((m - p) ** 2 for m, p in zip(meas, preds))
    ss_tot = sum((m - mean) ** 2 for m in meas)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    rmse = math.sqrt(ss_res / n)
    mae = sum(abs(m - p) for m, p in zip(meas, preds)) / n
    print("%s n=%d R2=%.3f RMSE=%.3f MAE=%.3f" % (tag, n, r2, rmse, mae))
    return True


def main(argv):
    if "--selfcheck" in argv:
        sys.exit(0 if selfcheck() else 1)
    if "--csv" in argv:
        path = argv[argv.index("--csv") + 1]
        sys.exit(0 if run_csv(path, ols="--ols" in argv) else 1)
    print(__doc__.strip().split("\n")[0])
    print("try --selfcheck")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
