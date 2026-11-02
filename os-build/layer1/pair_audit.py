#!/usr/bin/env python3
"""R13-076..100 — pair audit: does each named caller->callee pair exist?

The Round 13 task list names 25 pairs and asks for a pair contract plus a run
with exit codes for both sides. A pair has three independent facts, and the
audit reports all three rather than collapsing them:

  BOOTABLE   the directory is a service (it ships entry.goose exporting svc_entry)
  IMPORTS    the caller's sources import the callee's module
  MATRIX     services/callmatrix/callmatrix.goose allows caller -> callee

A pair is an EDGE only when IMPORTS and MATRIX are both true. Matrix-allowed
without an import is DORMANT (a declared permission no code uses). Everything
else is DENIED, and that is a finding about the task list, not a pass: the
list named a pair the OS does not have.

Usage:
    python3 os-build/layer1/pair_audit.py            # table, exit 0 always (audit)
    python3 os-build/layer1/pair_audit.py --json     # machine-readable
    python3 os-build/layer1/pair_audit.py --strict   # exit 1 if any pair is not an EDGE
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")
MATRIX = os.path.join(SERVICES, "callmatrix", "callmatrix.goose")
ALIASES = {"log": "logd"}

PAIRS = [
    ("R13-076", "agenthost", "display"),
    ("R13-077", "audit", "dns"),
    ("R13-078", "board", "dock"),
    ("R13-079", "bootlog", "echo"),
    ("R13-080", "build", "fs"),
    ("R13-081", "callmatrix", "heartbeat"),
    ("R13-082", "console", "input"),
    ("R13-083", "dashboard", "logd"),
    ("R13-084", "devices", "logfmt"),
    ("R13-085", "devmgr", "mcp-host"),
    ("R13-086", "dhcp", "net"),
    ("R13-087", "display", "netcfg"),
    ("R13-088", "dns", "notify"),
    ("R13-089", "dock", "registry"),
    ("R13-090", "echo", "session"),
    ("R13-091", "fs", "settings"),
    ("R13-092", "heartbeat", "shell"),
    ("R13-093", "input", "socket"),
    ("R13-094", "logd", "sockets"),
    ("R13-095", "logfmt", "storage"),
    ("R13-096", "mcp-host", "supervisor"),
    ("R13-097", "net", "time"),
    ("R13-098", "netcfg", "timesync"),
    ("R13-099", "notify", "updater"),
    ("R13-100", "registry", "wallpaper"),
]


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_matrix(text):
    ids = {}
    for name, num in re.findall(r"^let SVC_([A-Z0-9_]+): i64 = (\d+);", text, re.M):
        if name in ("NONE", "COUNT"):
            continue
        ids[name.lower()] = int(num)
    rows = {}
    for block in re.findall(r"cm_set\((.*?)\);", text, re.S):
        flat = " ".join(block.split())
        caller = re.match(r"SVC_([A-Z0-9_]+)", flat)
        if not caller:
            continue
        rows[caller.group(1).lower()] = {
            callee.lower() for callee in re.findall(r"cm_bit\(SVC_([A-Z0-9_]+)\)", flat)
        }
    return ids, rows


def canonical(name):
    return ALIASES.get(name, name)


def bootable(name):
    entry = os.path.join(SERVICES, name, "entry.goose")
    if not os.path.isfile(entry):
        return False
    return 'export "svc_entry"' in read(entry)


def imports(module, service):
    """True when any file in services/<module>/ imports services/<service>/'s module."""
    directory = os.path.join(SERVICES, module)
    if not os.path.isdir(directory):
        return False
    needle = re.compile(r"^\s*import\s+%s\s*[.;]" % re.escape(canonical(service)), re.M)
    for base in sorted(os.listdir(directory)):
        if not base.endswith(".goose"):
            continue
        if needle.search(read(os.path.join(directory, base))):
            return True
    return False


def main():
    text = read(MATRIX)
    ids, rows = parse_matrix(text)
    out = []
    for task, caller, callee in PAIRS:
        caller_row = rows.get(canonical(caller), set())
        callee_key = canonical(callee)
        matrix = callee_key in caller_row or (caller == callee and caller in rows)
        rec = {
            "task": task,
            "caller": caller,
            "callee": callee,
            "caller_bootable": bootable(caller),
            "callee_bootable": bootable(callee),
            "caller_known": canonical(caller) in rows,
            "callee_id": ids.get(callee_key),
            "imports": imports(caller, callee),
            "matrix_allows": matrix,
        }
        if not (rec["caller_bootable"] and rec["callee_bootable"]):
            rec["verdict"] = "NOT_A_SERVICE"
        elif rec["matrix_allows"] and rec["imports"]:
            rec["verdict"] = "EDGE"
        elif rec["matrix_allows"]:
            rec["verdict"] = "DORMANT"
        else:
            rec["verdict"] = "DENIED"
        out.append(rec)

    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
    else:
        print("%-9s %-12s %-12s %-14s %-8s %-8s %s"
              % ("task", "caller", "callee", "verdict", "import", "matrix", "bootable"))
        for rec in out:
            print("%-9s %-12s %-12s %-14s %-8s %-8s %s/%s" % (
                rec["task"], rec["caller"], rec["callee"], rec["verdict"],
                "yes" if rec["imports"] else "no",
                "ALLOW" if rec["matrix_allows"] else "DENY",
                "y" if rec["caller_bootable"] else "n",
                "y" if rec["callee_bootable"] else "n"))
        counts = {}
        for rec in out:
            counts[rec["verdict"]] = counts.get(rec["verdict"], 0) + 1
        print("\ntotal=%d %s" % (len(out), " ".join(
            "%s=%d" % (k, counts[k]) for k in sorted(counts))))

    if "--strict" in sys.argv and any(r["verdict"] != "EDGE" for r in out):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
