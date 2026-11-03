#!/usr/bin/env python3
"""Verify that userspace ELFs occupy disjoint address ranges.

The kernel maps each program at its linked address and refuses a page that is
already mapped. Two programs sharing a base is therefore a boot failure, not a
cosmetic issue. This reads the real ELF headers (entry + PT_LOAD ranges) and
fails on overlap, on a base below the userspace floor, or on a missing file.

No pyelftools: the ELF64 header and program headers are fixed-layout, and this
check runs on a machine with only python3.

Usage:
  verify_bases.py --bases bases.txt --dir target/x86_64-unknown-none/release [bins...]
"""

import argparse
import os
import struct
import sys

USER_FLOOR = 0x0000_4000_0000_0000
USER_CEIL = 0x0000_7FFF_FFFF_FFFF


def read_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF")
    if data[4] != 2:
        raise ValueError("not ELF64")
    (e_type, e_machine, _version, e_entry, e_phoff, _shoff, _flags,
     _ehsize, e_phentsize, e_phnum, *_rest) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, _align = \
            struct.unpack_from("<IIQQQQQQ", data, off)
        if p_type == 1 and p_memsz:  # PT_LOAD
            segments.append({
                "vaddr": p_vaddr,
                "start": p_vaddr & ~0xFFF,
                "end": (p_vaddr + p_memsz + 0xFFF) & ~0xFFF,
                "flags": p_flags,
                "filesz": p_filesz,
                "memsz": p_memsz,
            })
    return {"entry": e_entry, "type": e_type, "machine": e_machine, "segments": segments}


def load_bases(path):
    bases = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                bases[parts[0]] = int(parts[1], 16)
    return bases


def main(argv=None):
    ap = argparse.ArgumentParser(description="check userspace ELF base overlap")
    ap.add_argument("--bases", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("bins", nargs="*")
    args = ap.parse_args(argv)

    bases = load_bases(args.bases)
    bins = args.bins or sorted(bases)
    failures = []
    rows = []

    for name in bins:
        path = os.path.join(args.dir, name)
        if not os.path.exists(path):
            failures.append(f"{name}: missing at {path}")
            continue
        try:
            elf = read_elf(path)
        except ValueError as exc:
            failures.append(f"{name}: {exc}")
            continue
        want = bases.get(name)
        if want is None:
            failures.append(f"{name}: no base in {args.bases}")
            continue
        lo = min(s["start"] for s in elf["segments"])
        hi = max(s["end"] for s in elf["segments"])
        if lo < USER_FLOOR or hi > USER_CEIL:
            failures.append(f"{name}: range {lo:#x}-{hi:#x} outside userspace")
        if lo != want:
            failures.append(
                f"{name}: linked at {lo:#x}, manifest says {want:#x} "
                f"(the -T/--defsym flags did not reach the linker)"
            )
        if elf["entry"] < lo or elf["entry"] >= hi:
            failures.append(f"{name}: entry {elf['entry']:#x} outside its own image")
        rows.append((name, elf["entry"], lo, hi, len(elf["segments"])))

    # Pairwise overlap: the kernel's hard refusal, checked before boot.
    spans = sorted(((lo, hi, name) for name, _e, lo, hi, _n in rows))
    for i in range(1, len(spans)):
        prev_lo, prev_hi, prev_name = spans[i - 1]
        lo, hi, name = spans[i]
        if lo < prev_hi:
            failures.append(f"OVERLAP: {prev_name} {prev_lo:#x}-{prev_hi:#x} and {name} {lo:#x}-{hi:#x}")

    if rows:
        print(f"{'bin':<12} {'entry':>18} {'image':>36} segs")
        for name, entry, lo, hi, n in rows:
            print(f"{name:<12} {entry:#18x} {lo:#x}-{hi:#x} {n:>4}")
    print()
    if failures:
        for f in failures:
            print(f"FAIL {f}")
        print(f"\n{len(failures)} failure(s) — these programs would not all load")
        return 1
    print(f"{len(rows)} program(s): disjoint, at their manifest bases, entries inside images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
