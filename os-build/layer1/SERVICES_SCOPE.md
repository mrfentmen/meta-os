# Services layer scope — what L4 is, and what it is not

Rewritten 2026-11-02 after Waves 1–2 of Round 4. The first version of this page said the corpus
had never been compiled and never been run. That is no longer true, and every status word below is
measured in this checkout on this date, not remembered. Where a number is quoted, the command that
produces it is named; `DEMO_FACTS.md` is regenerated from those same commands.

## Three things, three names

| Name | What it is | Where | Size | Status word |
|---|---|---|---|---|
| **The merged set** | The Goose programs on `main`'s branch tip | `services/{echo,heartbeat,hello,mcp-host,updater}` | 5 files | typechecks; not wired to the kernel |
| **The corpus** | This lane's layer-4 build-out | `buffy/layer1-goose-services`, `services/` | 115 files, 24,785 lines | **RUNS natively** — 33 drivers, 1,253 assertions, 0 failed |
| **Layer 4** | The specified system-services tier | `KERNEL_SPEC.md`, `os-build/LAYERS.md` | 25 services in the manifest | the corpus is its implementation |

**The corpus is the L4 implementation, and it executes on a host — not on the kernel.** Those are
different sentences and the difference is the whole page.

## The shape of the corpus, counted

| Thing | Count | Command |
|---|---|---|
| Service directories | 29 | `ls -d services/*/ \| grep -v tests \| grep -v common` |
| …with code and a native test | 25 | `jq '.services \| length' os-build/layer1/services.json` |
| …placeholders (README only, or empty) | 4 | `sockets`, `registry`, `devmgr` (README), `build` (empty) |
| Shared libraries under `services/common` | 18 | `ls -d services/common/*/` |
| Test drivers | 33 | `ls services/tests/*.goose` |
| Entry points (`svc_entry`) | 5 | 4 build, 1 typechecks only |

The four placeholders are named because a count of 29 directories reads as 29 implemented services
and that would be false. `PROPOSALS.md` and `BOUNDARIES.md` carry what each of them would need.

## What is proven, in this lane, on this Mac

- **33 of 33 drivers build and run to exit 0: 1,253 assertions, 0 failed.** `run_native.sh`. Each
  driver is compiled by Goose to C, linked by clang against `host/host_shim.c`, and executed.
- **The corpus typechecks as 39 programs** (6 roots + 33 tests), 0 errors. `check_services.sh`.
- **Eight mechanical audits are green**: source consistency (115 files, 0 findings), error
  vocabulary (every code declared, no local redefinitions), static size (165.4 KiB resident across
  33 units), boot order (22 services, DAG proven, no cycles), link map (56 distinct service→service
  edges), permission table (0 missing permissions, 67 dormant rows named), status words (101 lines,
  0 stale), limits (26 of 75 constants exercised by a test).
- **The filesystem, the shell, log rotation, the protocol pack, the supervisor state machine and the
  permission table all have transcripts.** `TRANSCRIPTS.md`, ten sections, output unedited.

## What is not proven, and cannot be from here

- **No service has been started by the kernel.** `sys_spawn` and `sys_kill` are not declared
  anywhere in the corpus (`PROPOSALS.md` P3), so the supervisor decides and records; it cannot act.
  Nothing in this tree starts a Goose service process.
- **The runs are host processes.** The shim substitutes the ten `sys_*` symbols and refuses five on
  purpose — spawn, kill, net send, net recv, read_key. A green run therefore proves service logic
  and proves nothing about the scheduler, the address space, or a NIC.
- **The filesystem does not persist.** The backend is RAM; the remount test proves survival within
  one process, not across a reboot.
- **No boot log exists in this checkout.** Boot time, services started at boot, and memory at
  runtime are kernel numbers and belong to Milo's gate file, not to this page.
- **The start timeout still does not exist** (`FAILURE_TRACE.md` item 4). A service that hangs
  mid-start holds the boot silently.

## What L4 is not

- **Not a driver tier.** Storage and the packet interface are bound to a RAM backend and an
  in-memory link. Real drivers are not in tree.
- **Not the agent runtime.** `agenthost` is L4: process table, lifecycle, capability grants, audit
  records. Lobster's runtime is L5. There is no Lobster source in this repo (`LOBSTER_BINDING.md`).
- **Not the shell experience.** `shell/` is the parsed-command core and its builtins, written as a
  library so L6 can drive it. The console is Hana's.
- **Not the programs.** L7 (Imperium, Scientia, Musica, Officina, Custos) is untouched by this lane.
- **Not a platform decision.** No heap, no threads, no libc: fixed buffers, caller-owned storage,
  static tables. The one place this showed up in Waves 1–2 was the 512-byte file and the 16-entry
  ring refusing politely instead of growing — refusals are the design.

## What would change the status word next

In order, each small enough to land in a session:

1. **One service started by a supervisor that owns a process** — needs `svc_start`/`svc_ready` (or
   one of the P-proposals) and a kernel-side spawn. This is the line between a library and a tier.
2. **The start timeout** — `starting_since_ms` on the supervisor slot, checked by its tick. Closes
   the one failure class currently promised in prose.
3. **A segment name that maps to a file** — log rotation names its segments correctly and nothing
   writes them to MOSFS01 yet. The mapping is a small, provable piece of plumbing.
4. **The 67 dormant permission rows** — each is a real call or a row to delete; the list prints on
   every `callmatrix_audit.py` run.
5. **The four placeholder services** — `sockets`, `registry`, `devmgr`, `build`. Wire or delete is
   the boss's ruling; `PROPOSALS.md` has the first three costed.

## The one-sentence version, for the record

Twenty-five services and eighteen libraries, 1,097 assertions green on this Mac against a
substituted syscall surface, with no kernel process, no persistence and no boot log — so the honest
word for L4 today is **RUNS ON A HOST, NOT ON THE KERNEL**.
