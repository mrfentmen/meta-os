# Layer 4 sign-off (B-L1-78)

One page, for the boss's demo. Every claim here is a claim in `BUFFY_REPORT.md`, and where the two
could drift the report wins.

## What Layer 4 is

The system services of Meta OS: 21 services and 17 libraries written in Goose, sitting above the
kernel (Layers 1–3) and below the agent runtime and shell (Layers 5–6). It owns the boot record,
the clock, logging, the supervisor and its boot order, the permission table, storage, the
filesystem, the network stack, sockets, updates, the audit trail, the agent host, the session, the
display, input, devices and the watchdog.

94 Goose files. 384.8 KiB of static storage across all of them. No heap, no threads, no libc.

## What is proven

Proven means a check ran and its output is in this tree.

| Claim | How it is proven |
|---|---|
| The sources are internally consistent | `source_audit.py`: 94 files, 0 findings — braces, defined functions, declared codes, no duplicate `let`, no non-Goose keywords |
| There is one error vocabulary | `error_audit.py`: 34 codes declared, 34 used, 0 undeclared, 0 local redefinitions |
| The boot order cannot deadlock on paper | `bootorder_check.py`: 22 services, every dependency starts earlier, DAG proven independently, no cycles, names match directories |
| The link structure is known | `linkmap.py`: 26 services, 74 files, 46 service→service edges, drift vs round 1 measured |
| The storage footprint is known | `size_audit.py`: 384.8 KiB resident, 0 unresolvable types, the largest consumer identified (`display`, 136.6 KiB) |
| Every parser has hostile inputs and stated outcomes | `hostile_check.py`: 93 cases across 10 packs |

## What is not proven

Not proven means nobody has checked it, or it cannot be checked here.

| Gap | Why it cannot be closed here |
|---|---|
| **Everything compiles** | no Goose toolchain on this machine (`goose__toolchain_status` = NOT FOUND) |
| **Anything runs** | no kernel above K1; nothing in this layer has ever been executed |
| **The supervisor starts a service** | needs K6 and a kernel |
| **A service that hangs mid-start is detected** | the start timeout is not implemented (`FAILURE_TRACE.md` item 4) |
| **The permission table is complete** | 12 edges are missing and 2 services have no id — `CALLMATRIX_DRIFT.md`; the gate is red on purpose |
| **Goose can link freestanding** | needs the toolchain; it is the assumption all of the above rests on |
| **The static storage is enough** | needs the linker's number; this layer measured its own side (384.8 KiB) and nothing else |

## What the next person should do, in order

1. Get the toolchain (`aardappel/goose`, cmake, `-DGOOSE_BUILTIN_LIBS=all`) and answer Q5 —
   freestanding link. Everything after this is ordinary work; everything before it is writing.
2. Compile `common/` first, in dependency order. A library that fails to compile stops the
   services before their own bugs can confuse the report.
3. Compile one service (`example`, the template) and read every error as a fact about the
   language's semantics. There are 22 open questions in `K6_NEEDS.md` that a compiler answers in
   seconds.
4. Add the 12 call-matrix edges (Pax's ruling), then turn the red gate green by changing the
   matrix, not the auditor.
5. Then, and only then, the run pass: `t45` … `t68` on a real kernel, one program at a time.

## The one-sentence version

**Layer 4 is written, internally consistent by seven mechanical checks, and has never compiled or
run; the report says exactly that on all 148 rows, and the red gate is the honest one.**
