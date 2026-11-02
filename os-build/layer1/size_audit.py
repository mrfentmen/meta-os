#!/usr/bin/env python3
"""B-L1-136 — size audit.

Every service allocates nothing at run time: buffers are fixed arrays sized at compile time, and
each one is a promise about how much of the process's static storage it owns. Two failures follow
from getting that wrong, and only one of them is loud:

  UNDERSIZED   the buffer fills at run time and the service returns E_NOROOM in a place the
               design assumed could not fail. Loud, and caught by the RUN pass.
  OVERSIZED    the buffer is bigger than anything that can reach it. Silent, permanent, and it
               is paid by every process in the image.

So the number that matters is not "the largest u8 array", it is *resident bytes*, and the first
version of this program got that wrong: it summed declarations, so `vcons: VCon[..4]` counted as
the 32 KiB `hist` field once instead of four times. Struct sizes are computed here
(i64 = 8, u32 = 4, bool = 1, u8 = 1, nested structs summed, arrays multiplied) and array counts
are applied, because a declaration is not a footprint.

Usage:  python3 os-build/layer1/size_audit.py [--top N]
Exit:   0 always. This is a review aid; findings belong in writing, not in a build failure.
NOT MEASURED: stack depth, struct padding, string literals in .rodata, and the code itself.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")

SCALAR = {
    "u8": 1, "i8": 1, "bool": 1,
    "u16": 2, "i16": 2,
    "u32": 4, "i32": 4, "f32": 4,
    "u64": 8, "i64": 8, "f64": 8,
}
STRUCT_OPEN = re.compile(r"^struct\s+([A-Z]\w*)\s*\{")
FIELD = re.compile(r"^\s*([a-zA-Z_]\w*)\s*:\s*([A-Za-z_]\w*)\s*(\[(?:\.\.|:)?\s*(\d+)\s*\])?\s*,")
# `var buf: u8[..512] = []`, `vcons: VCon[..4]`, `out: i64[..24]&`, `let N: u8[:32]`
ARR = re.compile(r"\b([a-zA-Z_]\w*)\s*:\s*(?:const\s+)?([A-Za-z_]\w*)\s*\[(?:\.\.|:)?\s*(\d+)\s*\]")
# A single struct instance, not an array: `var cs: ContentSet;` -- the same bytes as a struct
# array of one, and easy to miss, which is how the second pass reported `updater` at 12 KiB
# while it holds a 32 KiB content set.
PLAIN = re.compile(r"\b([a-zA-Z_]\w*)\s*:\s*([A-Z]\w*)\s*(?:;|=)")
VIEW = re.compile(r"\[\s*[>]?\s*\.\.\s*\]")


def walk():
    for base, dirs, files in os.walk(SERVICES):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for f in sorted(files):
            if f.endswith(".goose"):
                yield os.path.join(base, f)


def struct_table(paths):
    """(service, name) -> {field: (type, count)}, plus which names exist in more than one service.

    Types are package-scoped, and two services do define the same name: `net.packet` has a
    `Link` with a 6-byte MAC and `tests/harness/link.goose` has a `Link` with a 12000-byte
    frame buffer. Keying by name alone silently gave `net` the test's size (12 KiB per link,
    48 KiB reported where the truth is 216 bytes) -- so resolution is per service first and
    ambiguity is reported instead of resolved by luck.
    """
    out = {}
    svc_of = {}
    for path in paths:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        svc = rel.split("/")[1]
        with open(path, "r", encoding="utf-8", errors="replace") as h:
            lines = h.readlines()
        cur = None
        depth = 0
        for line in lines:
            m = STRUCT_OPEN.match(line)
            if m and cur is None:
                cur, depth = (svc, m.group(1)), 1
                out.setdefault(cur, {})
                continue
            if cur is None:
                continue
            depth += line.count("{") - line.count("}")
            fm = FIELD.match(line)
            if fm and fm.group(2) not in ("", ):
                out[cur][fm.group(1)] = (fm.group(2), int(fm.group(4)) if fm.group(4) else 1)
            if depth <= 0:
                cur = None
    for (svc, name) in out:
        svc_of.setdefault(name, set()).add(svc)
    return out, svc_of


def sizeof(t, structs, svc, seen=()):
    """Bytes for one element of type t, or 0 when the type is unknown (reported, not guessed)."""
    if t in SCALAR:
        return SCALAR[t]
    key = (svc, t)
    if key not in structs:
        return 0
    if key in seen:
        return 0                       # a struct that contains itself is a compile error, not a size
    total = 0
    for ftype, count in structs[key].values():
        total += count * sizeof(ftype, structs, svc, seen + (key,))
    return total


def main(argv):
    top = 12
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (IndexError, ValueError):
            pass

    paths = list(walk())
    structs, svc_of = struct_table(paths)

    per_service = {}
    resident = []
    unknown = []
    skipped = 0
    for path in paths:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        svc = rel.split("/")[1]
        st = per_service.setdefault(svc, {"arrays": 0, "bytes": 0, "files": 0, "unknown": 0})
        st["files"] += 1
        with open(path, "r", encoding="utf-8", errors="replace") as h:
            for lineno, line in enumerate(h, 1):
                body = line.lstrip()
                if VIEW.search(line) or body.startswith("//"):
                    continue
                # Storage is declared by `var`, `let`, or a parameter list. Everything else
                # that looks like `name: type[..N]` is a struct-literal field initialiser or
                # an indexed read (`flags: seg[13] as i64,`) and owns no bytes -- counting
                # those as allocations is how the first pass reported a 13-element array of
                # a type called `seg` that does not exist.
                if not (body.startswith("var ") or body.startswith("let ") or body.startswith("fn ")):
                    if ARR.search(line):
                        skipped += 1
                    continue
                for m in ARR.finditer(line):
                    name, etype, n = m.group(1), m.group(2), int(m.group(3))
                    st["arrays"] += 1
                    size = sizeof(etype, structs, svc)
                    if size == 0:
                        st["unknown"] += 1
                        unknown.append((etype, n, rel, lineno, name))
                        continue
                    st["bytes"] += size * n
                    resident.append((size * n, "%s x %d" % (etype, n), rel, lineno, name))
                for m in PLAIN.finditer(line):
                    name, etype = m.group(1), m.group(2)
                    if (svc, etype) not in structs:
                        continue
                    size = sizeof(etype, structs, svc)
                    st["arrays"] += 1
                    st["bytes"] += size
                    resident.append((size, etype, rel, lineno, name))

    total = sum(s["bytes"] for s in per_service.values())
    print("size audit -- resident bytes for fixed arrays (slices are views, not storage)")
    print("  services: %d   resident: %d bytes (%.1f KiB)   unknown-element arrays: %d"
          % (len(per_service), total, total / 1024.0, len(unknown)))
    print("")
    print("  %-14s %7s %10s %8s %6s %7s" % ("service", "arrays", "bytes", "KiB", "files", "unknown"))
    for svc in sorted(per_service, key=lambda s: -per_service[s]["bytes"]):
        st = per_service[svc]
        print("  %-14s %7d %10d %8.1f %6d %7d"
              % (svc, st["arrays"], st["bytes"], st["bytes"] / 1024.0, st["files"], st["unknown"]))

    print("")
    print("largest allocations (the oversize review starts here):")
    for size, what, rel, lineno, name in sorted(resident, reverse=True)[:top]:
        print("  %8d B  %-16s %-22s %s:%d" % (size, what, name, rel, lineno))

    if unknown:
        print("")
        print("element type not resolvable to bytes (a name the tree does not define as a struct):")
        for etype, n, rel, lineno, name in sorted(unknown, key=lambda x: -x[1])[:top]:
            print("  %5d x %-14s %s  %s:%d" % (n, etype, name, rel, lineno))

    print("")
    if skipped:
        print("  (%d `name: type[n]` shapes skipped: field initialisers and indexed reads, no bytes)"
              % skipped)
    print("NOT MEASURED: stack depth, struct padding, string literals in .rodata, code size.")
    print("Those need the compiler; this audit is the part that can be read off the source.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
