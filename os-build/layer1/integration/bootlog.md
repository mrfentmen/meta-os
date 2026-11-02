# Integration pack — `bootlog` (load order 1)

The first thing that must work in any boot, because it is the thing that proves the others started.

## 1. The entry point, exactly

```goose
// services/bootlog/entry.goose
import bootlog.bootlog;
export "svc_entry" fn service_main() -> i32
```

- **No arguments.** It takes nothing, so the loader needs no `BootInfo` plumbing to start it.
- **Returns `i32`**: `0` is a clean stop, anything else is a failure the supervisor records.
- **Called once.** A second call repeats the three lines; it is not idempotent by design, because a
  boot log that silently ignores its own restart is worse than one that logs it again.

What it does, in order (`entry.goose`): `stage(LEVEL_INFO, "start")`, then `"serial path up"`, then
`"ready"`, and returns 0. `stage` formats one record and writes it through `sys_write_serial`.

## 2. What it needs from the kernel

| Need | Freeze cell | Frozen number | Class |
|---|---|---|---|
| Write one record to the serial port | `sys_write_serial` | **1** | frozen, in use |
| Timestamp the record | `sys_ticks` | — | **proposal P1** (`PROPOSALS.md`) |
| Exit cleanly | `sys_exit` | **0** | frozen, in use |

Nothing else. The other calls that appear in the manifest for this service (`sys_read_key`,
`sys_yield`, `sys_write_console`) come from modules it imports for shared formatting, not from its
start path.

**Consequence if P1 is refused:** `sys_ticks()` returns 0 in the shim and would return 0 on a kernel
without the call, so every record reads `0 bootlog 1 start`. The boot log still proves order; it
loses elapsed time. That is the degradation to rule on, and it is small.

## 3. What it runs on today

`host/host_shim.c` implements `sys_write_serial` over `write(1)` and `sys_ticks` over a monotonic
clock, so the service is run for real: `tests/t49_bootlog` (23 checks) and the boot rehearsal, where
it is the first service that starts:

```text
  1  bootlog     STARTED    3 lines, exit 0
```

Its transcript lines are in `BOOT_REHEARSAL.md`; the record format is checked in `t49`.

## 4. The smallest kernel-side change

**A single static image the kernel can jump to.** No syscall work: numbers 0 and 1 exist, and P1 is
the only ask.

The change, in `BOOT_PLAN.md` terms, is S1–S2:

1. link `services/bootlog` freestanding to one flat image at a known base;
2. map it, jump to `svc_entry`, and let it return;
3. the kernel keeps `sys_write_serial` pointed at the UART.

**The proof line** (BOOT_PLAN S2, quoted so the gate is a grep):

```text
svc bootlog: 0 <count> bytes
```

Today the rehearsal cannot produce that line, because nothing counts the bytes: `stage` returns a
bool. If the kernel side needs a byte count, that is a one-line change in `entry.goose`, and it
should be made when the loader exists rather than guessed at now.

## Risks, named

- **The record format is the boot log's contract.** `t49` pins it; changing it changes every log
  consumer. Do not "improve" it during the integration.
- **`sys_ticks` is a proposal.** The pack is honest about that: two of the three services in this
  batch need it, which is why P1 is the first ruling on the list.
- **No retention yet.** The ring that would keep the last N records is in the supervisor's design,
  not in this entry: records go straight to the kernel. Nothing is silently dropped, and nothing is
  buffered either.
