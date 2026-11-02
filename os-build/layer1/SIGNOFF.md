# Layer 4 sign-off (B-L1-78)

One page, for the boss's demo. Every claim here is a claim in `BUFFY_REPORT.md`, and where the two
could drift the report wins.

**Corrected 2026-11-01 under Pax P-5.** The first version of this page said the kernel was at K1 and
that no Goose toolchain existed. Both were true of the sandbox that wrote the sources and both are
false of this Mac. What follows is measured here, today.

## What Layer 4 is

The system services of Meta OS: 27 services and 17 libraries written in Goose, sitting above the
kernel (Layers 1–3) and below the agent runtime and shell (Layers 5–6). It owns the boot record,
the clock, logging, the supervisor and its boot order, the permission table, storage, the
filesystem, the network stack, sockets, updates, the audit trail, the agent host, the session, the
display, input, devices and the watchdog.

107 Goose files, 22,487 lines. 372.7 KiB of static storage across 34 services. No heap, no threads,
no libc.

## What is proven

Proven means a check ran on this Mac and its output is in this tree.

| Claim | How it is proven |
|---|---|
| **The corpus typechecks** | `check_services.sh`: **31 programs — 6 roots + 25 tests — 0 errors, 0 failed**, exit 0. It was 297 errors and 7 of 95 files before this pass. |
| The sources are internally consistent | `source_audit.py`: 107 files, 0 findings — braces, defined functions, declared codes, no duplicate `let`, no non-Goose keywords |
| There is one error vocabulary | `error_audit.py`: 34 codes declared, 34 used, 0 undeclared, 0 local redefinitions |
| The boot order cannot deadlock on paper | `bootorder_check.py`: 22 services, every dependency starts earlier, DAG proven independently, no cycles, names match directories |
| The link structure is known | `linkmap.py`: 26 services, 52 distinct service→service edges, drift vs round 1 measured |
| The storage footprint is known | `size_audit.py`: 372.7 KiB resident, 0 unresolvable types, the largest consumer identified (`display`, 136.6 KiB) |
| Every parser has hostile inputs and stated outcomes | `hostile_check.py`: 93 cases across 10 packs |
| The permission table covers every import edge | `callmatrix_audit.py`: 24 services, 0 missing permissions, 67 dormant rows named on every run |

**TYPECHECKED is not COMPILED.** `goose check` is the real front end and it accepts the whole
corpus, but no Goose program in this tree has produced an object file, been linked, or executed.
Those are three separate claims and this page only makes the first.

## What is not proven

Not proven means nobody has checked it, or it cannot be checked here.

| Gap | Why it cannot be closed here |
|---|---|
| **Anything runs** | no service host in the kernel: K6 boots userspace on this Mac, but nothing in the kernel starts a Goose service |
| **The supervisor starts a service** | needs both a runner and a built binary |
| **A service that hangs mid-start is detected** | the start timeout is not implemented (`FAILURE_TRACE.md` item 4) |
| **The permission table covers a call made without an import** | 67 rows allow one; "complete" here means "no known edge is denied" |
| **Goose can link freestanding** | needs codegen and a linker map; it is the assumption all of the above rests on |
| **The static storage is enough** | the source-side number is measured (372.7 KiB); the stack, padding and code size are not |
| **The tests pass** | they typecheck. Not one of the 25 has ever been executed, because nothing can execute them |

## What the next person should do, in order

1. **Compile** `common/` in dependency order, one program at a time via `check_services.sh`'s root
   list. The front end already agrees with the source; the backend is the open question (Q5).
2. **Read the failures as language facts**, not as typos. The three that cost the most this pass are
   permanent: no `++`/`--`, immutable parameters, and `T&` refusing an rvalue.
3. **Build one service** (`example`) and run it under the K6 userspace pattern, which is proven on
   this Mac. That single run turns B-L1-76 from NOT BUILT into a log.
4. **Drive the 67 dormant permission rows down** as runtime paths land: each is either a real call
   or a row to delete.
5. **Then** the run pass: `t45` … `t69` on a real kernel, one program at a time.

## The one-sentence version

**Layer 4 typechecks as 31 programs with zero errors, is internally consistent by eight mechanical
checks, and has never compiled to a binary or run; the report says exactly that on all 148 rows.**
