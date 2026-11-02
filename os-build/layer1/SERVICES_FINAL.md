# Services layer — final state for the submission record (BF5-08)

Branch `buffy/layer1-goose-services`, measured 2026-11-02. This page is the one a reviewer should
read first. It states what runs, what does not, and where the evidence is, and it does not repeat a
number that another file owns: `DEMO_FACTS.md` is generated from commands, `FREEZE_AUDIT.md` counts
status words, `TRANSCRIPTS.md` holds the output.

## What this layer is

Meta OS's system services: 25 services with code (plus 4 placeholder directories) and 18 shared
libraries, written in Goose, with no heap, no threads and no libc. 114 files, 24,369 lines, 155.2 KiB
of static storage. It owns the boot record, the clock, logging and rotation, the supervisor and its
boot order, the permission table, storage, the filesystem, the network stack and protocol pack, the
audit trail, the agent host, the session, display, input, devices, updates and the watchdog.

## What is proven, with the command

| Claim | Evidence |
|---|---|
| 32 test drivers build, run and exit 0 — **1,180 assertions, 0 failed** | `./os-build/layer1/run_native.sh` |
| 38 programs typecheck, 0 errors | `./os-build/layer1/check_services.sh` |
| Seven transcripts, stdout unedited | `TRANSCRIPTS.md` |
| 114 files, 0 source-audit findings | `python3 os-build/layer1/source_audit.py` |
| One error vocabulary, nothing undeclared | `python3 os-build/layer1/error_audit.py` |
| Boot order is acyclic, 22 services | `python3 os-build/layer1/bootorder_check.py` |
| 0 missing permissions, 67 dormant rows named | `python3 os-build/layer1/callmatrix_audit.py` |
| Every status word current (100 lines, 0 stale) | `python3 os-build/layer1/audit_status.py` |
| 22 of 75 numeric limits driven to their edge | `python3 os-build/layer1/gen_limits.py` |
| 22 services rehearsed in boot order: 3 start, 1 hangs, 18 no entry | `./os-build/layer1/boot_rehearsal.sh 5` |

The runs are real processes: Goose → C → clang, linked against `host/host_shim.c`, executed on this
Mac. That shim implements the ten `sys_*` symbols and **refuses five on purpose** — spawn, kill, net
send, net recv, `read_key`. A green run is a statement about service logic against a real clock and
real memory, and about nothing else.

## What is not proven

| Gap | Why |
|---|---|
| A kernel starts a service | `sys_spawn`/`sys_kill` are proposals (P3); nothing in this tree spawns a process |
| The supervisor acts on its decisions | same: it decides, records, and has no actor |
| Persistence | storage is RAM by design; a remount inside one process is not a reboot |
| The network reaches a wire | the protocol pack talks to itself through an in-memory link |
| Lobster calls a service | zero `.lobster` files; one no-argument `svc_entry` per service |
| A hung service is detected | the start timeout does not exist; `console` hangs and only the rehearsal's timeout catches it |
| Boot time, memory at runtime | kernel numbers; this checkout has no boot log |

## The four defects this layer's own runs found

1. **Inode writes used whatever block was in the buffer** — a filesystem-wide corruption bug, caught
   the first time the corpus executed.
2. **The fs checker double-counted blocks and read a stale bitmap**, so a clean tree reported leaks.
3. **The network pack had two byte-order/checksum bugs** — invisible to typechecking, fatal on a
   wire.
4. **An error log record was dropped on a full ring** before the flush that exists to make room for
   it: the priority policy was dead code in exactly the case it was written for.

Each has a test that fails before the fix and passes after; each is named in the commit message that
fixed it. The class of bug is the argument for running code rather than typechecking it: all four
typechecked.

## Where the evidence lives

| File | What it is |
|---|---|
| `DEMO_FACTS.md` | every number, with the command that produced it |
| `TRANSCRIPTS.md` | nine sections of unedited program output |
| `captures/` | three demo-grade captures, one per file |
| `SERVICE_RUNS.md` | the full pass/fail table, generated from `run_rows.txt` |
| `BOOT_REHEARSAL.md` | the boot order executed in the host runtime |
| `FAILURE_MATRIX.md` | each service's failure modes, exercised or named as unexercised |
| `SERVICES_SYSCALL_MAP.md`, `services.json` | the ABI map and the generated manifest |
| `PROPOSALS.md` | P1–P8, the calls this layer needs and the numbers it asks for |
| `LOAD_ORDER_1102.md` | the wire-or-delete input: which services first, and why |
| `SIGNOFF.md` | the one-page verdict |

## The verdict, in one sentence

Twenty-five services and eighteen libraries, 1,180 assertions green on this Mac and four real
defects found by running them — **executed on a host, never started by a kernel**, with no
persistence and no boot log, and every document in the lane says so.
