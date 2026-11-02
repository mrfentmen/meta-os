# `logd` — Layer 4, service 5

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## What it does

The layer's single log sink. Services call `log(level, tag, msg)`; records queue in
a retention ring and flush to the serial port.

Record format, one line, never wrapped:

```
<ticks> <tag> <level-letter> <message>
```

## Flush policy, exactly

1. **High water:** flush when the queue is at 48 of 64 slots (3/4). Batching keeps
   a busy path off the serial port per record.
2. **Error is immediate:** a record at `ERROR` or above flushes on the spot,
   because the record that matters most is the one just before everything stops.
3. **Explicit:** the entry loop flushes when asked.

Nothing else flushes. A timer-driven flush needs the time service to exist and is
B-L1-108's job; inventing a second clock here would be exactly the duplication the
contract forbids.

## Loss is counted, never hidden

| Counter | Meaning |
|---|---|
| `dropped_full` | queue was full |
| `dropped_level` | below `min_level` |
| `dropped_long` | message longer than a 159-byte slot |
| `written` | records actually on the wire |

A message that does not fit its slot is **refused**, not truncated — a silently
shortened error message is worse than an admitted gap. `loss_stats()` returns all
four for a status line, because a sink that cannot say what it dropped cannot be
trusted during an incident.

A port failure stops the flush and **leaves the rest queued**: a dead port must not
eat the records that explain why it died. Short writes are retried with `yield` and
a 1000-iteration guard, so a dead port cannot hang the sink forever.

## Storage

`160 bytes × 64 slots = 10 KiB` of static retention, one globals block. No heap.

## Contract

- **Entry:** `export "svc_entry" fn service_main() -> i32`. No `BootInfo` argument
  yet (Q-B-L1-4).
- **Kernel surface:** `sys_write_serial`, `sys_ticks`, `sys_yield`.
- **Offers:** the record format is a **CONTRACT** for Layer 5–6 (`BOUNDARIES.md`
  B3) — anything writing a record writes this shape.

## Deviations and limits

- **The idle loop gives up.** With no IPC there is nothing to receive, so the loop
  spins, yields, and exits after a bounded count rather than pretending to serve.
  B-L1-76 makes it real by feeding it records.
- **`min_level` is a global, not config**, until B-L1-13 has a file to read.
- **No rotation and no export** — B-L1-108.

## Verification

| Form | Source |
|---|---|
| `extern fn`, `export "svc_entry" fn` | `spec#40`, `spec#41` |
| builders, `append`, `.len` | `samples/03_strings.goose` |
| `format_int(out, v, base, width, padc)` | `stdlib#9` |
| struct literal with all fields | `tutorial#3` |
| trailing bool | `samples/04_errors.goose` |
| `while true` / `break` / `continue` | `list_keywords` |

## Not verified

Compilation; the cross-file import roots (same risk as `console`); and that
`sys_write_serial` returns a byte count rather than a status — if it returns a
status, `write_record`'s retry loop is wrong and the kernel contract (A2) needs
to say so explicitly.
