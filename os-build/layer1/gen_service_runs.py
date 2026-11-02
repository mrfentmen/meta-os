#!/usr/bin/env python3
"""os-build/layer1/gen_service_runs.py -- keep SERVICE_RUNS.md's table honest.

The table in SERVICE_RUNS.md is the pass/fail record for the whole corpus, and it is
generated from `host/run_rows.txt` -- the row set `run_native.sh` writes on a FULL run.
It used to be hand-copied, which is how it came to say 27 drivers when there were 29 and
to carry a stale count for t65 after that test gained cases.

This rewrites two things in place and nothing else:

  1. the row block under `| Program | Status | pass | fail | First failure |`
  2. the bold summary paragraph that follows it (`**N of N drivers ...**`)

Everything else in the file, including the history section, is left alone. Run it after
`./os-build/layer1/run_native.sh` (no arguments -- a filtered run does not rewrite
run_rows.txt by design).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L1 = os.path.join(ROOT, "os-build", "layer1")
ROWS = os.path.join(L1, "host", "run_rows.txt")
DOC = os.path.join(L1, "SERVICE_RUNS.md")
DATE = "2026-11-02"
HEADER = "| Program | Status | pass | fail | First failure |"


def read_rows():
    if not os.path.exists(ROWS):
        sys.exit("run_rows.txt missing: run ./os-build/layer1/run_native.sh first")
    out = []
    with open(ROWS, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            while len(parts) < 5:
                parts.append("")
            out.append(parts)
    return out


def main():
    rows = read_rows()
    tests = [r for r in rows if r[0].startswith("tests/")]
    entries = [r for r in rows if r[0].startswith("entry/")]
    runs = [r for r in tests if r[1] == "RUNS"]
    checks = sum(int(r[2]) for r in runs if r[2].isdigit())
    fails = sum(int(r[3]) for r in tests if r[3].isdigit())
    built = [r for r in entries if r[1].startswith("BUILDS")]
    tc = [r for r in entries if r[1].startswith("TYPECHECKS")]

    lines = []
    for name, status, p, f, note in tests + entries:
        note = note if note else "—"
        bold = "**%s**" % status if status == "RUNS" else status
        lines.append("| `%s` | %s | %s | %s | %s |" % (name, bold, p or "0", f or "0", note))

    tc_clause = (
        "%d entry point **typechecks** and is not run: its `svc_entry` takes a kernel "
        "`BootInfo`, and a host has no boot block to hand it." % len(tc)
        if len(tc) == 1 else
        "%d entry points **typecheck** and are not run." % len(tc)
    )
    summary = (
        "**%d of %d drivers run to completion, all green: %d assertions passed, %d failed** "
        "(measured %s, `run_native.sh` exit 0). %d entry points **build** and are not run — "
        "they export `svc_entry`, and a host process has no supervisor to call it. %s"
        % (len(runs), len(tests), checks, fails, DATE, len(built), tc_clause)
    )

    with open(DOC, encoding="utf-8") as fh:
        doc = fh.read()

    if HEADER not in doc:
        sys.exit("SERVICE_RUNS.md: table header not found; refusing to guess")

    before, rest = doc.split(HEADER, 1)
    body_lines = rest.split("\n")
    # Walk past the blank line and the |---| separator that a markdown table needs, then
    # drop the old row block. (The first version started at index 1 and stopped on the
    # separator, so it prepended a second copy of the table instead of replacing it.)
    i = 0
    while i < len(body_lines) and body_lines[i].strip() in ("",) + tuple():
        i += 1
    if i < len(body_lines) and body_lines[i].lstrip().startswith("|-"):
        i += 1
    while i < len(body_lines) and body_lines[i].startswith("| "):
        i += 1
    tail = body_lines[i:]

    # Replace the bold summary paragraph if it is still the generated one.
    joined = "\n".join(tail)
    joined = re.sub(
        r"\*\*\d+ of \d+ drivers run to completion.*?(?=\n\n)",
        summary.replace("\\", "\\\\"),
        joined,
        count=1,
        flags=re.S,
    )

    out = (before + HEADER + "\n" + "|" + "---|" * 5 + "\n"
           + "\n".join(lines) + "\n" + joined)
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("SERVICE_RUNS.md: %d rows (%d RUNS, %d checks, %d failed)"
          % (len(tests) + len(entries), len(runs), checks, fails))
    return 0


if __name__ == "__main__":
    sys.exit(main())
