#!/usr/bin/env python3
"""Cycle-002 runner: drag-free projectile range via the lab compute module.

Deterministic. Reads inputs.json, calls compute.run_physics once,
scores with compute.compare_to_prereg, writes result.json into
--out-dir.

Figure mode: --figure FIG --from RESULTJSON renders the trajectory
PNG (stdlib only).

Usage (from labs/cycles/cycle-002):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c2-clean   (verification re-run)
  python3 run.py --figure figure.png --from raw/result.json
"""

import argparse
import json
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "..", "..", "..", "os", "worlds", "science-lab")
DEFAULT_INPUTS = os.path.join(HERE, "inputs.json")
SEED = 500002
EXPECTED = 55.1938
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
            render_trajectory(args.figure, json.load(fh))
        print("figure written: %s" % args.figure)
        return 0
    with open(args.inputs, encoding="utf-8") as fh:
        plan = json.load(fh)
    record = compute.run_physics(plan)
    params = record["parameters"]
    comparison = compute.compare_to_prereg(
        {"value": params["range_m"], "metric": "range_m"},
        {"expected_value": EXPECTED, "tolerance": TOLERANCE,
         "metric": "range_m"})
    result = {
        "cycle": "cycle-002",
        "seed": SEED,
        "script": "run.py",
        "inputs": {"file": os.path.relpath(args.inputs, HERE),
                   "sha256": _sha(args.inputs), "params": plan},
        "runner": "os/worlds/science-lab/compute.py run_physics",
        "observed_range_m": params["range_m"],
        "expected_range_m": EXPECTED,
        "tolerance_m": TOLERANCE,
        "comparison": comparison,
        "record_text": record["execution_logs"][-1]
        if record.get("execution_logs") else "",
    }
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("range=%.6f expected=%.4f tol=%.4f verdict=%s -> %s"
          % (result["observed_range_m"], EXPECTED, TOLERANCE,
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
# Minimal deterministic PNG trajectory renderer (stdlib only).
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


def render_trajectory(fig_path, result):
    W, H = 640, 480
    ml, mr, mt, mb = 46, 14, 14, 40
    px = bytearray([255]) * (W * H * 3)
    plan = result["inputs"]["params"]
    v0, ang, g = plan["v0"], plan["angle_deg"], plan["g"]
    th = math.radians(ang)
    R = v0 ** 2 * math.sin(2 * th) / g
    Hmax = (v0 * math.sin(th)) ** 2 / (2 * g)

    def X(x):
        return round(ml + x / R * (W - ml - mr))

    def Y(y):
        return round(H - mb - y / (Hmax * 1.15) * (H - mt - mb))

    def dot(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            px[i:i + 3] = bytes(rgb)

    def line(x0, y0, x1, y1, rgb):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            dot(round(x0 + (x1 - x0) * s / steps),
                round(y0 + (y1 - y0) * s / steps), rgb)

    steps = 400
    prev = None
    for s in range(steps + 1):
        x = R * s / steps
        y = x * math.tan(th) - g * x ** 2 / (2 * v0 ** 2 * math.cos(th) ** 2)
        pt = (X(x), Y(max(y, 0)))
        if prev is not None:
            line(prev[0], prev[1], pt[0], pt[1], (30, 80, 180))
        prev = pt
    line(ml, Y(0), W - mr, Y(0), (0, 0, 0))
    line(ml, mt, ml, H - mb, (0, 0, 0))
    line(X(R), Y(0) - 8, X(R), Y(0) + 8, (200, 30, 30))
    write_png(fig_path, W, H, px)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
