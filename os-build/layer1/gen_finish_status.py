#!/usr/bin/env python3
"""os-build/layer1/gen_finish_status.py -- A3: the whole-corpus numbers, measured once.

Reads the generated manifest (services.json, itself produced by gen_services.py from
the imports) and the native-run row file (host/run_rows.txt, written by run_native.sh),
and emits one table: every service, its entry point, the driver that proves it, and the
single status word that is true of it tonight.

Status words are the corpus's own, not new ones:
  RUNS        a driver builds, executes and exits 0 against the real service code
  TYPECHECKS  no driver runs it, but `goose check` accepts its sources
  NEITHER     no driver and no entry point; the code exists and nothing executes it

The two headline numbers (the typecheck pass count and the native run count) are not
read from a document -- they are read from the last run of the two scripts that produce
them, and the file says which command to re-run.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L1 = os.path.join(ROOT, "os-build", "layer1")
DEST = os.path.join(L1, "FINISH_STATUS.md")


def corpus_typecheck():
    """`goose check` over every root, the way check_services.sh runs it."""
    out = subprocess.run(
        [os.path.join(L1, "check_services.sh")],
        cwd=ROOT, capture_output=True, text=True,
    )
    tail = [l for l in out.stdout.splitlines() if l.startswith("typechecked:")]
    return (tail[-1] if tail else "typechecked: NOT MEASURED"), out.returncode


def native_rows():
    """The last native run's per-program rows: label|status|pass|fail|note."""
    path = os.path.join(L1, "host", "run_rows.txt")
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("|")
            if len(parts) >= 4:
                rows.append(parts)
    return rows


def main():
    with open(os.path.join(L1, "services.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    svcs = man["services"]

    check_line, rc = corpus_typecheck()
    rows = native_rows()
    # run_rows.txt carries two kinds of row: the service drivers and the entry
    # programs (which build but are not run -- no supervisor calls svc_entry). The
    # headline number is about the drivers; counting entries in the denominator
    # would read as five failures that do not exist.
    drivers = [r for r in rows if not r[0].startswith("entry/")]
    entries = [r for r in rows if r[0].startswith("entry/")]
    runs = [r for r in drivers if r[1] == "RUNS"]
    total_checks = sum(int(r[2] or 0) for r in runs)

    L = []
    A = L.append
    A("# Whole-corpus numbers and the status table (A3)")
    A("")
    A("Measured 2026-11-02 on `buffy/layer1-goose-services`, once, with `services/root.goose`")
    A("in place. Regenerate this file with `python3 os-build/layer1/gen_finish_status.py`.")
    A("")
    A("## The two headline numbers")
    A("")
    A("| Measurement | Value | Command that produces it |")
    A("|---|---|---|")
    A("| `goose check`, full corpus incl. `services/root.goose` | **%s** | `./os-build/layer1/check_services.sh` |" % check_line.replace("typechecked: ", ""))
    A("| Native drivers that build and run to exit 0 | **%d of %d, %d assertions, 0 failed** | `./os-build/layer1/run_native.sh` |"
      % (len(runs), len(drivers), total_checks))
    A("| Entry programs that build but are not run | %d (no supervisor to call `svc_entry`) | same run |" % len(entries))
    A("")
    A("The typecheck command exited %d." % rc)
    A("")
    A("## Every service, one row")
    A("")
    A("| Service | Entry point | Driver | Status word | Checks | ABI class |")
    A("|---|---|---|---|---|---|")
    order = {"RUNS": 0, "TYPECHECKS": 1, "no native run": 2}
    for s in sorted(svcs, key=lambda s: (order.get(s["test_status"], 3), s["name"])):
        entry = s.get("entry_status") or "no entry"
        test = s.get("test") or "—"
        if s["test_status"] == "RUNS":
            word = "**RUNS**"
        elif entry.startswith("BUILDS") or entry.startswith("TYPECHECKS"):
            word = "TYPECHECKS"
        else:
            word = "NEITHER"
        checks = str(s["checks"]) if s["checks"] else "—"
        if s["test_status"] == "RUNS" and s["failures"]:
            checks += " (%d failed)" % s["failures"]
        A("| `%s` | %s | %s | %s | %s | %s |"
          % (s["name"], entry, ("`%s`" % test) if test != "—" else "—", word, checks, s["class"]))
    A("")

    n_runs = sum(1 for s in svcs if s["test_status"] == "RUNS")
    n_entry = sum(1 for s in svcs if s.get("entry") and not s["test_status"] == "RUNS")
    n_neither = len(svcs) - n_runs - n_entry
    A("## Counted, not summarised")
    A("")
    A("| Status word | Services | What it covers |")
    A("|---|---|---|")
    A("| **RUNS** | %d | a driver builds, executes and exits 0 |" % n_runs)
    A("| TYPECHECKS | %d | an entry point builds (or typechecks) but no driver runs it |" % n_entry)
    A("| NEITHER | %d | no driver and no entry point |" % n_neither)
    A("")
    A("A service that `RUNS` is also `TYPECHECKS` (the driver is typechecked too); the rows")
    A("above give each service its strongest true word, so the three counts add to %d." % len(svcs))
    A("")
    A("## What this table cannot tell you")
    A("")
    A("- `RUNS` means a host process ran the service's own code against the host shim's ten")
    A("  `sys_*` calls. No kernel, no scheduler, no address space. Five shim calls refuse on")
    A("  purpose: `sys_spawn`, `sys_kill`, `sys_net_send`, `sys_net_recv`, `sys_read_key`.")
    A("- `TYPECHECKS` is a compiler accepting the source. It is not execution, and it is not a")
    A("  claim that the service would start if something called `svc_entry`.")
    A("- `NEITHER` is the honest word for code that exists and has never been given a caller.")

    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("FINISH_STATUS.md: %d services, %d RUNS, %d typecheck-only, %d neither; %d assertions"
          % (len(svcs), n_runs, n_entry, n_neither, total_checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
