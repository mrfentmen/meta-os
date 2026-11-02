# Boot manifest — services, order, dependencies, and what their loss costs

For the image lane to consume (`os-build/face/` reads it) and for the supervisor table to be
checked against. Source of the sequence: `os-build/layer1/BOOT_ORDER.md` (22 rows) and
`services/supervisor/bootorder.goose`, which is meant to be the executable copy. Where they
disagree, the `.goose` file is the bug — but no check has ever run, so this file assumes the
document is right and says so.

**Status: the sequence is WRITTEN, not booted.** No service has ever been started in this
order, on a kernel or a host, because no kernel service loader exists. This manifest is a
contract the image lane can wire and a checker can hold, not a description of a running boot.

## The boot line this manifest must produce

```
meta-os 0.1  (K6)  <n> services degraded: <comma-separated ids>
```

The supervisor's own counter line is `started <up>/22 failed <n>` (`services/supervisor/deps.goose`).
A boot that reports clean when a service is down is the failure mode both lines exist to prevent.

## The table

`fatal` is the table's flag. `effective` is what the cascade actually does: a non-fatal service
that a *fatal* service depends on (directly or through the chain) stops the boot just as hard,
because the fatal dependant dies and takes the boot with it.

| # | service | needs | fatal | effective | what the system loses |
|---|---|---|---|---|---|
| 1 | bootlog | — | yes | **yes** | the boot record; nothing runs first |
| 2 | devices | bootlog | yes | **yes** | device inventory; drivers have no list |
| 3 | time | devices | yes | **yes** | the clock; every timeout and budget |
| 4 | storage | devices | yes | **yes** | all block storage beneath fs/audit/updater |
| 5 | callmatrix | — | yes | **yes** | authorization; every service call is unguarded |
| 6 | supervisor | callmatrix | yes | **yes** | the starter itself; nothing else launches |
| 7 | console | bootlog | no | **yes** | the user's line console — and `log` needs it, so the boot stops |
| 8 | logfmt | time | no | **yes** | uniform record format — `log` needs it, so the boot stops |
| 9 | log | console, logfmt, storage | yes | **yes** | the log sink; nothing can report a later failure |
| 10 | watchdog | time | no | no | health checks and escalation; deaths are noticed only by restart policy |
| 11 | audit | log, storage, time | no | no | the append-only record of what agents did |
| 12 | netcfg | storage | no | no | interface configuration; the network has no addresses |
| 13 | net | devices, netcfg | no | no | the packet layer; nothing above it can reach a network |
| 14 | input | log | no | no | key events; the console loses typing |
| 15 | display | log | no | no | draw calls; the console loses its screen |
| 16 | session | audit, display, input | no | no | the login and session scope; no user is at the console |
| 17 | dhcp | log, net, netcfg, time | no | no | leased addresses; only static configuration remains |
| 18 | dns | log, net, netcfg | no | no | name resolution; sockets have addresses but no names |
| 19 | socket | dns, log, net, time | no | no | the network API above layer 4 |
| 20 | timesync | log, socket, time | no | no | wall-clock correction; the monotonic clock keeps ticking |
| 21 | updater | audit, log, socket, storage, time | no | no | OS updates, including rollback |
| 22 | agenthost | audit, log, session, storage, supervisor | no | no | agents as citizens: no agent can be spawned, granted or limited |

## The two findings this table makes visible

1. **`fatal` is not the real risk flag.** `console` and `logfmt` are marked non-fatal, but `log`
   is fatal and needs both, so losing either stops the boot exactly like losing `storage`. Seven
   rows are "fatal" on paper; **nine** are fatal in effect. A boot planner that sorts by the
   `fatal` flag would under-count its own failure modes by two.
2. **The agent layer is the most fragile thing on the machine, and it is last.** `agenthost`
   needs five services, including `session` (which needs `audit`, `display`, `input`) and
   `audit` (which needs `log`, `storage`, `time`). Any of nine upstream losses removes agents
   while the machine still reports a boot. That is the correct ordering for boot stability and
   the wrong ordering if agents are the point of the OS — which, per `KERNEL_SPEC.md`, they are.

## Drift worth naming

The boot table's `log` is `services/logd/` on disk, and the boot table's `devices` is
`services/devices/` while the manifest names `devmgr` as NOT BUILT with the work living in
`devices`. The ids in this table are the boot ids, not directory names; the checker below
matches on table ids only, and the alias drift is already recorded in
`os-build/layer1/CALLMATRIX_DRIFT.md`.

## How this is checked

`os-build/layer1/boot_manifest_check.py` parses `BOOT_ORDER.md`, recomputes the dependency
closure and the effective-fatal set, and fails if this file disagrees, if an order violates
`needs < own order`, or if a service appears in one file and not the other.
