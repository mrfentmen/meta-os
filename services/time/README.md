# `time` — Layer 4, service 3

**Status: WRITTEN.** Not COMPILED — `goose__toolchain_status` → `NOT FOUND`.

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
- `service_main()` — a self-check entry: sleep 10 ms, prove the counter moved,
  return a distinct non-zero code for each way it could have failed.

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

Compilation (no toolchain), and the one assumption this file makes about the
kernel: that `sys_ticks` is monotonic and cheap enough to poll. Neither is
proven by anything in this repo today.
