#!/usr/bin/env python3
"""Every userspace bin has exactly one base, and every base has a bin.

Why this exists: on 2026-11-02 `bases.txt` carried slots for 8 of 32 bins.
`build.sh` silently built only the listed eight, so five sixths of the corpus
was never compiled and nothing failed. `verify_bases.py` can only check the
bins it is handed; it cannot see a bin that has no slot at all.

This is the cheap check that closes that class before the expensive build:

  * a source bin with no slot        -> FAIL (it would never be built)
  * a slot with no source bin        -> FAIL (stale manifest hides intent)
  * two names sharing one base       -> FAIL (the loader's `address in use`)
  * a base outside USER_FLOOR..CEIL  -> FAIL (cannot be mapped in ring 3)
  * a duplicate name                 -> FAIL

It does not check images or overlaps; `verify_bases.py` reads ELF headers for
that. Run this first, then build, then verify.

Usage: check_manifest.py [--bases bases.txt] [--bin-dir user/src/bin]
"""

import argparse
import os
import sys

USER_FLOOR = 0x0000_4000_0000_0000
USER_CEIL = 0x0000_7FFF_FFFF_FFFF

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASES = os.path.join(HERE, "bases.txt")
DEFAULT_BIN_DIR = os.path.join(HERE, "user", "src", "bin")


def load_bases(path):
    entries = []
    seen_names = set()
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                entries.append((parts[0] if parts else f"line{lineno}", None, lineno))
                continue
            name = parts[0]
            if name in seen_names:
                entries.append((name, None, lineno))
            seen_names.add(name)
            try:
                entries.append((name, int(parts[1], 16), lineno))
            except ValueError:
                entries.append((name, None, lineno))
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description="bases.txt vs src/bin coverage")
    ap.add_argument("--bases", default=DEFAULT_BASES)
    ap.add_argument("--bin-dir", default=DEFAULT_BIN_DIR)
    args = ap.parse_args(argv)

    if not os.path.exists(args.bases):
        print(f"FAIL: no manifest at {args.bases}")
        return 1
    if not os.path.isdir(args.bin_dir):
        print(f"FAIL: no bin directory at {args.bin_dir}")
        return 1

    bins = sorted(f[:-3] for f in os.listdir(args.bin_dir) if f.endswith(".rs"))
    entries = load_bases(args.bases)
    by_name = {}
    problems = []

    for name, value, lineno in entries:
        if name in by_name:
            problems.append(f"{name}: listed twice (line {lineno})")
            continue
        if value is None:
            problems.append(f"{name}: line {lineno} has no parseable hex base")
            continue
        by_name[name] = value

    for name in bins:
        if name not in by_name:
            problems.append(f"{name}: source exists, NO BASE (it would never be built)")
    for name in sorted(by_name):
        if name not in bins:
            problems.append(f"{name}: base exists, no source at {args.bin_dir}/{name}.rs")

    by_value = {}
    for name, value in by_name.items():
        by_value.setdefault(value, []).append(name)
    for value, names in sorted(by_value.items()):
        if len(names) > 1:
            problems.append(f"base {value:#016x} shared by {', '.join(sorted(names))}")
        if value < USER_FLOOR or value > USER_CEIL:
            problems.append(f"{names[0]}: base {value:#016x} outside userspace")

    print(f"{len(bins)} source bins, {len(by_name)} manifest slots")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"\n{len(problems)} problem(s) — fix bases.txt before building")
        return 1
    print("coverage: every bin has one slot, every slot has a bin, no base reused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
