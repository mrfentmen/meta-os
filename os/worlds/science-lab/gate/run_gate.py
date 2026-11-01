#!/usr/bin/env python3
"""Stage-1 gate runner (PREP) — Delaney (2004) ESOL reproduction.

This script prepares and smoke-tests the Science Lab's stage-1
reproduction gate. A full run of this script is a PREP RUN, not the
gate: the gate additionally requires the Independent Verifier to
re-run from the archived inputs as a separate step and confirm the
aggregate error lands within a stated tolerance of the paper's
reported figure. Nothing this script writes, by itself, earns any
evidence level.

Method (per SCIENCE_LAB_PLAN.md, gate section):
  - Input is ONLY the archived dataset:
    delaney/delaney-processed.csv (sha256 in delaney/SOURCES.md).
  - Descriptors per compound, computed with RDKit:
      MolWt              -> Descriptors.MolWt
      MolLogP            -> Crippen.MolLogP  (Wildman-Crippen; the paper
                            used Daylight CLOGP 4.72 — a real method
                            difference, recorded in every result)
      NumRotatableBonds  -> Lipinski.NumRotatableBonds
      AromaticProportion -> aromatic heavy atoms / heavy atoms
  - Two predictions per compound:
      (a) PAPER EQUATION — Delaney's published coefficients, verified
          from the paper itself (see PAPER below):
          logSw = 0.16 - 0.63*clogP - 0.0062*MWT + 0.066*RB - 0.74*AP
      (b) FITTED — ordinary least squares of measured log solubility
          on the same four RDKit descriptors, fit on THIS set. These
          coefficients are ours, fitted here, and are never to be
          presented as Delaney's.
  - Stats reported: R^2, RMSE, MAE for both, plus the paper's own
    reported statistics (verified from the paper) for honest
    comparison — different set (paper fit on 2,874 compounds) and a
    different LogP method, so the comparison is context, not a target.

Usage (RDKit venv):
  .venv-rdkit/bin/python run_gate.py --selfcheck
  .venv-rdkit/bin/python run_gate.py --limit 50      # smoke test
  .venv-rdkit/bin/python run_gate.py                 # full prep run
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE / "delaney" / "delaney-processed.csv"
EXPECTED_ROWS = 1128
EXPECTED_SHA256 = "8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f159c8be8964602f189"

MEASURED_COL = "measured log solubility in mols per litre"
SMILES_COL = "smiles"

# Delaney (2004), verified 2026-11-01 from the paper's own text
# (J. Chem. Inf. Comput. Sci. 44(3), 1000-1005; final equation p.1001,
# Table 1 regression summary, blind-test paragraph p.1001):
PAPER = {
    "equation": {"intercept": 0.16, "clogP": -0.63, "MWT": -0.0062, "RB": 0.066, "AP": -0.74},
    "reported_training": {"n": 2874, "r2": 0.72, "se": 0.97},
    "reported_blind_test": {"n": 528, "r2": 0.55, "se": 0.96, "aae": 0.83},
    "source": "Paper PDF opened and read 2026-11-01 (moreisdifferent.com mirror of the publisher text); equation wording corroborated by two further independent sources the same day.",
    "method_note": "Paper's clogP is Daylight CLOGP 4.72; this runner uses RDKit Wildman-Crippen MolLogP. Paper stats are for its 2,874-compound training set / 528-compound blind set, not for this 1,128-compound processed set.",
}


def sha256_of(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_rows():
    with DATASET.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def selfcheck():
    ok = True
    digest = sha256_of(DATASET)
    if digest != EXPECTED_SHA256:
        print(f"FAIL: dataset sha256 {digest} != archived {EXPECTED_SHA256}")
        ok = False
    rows = load_rows()
    if len(rows) != EXPECTED_ROWS:
        print(f"FAIL: {len(rows)} data rows, expected {EXPECTED_ROWS}")
        ok = False
    missing_meas = sum(1 for r in rows if not (r.get(MEASURED_COL) or "").strip())
    missing_smi = sum(1 for r in rows if not (r.get(SMILES_COL) or "").strip())
    if missing_meas:
        print(f"FAIL: {missing_meas} rows missing measured solubility")
        ok = False
    if missing_smi:
        print(f"FAIL: {missing_smi} rows missing SMILES")
        ok = False
    print(f"selfcheck: {len(rows)} rows, sha256 {'OK' if digest == EXPECTED_SHA256 else 'BAD'}, "
          f"missing measured={missing_meas}, missing smiles={missing_smi}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def descriptors(smiles):
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    heavy = [a for a in mol.GetAtoms() if a.GetAtomicNum() > 1]
    if not heavy:
        return None
    aromatic = sum(1 for a in heavy if a.GetIsAromatic())
    return {
        "MolWt": Descriptors.MolWt(mol),
        "MolLogP": Crippen.MolLogP(mol),
        "NumRotatableBonds": float(Lipinski.NumRotatableBonds(mol)),
        "AromaticProportion": aromatic / len(heavy),
    }


def stats(measured, predicted):
    import numpy as np

    y = np.asarray(measured, dtype=float)
    p = np.asarray(predicted, dtype=float)
    resid = y - p
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {
        "n": int(len(y)),
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else None,
        "rmse": math.sqrt(ss_res / len(y)),
        "mae": float(np.mean(np.abs(resid))),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=None, help="only process the first N compounds (smoke test)")
    ap.add_argument("--selfcheck", action="store_true", help="validate the archived dataset and exit")
    ap.add_argument("--out", default=str(HERE / "prep_results.json"), help="results JSON path")
    args = ap.parse_args()

    if args.selfcheck:
        return selfcheck()

    try:
        import rdkit  # noqa: F401
        import numpy as np
    except ImportError as e:
        print(f"ERROR: RDKit/numpy required (use the .venv-rdkit interpreter): {e}", file=sys.stderr)
        return 2

    rows = load_rows()
    if args.limit:
        rows = rows[: args.limit]

    eq = PAPER["equation"]
    records, skipped = [], []
    for r in rows:
        d = descriptors(r[SMILES_COL])
        if d is None:
            skipped.append(r["Compound ID"])
            continue
        measured = float(r[MEASURED_COL])
        paper_pred = (eq["intercept"] + eq["clogP"] * d["MolLogP"] + eq["MWT"] * d["MolWt"]
                      + eq["RB"] * d["NumRotatableBonds"] + eq["AP"] * d["AromaticProportion"])
        records.append({"id": r["Compound ID"], "measured": measured,
                        "paper_pred": paper_pred, "desc": d})

    if not records:
        print("ERROR: no compounds could be processed", file=sys.stderr)
        return 2

    # FITTED model: OLS of measured on the same four RDKit descriptors.
    X = np.array([[1.0, r["desc"]["MolLogP"], r["desc"]["MolWt"],
                   r["desc"]["NumRotatableBonds"], r["desc"]["AromaticProportion"]]
                  for r in records])
    y = np.array([r["measured"] for r in records])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted_pred = X @ coef
    for r, fp in zip(records, fitted_pred):
        r["fitted_pred"] = float(fp)

    measured_all = [r["measured"] for r in records]
    worst = sorted(records, key=lambda r: abs(r["measured"] - r["paper_pred"]), reverse=True)[:10]

    results = {
        "label": "PREP RUN — not the gate. The stage-1 gate requires the Independent Verifier to re-run from the archived inputs as a separate step.",
        "dataset": {"file": str(DATASET.relative_to(HERE)), "sha256": sha256_of(DATASET),
                    "rows_total": EXPECTED_ROWS, "rows_processed": len(records),
                    "rows_skipped_unparseable": skipped},
        "descriptors": "RDKit: MolWt=Descriptors.MolWt, MolLogP=Crippen Wildman-Crippen (paper used Daylight CLOGP 4.72), NumRotatableBonds=Lipinski, AromaticProportion=aromatic heavy atoms / heavy atoms",
        "paper_equation_applied": {
            "coefficients": eq,
            "provenance": PAPER["source"],
            "stats_on_this_set": stats(measured_all, [r["paper_pred"] for r in records]),
        },
        "fitted_model_NOT_delaney": {
            "coefficients": {"intercept": float(coef[0]), "MolLogP": float(coef[1]),
                             "MolWt": float(coef[2]), "NumRotatableBonds": float(coef[3]),
                             "AromaticProportion": float(coef[4])},
            "note": "Ordinary least squares fit on THIS 1,128-compound set with RDKit descriptors. Fitted here; not the paper's coefficients.",
            "stats_on_this_set": stats(measured_all, [r["fitted_pred"] for r in records]),
        },
        "paper_reported_stats_for_comparison": {
            "training": PAPER["reported_training"],
            "blind_test": PAPER["reported_blind_test"],
            "method_note": PAPER["method_note"],
        },
        "worst_paper_equation_misses": [
            {"id": r["id"], "measured": r["measured"], "predicted": r["paper_pred"],
             "abs_error": abs(r["measured"] - r["paper_pred"])} for r in worst
        ],
    }

    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    pe = results["paper_equation_applied"]["stats_on_this_set"]
    fm = results["fitted_model_NOT_delaney"]["stats_on_this_set"]
    print(f"processed {len(records)} compounds, skipped {len(skipped)}")
    print(f"PAPER EQUATION on this set: R2={pe['r2']:.3f} RMSE={pe['rmse']:.3f} MAE={pe['mae']:.3f}")
    print(f"FITTED (not Delaney):       R2={fm['r2']:.3f} RMSE={fm['rmse']:.3f} MAE={fm['mae']:.3f}")
    print(f"paper reported: training R2=0.72 SE=0.97 (n=2874); blind R2=0.55 SE=0.96 AAE=0.83 (n=528)")
    print(f"results -> {args.out}  [PREP RUN — not the gate]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
