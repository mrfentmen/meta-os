# registry — Round 11 record

Source: none — `services/registry/` holds a README only · Test: none (nothing to import) · Status: NOT A SERVICE

`services/registry/` is not an implementation. The name-to-handle registry is four functions
inside the supervisor (`services/supervisor/supervisor.goose`: `sup_register`,
`sup_lookup`, `sup_release`, `sup_resolve`). The directory exists so the MANIFEST row is not a
dead link. That is the whole finding, and the six-task pass is answered against it rather than
against an imaginary file.

## 1. Limits — NOT APPLICABLE

No constants live here. The limits a registry entry is subject to are the supervisor's, and
`os-build/layer1/LIMITS.md` lists them under `supervisor`: `NAME_MAX` (32, driven by
`t52_supervisor`), `MAX_SERVICES` (32, driven by `t75_supervisor_load`), `HANDLE_GEN_MAX`
(65535, driven by `t83_sup_deep`). A limit row for `registry` would be a row about code that is
not in the directory.

## 2. Refusals — NOT APPLICABLE

Nothing here refuses anything. The refusals a caller sees when registering or resolving come
from the supervisor and are exercised by `t52_supervisor` (`E_BUSY` for a duplicate name,
`E_INVAL` for an empty or over-long name), `t83_sup_deep` (release while running, out-of-range
slot, generation wrap) and `t75_supervisor_load` (`E_NO_SPACE` at `MAX_SERVICES`).

## 3. Restart — NAMED GAP

The table is in-memory inside the supervisor. A supervisor restart loses every name and every
handle; boot re-registers from `services/supervisor/bootorder.goose`. No run has proved that
re-registration produces the same handles after a restart — the supervisor's restart drill
(`t83_sup_deep`) drives state transitions, not a process restart. What is lost, named plainly:
all registered names, every handle, and the generation counters.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| internal | supervisor | `sup_register`, `sup_lookup`, `sup_release`, `sup_resolve` | no row for `registry`; the calls are the supervisor's own |
| inbound | every service | a name is resolved through the supervisor, never through this directory | `SVC_SUPERVISOR` row (id 6) is the only relevant row |

**FINDING: there is no `SVC_REGISTRY` id, by design.** A second permission row for a table that
is not addressable would be a row nobody can call. The consequence to keep visible: the
registry cannot be audited through `cm_allows`, because it has no id to be a caller or callee.

## 5. Load — NOT APPLICABLE

No driver exists and none can be written against this directory. The load shape of the
registry is the supervisor's load shape, measured by `t75_supervisor_load` (the table filled
past `MAX_SERVICES`).

## 6. README truth pass — PROVEN

The README claimed things that were never true of this directory:

- **"Status: WRITTEN (not COMPILED). Source exists"** — no source exists. Rewritten to say the
  directory is a pointer and the implementation is RUNS under the supervisor.
- **"the functions listed below in the source"** — there is no source and no list. Removed.
- **"Verification: checked against the Goose docs …"** — a table of language features with no
  file behind it. Removed.
- **"Not verified: compilation … no assertion has run"** — true only because there is nothing
  to compile; the sentence implied a written unit waiting for a toolchain. Replaced with the
  supervisor's measured drivers.
- **Duplicate paragraph** repeated in "What it does" and "Contract". Removed the duplicate.
