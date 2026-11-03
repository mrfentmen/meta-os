#!/usr/bin/env python3
"""Cycle-001 runner: Delaney (2004) paper equation over the frozen set.

Deterministic. Reads inputs/delaney-processed.csv (frozen copy),
applies logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP
with RDKit descriptors, writes result.json into --out-dir.

Figure mode: --figure FIG --from RESULTJSON renders a measured-vs-
predicted scatter PNG (stdlib only, no matplotlib) for the pack.

Usage (from labs/cycles/cycle-001):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c1-clean   (verification re-run)
  python3 run.py --figure figure.png --from raw/result.json
"""

import argparse
import csv
import hashlib
import json
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUTS = os.path.join(HERE, "inputs", "delaney-processed.csv")
MEASURED_COL = "measured log solubility in mols per litre"
SMILES_COL = "smiles"
EXPECTED_RMSE = 1.099
TOLERANCE = 0.05
SEED = 500001

C0, C_LOGP, C_MW, C_RB, C_AP = 0.16, -0.63, -0.0062, 0.066, -0.74


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def descriptors(mol):
    from rdkit import Chem  # noqa: F401
    from rdkit.Chem import Crippen, Descriptors, Lipinski

    heavy = [a for a in mol.GetAtoms() if a.GetAtomicNum() > 1]
    if not heavy:
        return None
    aromatic = sum(1 for a in heavy if a.GetIsAromatic())
    return {
        "MolLogP": Crippen.MolLogP(mol),
        "MolWt": Descriptors.MolWt(mol),
        "RB": float(Lipinski.NumRotatableBonds(mol)),
        "AP": aromatic / len(heavy),
    }


def predict(d):
    return (C0 + C_LOGP * d["MolLogP"] + C_MW * d["MolWt"]
            + C_RB * d["RB"] + C_AP * d["AP"])


def compute(inputs_path):
    from rdkit import Chem

    with open(inputs_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    measured, predicted, skipped = [], [], []
    for i, r in enumerate(rows):
        smi = (r.get(SMILES_COL) or "").strip()
        try:
            mval = float(r[MEASURED_COL])
        except (ValueError, TypeError, KeyError):
            skipped.append({"row": i, "reason": "bad-measured"})
            continue
        mol = Chem.MolFromSmiles(smi) if smi else None
        if mol is None:
            skipped.append({"row": i, "reason": "unparseable-SMILES"})
            continue
        d = descriptors(mol)
        if d is None:
            skipped.append({"row": i, "reason": "no-heavy-atoms"})
            continue
        measured.append(mval)
        predicted.append(predict(d))
    n = len(measured)
    mean = sum(measured) / n
    ss_res = sum((m - p) ** 2 for m, p in zip(measured, predicted))
    ss_tot = sum((m - mean) ** 2 for m in measured)
    worst = sorted(range(n), key=lambda k: abs(measured[k] - predicted[k]),
                   reverse=True)[:10]
    return {
        "cycle": "cycle-001",
        "seed": SEED,
        "script": "run.py",
        "inputs": {"file": os.path.relpath(inputs_path, HERE),
                   "sha256": sha256_file(inputs_path),
                   "rows_total": len(rows)},
        "equation": ("logS = 0.16 - 0.63*cLogP - 0.0062*MWT"
                     " + 0.066*RB - 0.74*AP"),
        "descriptors": ("RDKit Crippen MolLogP (paper used Daylight CLOGP),"
                        " Descriptors MolWt, Lipinski RB,"
                        " aromatic-heavy/heavy"),
        "expected_rmse": EXPECTED_RMSE,
        "tolerance": TOLERANCE,
        "n": n,
        "skipped": skipped,
        "r2": 1.0 - ss_res / ss_tot if ss_tot else None,
        "rmse": math.sqrt(ss_res / n),
        "mae": sum(abs(m - p) for m, p in zip(measured, predicted)) / n,
        "measured": measured,
        "predicted": predicted,
        "worst10_idx": worst,
    }


# ------------------------------------------------------------------
# Minimal deterministic PNG scatter renderer (stdlib only).
# ------------------------------------------------------------------

def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, px):
    raw = b"".join(b"\x00" + bytes(px[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def _dot(px, w, h, x, y, rgb):
    if 0 <= x < w and 0 <= y < h:
        i = (y * w + x) * 3
        px[i:i + 3] = bytes(rgb)


def _line(px, w, h, x0, y0, x1, y1, rgb):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for s in range(steps + 1):
        _dot(px, w, h, round(x0 + (x1 - x0) * s / steps),
             round(y0 + (y1 - y0) * s / steps), rgb)


def render_scatter(fig_path, result):
    W, H = 640, 480
    ml, mr, mt, mb = 46, 14, 14, 40
    px = bytearray([255]) * (W * H * 3)
    xs, ys = result["measured"], result["predicted"]
    lo = min(min(xs), min(ys))
    hi = max(max(xs), max(ys))
    pad = (hi - lo) * 0.04 or 0.1
    lo, hi = lo - pad, hi + pad

    def X(v):
        return round(ml + (v - lo) / (hi - lo) * (W - ml - mr))

    def Y(v):
        return round(H - mb - (v - lo) / (hi - lo) * (H - mt - mb))

    for gx in range(ml, W - mr + 1, 53):
        _line(px, W, H, gx, mt, gx, H - mb, (232, 232, 232))
    for gy in range(mt, H - mb + 1, 44):
        _line(px, W, H, ml, gy, W - mr, gy, (232, 232, 232))
    _line(px, W, H, X(lo), Y(lo), X(hi), Y(hi), (200, 30, 30))
    for x, y in zip(xs, ys):
        Xp, Yp = X(x), Y(y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                _dot(px, W, H, Xp + dx, Yp + dy, (30, 80, 180))
    _line(px, W, H, ml, mt, ml, H - mb, (0, 0, 0))
    _line(px, W, H, ml, H - mb, W - mr, H - mb, (0, 0, 0))
    write_png(fig_path, W, H, px)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "raw"))
    ap.add_argument("--inputs", default=DEFAULT_INPUTS)
    ap.add_argument("--figure", default=None)
    ap.add_argument("--from", dest="from_result", default=None)
    args = ap.parse_args(argv)
    if args.figure is not None:
        if not args.from_result:
            print("figure mode needs --from RESULTJSON", file=sys.stderr)
            return 2
        with open(args.from_result, encoding="utf-8") as fh:
            render_scatter(args.figure, json.load(fh))
        print("figure written: %s" % args.figure)
        return 0
    result = compute(args.inputs)
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("n=%d rmse=%.4f r2=%.4f mae=%.4f skipped=%d -> %s"
          % (result["n"], result["rmse"], result["r2"], result["mae"],
             len(result["skipped"]), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
