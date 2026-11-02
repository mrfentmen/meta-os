# time — Round 11 record

Source: `services/time/{time,entry,calendar}.goose` · Test: `services/tests/t136_time_r11.goose`
· Status: RUNS

## 1. Limits — NAMED GAP

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `STALL_LIMIT` | `100000` | `time.goose` | **unreachable on the host** | `LIMITS.md` says so: it is reached only by a frozen kernel clock, and the host shim's clock advances. `t136` asserts the value and the no-sleep paths; a frozen clock needs the kernel test |
| `requested_tick_hz()` | `1000` | `time.goose` | not a limit | a request to the kernel (R5), not an enforced bound; `t136` asserts the value so the one place it changes is named |

`STALL_LIMIT` is the only constant in this service that looks like a cap. `BLOCK_*`-style
declarations do not exist here; `ticks_to_ms`/`ms_to_ticks` bound nothing, they convert.

## 2. Refusals — PROVEN

This service returns trailing bools, not error codes; its refusals are the `false` half of a
conversion and the no-op half of a sleep.

| refusal | form | the test assertion that expects it |
|---|---|---|
| a zero or negative tick rate in `ticks_to_ms` | `(0, false)` | `t136` `ticks_to_ms(10, 0)` and `(10, -1)` |
| a zero tick rate in `ticks_to_us` | `(0, false)` | `t136` `ticks_to_us(1, 0)` |
| `clock_init` with a nonsense rate | replaced by `1000`, not propagated | `t136` `clock_init(0).hz == 1000`, `clock_init(-5).hz == 1000` |
| `sleep_ticks`/`sleep_ms` with zero or negative input | `true`, no clock read | `t136` four no-op assertions, including `sleep_ms(10, 0)` |
| a deadline past its instant | remaining is `0`, never negative | `t136` `deadline_remaining(d, 900) == 0` |
| a budget past its total | `clock_budget_expired` true, remainder `0` | `t136` `Budget { total: 0 }`; `clock_budget_left` is asserted non-negative |
| an already-expired wait | returns `true` without sleeping | `t136` `clock_wait(c, past)` with `at = now - 1` |

## 3. Restart — NOT APPLICABLE (state), NAMED GAP (in-flight waits)

The clock owns no persistent state. After a restart the monotonic counter is whatever the
kernel says it is; nothing here is restored and nothing needs to be. A caller's `Deadline` and
`Budget` values are ordinary data in the caller's memory and are lost with the caller, not with
this service. A sleep in progress when the process dies is simply gone; no code claims
otherwise, and `sleep_ticks` returning `false` on a stalled clock is the only in-band failure.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | every service that times anything (`SVC_LOG`, `SVC_SUPERVISOR`, `SVC_WATCHDOG`, `SVC_DHCP`, `SVC_SOCKET`, `SVC_UPDATER`, `SVC_TIMESYNC`, `SVC_AGENTHOST`, `SVC_AUDIT`, `SVC_SESSION`, `SVC_SHELL`, `SVC_EXAMPLE`, `SVC_SETTINGS`, `SVC_WALLPAPER`, `SVC_DOCK`, `SVC_DASHBOARD`, `SVC_BOARD`, `SVC_NOTIFY`) | `Clock`, deadlines, sleeps | yes — each caller's row carries `TIME` |
| out | `devices` | reading a tick source | declared on `SVC_TIME`, **dormant**: the file calls `sys_ticks`/`sys_yield`, which are the kernel surface, not the devices service |

The kernel surface (`sys_ticks`, `sys_yield`) is not a matrix edge: the matrix is service to
service, and syscalls are below it. No call this service makes is missing from the matrix.

## 5. Load — PROVEN

1000 pure conversions (500 `ticks_to_ms` + 500 `ms_to_ticks`), no clock reads and no sleeps,
so the loop measures the arithmetic path only.

RUNS pass=41 fail=0 · `LOAD time ops=1000 ok=1000 refused=0`

## 6. README truth pass — PROVEN

- `**Status: WRITTEN.** Not COMPILED — goose__toolchain_status → NOT FOUND.` → `**Status:
  RUNS**`, naming `t51_time` (24 checks) and the new driver.
- `service_main() — a self-check entry` attributed to this file was wrong: `service_main` lives
  in `entry.goose`; `time.goose` holds the clock. The bullet now says so.
- `Not verified: Compilation (no toolchain), and the one assumption … sys_ticks is monotonic` →
  the compilation half is false against the run rows and is removed; the assumption is kept and
  named, because it is still the one thing a host run cannot prove.
- The trailing `-` bullet under "Still absent, deliberately" (an empty list item) was removed.
