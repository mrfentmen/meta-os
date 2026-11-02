#!/usr/bin/env python3
"""B-L1-118 — Call-matrix auditor.

Walks the permission matrix in services/callmatrix/callmatrix.goose against the edges that
actually exist in the sources, and reports drift in both directions:

  MISSING   a service imports another service's module, but the matrix does not allow the
            call. This is the drift that breaks a boot: the code compiles, the registry
            denies, and the failure shows up as "service did not start".
  DORMANT   the matrix allows a call that no source makes. Not an error -- a permission
            kept for a restart path is legitimate -- but it is the list to read when asking
            "who can reach the audit log".
  UNKNOWN   an id in the matrix with no service directory, or the reverse.

Scope, stated: only cross-SERVICE imports are edges. `common.*` is a library and is
deliberately outside the matrix; anything else under services/ is a service.

Usage:
    python3 os-build/layer1/callmatrix_audit.py            # report, exit 1 on MISSING only
    python3 os-build/layer1/callmatrix_audit.py --all      # also exit 1 on DORMANT (strict)

Exit codes: 0 clean (or informational drift only), 1 drift found, 2 the inputs could not be
parsed -- which is itself a finding, because a matrix that cannot be read is a matrix that
is not enforcing anything.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MATRIX = os.path.join(ROOT, "services", "callmatrix", "callmatrix.goose")
SERVICES = os.path.join(ROOT, "services")

LIBRARY_DIRS = {"common", "tests", "build"}
# The matrix names services by CONCEPT, the tree names directories by MODULE. These are the
# pairs that differ; everything else must match exactly, because a lookup table that "fixes"
# names silently is a table that hides a rename.
ALIASES = {"log": "logd"}
# Not services: the example is a template for future services, and callmatrix is this table.
NOT_SERVICES = {"example", "callmatrix"}


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_matrix(text):
    """Return (ids_by_name, rows) where rows maps caller name -> set of callee names."""
    ids = {}
    for name, num in re.findall(r"^let SVC_([A-Z0-9_]+): i64 = (\d+);", text, re.M):
        if name in ("NONE", "COUNT"):
            continue
        ids[name.lower()] = int(num)
    by_id = {v: k for k, v in ids.items()}

    rows = {}
    for block in re.findall(r"cm_set\((.*?)\);", text, re.S):
        flat = " ".join(block.split())
        caller = re.match(r"SVC_([A-Z0-9_]+)", flat)
        if not caller:
            continue
        caller_name = caller.group(1).lower()
        allowed = set()
        for callee in re.findall(r"cm_bit\(SVC_([A-Z0-9_]+)\)", flat):
            allowed.add(callee.lower())
        rows[caller_name] = allowed

    count = re.search(r"let SVC_COUNT: i64 = (\d+);", text)
    declared = int(count.group(1)) if count else 0
    return ids, by_id, rows, declared


def service_dirs():
    out = {}
    for entry in sorted(os.listdir(SERVICES)):
        path = os.path.join(SERVICES, entry)
        if not os.path.isdir(path) or entry in LIBRARY_DIRS:
            continue
        if not any(f.endswith(".goose") for f in os.listdir(path)):
            continue
        out[entry] = path
    return out


def source_edges(dirs):
    """service -> set of other services it imports a module from."""
    edges = {}
    for name, path in dirs.items():
        found = set()
        for fname in sorted(os.listdir(path)):
            if not fname.endswith(".goose"):
                continue
            text = read(os.path.join(path, fname))
            for module in re.findall(r"^import ([A-Za-z0-9_]+)\.([A-Za-z0-9_]+);", text, re.M):
                target = module[0]
                if target == name or target in LIBRARY_DIRS:
                    continue
                found.add(target)
        edges[name] = found
    return edges


def canon(name):
    """A matrix name to the directory name, through the declared aliases and nothing else."""
    return ALIASES.get(name, name)


def main(argv):
    strict = "--all" in argv
    for path in (MATRIX, SERVICES):
        if not os.path.exists(path):
            print("cannot find %s" % path)
            return 2

    ids, by_id, rows, declared = parse_matrix(read(MATRIX))
    if not ids or not rows or declared == 0:
        print("matrix parsed as empty (ids=%d rows=%d count=%d)" % (len(ids), len(rows), declared))
        return 2

    # Compare in DIRECTORY names on both sides. Without this the alias is decorative: the
    # matrix says `log`, the tree says `logd`, and every edge to the log service showed up
    # twice -- once as a missing permission and once as a dormant one. The round-1 audit did
    # exactly that for all 24 callers, which is why its dormant count was 65.
    rows = {canon(caller): {canon(c) for c in callees} for caller, callees in rows.items()}

    dirs = service_dirs()
    edges = source_edges(dirs)

    problems = 0
    print("call-matrix audit  (%d services in the matrix, %d with sources)" % (declared, len(dirs)))
    print("")

    # 1. MISSING -- a real edge with no permission.
    missing = []
    for caller in sorted(edges):
        for callee in sorted(edges[caller]):
            allowed = rows.get(caller, set())
            if callee not in allowed:
                missing.append((caller, callee))
    if missing:
        problems += len(missing)
        print("MISSING permission (%d):" % len(missing))
        for caller, callee in missing:
            print("  %-12s -> %-12s imports %s.%s but the matrix denies it"
                  % (caller, callee, callee, callee))
        print("")

    # 2. DORMANT -- permission with no edge.
    dormant = []
    for caller in sorted(rows):
        for callee in sorted(rows[caller]):
            if callee not in edges.get(caller, set()):
                dormant.append((caller, callee))
    if dormant:
        print("DORMANT permission (%d, informational):" % len(dormant))
        for caller, callee in dormant:
            print("  %-12s -> %-12s allowed, not called from a source" % (caller, callee))
        print("")

    # 3. UNKNOWN -- id/directory mismatch.
    matrix_names = set(ids)
    unmatched = []
    resolved = {ALIASES.get(n, n) for n in matrix_names}
    for name in sorted(matrix_names):
        target = ALIASES.get(name, name)
        if target not in dirs and name not in NOT_SERVICES:
            unmatched.append(("matrix", name))
    for name in sorted(dirs):
        if name in NOT_SERVICES:
            continue
        if name not in resolved:
            unmatched.append(("source", name))
    if unmatched:
        problems += len(unmatched)
        print("UNKNOWN (%d):" % len(unmatched))
        for side, name in unmatched:
            print("  in %s only: %s" % (side, name))
        print("")

    # 4. Self-consistency: ids contiguous from 1, count matches.
    nums = sorted(ids.values())
    if nums != list(range(1, len(nums) + 1)):
        print("matrix ids are not contiguous from 1: %s" % nums)
        problems += 1
    if len(nums) != declared:
        print("SVC_COUNT is %d but %d ids are defined" % (declared, len(nums)))
        problems += 1

    if problems == 0 and not dormant:
        print("clean: no missing permissions, no dormant rows, no unknown services")
        return 0
    if problems == 0 and dormant and not strict:
        print("clean on permissions; %d dormant row(s) reported above" % len(dormant))
        return 0
    if problems > 0:
        print("drift: %d problem(s)" % problems)
        return 1
    print("strict mode: %d dormant row(s)" % len(dormant))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
