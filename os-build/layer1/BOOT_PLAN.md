# BOOT_PLAN — loading Layer 4 into the kernel (BF4-12)

> Counts in this file are as of the round it records. Live numbers: `COUNTS.md`.

Written 2026-11-01 night, for the 2026-11-02 ruling on the syscall surface. The
point of writing it now is that nobody designs a load sequence at 03:00 with a
build failing. **Nothing in this document has been run against a kernel.** The
order it uses is `BOOT_ORDER.md` (proven as a dependency table by
`bootorder_check.py`); the mechanism is new text and is no stronger than the
ruling it waits on.

Status words used here are the standing ones: DESIGNED / WRITTEN / TYPECHECKS /
RUNS / DEAD. Every claim names its evidence.

---

## 0. What "loading a service" does not mean today

There is no load path. What exists:

- `services/` compiles as one root per service (`services/root_<svc>.goose`);
  every root and every test typechecks (`check_services.sh`: 39 ok, 0 failed —
  that count is roots plus test roots, not 39 services).
- 33 programs **run** natively against `host_shim.c` (`run_rows.txt`: 33 test
  rows, 1,253 assertions, 0 failures — measured 2026-11-02). That proves logic against a real clock and real memory. It does
  not prove an image the kernel can load, because the shim is a linker
  substitution: no address space, no privilege boundary, no entry protocol.
- `services/*/entry.goose` exports `svc_entry` and is built but not run. Five
  entries build; one (`example`) typechecks only because its `svc_entry` takes a
  `BootInfo` with no host boot block. That gap is the load path, named.

So the first step of any load plan is not "start service 1". It is "produce one
freestanding image, for one service, that the kernel can jump to".

## 1. Preconditions, in the order they unblock

| # | precondition | owner | why it is first | evidence it is met |
|---|---|---|---|---|
| A | Ruling on the syscall surface (P1 `sys_ticks`, P2 net, P3 spawn/kill, P4 sleep) — `PROPOSALS.md` | Pax | every waiting service calls ticks; without a ruling no service can even log its own start time | the ruled document |
| B | `svc_entry` calling convention fixed (Q-B-L1-1: arg registers, stack cleanup, return = exit code) | Rowan / OpenCode | the entry point is the load path's ABI; guessing it writes a loader twice | one line in `kernel/MAC_QUESTIONS.md` |
| C | BootInfo delivery fixed (Q-B-L1-11: argument pointer vs fixed address vs syscall) | Rowan | `console`/`example` cannot start without it; `boot_log` fields come from it | same file |
| D | Per-process static storage size + zeroing rule (Q-B-L1-9, Q-B-L1-10) | Rowan | Goose services never allocate; the size is a linker constant, and `ring`/`bootlog`/`audit` assume zeroed slots | a number and a yes/no |
| E | One image format that a freestanding link can produce (Q-B-L1-13 area; K6_SERVICE_SHAPE §1 OPEN) | OpenCode | without it there is nothing to put in the task's memory | a file in `kernel/` and its size |

A–E are the whole of "when a syscall surface is ruled". None of them is a
Layer 4 decision; three are one-line answers, two are kernel-side formatting.

## 2. The stages, and the exact line that proves each

Each stage is one commit, one boot, one log line. The line is quoted here so the
gate is a grep, not an opinion. `S<n>` runs before `S<n+1>` and a failed stage
stops the sequence: a boot that proceeds past a failed `storage` is a boot that
will fail in a way nobody can attribute.

| stage | what the kernel does | proof line (exact) | fatal |
|---|---|---|---|
| S0 | bootloader → kernel, K1 alive line | `META OS KERNEL - alive (K1)` | yes |
| S1 | map a single static image at a fixed address, jump, service returns | `K6 load: image n bytes at 0x......... entry 0x.........` | yes |
| S2 | first service: `bootlog`, writes one line through `sys_write_serial` | `svc bootlog: 0 `<count>` bytes` | yes |
| S3 | `BootInfo` delivered; service echoes two fields back | `svc bootlog: bootinfo ok framebuffer 0x........ ticks 100` | yes |
| S4 | second image, separate address space — proves the loader is not one-shot | `K6 load: 2 images, 2 address spaces` | yes |
| S5 | kernel-started supervisor (`BootEntry.by_kernel`), which loads `callmatrix` itself | `svc supervisor: table 6/22 running, callmatrix granted` | yes |
| S6 | `storage` up, then `log` — first service that can fail without stopping the boot | `svc log: up, 2 sinks, retention 10 KiB` | yes for storage, no for log |
| S7 | rest of `BOOT_ORDER.md` in table order, each announcing itself | `svc <name>: started (order <n>)` | per table |

S1–S3 are the real work: one image, one address space, one BootInfo. Everything
after S4 is repetition of a proven mechanism plus the dependency table that
already passes its checker.

## 3. Why S5 is the supervisor and not something easier

`BOOT_ORDER.md` makes the supervisor service 6 and started by the kernel,
because it is the thing that starts 7–22. A load path that cannot start the
supervisor can still boot 5 services and will never boot 22. So S5 is the
honest "half the OS is real" line, and it is worth doing before S6–S7 rather
than after: if the supervisor cannot load a child, every later stage is a lie
about who started what.

## 4. What the kernel prints when a load fails

Not optional, and not `panic!`. Three lines, each greppable, because a failed
load that prints nothing looks exactly like a slow boot:

```
K6 load: image <name> FAILED <reason> at <offset>
K6 load: <name> faulted at 0x<addr>, killing task <pid>
K6 load: stage <n> abandoned, <k> services running
```

`<reason>` is one of a closed set: `too-large`, `bad-magic`, `unmappable`,
`no-storage`, `entry-out-of-range`. A closed set is the point: the gate can
assert that a failure line exists, and a new reason is a deliberate edit rather
than a string that happened to be written in a hurry.

## 5. Day-1 load set, if the ruling is only P1 (`sys_ticks`)

If Pax rules P1 and nothing else, this is what loads, in order, and it is a
complete answer to "what does the OS boot into":

1. `bootlog` — writes to serial; needs ticks + write.
2. `devices` — enumerates what the kernel told it in BootInfo; no storage yet.
3. `time` — ticks + yield.
4. `console` — ticks + write_console + read_key.
5. `callmatrix` — pure table, no syscalls at all.
6. `supervisor` — kernel-started; can start 1–5 again but cannot restart a
   crashed child with effect until P3.

That is four services with a real process and one table with none, and it is
the honest ceiling until P2: no `log` (needs storage), no `net`, no `socket`, no
`session`, no `agenthost`. `agenthost` is the one that matters — the agent
runtime is the reason the OS exists — and it sits behind `log`, `storage`,
`audit` and `session`. Anyone asking "when can an agent run on it" should read
this paragraph, not the milestone list.

## 6. Open, and deliberately not decided here

- **Shared read-only pages** (Q-B-L1-12): `callmatrix` and `registry` currently
  assume a copy per process, which drifts. If the ruling is "no sharing", the
  plan is to regenerate the table at start from one source of truth instead of
  sharing a page — a Layer 4 change, not a kernel one.
- **Who kills on timeout** (Q-B-L1-14): the design says the supervisor asks and
  the kernel kills only on timeout. That needs `sys_kill` (P3) to have any
  meaning.
- **Image format** (E above): until OpenCode answers, this document's S1 is a
  description, not a plan.

## 7. The one sentence version

One freestanding image, one address space, one BootInfo block, then the
existing dependency table repeated until the table is empty — and the gate is a
log line per stage, quoted above, so "it boots" is a file and not a memory.
