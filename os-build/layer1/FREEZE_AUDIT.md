# Services freeze audit — the corpus at the H+9 freeze (BF5-07)

One page, measured 2026-11-02 on `buffy/layer1-goose-services`. Counts only; no claim here is
stronger than the command beside it. `gen_demo_facts.py` regenerates every number in this file's
first two tables, and `DEMO_FACTS.md` is its output.

## The corpus

| Count | Value | Command |
|---|---|---|
| Goose files | 115 | `find services -name '*.goose' \| wc -l` |
| Lines of Goose | 24,785 | `cat $(find services -name '*.goose') \| wc -l` |
| Service directories | 29 | `ls -d services/*/ \| grep -v tests \| grep -v common` |
| …in the manifest (code + a mapped test) | 25 | `jq '.services \| length' os-build/layer1/services.json` |
| …placeholders, no code | 4 | `sockets`, `registry`, `devmgr` (README), `build` (empty) |
| Shared libraries | 18 | `ls -d services/common/*/` |
| Test drivers | 33 | `ls services/tests/*.goose \| wc -l` |
| Entry points (`svc_entry`) | 5 | 4 build, 1 typechecks only |

## Status words, counted

| Status word | Count | What it applies to |
|---|---|---|
| **RUNS** | 33 | test drivers that build, execute and exit 0 (`run_native.sh`) — 1,253 assertions, 0 failed |
| **TYPECHECKS** | 39 | roots + test roots accepted by `goose check` (includes the 33 that also run) |
| **BUILDS (not run)** | 4 | `entry_{bootlog,console,logd,time}` — real binaries, no supervisor to call `svc_entry` |
| **TYPECHECKS (not run)** | 1 | `entry/example` — its `svc_entry` takes a `BootInfo` a host cannot fabricate |
| **NO ENTRY** | 18 of 22 | boot-order services with no `entry.goose` at all (`BOOT_REHEARSAL.md`) |
| **STARTS** | 3 | `bootlog`, `time`, `logd` — ran to exit 0 in the rehearsal |
| **HANGS** | 1 | `console` — loops on `sys_read_key`, killed by the rehearsal's timeout |
| **NOT BUILT** | 4 | the placeholder directories; the kernel-side runner; the start timeout; the Lobster binding |

The words are used as the work order defines them: a service can be RUNS as a **library** and not
startable as a **process**, and most of the corpus is exactly that.

## By ABI class

| Class | Count | Meaning |
|---|---|---|
| Library, no kernel calls | 17 | startable the moment a loader exists |
| Needs a proposal | 8 | 7 need `sys_ticks` (P1), 1 needs `sys_net_*` (P2) |
| Needs a process | 25 | `sys_spawn`/`sys_kill` (P3) for the supervisor to start any of them |

`services.json` holds the per-service rows; `SERVICES_SYSCALL_MAP.md` holds the reasoning per call.

## What is frozen and must not move during the freeze

1. **The syscall freeze.** 0 exit, 1 write, 2 sleep, 3 pid, 4 yield, 5 `read_key`, 6–15 reserved.
   `PROPOSALS.md` asks; it does not allocate.
2. **The record formats.** Boot record (`t48`), log record (`t50`), audit record (`t60`), status line
   (`t70`), update manifest (`t58`). A consumer outside this lane reads all five.
3. **The boot order.** `bootorder_check.py` proves the 22-row table acyclic; changing an order field
   without rerunning it is how a deadlock gets in.
4. **The permission table.** `callmatrix_audit.py` is clean at 0 missing edges, with 67 dormant rows
   named on every run.

## What is not frozen because it does not exist yet

- **The loader.** No image format, no entry convention beyond the codegen default, no `BootInfo`
  delivery.
- **The start timeout.** A hung service is invisible to this layer (`console` demonstrates it).
- **Persistence.** Storage is RAM; nothing survives a reboot.
- **The Lobster binding.** Zero `.lobster` files, one no-argument entry per service.

## The one-line state of the layer

**33 drivers, 1,253 assertions, 0 failed; 25 services of which 17 need no kernel call; 3 start, 1
hangs, 18 have no entry point; nothing has been started by the kernel.**
