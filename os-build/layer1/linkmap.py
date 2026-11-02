#!/usr/bin/env python3
"""B-L1-138 — link map round 2.

`LINK_MAP.md` round 1 was drawn by hand from `grep '^import'`. Waves G-J added 40-odd files
after it, so the map has to be regenerated, and the point of regenerating it mechanically is
that the DRIFT is then a fact rather than a memory: this program reads the sources, reads the
round-1 table out of `LINK_MAP.md`, and prints what changed.

What an import edge means here: `import <a>.<b>;` in `services/<dir>/<file>.goose`. Libraries
(`common.*`, `std`) are one bucket, services another -- a service importing a service is a
runtime dependency the call matrix has an opinion about, and a library import is a compile-time
copy with no permission check.

Usage:  python3 os-build/layer1/linkmap.py [--md]
Exit:   0 always (this is a map, not a linter -- the call matrix audit fails builds)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")
LINKMAP = os.path.join(HERE, "LINK_MAP.md")

IMPORT = re.compile(r"^import\s+([\w.]+);")
# Round-1 rows: | `svc` | `a`, `b` | note |
ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*([^|]+?)\s*\|")


def scan():
    """dir -> {"services": set, "libs": set, "files": int, "edges": [(mod, file)]}"""
    out = {}
    for d in sorted(os.listdir(SERVICES)):
        base = os.path.join(SERVICES, d)
        if not os.path.isdir(base):
            continue
        info = {"services": set(), "libs": set(), "files": 0, "edges": []}
        for f in sorted(os.listdir(base)):
            if not f.endswith(".goose"):
                continue
            info["files"] += 1
            with open(os.path.join(base, f), "r", encoding="utf-8", errors="replace") as h:
                for line in h:
                    m = IMPORT.match(line)
                    if not m:
                        continue
                    mod = m.group(1)
                    top = mod.split(".")[0]
                    info["edges"].append((mod, f))
                    if top in ("common", "std"):
                        info["libs"].add(mod if top == "common" else "std")
                    else:
                        info["services"].add(top)
        if info["files"]:
            out[d] = info
    return out


def round_one():
    """The service->library table from LINK_MAP.md round 1: svc -> set of import tokens."""
    if not os.path.exists(LINKMAP):
        return {}
    rows = {}
    with open(LINKMAP, "r", encoding="utf-8") as h:
        for line in h:
            m = ROW.match(line)
            if not m:
                continue
            svc, cell = m.group(1), m.group(2)
            toks = set(re.findall(r"`([\w.]+)`", cell))
            toks = {t for t in toks if "." in t or t == "std"}
            if toks:
                rows.setdefault(svc, set()).update(toks)
    return rows


def main(argv):
    found = scan()
    old = round_one()

    print("link map round 2")
    print("  services with source: %d   files: %d" % (len(found), sum(i["files"] for i in found.values())))
    print("")

    # The regenerated table: one line per service, libraries and services separated, because
    # they are different kinds of edge.
    for svc in sorted(found):
        libs = sorted(found[svc]["libs"])
        svcs = sorted(found[svc]["services"])
        if not libs and not svcs:
            continue
        print("  %-12s libs: %-40s svc: %s"
              % (svc, ", ".join(libs) or "-", ", ".join(svcs) or "-"))

    # Both kinds of edge: round 1's table mixed libraries and services in one cell, so a
    # comparison against libraries alone would report every service import as "removed".
    new = {s: found[s]["libs"] | {x + "." + x for x in found[s]["services"]} for s in found}
    only_now = sorted(set(new) - set(old))
    gone = sorted(set(old) - set(new))
    grew = []
    for s in sorted(set(new) & set(old)):
        added = sorted(new[s] - old[s])
        removed = sorted(old[s] - new[s])
        if added or removed:
            grew.append((s, added, removed))

    print("")
    print("DRIFT vs round 1")
    if only_now:
        print("  services new since round 1 (%d): %s" % (len(only_now), ", ".join(only_now)))
    if gone:
        print("  services gone since round 1: %s" % ", ".join(gone))
    for s, added, removed in grew:
        bits = []
        if added:
            bits.append("+ " + ", ".join(added))
        if removed:
            bits.append("- " + ", ".join(removed))
        print("  %-12s %s" % (s, "; ".join(bits)))
    if not (only_now or gone or grew):
        print("  none: every round-1 edge still holds and no service gained an import")

    # Service->service edges are the ones with a runtime meaning, so they get their own count.
    svc_edges = sum(len(found[s]["services"]) for s in found)
    print("")
    print("service->service edges: %d distinct across %d services" % (svc_edges, len(found)))
    print("NOTE: an import edge is not a permission. The call matrix decides that; "
          "see CALLMATRIX_DRIFT.md.")
    return 0


if __name__ == "__main__":
    code = main(sys.argv[1:])
    # `--write` refreshes the generated appendix in LINK_MAP.md, so the document's edge
    # tables cannot be older than the tree. The prose above the appendix is hand-written
    # on purpose: it is the argument for the shape of the graph, not a listing of it.
    if "--write" in sys.argv[1:]:
        import io
        import contextlib
        import datetime
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main([a for a in sys.argv[1:] if a != "--write"])
        body = buf.getvalue().rstrip()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LINK_MAP.md")
        with open(path, "r", encoding="utf-8") as h:
            text = h.read()
        marker = "## Appendix — the edge list, regenerated"
        head = text.split(marker)[0].rstrip()
        stamp = datetime.date.today().isoformat()
        with open(path, "w", encoding="utf-8") as h:
            h.write(head + "\n\n" + marker + " (" + stamp + ")\n\n```\n" + body + "\n```\n")
        print("wrote LINK_MAP.md appendix")
    sys.exit(code)
