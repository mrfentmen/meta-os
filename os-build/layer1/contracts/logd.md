# logd — contract (Round 7 B, refreshed 2026-11-02)

What this service promises, checked against the code as it stands. Status: **RUNS**
as a host process; nothing boots it.

## Inputs

| Input | Type | Accepted | Refused |
|---|---|---|---|
| `log(level, tag, msg)` | i64, slice, slice | level ≥ `min_level` (INFO by default), record ≤ `SLOT` (160) bytes including the newline | level below the floor → `dropped_level`; record too long → `dropped_long` |
| `log_info/warn/error` | slice, slice | same as `log` with the level fixed | same |
| `flush()` | — | drains the queue oldest-first, stopping on the first port failure | never refuses; returns the count sent |
| `should_flush()` | — | `true` at `msg_len ≥ HIGH_WATER` (48) | — |
| `loss_stats()` | — | four counters: full, level, long, written | — |

## Outputs

- **Serial:** one record per line, `<ticks> <tag> <L> <msg>\n`, formatted in full or
  not at all. A partial line is never written.
- **State:** `queue` (a `MsgRing` of `SLOTS` × `SLOT`), and the four counters.

## Limits (see `LIMITS.md`)

| Constant | Value | Enforced | Proven by |
|---|---|---|---|
| `SLOT` | 160 bytes | record refused if it cannot fit | `t50_logd`, `t81_logd_deep` |
| `SLOTS` | 64 records | ring refuses at full | `t50_logd`, `t81_logd_deep` |
| `HIGH_WATER` | 48 | `should_flush` flips at the mark | `t81_logd_deep` (47/48) |
| `TAG_MAX` | 8 | tag longer than the slot is refused | `t50_logd` |
| `MSG_MAX` | 160 | message over the slot is refused | `t50_logd`, `t81_logd_deep` |
| `LINE_MAX` | 160 | formatted line past the record is refused | `t50_logd` |

## Failure modes

| Failure | Behaviour | Counted |
|---|---|---|
| ring full | refuse; **if the record is ≥ ERROR, flush once, retry once, then refuse** | `dropped_full` |
| message or tag too long | refuse outright; the buffer is left empty, not half-written | `dropped_long` |
| level below the floor | refuse before formatting | `dropped_level` |
| serial port fails | `flush` stops, leaving the rest queued; the queue is not drained into a dead port | — |
| serial port makes no progress | 1000 yields, then `write_record` returns false | — |

## Restart semantics — the finding

**`logd_init()` is not a restart.** It appends another `SLOT × SLOTS` arena to the
existing `storage` builder: measured 20480 → 30720 bytes over the driver's run, and
queued records survive it. Counters are never cleared.

A real restart means a new process image: empty queue, zero counters, no history.
A supervisor that "restarts" a service by calling its init again therefore leaves
old records queued and doubles the arena — worth fixing at the supervisor, not
here, and recorded rather than patched because the initializer's signature is
frozen.

## Drivers

| Driver | Checks | What it covers |
|---|---|---|
| `tests/t50_logd.goose` | 26 | happy path, retention, policy 2, formatting |
| `tests/t81_logd_deep.goose` | 24 | failure injection, SLOTS/HIGH_WATER edges, re-init behaviour |

## What this contract does not claim

- No record survives a reboot: the ring is RAM.
- No timestamps beyond `sys_ticks()` — there is no wall clock in this layer.
- No rate limiting: the counters report loss, they do not prevent it.
