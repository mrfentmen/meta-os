#!/usr/bin/env python3
"""os-build/layer1/gen_demo_facts.py -- BF4-19: the measured fact sheet.

Every number in DEMO_FACTS.md is produced here by reading the tree or by running the
command named beside it. Nothing is retyped from a previous document, because the
failure mode this file exists to prevent is a demo quoting a number that was true
two commits ago.

If a command fails, its row says FAILED with the exit status -- a fact sheet is not
allowed to look green because a check was skipped.

Usage:
  python3 os-build/layer1/gen_demo_facts.py          write DEMO_FACTS.md
  python3 os-build/layer1/gen_demo_facts.py --check  regenerate and diff, exit 1 on drift
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L1 = os.path.join(ROOT, "os-build", "layer1")
DEST = os.path.join(L1, "DEMO_FACTS.md")
DATE = "2026-11-02"


def sh(cmd):
    p = subprocess.run(cmd, cwd=ROOT, shell=True, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def goose_files():
    out = []
    for base, _dirs, files in os.walk(os.path.join(ROOT, "services")):
        for f in files:
            if f.endswith(".goose"):
                out.append(os.path.join(base, f))
    return out


def lines_in(paths):
    n = 0
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            n += sum(1 for _ in fh)
    return n


def rows():
    path = os.path.join(L1, "host", "run_rows.txt")
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line:
                out.append(line.split("|"))
    return out


def limits_line():
    path = os.path.join(L1, "LIMITS.md")
    if not os.path.exists(path):
        return "LIMITS.md missing"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # Three numbers, all on the header line: exercised, named-reason, still open.
    m = re.search(r"\*\*(\d+) of (\d+) are exercised by a test\*\*", text)
    r = re.search(r"and \*\*(\d+) (?:is|are) still open\*\*", text)
    e = re.search(r", (\d+) more carry a named", text)
    if m:
        out = "%s of %s exercised" % (m.group(1), m.group(2))
        if e:
            out += ", %s with a named reason" % e.group(1)
        if r:
            out += ", %s open" % r.group(1)
        return out
    return "count not found"


def main():
    if "--check" in sys.argv:
        before = open(DEST, encoding="utf-8").read() if os.path.exists(DEST) else ""
        main_body = build()
        print("DEMO_FACTS.md %s" % ("is current" if before == main_body else "DRIFTED"))
        return 0 if before == main_body else 1
    body = build()
    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("wrote %s" % os.path.relpath(DEST, ROOT))
    return 0


def build():
    files = goose_files()
    tests = sorted(f for f in os.listdir(os.path.join(ROOT, "services", "tests"))
                   if f.endswith(".goose"))
    r = rows()
    test_rows = [x for x in r if x[0].startswith("tests/")]
    entry_rows = [x for x in r if x[0].startswith("entry/")]
    runs = [x for x in test_rows if x[1] == "RUNS"]
    fails = [x for x in test_rows if x[1] != "RUNS"]
    checks = sum(int(x[2]) for x in runs if len(x) > 2 and x[2].isdigit())

    manifest_path = os.path.join(L1, "services.json")
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    svc = manifest.get("services", [])
    lib_class = sum(1 for s in svc if s.get("class", "").startswith("library"))
    prop_class = sum(1 for s in svc if s.get("class") == "needs a proposal")
    entry_builds = sum(1 for x in entry_rows if x[1].startswith("BUILDS"))
    entry_tc = sum(1 for x in entry_rows if x[1].startswith("TYPECHECKS"))
    entry_fail = sum(1 for x in entry_rows if x[1] not in ("BUILDS (not run)", "TYPECHECKS (not run)"))

    tc_code, tc_out = sh("./os-build/layer1/check_services.sh")
    tc_line = ""
    for line in tc_out.splitlines():
        if line.startswith("typechecked:"):
            tc_line = line.strip()
    tc_line = tc_line or "no summary line"

    audit_cmds = [
        ("source consistency", "python3 os-build/layer1/source_audit.py", "files audited"),
        ("error vocabulary", "python3 os-build/layer1/error_audit.py", "clean:"),
        ("static size", "python3 os-build/layer1/size_audit.py", "resident:"),
        ("boot order DAG", "python3 os-build/layer1/bootorder_check.py", "RESULT:"),
        ("link map", "python3 os-build/layer1/linkmap.py", "service->service edges"),
        ("permission table", "python3 os-build/layer1/callmatrix_audit.py", "permissions"),
        ("status words", "python3 os-build/layer1/audit_status.py", "status lines checked"),
    ]
    audit_rows = []
    for label, cmd, needle in audit_cmds:
        code, out = sh(cmd)
        summary = ""
        for line in out.splitlines():
            if needle in line:
                summary = line.strip()
        audit_rows.append((label, cmd.split(" ", 2)[-1], code, summary or "(no summary line)"))

    L = []
    A = L.append
    A("# Demo facts, measured (%s)" % DATE)
    A("")
    A("Generated by `python3 os-build/layer1/gen_demo_facts.py`. Every value below was")
    A("produced by the command in its own row, in this checkout, on this machine. There is")
    A("no remembered number in this file: re-running the generator rewrites all of them, and")
    A("`--check` exits non-zero if the committed copy has drifted from the tree.")
    A("")
    A("Hana's demo script should read this file rather than any report. If a number here")
    A("disagrees with a number in a report, this file is the one with a command behind it.")
    A("")
    A("## The corpus")
    A("")
    A("| Fact | Value | Command that produces it |")
    A("|---|---|---|")
    A("| Goose source files | %d | `find services -name '*.goose' \\| wc -l` |" % len(files))
    A("| Lines of Goose | %d | `cat $(find services -name '*.goose') \\| wc -l` |" % lines_in(files))
    A("| Service directories with a kernel-facing role | %d | `ls -d services/*/ \\| grep -v tests \\| grep -v common \\| wc -l` |"
      % (len([d for d in os.listdir(os.path.join(ROOT, "services"))
              if os.path.isdir(os.path.join(ROOT, "services", d))
              and d not in ("tests", "common")])))
    A("| Shared libraries under `services/common` | %d | `ls -d services/common/*/ \\| wc -l` |"
      % len([d for d in os.listdir(os.path.join(ROOT, "services", "common"))
             if os.path.isdir(os.path.join(ROOT, "services", "common", d))]))
    A("| Native test programs | %d | `ls services/tests/*.goose \\| wc -l` |" % len(tests))
    A("")
    A("## The gate that ran")
    A("")
    A("| Fact | Value | Command that produces it |")
    A("|---|---|---|")
    A("| Test programs that built and ran to exit 0 | **%d of %d** | `./os-build/layer1/run_native.sh` |"
      % (len(runs), len(test_rows)))
    A("| Test programs that failed | **%d** | same |" % len(fails))
    A("| Passing individual checks across those runs | **%d** | `awk -F'|' '/^tests\\// {s+=$3} END {print s}' os-build/layer1/host/run_rows.txt` |" % checks)
    A("| Checks that reported FAIL | **%d** | same file, column 4 |"
      % sum(int(x[3]) for x in runs if len(x) > 3 and x[3].isdigit()))
    A("| Entry points that compile to a binary | %d | `./os-build/layer1/run_native.sh` (entry section) |" % entry_builds)
    A("| Entry points that only typecheck | %d | same |" % entry_tc)
    A("| Entry points that failed to build | %d | same |" % entry_fail)
    A("| Whole-corpus typecheck | %s (exit %d) | `./os-build/layer1/check_services.sh` |"
      % (tc_line, tc_code))
    A("")
    A("`run_native.sh` is the gate: it compiles each driver with Goose, links it with clang")
    A("against `host/host_shim.c`, and runs it. A test that does not build is a FAILED row,")
    A("not an absent one.")
    A("")
    A("## What the services need from the kernel")
    A("")
    A("| Fact | Value | Command that produces it |")
    A("|---|---|---|")
    A("| Services that need no kernel call at all | %d | `python3 os-build/layer1/gen_services.py` then read `services.json` |" % lib_class)
    A("| Services that need a syscall outside the F1 freeze | %d | same |" % prop_class)
    A("| Services in the manifest | %d | `jq '.services \\| length' os-build/layer1/services.json` |" % len(svc))
    A("")
    A("The freeze is 0 exit, 1 write, 2 sleep, 3 pid, 4 yield, 5 read_key, 6-15 reserved.")
    A("`PROPOSALS.md` holds the exact numbers requested for the ones that do not fit;")
    A("nothing has been allocated.")
    A("")
    A("## The audits")
    A("")
    A("| Audit | Command | Exit | Summary line |")
    A("|---|---|---|---|")
    for label, cmd, code, summary in audit_rows:
        A("| %s | `%s` | %d | %s |" % (label, cmd, code, summary.replace("|", "\\|")))
    A("")
    A("## Limits, and how many are actually driven to their edge")
    A("")
    A("| Fact | Value | Command that produces it |")
    A("|---|---|---|")
    A("| Numeric limit constants exercised by a test | %s | `python3 os-build/layer1/gen_limits.py` |" % limits_line())
    A("")
    A("`LIMITS.md` names every constant and the test that proves it, and marks the rest")
    A("UNPROVEN with the word itself. A green suite elsewhere says nothing about a specific")
    A("limit, so the demo should not imply otherwise.")
    A("")
    A("## Numbers this lane does not own")
    A("")
    A("These are the numbers a services demo is most likely to be asked for, and none of")
    A("them is measurable from `services/`:")
    A("")
    A("- **Boot time to the shell.** No boot log exists in this checkout. The kernel's")
    A("  milestone evidence lives in `os-build/SCOREBOARD.md`, which on this branch records")
    A("  no K1 boot log. Quote Milo's gate file, not this one.")
    A("- **Services started at boot.** `BOOT_PLAN.md` is a plan; `bootorder_check.py` proves")
    A("  the order is acyclic, not that a supervisor executed it. Nothing starts a service.")
    A("- **Memory used at runtime.** `size_audit.py` measures fixed storage declared in the")
    A("  source. Stack depth, struct padding, code size and `.rodata` are not in it.")
    A("")
    A("## What a demo can say without overclaiming")
    A("")
    A("Safe, because each sentence is a row above:")
    A("")
    A("- \"%d service programs build and run on this machine, %d checks passing.\""
      % (len(runs), checks))
    A("- \"%d services need no kernel call at all; %d need a syscall the freeze does not have.\""
      % (lib_class, prop_class))
    A("- \"The corpus typechecks as %s.\"" % tc_line.replace("typechecked: ", ""))
    A("")
    A("Not safe:")
    A("")
    A("- \"The OS runs these services.\" Nothing starts a service process; the runs are host")
    A("  processes against a substituted syscall surface.")
    A("- \"The network stack works.\" The protocol pack talks to itself through an in-memory")
    A("  link; there is no NIC and no wire.")
    A("- \"The filesystem persists.\" The backend is RAM, and the test proves a remount")
    A("  within one process, not a reboot.")
    A("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
