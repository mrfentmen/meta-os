# Layer 4 — Goose service worklist

Status: the first Goose services, in build order. One line each: what it does,
what it needs from Layers 1–3 (the kernel), what it offers Layers 5–6 (agent
runtime and shell), and its honest status word.

Source of this list: `BUFFY_LAYER1_TASKS.md` (order B-L1-01),
`OPENCODE_OS_BUILD.md` Section K (OS-153..166), and the library/service split
the work order itself lays down in Wave A/B. Nothing here is invented; every
service below is named in the work order and appears in the task numbers next
to it.

## Status words — used with no wiggle room

- **DESIGNED** — a contract/spec exists, grounded in the Goose docs.
- **WRITTEN** — Goose source exists, every symbol verified against `goose__*`.
- **COMPILED** — only with a build log from a real Goose toolchain.
- **NOT BUILT** — anything else.

Measured today, 2026-11-01: `goose__toolchain_status` returns
`Goose toolchain: NOT FOUND / Looked for: goose (from PATH)`. There is no Goose
compiler on this machine, so **nothing in this layer can honestly rise above
WRITTEN on the day this list was written**, and most of it starts at NOT BUILT.
The kernel side is equally early: `kernel/src/main.rs` is the K1 skeleton, so
K2–K6 services are blocked on kernel milestones, not on Goose work.

## Kernel surface this layer assumes

Named here once so the per-service "needs" column can stay short. Every line is
a **requirement on Layers 1–3, not a fact** — the K-numbers are from
`KERNEL_SPEC.md`, and none of K2 upward is proven yet.

| Tag | Capability | Kernel milestone |
|---|---|---|
| K-serial | write bytes to the serial port | K1 (skeleton exists) |
| K-fb | framebuffer text/box drawing | K2 |
| K-timer | monotonic ticks, at least 100 Hz | K3 |
| K-key | scancode/key events | K3 |
| K-mem | heap or arena allocation, paging | K4 |
| K-sched | tasks, context switch, sleep/wake | K5 |
| K-sys | syscall entry: exit, write_serial, write_console, read_key, ticks, yield | K6 |
| K-ipc | message passing between processes (shape OPEN, question Q9) | K6+ |

## Services, in build order

| # | Service | What it does | Needs from L1–3 | Offers L5–6 | Task | Status |
|---|---|---|---|---|---|---|
| 1 | `bootlog` | Boot-time record writer: the first thing that runs and the last thing to go quiet | K-serial | append-only boot record | B-L1-03 | NOT BUILT |
| 2 | `console` | Interactive line console: echo, line editing, history | K-fb, K-key, K-sys | the user's terminal surface | B-L1-17 | NOT BUILT |
| 3 | `time` | Monotonic clock service: ticks, uptime, sleep | K-timer, K-sys | `now()`, `sleep()` to every layer above | B-L1-19 | NOT BUILT |
| 4 | `logfmt` | Log record formatting: levels, tags, timestamps | K-timer | one record format for the whole OS | B-L1-28 | NOT BUILT |
| 5 | `logd` | Log sink: retention ring, flush policy, export | K-serial, K-timer | `log(level, tag, msg)` | B-L1-18 | NOT BUILT |
| 6 | `supervisor` | Starts services in dependency order, restarts per policy | K-sched, K-sys | every other service's lifecycle | B-L1-20, 21 | NOT BUILT |
| 7 | `registry` | Name → service id lookup | K-ipc | `lookup(name)` for L5–6 | B-L1-22 | NOT BUILT |
| 8 | `watchdog` | Health checks and escalation: restart, then surface | K-timer, K-sched | failure signal to supervisor + user | B-L1-23 | NOT BUILT |
| 9 | `devmgr` | Device inventory and hot-plug events | K-mem, K-key | device events to drivers-above layer | B-L1-24 | NOT BUILT |
| 10 | `storage` | Block storage contract + RAM backend | K-mem | read/write blocks | B-L1-25 | NOT BUILT |
| 11 | `input` | Keymap, compose, escape sequences | K-key | key events to console/shell | B-L1-26 | NOT BUILT |
| 12 | `display` | Text grid, cursor, minimal attributes | K-fb | draw calls to console/shell | B-L1-27 | NOT BUILT |
| 13 | `netcfg` | Interface model, address assignment, persistence | K-ipc | configured interfaces to sockets | B-L1-30, 104 | NOT BUILT |
| 14 | `dhcp` | DHCP client over the packet interface | K-ipc + packet driver below | addresses to netcfg | B-L1-31 | NOT BUILT |
| 15 | `dns` | Resolver client | K-ipc | `resolve(name)` | B-L1-32 | NOT BUILT |
| 16 | `sockets` | Socket contract: bind, connect, send, recv | K-ipc | the network API for L5–6 | B-L1-33 | NOT BUILT |
| 17 | `timesync` | NTP-style time sync client | K-timer, sockets | corrected wall clock | B-L1-37 | NOT BUILT |
| 18 | `updater` | Checks, stages, verifies, applies, rolls back | K-ipc, storage | OS update as a service, not a script | B-L1-34..36 | NOT BUILT |
| 19 | `audit` | Append-only record of what agents did, readable by the user | K-ipc, storage | the audit trail the OS promises | B-L1-41, 42 | NOT BUILT |
| 20 | `agenthost` | Agent process table, lifecycle, capability grants, quotas | K-sched, K-ipc | agents as citizens: spawn, grant, limit | B-L1-38..40, 116 | NOT BUILT |
| 21 | `session` | Login flow, user identity, session scope | K-ipc | who is at the console | B-L1-43, 114 | NOT BUILT |
| 22 | `fs` | Filesystem: files, directories, paths over the storage contract | K-mem, storage | the layer above stops thinking in blocks | B-L1-79..84 | NOT BUILT |
| 23 | `shell` | Command shell: parser, builtins, scripts | console, fs | the user's and agent's command surface | B-L1-87..92 | NOT BUILT |
| 24 | `example` | The reference service: a template that does one thing well | K-serial | a copyable shape for new services | B-L1-94 | NOT BUILT |

## Shared libraries (not services, but in the same tree)

These live in `services/common/` and are imported by the services above. They
are listed here because the manifest is the index, and a service is not WRITTEN
if it leans on a library that does not exist yet.

| Library | Purpose | Task | Status |
|---|---|---|---|
| `sys` | Syscall externs + C shim specification | B-L1-09 | NOT BUILT |
| `fmt` | Fixed-buffer formatting: int, hex, pad, append | B-L1-10 | NOT BUILT |
| `ring` | Byte ring and message ring over caller storage | B-L1-11 | NOT BUILT |
| `err` | Error codes + trailing-bool result convention | B-L1-12 | NOT BUILT |
| `cfg` | key=value config parser with typed getters | B-L1-13 | NOT BUILT |
| `hash` | CRC32 and SHA-256 from their specifications | B-L1-14 | NOT BUILT |
| `args` | Shell-style argument parser | B-L1-88 | NOT BUILT |
| `json` | JSON subset reader/writer | B-L1-120 | NOT BUILT |
| `boot` | BootInfo types, mirroring the K2 framebuffer struct | B-L1-08 | NOT BUILT |

## What is deliberately not here

- **No mock backends.** Interface-first tasks (B-L1-29, 73, 74) write a
  contract with the transport left OPEN; a fake device presenting itself as
  hardware is forbidden by the work order and by `KERNEL_SPEC.md` rule 6.
- **No Debian work.** The work order says the Debian image is a development
  carrier only and nothing in this lane touches it.
- **No programs.** Imperium, Custos, Musica and everything under `os/worlds/`
  are Layer 7 programs, not this layer.

## Next action

B-L1-02 writes the service contract these 24 entries all assume, then B-L1-03
and B-L1-04 write the first two services for real (`bootlog`, `time`).
