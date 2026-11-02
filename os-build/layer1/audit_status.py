#!/usr/bin/env python3
"""os-build/layer1/audit_status.py -- BF4-18: re-measure every status word.

Each source file in `services/` opens with a `Status:` line. Those lines were
written before anything compiled, so most of them say "WRITTEN (not COMPILED,
not RUN)" — a claim that was true when it was typed and is false now.

This script measures instead: a test that ran is RUNS with its check count, and a
module is RUNS if a passing test imports it, otherwise WRITTEN. `--fix` rewrites
the line. Without `--fix` it only reports, which is what the audit pass needs:
the mismatch list is the finding.

Usage:
  audit_status.py          report
  audit_status.py --fix    rewrite the Status line in each file with a mismatch
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_services as gs  # noqa: E402  (same directory, shared import resolver)

ROOT = gs.ROOT
SERVICES = gs.SERVICES
STATUS = re.compile(r"^// Status:.*$", re.M)
DATE = "2026-11-02"


def rows():
    return gs.read_rows()


def test_closures():
    """test name -> set of service-relative files it can reach."""
    out = {}
    tdir = os.path.join(SERVICES, "tests")
    for f in sorted(os.listdir(tdir)):
        if not f.endswith(".goose"):
            continue
        name = f[:-6]
        out[name] = gs.closure(["tests/" + f])
    return out


def measured(path_rel, run_rows, closures):
    """(status word, evidence) for a services-relative file."""
    if path_rel.startswith("tests/"):
        name = path_rel[:-6].split("/")[-1]
        row = run_rows.get("tests/" + name)
        if row and row[0] == "RUNS":
            return "RUNS", "%s: %d checks, 0 failures" % ("tests/" + name, row[1])
        if row:
            return row[0], "%s: %d failed" % ("tests/" + name, row[2])
        return "WRITTEN", "no native run row"
    best = None
    for tname, files in closures.items():
        if path_rel not in files:
            continue
        row = run_rows.get("tests/" + tname)
        if row and row[0] == "RUNS" and (best is None or row[1] > best[1]):
            best = ("tests/" + tname, row[1])
    if best:
        return "RUNS", "reached by %s (%d checks, exit 0)" % best
    return "WRITTEN", "no passing test reaches it"


def main():
    fix = "--fix" in sys.argv[1:]
    run_rows = rows()
    closures = test_closures()
    mismatches = []
    checked = 0

    for base, _dirs, files in os.walk(SERVICES):
        for f in sorted(files):
            if not f.endswith(".goose") or f.startswith("."):
                continue
            path = os.path.join(base, f)
            rel = os.path.relpath(path, SERVICES)
            text = open(path, encoding="utf-8").read()
            m = STATUS.search(text)
            if not m:
                continue
            checked += 1
            old = m.group(0)
            word, why = measured(rel, run_rows, closures)
            # Keep whatever followed the old status claim: those sentences are the
            # caveats ("this cannot prove crash safety", "runs at K6, not before"), and
            # deleting them to update a status word would be the audit destroying the
            # thing it is auditing.
            body = old[len("// Status: "):]
            dot = body.find(".")
            tail = body[dot + 1:] if dot >= 0 else ""
            new = "// Status: %s — %s. Measured %s by audit_status.py.%s" % (word, why, DATE, tail)

            # A file already carrying the measured word is not a finding.
            stale = word == "RUNS" and ("not RUN" in old or "not COMPILED" in old or "WRITTEN" in old)
            if word == "WRITTEN" and "WRITTEN" in old:
                stale = False
            if not stale:
                continue
            mismatches.append((rel, old.strip(), new))
            if fix:
                text = STATUS.sub(lambda _m: new, text, count=1)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)

    print("status lines checked: %d, stale: %d" % (checked, len(mismatches)))
    for rel, old, new in mismatches:
        print("  %-40s %s" % (rel, old[10:70]))
        if fix:
            print("  %-40s -> %s" % ("", new[10:]))
    if mismatches and not fix:
        print("\nrun with --fix to rewrite them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
