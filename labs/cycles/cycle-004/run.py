#!/usr/bin/env python3
"""Cycle-004 runner: photon energy E = h*c/lambda, stdlib only.

Deterministic single evaluation. Reads inputs.json, writes
result.json into --out-dir.

Figure mode: --figure FIG --from RESULTJSON renders a spectrum bar
with the 500 nm marker (stdlib PNG, no matplotlib).

Usage (from labs/cycles/cycle-004):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c4-clean   (verification re-run)
  python3 run.py --figure figure.png --from raw/result.json
"""

import argparse
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUTS = os.path.join(HERE, "inputs.json")
SEED = 500004
EXPECTED_J = 3.972892e-19
TOLERANCE_J = 1.0e-24


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "raw"))
    ap.add_argument("--inputs", default=DEFAULT_INPUTS)
    ap.add_argument("--figure", default=None)
    ap.add_argument("--from", dest="from_result", default=None)
    args = ap.parse_args(argv)
    if args.figure is not None:
        with open(args.from_result, encoding="utf-8") as fh:
            render_spectrum(args.figure, json.load(fh))
        print("figure written: %s" % args.figure)
        return 0
    with open(args.inputs, encoding="utf-8") as fh:
        plan = json.load(fh)
    e_j = plan["h"] * plan["c"] / plan["lambda_m"]
    e_ev = e_j / plan["eV_J"]
    diff = abs(e_j - EXPECTED_J)
    result = {
        "cycle": "cycle-004",
        "seed": SEED,
        "script": "run.py",
        "inputs": {"file": os.path.relpath(args.inputs, HERE),
                   "sha256": _sha(args.inputs), "params": plan},
        "runner": "E = h*c/lambda (stdlib)",
        "observed_E_J": e_j,
        "observed_E_eV": e_ev,
        "expected_E_J": EXPECTED_J,
        "tolerance_J": TOLERANCE_J,
        "abs_diff_J": diff,
        "verdict": "match" if diff <= TOLERANCE_J else "no-match",
    }
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("E=%.6e J expected=%.6e tol=%.1e verdict=%s -> %s"
          % (e_j, EXPECTED_J, TOLERANCE_J, result["verdict"], out))
    return 0


def _sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------
# Minimal deterministic PNG spectrum renderer (stdlib only).
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


def _wavelength_rgb(nm):
    """Approximate visible-spectrum color (nm 380-780)."""
    if nm < 440:
        r, g, b = (0.3 + 0.7 * (nm - 380) / 60.0), 0.0, 1.0
    elif nm < 490:
        r, g, b = 0.0, (nm - 440) / 50.0, 1.0
    elif nm < 510:
        r, g, b = 0.0, 1.0, 1.0 - (nm - 490) / 20.0
    elif nm < 580:
        r, g, b = (nm - 510) / 70.0, 1.0, 0.0
    elif nm < 645:
        r, g, b = 1.0, 1.0 - (nm - 580) / 65.0, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    return (round(r * 255), round(g * 255), round(b * 255))


def render_spectrum(fig_path, result):
    W, H = 640, 480
    ml, mr, mt, mb = 46, 14, 120, 40
    px = bytearray([255]) * (W * H * 3)

    def dot(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            px[i:i + 3] = bytes(rgb)

    def line(x0, y0, x1, y1, rgb):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            dot(round(x0 + (x1 - x0) * s / steps),
                round(y0 + (y1 - y0) * s / steps), rgb)

    lo, hi = 380.0, 780.0

    def X(nm):
        return round(ml + (nm - lo) / (hi - lo) * (W - ml - mr))

    for x in range(ml, W - mr + 1):
        nm = lo + (x - ml) / (W - ml - mr) * (hi - lo)
        rgb = _wavelength_rgb(nm)
        for y in range(mt, H - mb + 1):
            dot(x, y, rgb)
    lam_nm = result["inputs"]["params"]["lambda_m"] * 1e9
    line(X(lam_nm), mt - 30, X(lam_nm), H - mb, (0, 0, 0))
    line(X(lam_nm) - 6, mt - 30, X(lam_nm) + 6, mt - 30, (0, 0, 0))
    line(ml, H - mb, W - mr, H - mb, (0, 0, 0))
    write_png(fig_path, W, H, px)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
