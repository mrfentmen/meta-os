# bootlog — Round 11 record

Source: `services/bootlog/bootlog.goose` + `services/bootlog/entry.goose` · Test:
`services/tests/t107_bootlog_r11.goose` (plus existing `t49_bootlog`) · Status: RUNS (t49, 23 checks)

## 1. Limits — PROVEN

`os-build/layer1/LIMITS.md` lists no constant for this service. That is a generator gap, not an
absence of a limit: `BL_LINE` is the cap `record` enforces, and `t49` already names it.

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `BL_LINE` | 200 | `bootlog.goose` (`record`, `stage`) | driven | `t49_bootlog` passes `BL_LINE` as the cap and proves a 12-byte cap is refused with the buffer empty; `t107` adds the boundary (150-byte message fits, 200-byte refused, 256-byte refused, cap 0 refused) |

The header is `ticks tag level message\n`; `record` computes `need` from the formatted width and
refuses before writing a byte, so the cap is enforced, not advisory.

## 2. Refusals — PROVEN

The service returns `bool`, not a code: there is one refusal, and it has one meaning.

| refusal | answer | the test assertion that expects it |
|---|---|---|
| record does not fit the caller's cap | `false`, buffer unchanged | `t49`: `record(tight, 12, 3, "storage") == false && tight.len == 0`; `t107`: 200-byte message at `BL_LINE`, and a pre-filled builder still holding its one byte |
| message itself exceeds the cap | `false`, never truncated | `t107`: 256-byte message at `BL_LINE`, `len == 0` |
| serial write returns negative | `false` (the caller decides; the boot does not die) | not reachable on the host shim, which accepts every write — NAMED GAP, structural |

An empty message is *not* a refusal: it produces a bare stage marker (`t49`).

## 3. Restart — NOT APPLICABLE

The service holds no state. Each `stage` builds its record in a fresh stack buffer and writes it
in one call; nothing survives the call, so there is nothing for a supervisor restart to lose or
continue. What *is* lost across a restart is the serial transcript's continuity, and that is the
kernel's buffer, not this service's.

## 4. Contract — PROVEN

| direction | other | call | in the matrix? |
|---|---|---|---|
| out | kernel | `sys_ticks()` | n/a — kernel surface, not a service edge |
| out | kernel | `sys_write_serial(buf)` | n/a — kernel surface |
| in | console | the down line is printed by console on this service's absence | `SVC_BOOTLOG` row declares console, log, time, devices; all four edges are **DORMANT**: `bootlog.goose` imports no service |

`cm_set(SVC_BOOTLOG, ...)` exists, so the row is present. The edges are declarations of what the
service may reach when the console starts consuming it; today the module imports only `common`
and `std`.

## 5. Load — NAMED GAP

The test ends with the line below. Numbers are produced by the run, not written here.

`LOAD bootlog ops=220 ok=? refused=?`
RUNS pass=16 fail=0 · `LOAD bootlog ops=220 ok=220 refused=0`

220 is ten boots' worth at the published 22-stage table. The load path is the same `record` call
the boot uses, so the thing under volume is the cap check plus one serial write per line.

## 6. README truth pass — PROVEN

`services/bootlog/README.md` was stale in the two places that matter most:

- **Status** said `WRITTEN. Not COMPILED` and claimed no part of the build rests on a compiler.
  It now says RUNS, cites `t49_bootlog` (23 checks) and `t107`, and keeps the honest scope: the
  service logic runs on a host shim, nothing has booted.
- **What is not verified** claimed the module had never compiled or run. It has run; what is
  still unverified is the freestanding link and the kernel's real syscall return. Rewritten to
  say exactly that.
- The **Entry** section was right: `entry.goose` exports `svc_entry`, split from the module so a
  test importing `bootlog.bootlog` does not drag a second entry symbol in. The deviation that
  `service_main` takes no `BootInfo` is still true and stays.
