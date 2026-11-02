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
WRITTEN**, and no row below says COMPILED. The kernel side is equally early:
`kernel/src/main.rs` is the K1 skeleton, so K2–K6 services are blocked on kernel
milestones, not on Goose work.

Updated at the close of the build-out (B-L1-71): **21 services and 12 libraries are
WRITTEN** — the file exists, every symbol was checked, and the mechanical gates in
`os-build/layer1/` run clean over it. Three services are still **NOT BUILT**
(`registry`, `devmgr`, `sockets`): each is a README-only contract, and their real
work landed inside `callmatrix`, `devices`/`hotplug` and `socket` respectively —
the rows stay because the work order names them and a deleted row is a lost
decision. WRITTEN is a statement about text. Nothing here has run.

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
| 1 | `bootlog` | Boot-time record writer: the first thing that runs and the last thing to go quiet | K-serial | append-only boot record | B-L1-03 | WRITTEN |
| 2 | `console` | Interactive line console: echo, line editing, history | K-fb, K-key, K-sys | the user's terminal surface | B-L1-17 | WRITTEN |
| 3 | `time` | Monotonic clock service: ticks, uptime, sleep | K-timer, K-sys | `now()`, `sleep()` to every layer above | B-L1-19 | WRITTEN |
| 4 | `logfmt` | Log record formatting: levels, tags, timestamps | K-timer | one record format for the whole OS | B-L1-28 | WRITTEN |
| 5 | `logd` | Log sink: retention ring, flush policy, export | K-serial, K-timer | `log(level, tag, msg)` | B-L1-18 | WRITTEN |
| 6 | `supervisor` | Starts services in dependency order, restarts per policy | K-sched, K-sys | every other service's lifecycle | B-L1-20, 21 | WRITTEN |
| 7 | `registry` | Name → service id lookup | K-ipc | `lookup(name)` for L5–6 | B-L1-22 | NOT BUILT |
| 8 | `watchdog` | Health checks and escalation: restart, then surface | K-timer, K-sched | failure signal to supervisor + user | B-L1-23 | WRITTEN |
| 9 | `devmgr` | Device inventory and hot-plug events | K-mem, K-key | device events to drivers-above layer | B-L1-24 | NOT BUILT |
| 10 | `storage` | Block storage contract + RAM backend | K-mem | read/write blocks | B-L1-25 | WRITTEN |
| 11 | `input` | Keymap, compose, escape sequences | K-key | key events to console/shell | B-L1-26 | WRITTEN |
| 12 | `display` | Text grid, cursor, minimal attributes | K-fb | draw calls to console/shell | B-L1-27 | WRITTEN |
| 13 | `netcfg` | Interface model, address assignment, persistence | K-ipc | configured interfaces to sockets | B-L1-30, 104 | WRITTEN |
| 14 | `dhcp` | DHCP client over the packet interface | K-ipc + packet driver below | addresses to netcfg | B-L1-31 | WRITTEN |
| 15 | `dns` | Resolver client | K-ipc | `resolve(name)` | B-L1-32 | WRITTEN |
| 16 | `sockets` | Socket contract: bind, connect, send, recv | K-ipc | the network API for L5–6 | B-L1-33 | NOT BUILT |
| 17 | `timesync` | NTP-style time sync client | K-timer, sockets | corrected wall clock | B-L1-37 | WRITTEN |
| 18 | `updater` | Checks, stages, verifies, applies, rolls back | K-ipc, storage | OS update as a service, not a script | B-L1-34..36 | WRITTEN |
| 19 | `audit` | Append-only record of what agents did, readable by the user | K-ipc, storage | the audit trail the OS promises | B-L1-41, 42 | WRITTEN |
| 20 | `agenthost` | Agent process table, lifecycle, capability grants, quotas | K-sched, K-ipc | agents as citizens: spawn, grant, limit | B-L1-38..40, 116 | WRITTEN |
| 21 | `session` | Login flow, user identity, session scope | K-ipc | who is at the console | B-L1-43, 114 | WRITTEN |
| 22 | `fs` | Filesystem: files, directories, paths over the storage contract | K-mem, storage | the layer above stops thinking in blocks | B-L1-79..84 | WRITTEN |
| 23 | `shell` | Command shell: parser, builtins, scripts | console, fs | the user's and agent's command surface | B-L1-87..92 | WRITTEN |
| 24 | `example` | The reference service: a template that does one thing well | K-serial | a copyable shape for new services | B-L1-94 | WRITTEN |

## Shared libraries (not services, but in the same tree)

These live in `services/common/` and are imported by the services above. They
are listed here because the manifest is the index, and a service is not WRITTEN
if it leans on a library that does not exist yet.

| Library | Purpose | Task | Status |
|---|---|---|---|
| `sys` | Syscall externs + C shim specification | B-L1-09 | WRITTEN |
| `fmt` | Fixed-buffer formatting: int, hex, pad, append | B-L1-10 | WRITTEN |
| `ring` | Byte ring and message ring over caller storage | B-L1-11 | WRITTEN |
| `err` | Error codes + trailing-bool result convention | B-L1-12 | WRITTEN |
| `cfg` | key=value config parser with typed getters | B-L1-13 | WRITTEN |
| `hash` | CRC32 and SHA-256 from their specifications | B-L1-14 | WRITTEN |
| `args` | Shell-style argument parser | B-L1-88 | WRITTEN |
| `json` | JSON subset reader/writer | B-L1-120 | WRITTEN |
| `boot` | BootInfo types, mirroring the K2 framebuffer struct | B-L1-08 | WRITTEN |
| `bytes` | Byte helpers: find, compare, copy with explicit caps | B-L1-68 | WRITTEN |
| `str` | String helpers over `u8` slices | B-L1-69 | WRITTEN |
| `hex` | Hex encode/decode | B-L1-70 | WRITTEN |
| `enc` | Base64 and percent encoding | B-L1-122 | WRITTEN |
| `text` | Line wrapping, padding, column layout | B-L1-142 | WRITTEN (no consumer yet) |
| `table` | Fixed-capacity table of records | B-L1-143 | WRITTEN (no consumer yet) |
| `sort` | Insertion and quick sort over caller storage | B-L1-144 | WRITTEN (no consumer yet) |
| `pool` | Fixed-block pool with generations | B-L1-145 | WRITTEN (no consumer yet) |

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
