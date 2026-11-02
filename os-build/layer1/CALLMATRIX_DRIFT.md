# Call-matrix drift (B-L1-118)

Produced by `python3 os-build/layer1/callmatrix_audit.py` against the tree as of this
branch. Status: **CLOSED for the six missing edges and the six UNKNOWN services, as of R7.** The
matrix now declares ids 1–30 and every service directory resolves. The body below is the
original report kept as the record of what was wrong; the appendix is the audit as it runs
today. Permissions are still a policy surface: adding a row is Pax's call, not the lane's.

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

## Findings — DORMANT permissions (65 when this was written; 95 now)

Not a defect. The count grew with the services: the six face services and `notify` added rows
before anything imported them, which is the deliberate order described in the matrix — declare
the edge, then wire it — and is why the number here is a date, not a defect count. Two readings are both true: the code paths that use these edges go through the
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
call-matrix audit  (31 services in the matrix, 32 with sources)

DORMANT permission (95, informational):
  agenthost    -> audit        allowed, not called from a source
  agenthost    -> logd         allowed, not called from a source
  agenthost    -> session      allowed, not called from a source
  agenthost    -> storage      allowed, not called from a source
  agenthost    -> supervisor   allowed, not called from a source
  agenthost    -> time         allowed, not called from a source
  audit        -> logd         allowed, not called from a source
  audit        -> storage      allowed, not called from a source
  audit        -> time         allowed, not called from a source
  board        -> logd         allowed, not called from a source
  board        -> net          allowed, not called from a source
  board        -> notify       allowed, not called from a source
  board        -> storage      allowed, not called from a source
  board        -> time         allowed, not called from a source
  bootlog      -> console      allowed, not called from a source
  bootlog      -> devices      allowed, not called from a source
  bootlog      -> logd         allowed, not called from a source
  bootlog      -> time         allowed, not called from a source
  console      -> bootlog      allowed, not called from a source
  console      -> logd         allowed, not called from a source
  dashboard    -> logd         allowed, not called from a source
  dashboard    -> session      allowed, not called from a source
  dashboard    -> settings     allowed, not called from a source
  dashboard    -> supervisor   allowed, not called from a source
  dashboard    -> watchdog     allowed, not called from a source
  devices      -> bootlog      allowed, not called from a source
  devices      -> logd         allowed, not called from a source
  dhcp         -> logd         allowed, not called from a source
  dhcp         -> net          allowed, not called from a source
  dhcp         -> time         allowed, not called from a source
  display      -> logd         allowed, not called from a source
  display      -> session      allowed, not called from a source
  dns          -> logd         allowed, not called from a source
  dns          -> net          allowed, not called from a source
  dock         -> logd         allowed, not called from a source
  dock         -> session      allowed, not called from a source
  dock         -> settings     allowed, not called from a source
  dock         -> storage      allowed, not called from a source
  example      -> logd         allowed, not called from a source
  fs           -> logd         allowed, not called from a source
  input        -> display      allowed, not called from a source
  input        -> logd         allowed, not called from a source
  input        -> session      allowed, not called from a source
  logd         -> console      allowed, not called from a source
  logd         -> logfmt       allowed, not called from a source
  logd         -> storage      allowed, not called from a source
  logd         -> time         allowed, not called from a source
  logfmt       -> time         allowed, not called from a source
  net          -> devices      allowed, not called from a source
  net          -> logd         allowed, not called from a source
  netcfg       -> logd         allowed, not called from a source
  netcfg       -> net          allowed, not called from a source
  netcfg       -> storage      allowed, not called from a source
  notify       -> logd         allowed, not called from a source
  notify       -> time         allowed, not called from a source
  session      -> audit        allowed, not called from a source
  session      -> display      allowed, not called from a source
  session      -> input        allowed, not called from a source
  session      -> logd         allowed, not called from a source
  session      -> time         allowed, not called from a source
  settings     -> logd         allowed, not called from a source
  settings     -> storage      allowed, not called from a source
  settings     -> time         allowed, not called from a source
  socket       -> dns          allowed, not called from a source
  socket       -> logd         allowed, not called from a source
  socket       -> time         allowed, not called from a source
  storage      -> devices      allowed, not called from a source
  storage      -> logd         allowed, not called from a source
  supervisor   -> agenthost    allowed, not called from a source
  supervisor   -> audit        allowed, not called from a source
  supervisor   -> logd         allowed, not called from a source
  supervisor   -> session      allowed, not called from a source
  supervisor   -> time         allowed, not called from a source
  supervisor   -> watchdog     allowed, not called from a source
  time         -> devices      allowed, not called from a source
  timesync     -> logd         allowed, not called from a source
  timesync     -> socket       allowed, not called from a source
  timesync     -> time         allowed, not called from a source
  updater      -> audit        allowed, not called from a source
  updater      -> logd         allowed, not called from a source
  updater      -> socket       allowed, not called from a source
  updater      -> storage      allowed, not called from a source
  updater      -> time         allowed, not called from a source
  updater_client -> logd         allowed, not called from a source
  updater_client -> net          allowed, not called from a source
  updater_client -> notify       allowed, not called from a source
  updater_client -> socket       allowed, not called from a source
  updater_client -> time         allowed, not called from a source
  updater_client -> updater      allowed, not called from a source
  wallpaper    -> logd         allowed, not called from a source
  wallpaper    -> settings     allowed, not called from a source
  wallpaper    -> storage      allowed, not called from a source
  watchdog     -> logd         allowed, not called from a source
  watchdog     -> supervisor   allowed, not called from a source
  watchdog     -> time         allowed, not called from a source

clean on permissions; 95 dormant row(s) reported above
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

## What the dormant rows mean now

They are permissions with no import edge: mostly runtime registry lookups rather than compile-time
imports. That is still the answer to "who can reach the audit log" — `supervisor`, `agenthost`,
`session`, `updater`, `shell` — and it is a deliberate list, not a surprise one. The strict mode
(`--all`) remains available for a gate that wants to drive that list to zero.

This file stays as the record of the order-of-work gap inside this build-out: the permission table
was written before the services it governs, and twelve edges were missing by the time the last
wave landed. The green light is the end of the story, not the whole story.

## Appendix — the audit, regenerated (2026-11-02)

```
call-matrix audit  (31 services in the matrix, 32 with sources)

DORMANT permission (95, informational):
  agenthost    -> audit        allowed, not called from a source
  agenthost    -> logd         allowed, not called from a source
  agenthost    -> session      allowed, not called from a source
  agenthost    -> storage      allowed, not called from a source
  agenthost    -> supervisor   allowed, not called from a source
  agenthost    -> time         allowed, not called from a source
  audit        -> logd         allowed, not called from a source
  audit        -> storage      allowed, not called from a source
  audit        -> time         allowed, not called from a source
  board        -> logd         allowed, not called from a source
  board        -> net          allowed, not called from a source
  board        -> notify       allowed, not called from a source
  board        -> storage      allowed, not called from a source
  board        -> time         allowed, not called from a source
  bootlog      -> console      allowed, not called from a source
  bootlog      -> devices      allowed, not called from a source
  bootlog      -> logd         allowed, not called from a source
  bootlog      -> time         allowed, not called from a source
  console      -> bootlog      allowed, not called from a source
  console      -> logd         allowed, not called from a source
  dashboard    -> logd         allowed, not called from a source
  dashboard    -> session      allowed, not called from a source
  dashboard    -> settings     allowed, not called from a source
  dashboard    -> supervisor   allowed, not called from a source
  dashboard    -> watchdog     allowed, not called from a source
  devices      -> bootlog      allowed, not called from a source
  devices      -> logd         allowed, not called from a source
  dhcp         -> logd         allowed, not called from a source
  dhcp         -> net          allowed, not called from a source
  dhcp         -> time         allowed, not called from a source
  display      -> logd         allowed, not called from a source
  display      -> session      allowed, not called from a source
  dns          -> logd         allowed, not called from a source
  dns          -> net          allowed, not called from a source
  dock         -> logd         allowed, not called from a source
  dock         -> session      allowed, not called from a source
  dock         -> settings     allowed, not called from a source
  dock         -> storage      allowed, not called from a source
  example      -> logd         allowed, not called from a source
  fs           -> logd         allowed, not called from a source
  input        -> display      allowed, not called from a source
  input        -> logd         allowed, not called from a source
  input        -> session      allowed, not called from a source
  logd         -> console      allowed, not called from a source
  logd         -> logfmt       allowed, not called from a source
  logd         -> storage      allowed, not called from a source
  logd         -> time         allowed, not called from a source
  logfmt       -> time         allowed, not called from a source
  net          -> devices      allowed, not called from a source
  net          -> logd         allowed, not called from a source
  netcfg       -> logd         allowed, not called from a source
  netcfg       -> net          allowed, not called from a source
  netcfg       -> storage      allowed, not called from a source
  notify       -> logd         allowed, not called from a source
  notify       -> time         allowed, not called from a source
  session      -> audit        allowed, not called from a source
  session      -> display      allowed, not called from a source
  session      -> input        allowed, not called from a source
  session      -> logd         allowed, not called from a source
  session      -> time         allowed, not called from a source
  settings     -> logd         allowed, not called from a source
  settings     -> storage      allowed, not called from a source
  settings     -> time         allowed, not called from a source
  socket       -> dns          allowed, not called from a source
  socket       -> logd         allowed, not called from a source
  socket       -> time         allowed, not called from a source
  storage      -> devices      allowed, not called from a source
  storage      -> logd         allowed, not called from a source
  supervisor   -> agenthost    allowed, not called from a source
  supervisor   -> audit        allowed, not called from a source
  supervisor   -> logd         allowed, not called from a source
  supervisor   -> session      allowed, not called from a source
  supervisor   -> time         allowed, not called from a source
  supervisor   -> watchdog     allowed, not called from a source
  time         -> devices      allowed, not called from a source
  timesync     -> logd         allowed, not called from a source
  timesync     -> socket       allowed, not called from a source
  timesync     -> time         allowed, not called from a source
  updater      -> audit        allowed, not called from a source
  updater      -> logd         allowed, not called from a source
  updater      -> socket       allowed, not called from a source
  updater      -> storage      allowed, not called from a source
  updater      -> time         allowed, not called from a source
  updater_client -> logd         allowed, not called from a source
  updater_client -> net          allowed, not called from a source
  updater_client -> notify       allowed, not called from a source
  updater_client -> socket       allowed, not called from a source
  updater_client -> time         allowed, not called from a source
  updater_client -> updater      allowed, not called from a source
  wallpaper    -> logd         allowed, not called from a source
  wallpaper    -> settings     allowed, not called from a source
  wallpaper    -> storage      allowed, not called from a source
  watchdog     -> logd         allowed, not called from a source
  watchdog     -> supervisor   allowed, not called from a source
  watchdog     -> time         allowed, not called from a source

clean on permissions; 95 dormant row(s) reported above
```
