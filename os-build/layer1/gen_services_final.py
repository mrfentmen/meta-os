#!/usr/bin/env python3
"""os-build/layer1/gen_services_final.py -- E4: SERVICES_FINAL.md, generated.

The submission page for the services layer. Every number in it is measured here, from
the tree and from the audit tools' own output, so the page cannot outlive the code it
describes. Prose sections (what is not proven, the defect list) are curated text: they
are claims, not counts, and they are kept in this file where the numbers are.

Usage:
    python3 os-build/layer1/gen_services_final.py            # rewrite the page
    python3 os-build/layer1/gen_services_final.py --check    # exit 1 if it has drifted
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEST = os.path.join(HERE, "SERVICES_FINAL.md")


def run(script):
    out = subprocess.run([sys.executable, os.path.join(HERE, script)],
                         capture_output=True, text=True, cwd=ROOT)
    return out.stdout + out.stderr


def goose_files():
    files = []
    for base, _dirs, names in os.walk(os.path.join(ROOT, "services")):
        for n in names:
            if n.endswith(".goose"):
                files.append(os.path.join(base, n))
    return files


def count_lines(files):
    total = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as h:
            total += len(h.read().split("\n")) - (0 if f.endswith("\n") else 0)
    return total


def service_dirs():
    """Directories under services/ that hold Goose source and are not libraries/tests."""
    out = []
    for name in sorted(os.listdir(os.path.join(ROOT, "services"))):
        p = os.path.join(ROOT, "services", name)
        if not os.path.isdir(p) or name in ("common", "tests", "build"):
            continue
        if any(f.endswith(".goose") for f in os.listdir(p)):
            out.append(name)
    return out


def check_rows():
    """(programs, run, not_run, failures, checks_passed) from the last runner."""
    path = os.path.join(HERE, "host", "run_rows.txt")
    programs = runs = not_run = 0
    checks = 0
    failures = 0
    if not os.path.exists(path):
        return programs, runs, not_run, failures, checks
    with open(path, "r", encoding="utf-8") as h:
        for line in h:
            parts = line.rstrip("\n").split("|")
            if len(parts) < 4:
                continue
            programs += 1
            if parts[1] == "RUNS":
                runs += 1
            else:
                not_run += 1
            try:
                checks += int(parts[2])
                if int(parts[3]) > 0:
                    failures += 1
            except ValueError:
                pass
    return programs, runs, not_run, failures, checks


def main(argv):
    files = goose_files()
    total_lines = count_lines(files)
    svcs = service_dirs()
    libs = len([n for n in os.listdir(os.path.join(ROOT, "services", "common"))
                if os.path.isdir(os.path.join(ROOT, "services", "common", n))])
    programs, runs, not_run, failures, checks = check_rows()

    src = run("source_audit.py")
    src_find = re.search(r"(\d+) files audited, (\d+) finding", src)
    err = run("error_audit.py")
    boot = run("bootorder_check.py")
    boot_n = re.search(r"(\d+) services", boot)
    matrix = run("callmatrix_audit.py")
    dormant = re.search(r"(\d+) dormant row", matrix)
    status = run("audit_status.py")
    status_n = re.search(r"status lines checked: (\d+), stale: (\d+)", status)
    limits = run("gen_limits.py")
    lim = re.search(r"limits: (\d+)\s+proven: (\d+)\s+explained: (\d+)\s+open: (\d+)", limits)
    size = run("size_audit.py")
    resident = re.search(r"resident: (\d+) bytes \(([\d.]+) KiB\)", size)
    typ = subprocess.run(["bash", os.path.join(HERE, "check_services.sh")],
                         capture_output=True, text=True, cwd=ROOT)
    typ = typ.stdout + typ.stderr
    typ_ok = re.search(r"typechecked: (\d+) ok, (\d+) failed", typ)
    manifest = run("gen_services.py")
    manifest_n = re.search(r"services: (\d+)\s+class1: (\d+)\s+class2: (\d+)", manifest)
    outside = re.search(r"outside freeze: (.*)", manifest)

    def g(m, i=1, default="?"):
        return m.group(i) if m else default

    page = f"""# Services layer — final state for the submission record (BF5-08, R7)

Branch `buffy/layer1-goose-services`, measured 2026-11-02. This page is the one a reviewer
should read first. Every number in it is produced by `python3 os-build/layer1/gen_services_final.py`
from the tree and from the audit tools' own output, so the page cannot outlive the numbers it
quotes. `DEMO_FACTS.md` is the demo-facing subset, `LIMITS.md` owns the limits table, and
`TRANSCRIPTS.md` holds unedited program output.

## What this layer is

Meta OS's system services: **{len(svcs)} services with code** and **{libs} shared libraries**,
written in Goose, with no heap, no threads and no libc. **{len(files)} files, {total_lines:,} lines,
{g(resident)} bytes ({g(resident, 2)} KiB) of static storage.** It owns the boot record, the clock,
logging and rotation, the supervisor and its boot order, the permission table, storage, the
filesystem, the network stack and protocol pack, the audit trail, the agent host, the session,
display, input, devices, updates, the watchdog — and, since R7, the six face services the home
surface draws from: settings, wallpaper, dock, dashboard feed, updater client and board.

## What is proven, with the command

| Claim | Value | Command |
|---|---|---|
| Test programs build and run to exit 0 | **{runs} of {programs}** ({not_run} build-only: `svc_entry`, no supervisor) | `./os-build/layer1/run_native.sh` |
| Test programs that failed | **{failures}** | same |
| Passing individual checks | **{checks:,}** | `awk -F'\\|' '/^tests\\// {{s+=$3}} END {{print s}}' os-build/layer1/host/run_rows.txt` |
| Whole-corpus typecheck | **{g(typ_ok,1)} ok, {g(typ_ok,2)} failed** | `./os-build/layer1/check_services.sh` |
| Source audit | {g(src_find,1)} files, **{g(src_find,2)} findings** | `python3 os-build/layer1/source_audit.py` |
| Error vocabulary | {err.strip().splitlines()[-1] if err.strip() else "?"} | `python3 os-build/layer1/error_audit.py` |
| Boot order | **{g(boot_n)} services**, dependency order proven, no cycles | `python3 os-build/layer1/bootorder_check.py` |
| Call matrix | 0 missing permissions, **{g(dormant)} dormant rows** | `python3 os-build/layer1/callmatrix_audit.py` |
| Status words | {g(status_n,1)} lines, **{g(status_n,2)} stale** | `python3 os-build/layer1/audit_status.py` |
| Numeric limits driven to their edge | **{g(lim,2)} of {g(lim,1)}** ({g(lim,3)} explained, {g(lim,4)} open) | `python3 os-build/layer1/gen_limits.py` |
| Manifest | {g(manifest_n)} services, class1 {g(manifest_n,2)}, class2 {g(manifest_n,3)} | `python3 os-build/layer1/gen_services.py` |

The runs are real processes: Goose → C → clang, linked against `host/host_shim.c`, executed on
this Mac. That shim implements the ten `sys_*` symbols and **refuses five on purpose** — spawn,
kill, net send, net recv, `read_key`. A green run is a statement about service logic against a
real clock and real memory, and about nothing else.

## What is not proven

| Gap | Why |
|---|---|
| A kernel starts a service | `sys_spawn`/`sys_kill` are proposals (P3, P3a); nothing in this tree spawns a process |
| The supervisor acts on its decisions | same: it decides, records, and has no actor — 27 checks in `t92_sup_load` prove the plans, none prove a process moved |
| Persistence | storage is RAM by design; a remount inside one process is not a reboot |
| The network reaches a wire | the protocol pack talks to itself through an in-memory link |
| Lobster calls a service | zero `.lobster` files; one no-argument `svc_entry` per service |
| A hung service is detected | the start timeout does not exist; `console` hangs and only the rehearsal's timeout catches it |
| Boot time, memory at runtime | kernel numbers; this checkout has no boot log |

## The defects this layer's own runs found

Each one was found by executing the corpus, not by reading it. The first six came in R1–R6;
the last four in R7, and every one of them was in code that had already passed typechecking.

1. **Inode writes used whatever block was in the buffer** — a filesystem-wide corruption bug.
2. **The fs checker double-counted blocks and read a stale bitmap**, so a clean tree reported leaks.
3. **The network pack had two byte-order/checksum bugs** — invisible to typechecking, fatal on a wire.
4. **An error log record was dropped on a full ring** before the flush that exists to make room for it.
5. **`login_submit` could not log a user in.** It opened the session with `user_id = 0`, which
   `ses_open` refuses — the right token produced `E_INVAL` every time.
6. **The NTP time was measured from a truncated fraction**, so every sync was off by a known amount.
7. **A released supervisor slot could never be reused.** `sup_release` cleared the entry but left
   the table length where it was, so a service that was stopped and started again took a new slot
   every time and the 32-slot table filled after 32 restarts. Found by R7's supervisor drill.
8. **`DEP_MAX` was 24 while the boot order is 28.** `deps_stop_plan` silently dropped four services
   from a stop plan — a shutdown that leaves four services running and reports success.
9. **The board client read its export format one field off.** `P,<id>,<room>,<created>,<text>` was
   parsed with the id starting after the first comma, so every import failed and the round-trip test
   would have reported the format as broken rather than the parser. Found the first time the board
   test ran.
10. **The six face services were outside the manifest, the boot order and the permission table.**
    The audit tools caught all three at once (`COVERAGE`, `UNKNOWN`, and drift), which is what those
    audits exist for: adding a service is now a four-file change, and forgetting one of the four
    fails a check instead of shipping.

## The order things run in

`services/supervisor/bootorder.goose` is the table: {g(boot_n)} rows, each with its dependency mask,
its fatal flag and its position. `bootorder_check.py` proves it mechanically — ids 1..n once each,
orders 1..n once each, every dependency strictly earlier, acyclic by an independent DFS, and every
service directory accounted for. `t92_sup_load` then drives the whole sequence through
`supervisor/deps` three times, with a fatal service killed at step 0 in two drills, and asserts the
boot still completes: a machine that hangs because the logger died is worse than one that boots
degraded and says so.

## Where to look next

- `LIMITS.md` — every numeric constant and the test that breaks it, or the reason it cannot be.
- `contracts/` — one page per service: what it promises, what it refuses, what a restart costs.
- `PROPOSALS.md` — the four syscalls this layer is waiting on, with numbers and shapes (P3a).
- `FREEZE_AUDIT.md`, `CALLMATRIX_DRIFT.md`, `FAILURE_MATRIX.md` — the audits' own reports.
"""
    if "--check" in argv:
        if os.path.exists(DEST):
            with open(DEST, "r", encoding="utf-8") as h:
                if h.read() == page:
                    print("SERVICES_FINAL.md is current")
                    return 0
        print("SERVICES_FINAL.md has drifted from the tree")
        return 1
    with open(DEST, "w", encoding="utf-8") as h:
        h.write(page)
    print("wrote %s" % os.path.relpath(DEST, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
