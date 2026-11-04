# `time` — Layer 4, service 3

**Status: COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/time/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — driven by `tests/t51_time` (24 checks) and
`tests/t136_time_r11`. B-L1-04 wrote the clock core; B-L1-19 added the deadline and
budget surface.

## What it does

The monotonic clock for the layer: tick-to-millisecond conversion, sleep, and
the one rate constant the whole layer refers to.

- `requested_tick_hz()` — the layer's **request** to the kernel: 1000 Hz (one
  tick per millisecond). Requirement R5: the kernel honours it or publishes
  what it actually uses in BootInfo.
- `ticks_to_ms(ticks, hz) -> i64, bool` — trailing-bool, because a zero tick
  rate is a kernel fault and the caller must see it.
- `ms_to_ticks(ms, hz) -> i64` — rounding down; `0` ms is a legal no-sleep.
- `sleep_ticks(n)` / `sleep_ms(ms, hz)` — poll `sys_ticks` and `sys_yield`,
  with a stall detector that returns `false` rather than spinning forever on a
  clock that never advances.
- `entry.goose` — a self-check entry: sleep 10 ms, prove the counter moved,
  return a distinct non-zero code for each way it could have failed. The clock
  itself lives in `time.goose`.

## Why this is the second service

The console needs the framebuffer (K2) and the keyboard (K3). Time needs only a
tick. With `bootlog` and `time` in place, every later service can record *when*
it failed as well as what.

## The gap that is not papered over

A real time service answers other services over IPC. **IPC does not exist** —
the transport is open question Q9, and no kernel message path is landed. So this
file is the clock core plus a self-check, and there is no request handler.
Writing one against an invented transport would be a mock.

Polling with `sys_yield` costs CPU the scheduler could give elsewhere; B-L1-51
measures it and, if it is bad, the fix is a kernel wait primitive — recorded as
a requirement, not hidden in the service.

## Kernel surface

```goose
extern fn sys_ticks() -> i64;
extern fn sys_yield();
```

`sys_ticks` must be monotonic (K3 timer). `sys_yield` must actually return the
CPU to the scheduler (K5) — a `yield` that is a no-op makes every sleep in the
layer a hard spin, which is why it is requirement R6.

## Verification

| Symbol / form | Source |
|---|---|
| `extern fn` | `spec#40`, `reference#106` |
| `export "svc_entry" fn` | `spec#41`, `reference#108` |
| `-> i64, bool` trailing bool | `samples/04_errors.goose`, `samples/01_tour.goose` |
| `while`, `if`, `return`, `var`, `let` | `list_keywords` |
| top-level declarations | `reference#5` |

## Not verified

The one assumption this file makes about the kernel: that `sys_ticks` is
monotonic and cheap enough to poll. Compilation and the pure surface are exercised
by `t51_time` and `t136_time_r11` on the host; monotonicity under the real timer
is not.

## B-L1-19: deadlines and budgets

The core converts and sleeps. What services schedule against is this:

| Type / function | Does |
|---|---|
| `Clock { hz }` / `clock_init` | carries the tick rate once; a nonsense rate is replaced, not propagated |
| `Deadline { at }` / `clock_after(c, ms)` | an **absolute** tick instant |
| `deadline_expired` / `deadline_remaining` / `remaining_ms` | remaining time, **clamped at zero** |
| `clock_wait(c, d)` | wait to the deadline; `false` if the clock stalled |
| `Budget` / `clock_budget` / `budget_left` / `budget_expired` | a total time for a multi-step operation |
| `ticks_to_us` | sub-tick resolution, rounded down |
| `clock_ok(c)` | is the clock advancing at all — call once at start-up |

**Why deadlines are absolute.** A duration passed down a chain of helpers restarts
at every hop, and a 50 ms timeout becomes 300 ms. An absolute instant is computed
once and compared everywhere.

**Why remaining time is clamped at zero.** A negative "remaining" subtracted from a
budget silently *adds* time on a slow path.

**Why budgets pass the remainder to each step.** Each step getting the original
20 ms is how a six-step operation takes two minutes.

## Still absent, deliberately

- **No calendar or time zones** — B-L1-110.
- **No settable clock.** Monotonic only; wall-clock correction is an offset held by
  the time sync client (B-L1-37), never a change to this counter. **No timer service.** Waking another process needs K5 and the IPC transport
  (Q-B-L1-2); a wake list here would be fiction.
