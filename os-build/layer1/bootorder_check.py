#!/usr/bin/env python3
"""B-L1-139 — Boot order data test.

The boot table lives in `services/supervisor/bootorder.goose` as data, and the supervisor
registers from it. That makes the table the single point of failure for the whole boot: one
forward reference and the machine hangs on service twelve, one duplicate order number and a
service is never started, one name off by a token and every log line names the wrong thing.

None of that can be caught by reading. This program reads the table and proves, mechanically:

  1. COUNT      the table has exactly `bo_count()` rows
  2. IDS        ids are 1..n, each exactly once
  3. ORDERS     order numbers are 1..n, each exactly once
  4. NAMES      the name table has n tokens, and token k is the name of id k
  5. DEPS       every dependency bit names an id that starts strictly earlier
  6. ACYCLIC    independent DFS over the edge set (does not trust check 5 to have been right)
  7. COVERAGE   every service directory with Goose source is either in the table or listed
                here explicitly as started later -- a silent omission is the failure mode

Usage:  python3 os-build/layer1/bootorder_check.py [--verbose]
Exit:   0 all checks pass, 1 a check failed, 2 the table could not be parsed.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")
BOOTORDER = os.path.join(SERVICES, "supervisor", "bootorder.goose")

ENTRY = re.compile(
    r"BootEntry\s*\{\s*id:\s*(\d+),\s*needs:\s*(\d+),\s*fatal:\s*(true|false),"
    r"\s*by_kernel:\s*(true|false),\s*order:\s*(\d+)\s*\}"
)
NAMES_LET = re.compile(r"let\s+BO_NAMES:[^=]*=\s*\"([^\"]*)\"", re.S)
COUNT_FN = re.compile(r"fn\s+bo_count\(\)\s*->\s*i64\s*\{\s*return\s+(\d+);")

# Services that exist in source but are not started by the boot sequence yet, with the reason.
# Listed here so the coverage check cannot be satisfied by forgetting one.
NOT_IN_BOOT = {
    "build": "not a service: build notes and tooling live here",
    "common": "libraries, linked into services; nothing to start",
    "tests": "test programs, started by hand or by the demo pack",
    "registry": "name->id lookup; folded into callmatrix in this build-out, see MANIFEST",
    "devmgr": "device inventory; devices + hotplug take its place at boot",
    "storage": "block contract; started by the layer that has a driver (B-L1-74)",
    "sockets": "socket contract; `socket` is the boot-table name for it",
    "fs": "filesystem; starts after the shell has something to show (B-L1-79..84)",
    "shell": "user surface; started by the session, not by the boot sequence",
    "example": "reference service; never started at boot",
}


def fail(msg):
    print("  FAIL  " + msg)
    return 1


def main(argv):
    verbose = "--verbose" in argv
    if not os.path.exists(BOOTORDER):
        print("cannot find %s" % BOOTORDER)
        return 2
    with open(BOOTORDER, "r", encoding="utf-8") as h:
        text = h.read()

    # Only the boot_table literal: the zero `BootEntry { id: 0, ... }` that bo_entry() returns
    # for an out-of-range index matches the same shape and is not a row of the table.
    start = text.find("var boot_table")
    end = text.find("];", start) if start >= 0 else -1
    if start < 0 or end < 0:
        print("cannot find the boot_table literal: the table format changed")
        return 2
    rows = ENTRY.findall(text[start:end])
    if not rows:
        print("no BootEntry rows parsed: the table format changed")
        return 2
    entries = [
        {"id": int(i), "needs": int(n), "fatal": f == "true", "by_kernel": k == "true", "order": int(o)}
        for (i, n, f, k, o) in [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    ]
    entries = sorted(entries, key=lambda e: e["id"])

    m = NAMES_LET.search(text)
    names = m.group(1).split() if m else []
    cm = COUNT_FN.search(text)
    declared_count = int(cm.group(1)) if cm else -1

    bad = 0
    n = len(entries)
    print("boot order data test")
    print("  parsed: %d rows, %d names, bo_count() = %d" % (n, len(names), declared_count))
    print("")

    # 1. COUNT
    if declared_count != n:
        bad += fail("COUNT: bo_count() says %d, the table has %d rows" % (declared_count, n))
    elif verbose:
        print("  ok    COUNT %d" % n)

    # 2. IDS
    ids = [e["id"] for e in entries]
    if ids != list(range(1, n + 1)):
        bad += fail("IDS: expected 1..%d, got %s" % (n, ids))
    elif verbose:
        print("  ok    IDS 1..%d" % n)

    # 3. ORDERS
    orders = sorted(e["order"] for e in entries)
    if orders != list(range(1, n + 1)):
        bad += fail("ORDERS: expected 1..%d each once, got %s" % (n, orders))
    elif verbose:
        print("  ok    ORDERS 1..%d each once" % n)

    # 4. NAMES -- token k (1-based) must be id k's name, because logs grep by id.
    if len(names) != n:
        bad += fail("NAMES: %d tokens for %d services" % (len(names), n))
    elif verbose:
        print("  ok    NAMES %d tokens" % n)
    id_to_name = {e["id"]: (names[e["id"] - 1] if 0 < e["id"] <= len(names) else "?") for e in entries}

    # 5. DEPS -- every set bit must be an earlier order.
    by_id = {e["id"]: e for e in entries}
    dep_ok = True
    for e in entries:
        bits = [b for b in range(1, n + 1) if e["needs"] & (1 << b)]
        for b in bits:
            if b not in by_id:
                bad += fail("DEPS: %s needs bit %d, which is not a service id" % (id_to_name[e["id"]], b))
                dep_ok = False
            elif by_id[b]["order"] >= e["order"]:
                bad += fail(
                    "DEPS: %s (order %d) needs %s (order %d), which starts later"
                    % (id_to_name[e["id"]], e["order"], id_to_name[b], by_id[b]["order"])
                )
                dep_ok = False
        if verbose and bits:
            print("       %-10s needs %s" % (id_to_name[e["id"]], " ".join(id_to_name[b] for b in bits)))
    if dep_ok and verbose:
        print("  ok    DEPS every dependency starts earlier")
    # Bits above n are silently ignored by a mask; say so rather than let them rot.
    for e in entries:
        stray = e["needs"] >> (n + 1)
        if stray:
            bad += fail("DEPS: %s carries bits above id %d (mask %d)" % (id_to_name[e["id"]], n, e["needs"]))

    # 6. ACYCLIC -- independent of check 5: DFS over dep -> dependent edges.
    edges = {i: [] for i in ids}
    for e in entries:
        for b in range(1, n + 1):
            if e["needs"] & (1 << b) and b in edges:
                edges[b].append(e["id"])
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {i: WHITE for i in ids}
    cycle = []

    def visit(node, path):
        colour[node] = GREY
        for nxt in edges[node]:
            if colour[nxt] == GREY:
                cycle.append(path + [node, nxt])
                return True
            if colour[nxt] == WHITE and visit(nxt, path + [node]):
                return True
        colour[node] = BLACK
        return False

    for i in ids:
        if colour[i] == WHITE and visit(i, []):
            break
    if cycle:
        bad += fail("ACYCLIC: cycle %s" % " -> ".join(id_to_name[i] for i in cycle[0]))
    elif verbose:
        print("  ok    ACYCLIC no dependency cycle")

    # 7. COVERAGE -- every service directory accounted for.
    on_disk = set()
    for name in sorted(os.listdir(SERVICES)):
        p = os.path.join(SERVICES, name)
        if not os.path.isdir(p) or name.startswith("."):
            continue
        if any(f.endswith(".goose") for f in os.listdir(p)):
            on_disk.add(name)
    named = set(names)
    unaccounted = sorted(d for d in on_disk if d not in named and d not in NOT_IN_BOOT)
    if unaccounted:
        bad += fail("COVERAGE: %s has source but is not in the boot table or NOT_IN_BOOT" % ", ".join(unaccounted))
    elif verbose:
        print("  ok    COVERAGE %d on-disk services, %d in the table, %d declared later"
              % (len(on_disk), len(named & on_disk), len(set(NOT_IN_BOOT) & on_disk)))
    phantom = sorted(named - on_disk)
    if phantom:
        bad += fail("COVERAGE: boot table names %s with no source directory" % ", ".join(phantom))

    print("")
    if bad:
        print("RESULT: %d finding(s)" % bad)
        return 1
    print("RESULT: boot order is consistent -- %d services, dependency order proven, no cycles" % n)
    print("NOT PROVEN: that the supervisor starts them in this order. That needs a boot log (B-L1-77).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
