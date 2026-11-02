# Services layer — final state for the submission record (BF5-08, R7)

Branch `buffy/layer1-goose-services`, measured 2026-11-02. This page is the one a reviewer
should read first. Every number in it is produced by `python3 os-build/layer1/gen_services_final.py`
from the tree and from the audit tools' own output, so the page cannot outlive the numbers it
quotes. `DEMO_FACTS.md` is the demo-facing subset, `LIMITS.md` owns the limits table, and
`TRANSCRIPTS.md` holds unedited program output.

## What this layer is

Meta OS's system services: **31 services with code** and **18 shared libraries**,
written in Goose, with no heap, no threads and no libc. **138 files, 31,530 lines,
203630 bytes (198.9 KiB) of static storage.** It owns the boot record, the clock,
logging and rotation, the supervisor and its boot order, the permission table, storage, the
filesystem, the network stack and protocol pack, the audit trail, the agent host, the session,
display, input, devices, updates, the watchdog — and, since R7, the six face services the home
surface draws from: settings, wallpaper, dock, dashboard feed, updater client and board.

## What is proven, with the command

| Claim | Value | Command |
|---|---|---|
| Test programs build and run to exit 0 | **50 of 55** (5 build-only: `svc_entry`, no supervisor) | `./os-build/layer1/run_native.sh` |
| Test programs that failed | **0** | same |
| Passing individual checks | **2,323** | `awk -F'\|' '/^tests\// {s+=$3} END {print s}' os-build/layer1/host/run_rows.txt` |
| Whole-corpus typecheck | **56 ok, 0 failed** | `./os-build/layer1/check_services.sh` |
| Source audit | 138 files, **0 findings** | `python3 os-build/layer1/source_audit.py` |
| Error vocabulary | clean: every code used is declared, and nothing redefines one locally | `python3 os-build/layer1/error_audit.py` |
| Boot order | **28 services**, dependency order proven, no cycles | `python3 os-build/layer1/bootorder_check.py` |
| Call matrix | 0 missing permissions, **91 dormant rows** | `python3 os-build/layer1/callmatrix_audit.py` |
| Status words | 116 lines, **0 stale** | `python3 os-build/layer1/audit_status.py` |
| Numeric limits driven to their edge | **71 of 91** (20 explained, 0 open) | `python3 os-build/layer1/gen_limits.py` |
| Manifest | 31 services, class1 0, class2 8 | `python3 os-build/layer1/gen_services.py` |

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

`services/supervisor/bootorder.goose` is the table: 28 rows, each with its dependency mask,
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
