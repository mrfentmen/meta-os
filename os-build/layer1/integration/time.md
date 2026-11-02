# Integration pack — `time` (load order 3)

The first service in the order that **cannot start honestly without a ruling**: it exists to check
that the clock advances, so a kernel without a clock makes it fail correctly rather than start.

## 1. The entry point, exactly

```goose
// services/time/entry.goose
import time.time;
import common.sys.sys;
export "svc_entry" fn service_main() -> i32
```

No arguments, `i32` return, and every non-zero code names a specific failure:

| Return | Meaning |
|---|---|
| 1 | `requested_tick_hz()` returned a non-positive rate |
| 2 | a 10 ms sleep did not advance the clock |
| 3 | the clock advanced backwards or not at all |
| 4 | `ticks_to_ms` could not convert the delta |
| 5 | the measured sleep was longer than one second |

On success it now prints one line (added this round, because the rehearsal measured "exit 0, zero
lines" and could not tell a start from a no-op):

```text
svc time: ready ticks <n>
```

## 2. What it needs from the kernel

| Need | Freeze cell | Frozen number | Class |
|---|---|---|---|
| Read the tick counter | `sys_ticks` | — | **proposal P1** |
| Yield while waiting | `sys_yield` | **4** | frozen, in use |
| Exit with a code | `sys_exit` | **0** | frozen, in use |

`sys_ticks` is the only ask, and it is the same ask as `bootlog`'s. One ruling unblocks both, plus
`logd`, `console`, `display`, `shell` and `example`: seven services, one call.

**If P1 is refused:** the entry returns 2 at its first sleep, the supervisor records a failure, and
the load order stops at service 3. The alternative — a boot-relative counter each service keeps
itself — is worth ruling on at the same time, because it is ten lines per service and loses
wall-clock meaning.

## 3. What it runs on today

`tests/t51_time` — 24 checks, green: tick conversion at several rates, elapsed across wraparound,
deadlines, budgets, honest failure when the counter stalls (`STALL_LIMIT`), and the sleep bounds that
used to report healthy-but-fast clocks as failures.

The boot rehearsal starts it:

```text
  3  time        STARTED    1 lines, exit 0
```

Before this round that line read `STARTED 0 lines`; the status line is the difference between "it
ran" and "it exited".

## 4. The smallest kernel-side change

Same loader as `bootlog`, plus one cell:

1. a `sys_ticks()` that returns monotonic milliseconds since boot (P1);
2. the loader mapping `services/time` and calling `svc_entry`.

**The proof line** (BOOT_PLAN S7 shape):

```text
svc time: started (order 3) ticks <n>
```

The service already prints `svc time: ready ticks <n>`; the supervisor's line wraps it. Keeping both
is deliberate: one proves the service started, the other proves the clock it read is a clock.

## Risks, named

- **A tick rate that is not milliseconds.** `requested_tick_hz()` reads the configured rate; if the
  kernel's tick is 100 Hz and the config says 1000, every sleep is ten times short and the entry's
  bounds still pass. The conversion is tested, the configuration agreement is not.
- **`sleep_ticks` spins on `sys_yield`.** On a kernel with no scheduler that is a busy loop; on one
  with a scheduler it is a yield loop. Both are correct; only one is cheap.
- **The 10 ms probe is a boot-time cost.** It is the cheapest way to prove the clock moves and it
  delays the boot by design. If the boot budget is tight, the probe should be conditional.
