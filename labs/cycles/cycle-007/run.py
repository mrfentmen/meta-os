#!/usr/bin/env python3
"""Cycle-007 runner: GC-content of the frozen 60-mer via lab run_bio,
plus an organism-provenance pass through the LIVE MCP-GATEWAY backend.

Deterministic computation. Reads inputs/plan.json + inputs/sequence.txt
(frozen), calls compute.run_bio once, scores with
compute.compare_to_prereg, writes result.json into --out-dir.

Provenance pass (live, recorded): gbif match_species search for the
study organism "Panthera leo", then a get_species read of the matched
usageKey, via the lab Gateway (backend "mcp-gateway", agent
literature-researcher). Call records go to
<out-dir>/gateway-calls.jsonl with backend=MCP-GATEWAY; payloads are
kept verbatim under <out-dir>/gateway/. Quarantined envelopes stay
leads until the pin check (explicit usageKey/name identifier match,
per the literature assemble_brief rules) passes; the pin decision is
filed in <out-dir>/gateway/pin.json. result.json carries only stable
pinned identifiers, so clean-directory re-runs agree bit-for-bit.

Live-read gotcha handled at call time (NOT in shared infra): the gbif
get_species wire key must be a string (the live server rejects
numbers; see os-build/logs/OC2B-gateway-setup.md), so the integer
usageKey from the plan is coerced with str() at call time and the wire
args are recorded verbatim. One attempt per call; transport errors are
recorded verbatim and yield a documented degraded path.

Figure mode: --figure FIG --from RESULTJSON renders an ACGT
composition bar PNG (stdlib only) for the pack.

Usage (from labs/cycles/cycle-007):
  python3 run.py --out-dir raw
  python3 run.py --out-dir /tmp/oc2b-c7-clean   (verification re-run)
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
DEFAULT_INPUTS = os.path.join(HERE, "inputs", "plan.json")
SEED = 500007
CYCLE = "cycle-007"
EXPECTED_FRAC = 31.0 / 60.0
TOLERANCE = 1e-9

ORGANISM = "Panthera leo"
USAGE_KEY_INT = 5219404

sys.path.insert(0, os.path.normpath(LAB))
import compute  # noqa: E402
import gateway  # noqa: E402


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance_pass(out_dir):
    """Live gbif match+read via the lab gateway. Returns pin record.

    One attempt per call. Any transport error is recorded verbatim by
    the gateway call record and re-raised as a degraded path.
    """
    gw = gateway.Gateway(CYCLE,
                         calls_path=os.path.join(out_dir,
                                                 "gateway-calls.jsonl"),
                         backend="mcp-gateway")
    search_env = gw.call_tool(
        "literature-researcher", "gbif",
        {"op": "search", "query": ORGANISM})
    # Live-read gotcha: gbif keys must be strings (server rejects
    # numbers), so coerce at call time; wire args recorded verbatim.
    read_env = gw.call_tool(
        "literature-researcher", "gbif",
        {"op": "read", "locator": str(USAGE_KEY_INT)})
    gw_dir = os.path.join(out_dir, "gateway")
    os.makedirs(gw_dir, exist_ok=True)
    for name, env in (("search.json", search_env),
                      ("read.json", read_env)):
        with open(os.path.join(gw_dir, name), "w",
                  encoding="utf-8") as fh:
            json.dump(env, fh, indent=1, sort_keys=True)
            fh.write("\n")

    def payload_blob(env):
        res = env.get("result", {})
        blob = res.get("source", res.get("result", res))
        return blob if not (
            isinstance(blob, dict) and set(blob) == {"raw_text"}) else {}

    search_blob = payload_blob(search_env)
    read_blob = payload_blob(read_env)
    read_text = json.dumps(read_blob, sort_keys=True)
    search_text = json.dumps(search_blob, sort_keys=True)
    pin = {
        "cycle": CYCLE,
        "rule": ("pinned iff the gateway read payload carries the "
                 "pre-registered usageKey and organism name "
                 "(literature assemble_brief explicit-id rule)"),
        "prereg_organism": ORGANISM,
        "prereg_usage_key": str(USAGE_KEY_INT),
        "wire_read_args": read_env["result"].get("remote_args"),
        "key_sent_as_string": isinstance(
            (read_env["result"].get("remote_args") or {}).get("key"), str),
        "usagekey_in_search": str(USAGE_KEY_INT) in search_text,
        "usagekey_in_read": str(USAGE_KEY_INT) in read_text,
        "name_in_read": ORGANISM in read_text,
        "search_payload_form": search_env["result"].get("payload_form"),
        "read_payload_form": read_env["result"].get("payload_form"),
        "remote_tools": [search_env["result"].get("remote_tool"),
                         read_env["result"].get("remote_tool")],
    }
    pin["pinned"] = bool(pin["key_sent_as_string"]
                         and pin["usagekey_in_read"]
                         and pin["name_in_read"])
    if not pin["pinned"]:
        pin["degraded"] = ("read payload missed a pre-registered "
                           "identifier; organism NOT pinned; computation "
                           "below stands on the frozen plan only")
    with open(os.path.join(gw_dir, "pin.json"), "w",
              encoding="utf-8") as fh:
        json.dump(pin, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return pin


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
            render_bars(args.figure, json.load(fh))
        print("figure written: %s" % args.figure)
        return 0
    with open(args.inputs, encoding="utf-8") as fh:
        plan = json.load(fh)
    seq_path = os.path.join(os.path.dirname(os.path.abspath(args.inputs)),
                            "sequence.txt")
    with open(seq_path, encoding="utf-8") as fh:
        sequence = fh.read().strip()
    os.makedirs(args.out_dir, exist_ok=True)
    pin = provenance_pass(args.out_dir)
    record = compute.run_bio({"sequence": sequence,
                              "research_question": plan.get(
                                  "research_question")})
    params = record["parameters"]
    from collections import Counter as _Counter
    base_counts = dict(_Counter(sequence.strip().upper()))
    comparison = compute.compare_to_prereg(
        {"value": params["gc_fraction"], "metric": "gc_fraction"},
        {"expected_value": EXPECTED_FRAC, "tolerance": TOLERANCE,
         "metric": "gc_fraction"})
    result = {
        "cycle": CYCLE,
        "seed": SEED,
        "script": "run.py",
        "inputs": {"plan_file": os.path.relpath(args.inputs, HERE),
                   "plan_sha256": sha256_file(args.inputs),
                   "sequence_file": os.path.relpath(seq_path, HERE),
                   "sequence_sha256": sha256_file(seq_path),
                   "params": plan},
        "runner": "os/worlds/science-lab/compute.py run_bio",
        "observed_gc_fraction": params["gc_fraction"],
        "observed_gc_count": params["gc_count"],
        "observed_length": params["length"],
        "base_counts": base_counts,
        "expected_gc_fraction": EXPECTED_FRAC,
        "tolerance": TOLERANCE,
        "comparison": comparison,
        "record_text": record["execution_logs"][-1]
        if record.get("execution_logs") else "",
        "provenance": {
            "backend": "MCP-GATEWAY",
            "gateway": "boss local MCP gateway 127.0.0.1:8931",
            "calls": 2,
            "calls_file": "gateway-calls.jsonl",
            "payloads": ["gateway/search.json", "gateway/read.json"],
            "remote_tools": pin["remote_tools"],
            "payload_forms": [pin["search_payload_form"],
                              pin["read_payload_form"]],
            "wire_read_args": pin["wire_read_args"],
            "pinned": pin["pinned"],
            "pinned_identifiers": {
                "organism": ORGANISM,
                "usageKey": str(USAGE_KEY_INT),
            },
            "model_spend_usd": 0.0,
            "network": ("keyless public servers; no credentials held; "
                        "no model calls"),
        },
    }
    out = os.path.join(args.out_dir, "result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("gc_fraction=%.10f expected=%.10f tol=%g verdict=%s "
          "pinned=%s -> %s"
          % (result["observed_gc_fraction"], EXPECTED_FRAC, TOLERANCE,
             comparison["verdict"], pin["pinned"], out))
    return 0


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
    counts = result.get("base_counts", {})
    W, H = 640, 480
    ml, mr, mt, mb = 46, 14, 14, 60
    px = bytearray([255]) * (W * H * 3)
    plot_w = W - ml - mr
    bases = ["A", "C", "G", "T"]
    vals = [counts.get(b, 0) for b in bases]
    top = max(vals)
    cols = [(46, 139, 87), (30, 80, 180), (200, 120, 30), (150, 40, 40)]

    def dot(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            px[i:i + 3] = bytes(rgb)

    def line(x0, y0, x1, y1, rgb):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            dot(round(x0 + (x1 - x0) * s / steps),
                round(y0 + (y1 - y0) * s / steps), rgb)

    def rect(x0, y0, x1, y1, rgb):
        for x in range(x0, x1 + 1):
            line(x, y0, x, y1, rgb)

    plot_w = W - ml - mr
    plot_h = H - mt - mb
    bw = plot_w // (len(bases) * 2)
    for i, (b, v) in enumerate(zip(bases, vals)):
        x0 = ml + i * 2 * bw + bw // 2
        bh = round(v / top * plot_h) if top else 0
        rect(x0, H - mb - bh, x0 + bw, H - mb, cols[i])
    line(ml, mt, ml, H - mb, (0, 0, 0))
    line(ml, H - mb, W - mr, H - mb, (0, 0, 0))
    write_png(fig_path, W, H, px)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
