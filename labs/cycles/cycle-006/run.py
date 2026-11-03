#!/usr/bin/env python3
"""Cycle-006 runner: Delaney (2004) paper equation over the frozen set,
plus a literature pass through the LIVE MCP-GATEWAY backend.

Deterministic computation. Reads inputs/delaney-processed.csv (frozen
copy), applies logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP
with RDKit descriptors, writes result.json into --out-dir.

Literature pass (live, recorded): openalex search for the Delaney 2004
ESOL record, then a get_work read of the resolved OpenAlex work id, via
the lab Gateway (backend "mcp-gateway", agent literature-researcher).
Call records go to <out-dir>/gateway-calls.jsonl with
backend=MCP-GATEWAY; payloads are kept verbatim under
<out-dir>/gateway/. Quarantined envelopes stay leads until the pin
check (explicit DOI/title identifier match, per the literature
assemble_brief rules) passes; the pin decision is filed in
<out-dir>/gateway/pin.json. result.json carries only stable pinned
identifiers (never volatile citation counts), so clean-directory
re-runs agree bit-for-bit.

Live-read gotchas (os-build/logs/OC2B-gateway-setup.md): openalex
get_work rejects DOI forms (hence the pre-resolved OpenAlex-id
locator, disclosed in prereg.md); the gbif string-key gotcha does not
apply to the openalex id map. One attempt per call; transport errors
are recorded verbatim and yield a documented degraded path.

Figure mode: --figure FIG --from RESULTJSON renders a measured-vs-
predicted scatter PNG (stdlib only, no matplotlib) for the pack.

Usage (from labs/cycles/cycle-006):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c6-clean   (verification re-run)
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
LAB = os.path.join(HERE, "..", "..", "..", "os", "worlds", "science-lab")
DEFAULT_INPUTS = os.path.join(HERE, "inputs", "delaney-processed.csv")
MEASURED_COL = "measured log solubility in mols per litre"
SMILES_COL = "smiles"
EXPECTED_RMSE = 1.099
TOLERANCE = 0.05
SEED = 500006
CYCLE = "cycle-006"

DOI = "10.1021/ci034243x"
WORK_URL = "https://openalex.org/W2076498053"
SEARCH_QUERY = ("Estimating aqueous solubility directly from "
                "molecular structure")

sys.path.insert(0, os.path.normpath(LAB))
import gateway  # noqa: E402

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


def literature_pass(out_dir):
    """Live openalex search+read via the lab gateway. Returns pin record.

    One attempt per call. Any transport error is recorded verbatim by
    the gateway call record and re-raised as a degraded path.
    """
    gw = gateway.Gateway(CYCLE,
                         calls_path=os.path.join(out_dir,
                                                 "gateway-calls.jsonl"),
                         backend="mcp-gateway")
    search_env = gw.call_tool(
        "literature-researcher", "openalex",
        {"op": "search", "query": SEARCH_QUERY, "limit": 3})
    read_env = gw.call_tool(
        "literature-researcher", "openalex",
        {"op": "read", "locator": WORK_URL})
    gw_dir = os.path.join(out_dir, "gateway")
    os.makedirs(gw_dir, exist_ok=True)
    for name, env in (("search.json", search_env),
                      ("read.json", read_env)):
        with open(os.path.join(gw_dir, name), "w",
                  encoding="utf-8") as fh:
            json.dump(env, fh, indent=1, sort_keys=True)
            fh.write("\n")

    def payload_text(env):
        res = env.get("result", {})
        inner = res.get("result", res)
        if isinstance(inner, dict) and "raw_text" in inner:
            return inner["raw_text"]
        return json.dumps(inner, sort_keys=True)

    search_text = payload_text(search_env)
    read_text = payload_text(read_env)
    pin = {
        "cycle": CYCLE,
        "rule": ("pinned iff the gateway read payload carries the "
                 "pre-registered DOI and author/year identifiers "
                 "(literature assemble_brief explicit-id rule)"),
        "prereg_doi": DOI,
        "prereg_work_url": WORK_URL,
        "doi_in_search": DOI in search_text,
        "doi_in_read": DOI in read_text,
        "delaney_in_read": "Delaney" in read_text,
        "year2004_in_read": "2004" in read_text,
        "search_payload_form": search_env["result"].get("payload_form"),
        "read_payload_form": read_env["result"].get("payload_form"),
        "remote_tools": [search_env["result"].get("remote_tool"),
                         read_env["result"].get("remote_tool")],
    }
    pin["pinned"] = bool(pin["doi_in_search"] and pin["doi_in_read"]
                         and pin["delaney_in_read"]
                         and pin["year2004_in_read"])
    if not pin["pinned"]:
        pin["degraded"] = ("read payload missed a pre-registered "
                           "identifier; source NOT pinned; computation "
                           "below stands on the archived gate record only")
    with open(os.path.join(gw_dir, "pin.json"), "w",
              encoding="utf-8") as fh:
        json.dump(pin, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return pin


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
        "cycle": CYCLE,
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
    os.makedirs(args.out_dir, exist_ok=True)
    pin = literature_pass(args.out_dir)
    result = compute(args.inputs)
    result["literature"] = {
        "backend": "MCP-GATEWAY",
        "gateway": "boss local MCP gateway 127.0.0.1:8931",
        "calls": 2,
        "calls_file": "gateway-calls.jsonl",
        "payloads": ["gateway/search.json", "gateway/read.json"],
        "remote_tools": pin["remote_tools"],
        "payload_forms": [pin["search_payload_form"],
                          pin["read_payload_form"]],
        "pinned": pin["pinned"],
        "pinned_identifiers": {
            "openalex_id": WORK_URL,
            "doi": DOI,
            "title": ("ESOL: Estimating Aqueous Solubility Directly "
                      "from Molecular Structure"),
            "year": 2004,
            "venue": ("Journal of Chemical Information and "
                      "Computer Sciences"),
            "author": "John S. Delaney",
        },
        "model_spend_usd": 0.0,
        "network": ("keyless public servers; no credentials held; "
                    "no model calls"),
    }
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("n=%d rmse=%.4f r2=%.4f mae=%.4f skipped=%d pinned=%s -> %s"
          % (result["n"], result["rmse"], result["r2"], result["mae"],
             len(result["skipped"]), pin["pinned"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
