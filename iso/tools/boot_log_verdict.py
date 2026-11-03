#!/usr/bin/env python3
"""boot_log_verdict — turn a MetaOS serial log into PASS/FAIL per marker.

The kernel's proof standard is a serial log. This reads one and says, line by
line, which of the six milestone markers are present, and whether the two
things that must never appear are absent.

    python3 iso/tools/boot_log_verdict.py <log> [--json]

Exit 0 when every row passes, 1 when any fails, 2 on bad usage.
This tool reads; it never writes to the log.
"""

import argparse
import json
import sys
from pathlib import Path

# Markers the kernel is expected to print. Key, needle, plain-English label.
PRESENT = [
    ("banner", "META OS", "banner printed"),
    ("alive", "META OS KERNEL - alive", "K1 alive line"),
    ("memory", "mem summary: K4 up", "K4 memory bring-up"),
    ("ring3", "HELLO FROM USERSPACE", "ring 3 program ran"),
    ("exit", "user exit code 0", "program exited clean"),
    ("fault", "task killed", "fault isolated to one task"),
    ("shell", "STATUS tasks=", "shell answered with live state"),
]

# Markers that must NOT appear.
ABSENT = [
    ("panic", "META OS KERNEL - panic", "no kernel panic"),
    ("refused", "loader refused", "no userspace program refused"),
]


def evaluate(text, extra=()):
    rows = []
    for key, needle, label in PRESENT:
        hit = needle in text
        rows.append({"key": key, "label": label, "kind": "present",
                     "status": "PASS" if hit else "FAIL",
                     "detail": "found" if hit else "missing: %r" % needle})
    for key, needle, label in list(ABSENT) + list(extra):
        absent = needle not in text
        rows.append({"key": key, "label": label, "kind": "absent",
                     "status": "PASS" if absent else "FAIL",
                     "detail": "absent" if absent else "found: %r" % needle})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(prog="boot_log_verdict")
    parser.add_argument("log")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.log)
    if not path.is_file():
        print("boot_log_verdict: no such log: %s" % path, file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    rows = evaluate(text)
    failed = [r for r in rows if r["status"] == "FAIL"]
    result = {
        "log": str(path),
        "bytes": path.stat().st_size,
        "lines": len(text.splitlines()),
        "ok": not failed,
        "rows": rows,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("log: %s (%d bytes, %d lines)" % (path, result["bytes"], result["lines"]))
        for row in rows:
            print("%-5s %-22s %s" % (row["status"], row["key"], row["detail"]))
        print()
        print("%d of %d passed" % (len(rows) - len(failed), len(rows)))
        if failed:
            print("verdict: FAIL — " + ", ".join(r["key"] for r in failed))
        else:
            print("verdict: PASS")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
