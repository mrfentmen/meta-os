# `bootlog` — Layer 4, service 1

**Status: COMPILED.** (Lane B R5, 2026-11-04 — build+run log: services/bootlog/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) `tests/t49_bootlog` exercises the record shape and the cap refusal (23 checks,
exit 0); `tests/t107_bootlog_r11` adds the boundary and the volume case. Both run on the host
shim — the service logic runs, nothing has booted, and no claim here rests on the kernel's UART.

## What it does

The first service to run and the last to go quiet. It writes records to the serial port in the
form:

```
<ticks> bootlog <level> <message>
```

One record per syscall, so a record is never interleaved with another writer's bytes. Levels are
fixed integers (`1` info, `2` warn, `3` error) rather than strings, so the record header has a
constant size.

`record` computes the formatted width first and refuses **before writing a byte** if it does not
fit the caller's cap: the buffer is left empty rather than holding half a line. A half-written
boot record is worse than a missing one — it is the line somebody reads at 3am and believes.

## Contract

- **Entry:** `entry.goose` exports `svc_entry` (`export "svc_entry" fn service_main() -> i32`),
  per `os-build/layer1/SERVICE_CONTRACT.md` §2. Returns `0` on a clean stop. The entry is split
  from `bootlog.goose` on purpose: a program may export `svc_entry` exactly once, and a driver
  importing the module must not drag a second one in.
- **Kernel surface:** `sys_write_serial(s: const u8[:]) -> i64` and `sys_ticks() -> i64`,
  declared as `extern fn` in `common/sys`. The transport is open question Q9 and is not asserted
  in the source.
- **Needs:** K-serial (K1 has the skeleton), K-timer for the tick stamp (K3).
- **Offers the layers above:** an append-only boot record. Nothing else imports it; it imports
  nothing but the kernel and the shared formatting library.

## Deviations and gaps, stated rather than hidden

1. **Entry takes no argument.** The contract says `service_main(boot: BootInfo&)`. `BootInfo` is
   B-L1-08 and does not exist yet; a placeholder struct would be a mock. Reconciling the signature
   is a listed step in B-L1-08.
2. **No ring retention.** Records go straight to the kernel. Retention over a ring needs B-L1-11
   (`ring`), which does not exist yet, and pretending to buffer would hide the gap. A full serial
   buffer therefore drops the record — `record` returns `false` and `stage` propagates it, but
   `service_main` deliberately does not abort the boot over it.
3. **No config.** The tag and levels are globals; a real service reads its config through
   B-L1-13. Until then there is nothing to configure.

## Limits

`BL_LINE` is 200 bytes, enforced in `record`. `LIMITS.md` does not list it (generator gap); the
record in `os-build/layer1/r11/bootlog.md` does. The new test drives the boundary: a 150-byte
message fits, a 200-byte message at `BL_LINE` is refused with an empty buffer, a 256-byte message
is refused rather than truncated, and cap 0 refuses everything.

## What is not verified

- That the freestanding link of Goose-generated C against our kernel works. B-L1-75 is the task
  that finds out; the host runs use `host_shim.c`.
- That `sys_write_serial` returns a byte count rather than a status. That is our requirement on
  the kernel, not a fact (`SERVICE_CONTRACT.md` §3).
- That the serial port exists at runtime: the host shim accepts every write, so the negative
  return path is unreachable here and is recorded as a named gap.
