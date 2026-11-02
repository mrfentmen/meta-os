# Call-matrix drift (B-L1-118)

Produced by `python3 os-build/layer1/callmatrix_audit.py` against the tree as of this
branch. Status: **REPORTED, NOT FIXED** — changing the permission table is a policy change
and belongs to Pax with the matrix's owner, not to the lane that found it.

## What the auditor does

It reads `services/callmatrix/callmatrix.goose` (the `SVC_*` ids and every `cm_set` row),
then reads every `import <service>.<module>;` line in `services/*/*.goose` and compares:

| Bucket | Meaning | Exit-code effect |
|---|---|---|
| MISSING | a source imports another service the matrix denies | failure |
| DORMANT | the matrix allows a call no source makes | informational (`--all` makes it a failure) |
| UNKNOWN | an id with no directory, or a service with no id | failure |

`common.*` is a library and is deliberately outside the matrix. `example/` is the template and
`callmatrix/` is the table itself; neither is a service. The matrix calls the log service
`log` while its directory is `logd`; that single alias is declared in the auditor rather than
pattern-matched, so a *second* rename still shows up as drift.

## Findings — MISSING permissions (12)

These are real edges. Each one compiles and then fails at `cm_allows` the first time the
call is made, which reads as "service did not start" rather than "permission denied".

| Caller | Callee | Where |
|---|---|---|
| `fs` | `storage` | `services/fs/fs.goose` block reads/writes |
| `netcfg` | `fs` | `services/netcfg/persist.goose` (B-L1-104) |
| `shell` | `fs` | `services/shell/shell.goose` file builtins |
| `shell` | `logd` | records builtin |
| `shell` | `audit` | records builtin |
| `shell` | `supervisor` | `services` builtin |
| `shell` | `time` | `uptime` builtin |
| `socket` | `netcfg` | address model |
| `example` | `fs`, `time`, `supervisor`, `watchdog` | the template, which is meant to be copied |

## Findings — services with no matrix row

`fs` and `shell` have sources and no `SVC_*` id. Adding them means appending ids 22 and 23
and raising `SVC_COUNT` to 23 (appending, never renumbering — the ids are also the numbers
services report to the supervisor). `example` and `callmatrix` are excluded by name; the
template still needs permissions the day a service is generated from it, which is why its
four edges are listed above.

## Findings — DORMANT permissions (65)

Not a defect. Two readings are both true: the code paths that use these edges go through the
registry at runtime rather than through imports, and the matrix was written before the
services were. The list is the one to read when answering "who can reach the audit log":
`supervisor -> audit`, `agenthost -> audit`, `session -> audit`, `updater -> audit` are all
allowed and none of them import the audit module.

## What would make this clean

1. Append `SVC_FS = 22` and `SVC_SHELL = 23` to the matrix and give each a row with exactly
   the callees above.
2. Give `example` a row, so the template cannot be copied without its permissions.
3. Re-run this auditor with `--all` in the gate; the dormant list should then be a deliberate
   list, not a surprise.

Until then, the honest status of the Layer 4 permission table is: **written, and incomplete
in twelve places that the tree already depends on.**

---

# Round 2 — resolved (2026-11-01)

Pax's ruling came back: append the ids, add the edges, and do not touch the auditor's standard.
All twelve edges are in, `fs` and `shell` have ids, and the gate is green:

```console
$ python3 os-build/layer1/callmatrix_audit.py
call-matrix audit  (24 services in the matrix, 25 with sources)

DORMANT permission (67, informational):
...
clean on permissions; 67 dormant row(s) reported above
$ echo $?
0
```

## What changed in the matrix

| Change | Why |
|---|---|
| `SVC_FS = 22` | `fs` had source and no id. Appended, never renumbered: the ids are also the numbers services report to the supervisor. |
| `SVC_SHELL = 23` | same, for `shell`. |
| `SVC_EXAMPLE = 24` | the template needs its own row. A service generated from `example` inherits nothing otherwise, and a template copied *without* permissions is exactly how these twelve edges went missing. |
| `SVC_COUNT` 21 → 24 | the array is the table. |
| `netcfg → fs` | `persist.goose` writes the config through the filesystem; the address model is a library import, the file is a call. |
| `socket → netcfg` | a bound address belongs to `netcfg`; the lookup is a call, not a copy. |
| `fs → storage, log` | the filesystem's whole job is another service's API, which is why its row is short. |
| `shell → fs, log, audit, supervisor, time` | the widest row in the table, and worth reading as a warning: a user's shell can do everything a user can. Agents do not get a shell handle. |
| `example → fs, time, supervisor, watchdog, log` | one of each thing it demonstrates. |

## The auditor bug this exposed

`ALIASES = {"log": "logd"}` was declared and never applied: the round-1 comparisons used matrix
names on one side and directory names on the other. So every edge to the log service was reported
**twice** — once as a missing permission (caller side) and once as a dormant one (callee side) —
which is why round 1's dormant count was 65 and why `shell → logd` survived the first fix.

Fixed in `callmatrix_audit.py`: `canon()` maps matrix names to directory names through the
declared alias table and nowhere else, applied to both sides before comparing. The dormant count is
67 after the fix, and every entry in it is real.

**The standard did not move.** The green light comes from adding permissions to the matrix and
adding ids to the table, not from exempting a caller (`example` is still audited, and now has a
row), not from `--all`-style weakening, and not from silencing the dormant list.

## What the 67 dormant rows mean now

They are permissions with no import edge: mostly runtime registry lookups rather than compile-time
imports. That is still the answer to "who can reach the audit log" — `supervisor`, `agenthost`,
`session`, `updater`, `shell` — and it is a deliberate list, not a surprise one. The strict mode
(`--all`) remains available for a gate that wants to drive that list to zero.

This file stays as the record of the order-of-work gap inside this build-out: the permission table
was written before the services it governs, and twelve edges were missing by the time the last
wave landed. The green light is the end of the story, not the whole story.

## The four programs the auditor used to call unknown (2026-11-02)

After round 8 gave `hello`, `heartbeat`, `echo` and `mcp-host` regression tests, the audit reported
them as `UNKNOWN (in source only)`: four directories with `.goose` files and no matrix id.

The first fix would have been to append four ids with empty rows. That is wrong here, and the
reason is checkable rather than stylistic:

| program | exports `svc_entry` | in `BOOT_ORDER.md` | cross-service imports |
|---|---|---|---|
| `hello` | no | no | none |
| `heartbeat` | no | no | none |
| `echo` | no | no | none |
| `mcp-host` | no | no | none |

None of the four is booted; they are run directly (and, for `echo`, as the child process the
Lobster host calls). They make no cross-service calls, so a row for each would be empty — and
`t69_callmatrix` asserts every row has at least one callee. An id added to satisfy that assertion
would be a permission in the table that no source makes and no boot needs: the exact drift this
file exists to remove, pointed the other way.

So the auditor's scope is now stated precisely: **a directory under `services/` is a service when
it can be booted** — it exports `svc_entry` or it is named in the boot table. The four programs are
listed by name in `NOT_SERVICES` (never a pattern), alongside `example` and `callmatrix`. The
standard did not move: no row was removed, no caller was exempted from an edge it actually makes,
and `--all` still reports the dormant list.
