# `common/ring` — byte rings and message rings

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## What it is

Ring buffers that never own their bytes: the caller supplies storage of at least
`cap`, and the ring only ever indexes `0 .. cap-1`. No heap, no resize, no
reallocation that would move a buffer under someone holding a reference.

Used by: the log service (retention ring), the console (history ring), the audit
writer (record ring), and later the IPC queues.

| API | Does |
|---|---|
| `ring_init(cap)` | ring over `cap` bytes of caller storage |
| `ring_push` / `ring_pop` / `ring_peek` | byte in and out; `push` returns `false` when full |
| `ring_push_over` | push, dropping the oldest; returns `true` if it dropped |
| `ring_drain` | copy out and consume, up to `max` |
| `ring_snapshot` | copy out **without** consuming (console history) |
| `ring_len` / `ring_space` / `ring_is_full` / `ring_clear` | state |
| `msg_init(slot, count)` | fixed-size message ring over `count × slot` bytes |
| `msg_push` / `msg_pop` | one record per slot, one-byte length prefix |

## Two decisions worth defending

1. **`ring_push` refuses when full; it does not overwrite.** A log ring that
   silently eats its oldest record is a log that lies about what happened. The
   overwrite behaviour exists as `ring_push_over`, which *tells the caller it
   dropped something* so dropped records can be counted.
2. **The message ring uses fixed slots.** A variable-length record in a byte ring
   needs a header scan on every pop and desynchronises permanently after one lost
   byte. Fixed slots cost some space and buy a queue that cannot drift.

## Known limitation, stated not hidden

`msg_init(slot, count)` requires `slot` to divide the storage exactly; the byte
ring's capacity is `count * slot`, so every slot starts aligned. A caller that
hands `msg_push` a buffer shorter than that capacity gets a bounds abort on the
first wrapped write — caller bug, caught loudly.

## Not provided, on purpose

- **No blocking pop** — no wait primitive exists (Q-B-L1-1); poll and `yield`.
- **No resize** — no heap, and moving a ring invalidates references.
- **No thread safety** — Goose threads share nothing (`tutorial#21`); a ring is
  owned by one service or reached over IPC.

## Verification

| Form | Source |
|---|---|
| growable `u8[>..]`, `push`, `.len` | `samples/03_strings.goose` |
| whole-element assignment `a[i] = v` | `stdlib#13` |
| bounds checks abort | `reference#82` |
| struct literal with all fields | `tutorial#3` |
| trailing-bool | `samples/04_errors.goose` |

## Not verified

Compilation, and specifically whether `buf[r.tail] = b` on a builder whose
length was grown by `push` is legal — the docs confirm whole-element assignment
in general (`stdlib#13`), not on a growable builder mid-life. B-L1-46 tests
exactly this before anything else depends on it.
