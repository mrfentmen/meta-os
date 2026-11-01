#!/usr/bin/env python3
"""Manifest writer (NC-180) + gap check (NC-181).
usage: python3 manifest.py <framesdir> <out.jsonl>
Emits one JSON object per frame (file, source, timestamp from the
-tSS.sss name, dhash, group id by hash). Re-running against a folder
with a deleted frame reports the gap (missing file vs manifest); it
never renumbers: group ids are content-derived (hash prefix).
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phash import dhash  # noqa: E402


def main(argv):
    if len(argv) < 2:
        print("usage: manifest.py <framesdir> <out.jsonl>")
        return 2
    framesdir, out = argv[0], argv[1]
    files = sorted(glob.glob(os.path.join(framesdir, "*.jpg")))
    lines = []
    if os.path.exists(out):
        old = {}
        for ln in open(out):
            ln = ln.strip()
            if ln:
                try:
                    r = json.loads(ln)
                    old[r["file"]] = r
                except (ValueError, KeyError):
                    pass
    else:
        old = {}
    for f in files:
        m = re.search(r"-t(\d+\.\d+)", os.path.basename(f))
        h = "%016x" % dhash(f)
        lines.append({"file": os.path.basename(f), "source": os.path.basename(framesdir),
                      "timestamp": float(m.group(1)) if m else None, "hash": h,
                      "group": h[:8]})
    if old:
        missing = [k for k in old if k not in {r["file"] for r in lines}]
        for k in missing:
            print("GAP: %s in manifest but not on disk" % k)
    with open(out, "w") as fh:
        fh.write("\n".join(json.dumps(r) for r in lines) + "\n")
    print("manifest %s: %d frames" % (out, len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
