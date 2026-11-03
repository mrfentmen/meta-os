# supervisor — contract (Round 7 B, 2026-11-02)

What this service promises, checked against the code as it stands. Status: **RUNS**
as a host process; nothing boots it, and it cannot act on the table it keeps.

## Inputs

| Input | Type | Accepted | Refused |
|---|---|---|---|
| `sup_register(name, needs, enabled)` | slice, i64, bool | `1 ≤ name.len ≤ NAME_MAX-1`, name not already present, `table_len < MAX_SERVICES` | empty name or `name.len ≥ NAME_MAX` → `E_INVAL`; duplicate → `E_STATE`; table full → `E_NOROOM` |
| `sup_lookup(name)` | slice | returns `(handle, CODE_OK)` | `(0, E_NOTFOUND)` |
| `sup_release(slot)` | i64 | slot in range and `ST_STOPPED` | anything else → `E_STATE`; out of range → `E_INVAL` |
| `sup_set_state(slot, to)` | i64, i64 | an edge in the transition table below | illegal edge → `E_STATE`, state unchanged |
| `sup_set_policy(slot, pol, max, base, cap)` | 5 × i64 | `pol ∈ {0,1,2}`, `base ≥ 1`, `cap ≥ base`, `max ≥ 0` | any other value → `E_INVAL`, policy unchanged |
| `sup_beat(slot, uptime_ms)` | i64, i64 | slot in `STARTING` or `RUNNING` | any other state → `E_STATE` (a live beat from a down service is a state disagreement, not a value to store) |
| `sup_can_start(slot)` | i64 | enabled, dependency running | not enabled → `E_STATE`; dependency not up → `E_STATE`; `needs == slot` → `E_STATE`; `needs ≥ table_len` → `E_INVAL` |
| `sup_on_exit(slot, clean, uptime_ms)` | i64, bool, i64 | always answers `(decision, delay_ms)` | out of range → `(RT_GIVE_UP, 0)` |

## Outputs

- **Decision:** `RT_LEAVE` (0), `RT_GIVE_UP` (1), `RT_NOW` (2), `RT_AFTER` (3), with
  the delay the caller owes the kernel.
- **State:** `ST_STOPPED` (0), `ST_STARTING` (1), `ST_RUNNING` (2), `ST_STOPPING` (3),
  `ST_FAILED` (4), `ST_RESTARTING` (5).
- **Handles:** `(slot + 1) * HANDLE_GEN_MAX + gen`; `0` is never valid. `sup_resolve`
  returns `-1` for a stale handle, so a handle from a replaced occupant cannot be
  mistaken for its replacement.

## Limits (see `LIMITS.md`)

| Constant | Value | Enforced | Proven by |
|---|---|---|---|
| `MAX_SERVICES` | 32 | the 33rd `sup_register` is refused with `E_NOROOM` | `t83_sup_deep` (fill to 32, then refuse) |
| `NAME_MAX` | 32 | names of 31 accepted, 32 refused | `t83_sup_deep` (31 / 32) |
| `HANDLE_GEN_MAX` | 65535 | generation wraps to 1 at the value, never onto it | `t83_sup_deep` (70 000 releases, no collision with slot 2's range) |
| backoff `base`/`cap` | caller-set (default 100 / 30 000) | doubling stops at `cap`; attempt 62 still returns `cap` | `t83_sup_deep` (10 → 1000 sweep) |

## Failure modes

| Failure | Behaviour | Counted |
|---|---|---|
| illegal transition | refused, state unchanged — a supervisor that accepted a jump would later report a dead service as running | — |
| crash loop | `RT_AFTER` with a doubling delay until `max_restarts`, then `RT_GIVE_UP` and the entry stays **`ST_FAILED`**, not `ST_STOPPED` | `restarts` |
| crash after long uptime | `uptime_ms ≥ max_ms` clears `restarts` first, so a service that fails once a week never exhausts its budget | `restarts` reset |
| clean exit | `RP_ON_FAIL` → `RT_LEAVE`; `RP_ALWAYS` → `RT_NOW` with no backoff and no charge to the budget | — |
| stale handle | resolves to `-1`; `sup_name_of` returns an empty slice, never a guess | — |
| heartbeat from a down service | `E_STATE`, nothing stored | — |

## Restart semantics

The table and every counter live in `var` module storage. There is **no reset and no
unregister**: `sup_release` clears a slot's fields but `sup_register` always appends
at `table_len`, which never shrinks. A supervisor "restart" is therefore a new address
space with `table_len == 0`; the only thing that produces one is the kernel spawning
the process again. Nothing carried across is preserved, because nothing is on disk.

## Known defect (found by `t83_sup_deep`, not fixed this round)

`sup_release` is documented as freeing a stopped slot **for reuse**, but no path can
reuse it:

- `sup_release` clears the name and bumps the generation, and leaves `table_len` alone.
- `sup_register` always writes at `slot == table_len`. It never scans for a cleared
  slot.

So a released slot is dead storage: a new service with the old name is refused with
`E_NOROOM` (the table is full), a new name is refused the same way, and the only way
to get the slot back is to restart the supervisor. This is one behaviour with two
possible fixes — scan for a cleared slot in `sup_register`, or drop the "reuse" claim
from `sup_release`'s comment. The current driver asserts what the code does and names
it a defect; the choice belongs to whoever owns the boot sequence, because reuse
changes which slot a service lands in after a restart.

## Drivers

| Driver | Checks | Covers |
|---|---|---|
| `t30_supervisor` | happy path | register, transitions, handles, dependency order |
| `t83_sup_deep` | 117 | illegal transitions, budget exhaustion, `MAX_SERVICES`/`NAME_MAX` edges, backoff cap, handle staleness and generation wrap, release semantics |

`t83_sup_deep` runs 70 000 releases to prove the generation wrap; it is the slowest
driver in the corpus (~0.2 s) and the only one that fills the table.
