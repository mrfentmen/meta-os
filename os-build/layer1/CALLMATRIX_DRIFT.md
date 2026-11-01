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
