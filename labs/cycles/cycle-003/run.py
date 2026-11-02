#!/usr/bin/env python3
"""Cycle-003 runner: rule-of-mixtures density via the lab compute module.

Deterministic. Reads inputs.json, calls compute.run_materials once,
scores with compute.compare_to_prereg, writes result.json into
--out-dir.

Figure mode: --figure FIG --from RESULTJSON renders the component /
mixture bar PNG (stdlib only).

Usage (from labs/cycles/cycle-003):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c3-clean   (verification re-run)
  python3 run.py --figure figure.png --from raw/result.json
"""

import argparse
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "..", "..", "..", "os", "worlds", "science-lab")
DEFAULT_INPUTS = os.path.join(HERE, "inputs.json")
SEED = 500003
EXPECTED = 5.204
TOLERANCE = 0.001

sys.path.insert(0, os.path.normpath(LAB))
import compute  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "raw"))
    ap.add_argument("--inputs", default=DEFAULT_INPUTS)
    ap.add_argument("--figure", default=None)
    ap.add_argument("--from", dest="from_result", default=None)
    args = ap.parse_args(argv)
    if args.figure is not None:
        with open(args.from_result, encoding="utf-8") as fh:
            render_bars(args.figure, json.load(fh))
        print("figure written: %s" % args.figure)
        return 0
    with open(args.inputs, encoding="utf-8") as fh:
        plan = json.load(fh)
    record = compute.run_materials(plan)
    params = record["parameters"]
    comparison = compute.compare_to_prereg(
        {"value": params["density"], "metric": "density"},
        {"expected_value": EXPECTED, "tolerance": TOLERANCE,
         "metric": "density"})
    result = {
        "cycle": "cycle-003",
        "seed": SEED,
        "script": "run.py",
        "inputs": {"file": os.path.relpath(args.inputs, HERE),
                   "sha256": _sha(args.inputs), "params": plan},
        "runner": "os/worlds/science-lab/compute.py run_materials",
        "observed_density": params["density"],
        "expected_density": EXPECTED,
        "tolerance": TOLERANCE,
        "comparison": comparison,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("density=%.6f expected=%.3f tol=%.4f verdict=%s -> %s"
          % (result["observed_density"], EXPECTED, TOLERANCE,
             comparison["verdict"], out))
    return 0


def _sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------
# Minimal deterministic PNG bar renderer (stdlib only).
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


def render_bars(fig_path, result):
    W, H = 640, 480
    ml, mr, mt, mb = 46, 14, 14, 40
    px = bytearray([255]) * (W * H * 3)
    params = result["inputs"]["params"]
    fracs = params["fractions"]
    dens = params["densities"]
    rho = result["observed_density"]
    top = max(dens + [rho]) * 1.1

    def Y(v):
        return round(H - mb - v / top * (H - mt - mb))

    def dot(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            px[i:i + 3] = bytes(rgb)

    def bar(x0, x1, v, rgb):
        for x in range(x0, x1 + 1):
            for y in range(Y(v), H - mb + 1):
                dot(x, y, rgb)

    def line(x0, y0, x1, y1, rgb):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            dot(round(x0 + (x1 - x0) * s / steps),
                round(y0 + (y1 - y0) * s / steps), rgb)

    slot = (W - ml - mr) // 4
    colors = [(30, 80, 180), (200, 120, 30)]
    for i, (f, d) in enumerate(zip(fracs, dens)):
        x0 = ml + slot * i + 20
        bar(x0, x0 + slot - 40, d, colors[i % 2])
    x0 = ml + slot * 2 + 20
    bar(x0, x0 + slot - 40, rho, (40, 160, 60))
    line(ml, Y(EXPECTED), ml + slot * 3, Y(EXPECTED), (200, 30, 30))
    line(ml, H - mb, W - mr, H - mb, (0, 0, 0))
    line(ml, mt, ml, H - mb, (0, 0, 0))
    write_png(fig_path, W, H, px)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
