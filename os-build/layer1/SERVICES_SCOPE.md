# Services layer scope — what L4 is, and what it is not

Written 2026-11-01 for Pax (scoreboard v5 needs this distinction) and for anyone reading the word
"services" in two different senses in the same repo.

**The problem this page solves.** "Layer 4" appears in three places with three different sizes:
`origin/main` carries 5 Goose files, `buffy/layer1-goose-services` carries 95 (107 including this
lane's tests and roots), and the scoreboard's L4 row said "DESIGNED, NOT BUILT" while the report
called the layer WRITTEN. All three were defensible and together they were misleading. This page
fixes the vocabulary.

## Three things, three names

| Name | What it is | Where | Size | Status word |
|---|---|---|---|---|
| **The merged set** | The Goose programs that are on `main` today | `services/{echo,heartbeat,hello,mcp-host,updater}` | 5 files | TYPECHECKED, not booted, not wired to the kernel |
| **The corpus** | This lane's layer-4 build-out: 27 services, 17 libraries, 25 test programs | `buffy/layer1-goose-services`, `services/` | 107 files, 22,487 lines | TYPECHECKED (31 programs, 0 errors), never compiled, never run |
| **Layer 4** | The *specified* system-services tier of Meta OS | `KERNEL_SPEC.md`, `os-build/LAYERS.md` | 27 services per the work order | the corpus is its implementation; the merged set is a stub of it |

So: **the corpus is the L4 implementation, and no part of L4 runs.** The merged set is not "L4
landed" — it is five programs that typecheck and have never been started by a kernel.

## What is proven, in this lane, on this Mac

- The corpus typechecks as 31 programs. `os-build/layer1/check_services.sh`, exit 0.
- Eight mechanical checks are green: typecheck, source audit (107 files, 0 findings), error
  registry (34 codes, 0 drift), boot order (22 services, DAG proven, no cycles), link map (52
  distinct service→service edges), size audit (372.7 KiB resident), hostile packs (93 cases), call
  matrix (0 missing permissions, 67 dormant rows named).
- Every one of those is a statement about the *source*. None is a statement about a running system.

## What is not proven, and cannot be from here

- **No Goose program in this tree has been compiled.** `goose check` is the front end; there is no
  object file, no link, no binary. COMPILED is a separate claim and it is zero rows.
- **Nothing has executed.** Not one of the 25 test programs has run. They typecheck; that is all
  they do. The word for that is typechecked, and reading it as "tested" is the exact mistake this
  page exists to prevent.
- **Goose linking freestanding is still an assumption.** It is Q5 in `K6_NEEDS.md` and everything
  above rests on it. If `goose`'s codegen pulls host-OS symbols the way its `os` stdlib does, the
  whole tier needs a different build story — that is a real risk, not a formality.
- **The supervisor has never started a service.** K6 boots userspace, so the *pattern* for a
  userspace program is proven on this Mac; the *runner* that starts a Goose service is not written.
- **The start timeout does not exist** (`FAILURE_TRACE.md` item 4). A service that hangs mid-start
  holds the boot silently, which is the one failure class this layer claims to cover.

## What L4 is not

- **Not a driver tier.** Storage and the packet interface are bound to a RAM backend and a loopback
  harness. Layers 3's real drivers are not in tree; B-L1-73/74 stay NOT BUILT until they are.
- **Not the agent runtime.** `agenthost` is L4: process table, lifecycle, capability grants, audit
  records. Lobster's agent runtime is L5 and is Milo's, not this lane's.
- **Not the shell.** `shell/` here is the parsed-command core and the builtins, written as a
  library so L6 can drive it. Hana's shell and its boot experience are L6.
- **Not the programs.** L7 (Imperium, Scientia, Musica, Officina, Custos) is untouched by this lane.
- **Not a platform decision.** No heap assumption, no threads, no libc: fixed buffers, caller-owned
  storage, static tables. If a service needs an allocator later, that is a ruling, not a tweak.

## What would change the status word

In order, each one small enough to land in a session:

1. **COMPILED for one program** — `example`, built by whatever backend `goose` has, one log line.
   This moves the corpus from TYPECHECKED to COMPILED-for-one and proves Q5 in either direction.
2. **RUN for one program** — the same binary under the K6 userspace pattern. B-L1-76 becomes PROVEN.
3. **A runner in the kernel** — one syscall pair (`svc_start`, `svc_ready`) and the supervisor's
   boot order drives it. That is the milestone that makes L4 a tier instead of a library.
4. **The start timeout** — `starting_since_ms` on the slot, checked by the supervisor's tick. Closes
   the one failure class that is currently a promise in a document.
5. **The 67 dormant permission rows** — each is a real call or a row to delete; the list is printed
   on every `callmatrix_audit.py` run so nobody has to remember it.

## The one-line rule for the scoreboard

> L4 on `main` = 5 programs, typechecked, not booted. L4 as specified = 27 services + 17 libraries on
> `buffy/layer1-goose-services`, typechecked as 31 programs, never compiled, never run. No row may
> say COMPILED, BOOTED or WORKING for any of it.
