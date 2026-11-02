# supervisor — the service table and lifecycle state machine

Status: **RUNS** — driven by `tests/t52_supervisor`, `t75_supervisor_load`,
`t83_sup_deep` and `tests/t135_supervisor_r11`. Every symbol in this file was
checked against the Goose docs (`struct` with fixed-size fields is `reference#32`,
`Entry { field: value }` is `tutorial#9`, and `class` is not a keyword); the run
rows are what make it RUNS rather than merely written.

Layer 4. The supervisor is the first service, not the last: nothing is running
before it, and every other service's life is a row in its table.

## What this file is, and is not

This is the **table + state machine** (B-L1-20) plus the **restart policy**
(B-L1-21): how many times a service may come back, how fast, and when to give up.
The policy was written against the state machine rather than beside it, which is
why it found a missing edge in that machine (`STARTING → STOPPING`) instead of
working around it.

It does **not** start processes. `sup_set_state` records what the supervisor
believes; making that belief true is the K6 fork/exec work (`services/common/sys`
has no spawn call yet — that is a requirement on Layers 1–3, not a fact).
Keeping the table honest first is deliberate: a supervisor that records a
service as RUNNING without having spawned it is exactly the mock KERNEL_SPEC
rule 6 forbids.

## The table

Fixed capacity (`MAX_SERVICES` = 32), no heap, no allocation — a static array of
`ServiceEntry`. This is the source, copied, not an illustration of it:

```goose
let NAME_MAX: i64 = 32;
let MAX_SERVICES: i64 = 32;

struct ServiceEntry {
    name: u8[..32],       // inline, no pointer: the entry is self-contained
    id: i64,              // kernel process id once spawned; -1 until then
    state: i64,
    needs: i64,           // which service starts this one; -1 = no dependency
    restarts: i64,
    last_beat_ms: i64,    // uptime when the last heartbeat arrived
    enabled: bool,
    policy: i64,          // RP_NEVER / RP_ON_FAIL / RP_ALWAYS
    max_restarts: i64,    // 0 = no count limit
    base_ms: i64,         // first backoff step
    max_ms: i64,          // backoff ceiling, and the "this run was healthy" line
    gen: i64,             // bumped whenever a stopped slot is released
}

var table: ServiceEntry[..32] = [ServiceEntry { .. }; 32];
```

`NAME_MAX` is 32 here, not 16: earlier prose in this lane said 16, and that was
wrong against the source. The name registry (B-L1-22) must adopt this value
rather than the other way round, or the two drift.

Names are NUL-terminated *and* length-checked at registration
(`name.len >= NAME_MAX` is refused), and `entry_name_matches` compares the
terminator too — so a stored `web` cannot answer a lookup for the longer `webx`
that shares its prefix.

## The state machine

Six states. `ST_RESTARTING` exists as a state rather than a flag because a
service waiting out a backoff is genuinely neither running nor failed, and a
health line that called it either one would be lying.

```
STOPPED ──▶ STARTING ──▶ RUNNING ──▶ STOPPING ──▶ STOPPED
               │            │            │
               └────────────┴────────────┴──▶ FAILED ──▶ RESTARTING ──▶ STARTING
                                              │              │
                                              └──▶ STOPPED ◀─┘
```

The complete legal set, as `transition_legal` implements it — fourteen pairs, no
more:

| From | To |
|---|---|
| STOPPED | STARTING, FAILED |
| STARTING | RUNNING, FAILED, STOPPING |
| RUNNING | STOPPING, FAILED |
| STOPPING | STOPPED, FAILED |
| FAILED | RESTARTING, STOPPED |
| RESTARTING | STARTING, STOPPED, FAILED |

Two exclusions carry the design:

- **`RUNNING → RUNNING` is not a transition.** It is a heartbeat, and
  `sup_beat` handles it. A state machine that re-enters the same state cannot
  tell a healthy service from a thrashing one.
- **`STOPPED → RUNNING` does not exist.** Every start goes through `STARTING`, so
  "did it actually come up" always has an answer instead of being assumed from a
  optimistic write.

`STARTING → STOPPING` was added at B-L1-21. Without it there was no legal way to
stop a service that had not yet reported ready — the only exit from `STARTING`
was a failure, so "stop" would have had to be spelled "crash". That was a hole in
the machine, not a policy question, and it is recorded here rather than quietly
widened.

`sup_set_state` refuses anything outside this set with `E_STATE` and leaves the
entry untouched. A supervisor that "fixes" a bad transition produces a table
nobody can audit, which is worse than a table with a hole in it.

`FAILED` is not terminal: a crashed service must be restartable without being
re-registered, otherwise every crash would need the whole table rebuilt.

## Why transition is a separate call from the action

`sup_set_state` does not do anything. The caller performs the action (spawn,
kill) and records the outcome. This keeps one code path that can refuse an
illegal transition, and it keeps the supervisor checkable on a machine with no
process spawning at all — which is every machine until K6.

The discipline this needs from callers: **record after acting, never before.**
If spawn fails, the next call is `sup_set_state(slot, ST_FAILED)`, not
`ST_RUNNING`. A state written before the fact is the bug that makes supervisors
untrustworthy in exactly the situation they exist for.

## Restart policy (B-L1-21)

Policy is data on the entry, not a parallel array keyed by slot index: a second
array would desync the moment anything moved, and the policy belongs to the
service, not to the table.

```goose
struct ServiceEntry {
    ...
    policy: i64,          // RP_NEVER / RP_ON_FAIL / RP_ALWAYS
    max_restarts: i64,    // 0 = no count limit
    base_ms: i64,         // first backoff step
    max_ms: i64,          // backoff ceiling, and the "this run was healthy" line
}
```

Defaults at registration: `RP_ON_FAIL`, unlimited retries, `base_ms` 100, `max_ms`
30 s. `RP_ALWAYS` must be asked for — restarting something that stopped on
purpose is a loop, and a loop is the failure mode this whole section exists to
avoid.

`sup_decide` is the whole policy as a pure function of `(slot, exited_clean,
uptime_ms)`, returning one of `RT_LEAVE` / `RT_GIVE_UP` / `RT_NOW` / `RT_AFTER
plus a delay`. No clock, no spawn, no side effects — which is why B-L1-52 can
test every branch on a machine with neither.

| Situation | RP_NEVER | RP_ON_FAIL | RP_ALWAYS |
|---|---|---|---|
| clean exit | leave | leave | restart now |
| unclean exit, budget left | give up | restart after backoff | restart after backoff |
| unclean exit, budget spent | give up | give up | give up |

Three decisions worth defending:

- **The backoff doubles and caps.** A flat retry turns a service that crashes on
  start-up into a spin loop that floods the log you would read to find the cause.
  `sup_backoff_ms` walks `base_ms × 2ⁿ` up to `max_ms`. It is a loop, not a shift,
  because the shift operators are not among the Goose forms verified in this file.
- **A healthy run resets the counter.** Uptime of at least `max_ms` means a working
  service that later failed, not a crash loop; counting those the same would spend
  the retry budget of anything that fails once a week.
- **Giving up leaves the entry `FAILED`, not `STOPPED`.** "Stopped" reads as a
  decision that went well. A service that crashed out of its retry budget must stay
  visible as failed in the health line and the audit record (B-L1-41).

`sup_on_exit` is the side-effecting wrapper: it applies the decision through
`sup_set_state` (never by assigning `state`), so every move is still one the state
machine allowed. `sup_restart_ready` is the counterpart for a caller that cancels a
pending restart while the backoff is still running.

The supervisor never sleeps through its own backoff either: `sup_on_exit` returns
`RT_AFTER` with the delay and the caller owns the wait, because sleeping inside the
supervisor would block the table for every other service.

## What this needs from below

- **A spawn call.** `services/common/sys/sys.goose` currently declares exit,
  write_serial, write_console, read_key, ticks, yield. There is no
  fork/exec/spawn. The supervisor cannot make a state true without it. This is
  a requirement on the K6 shape — flagged in `os-build/layer1/BOUNDARIES.md`,
  not invented here.
- **A clock.** `ticks` is enough for backoff timing, so B-L1-21 needs nothing
  new.

## What this offers above

- `sup_find` — by name, the only lookup other services need.
- `sup_set_state` — the single gate every lifecycle change passes through, so the
  boot log and the audit record (B-L1-41) can be driven off one function.
- `sup_can_start` — dependency-ordered starts, so a service whose `needs` is not
  running is refused for a stated reason instead of failing mysteriously later.
- `sup_beat` / `sup_ms_since_beat` — the watchdog's input (B-L1-23).

## Verification

- Every symbol (`class`, fixed-array fields, `u8[..N]`, `-> i32, bool`, `match`
  avoided in favour of `if` chains, trailing-bool returns) checked against the
  Goose MCP before being written; the specific sections are the ones cited in
  `services/common/fmt/README.md`.
- Bounds-check behaviour (abort, not exception — `reference#82`) is why every
  array write here is preceded by an explicit capacity check.
- Driven on a host by the four drivers named above; nothing here spawns a
  process, because no spawn call exists.

## Name registry (B-L1-22)

Every inter-service call names a service. Naming it by slot index would let a
caller act on whatever service holds that slot later — the caller thinks it is
talking to the logger and is writing to the updater.

A handle packs `(slot, gen)` into one i64: `(slot + 1) * 65535 + gen`, with 0
never valid so an uninitialised field cannot look like a service. `sup_resolve`
checks the slot still holds the generation the handle was issued for, and
`sup_release` bumps that generation when a stopped slot is freed for reuse, so
every handle from the previous occupant stops resolving instead of quietly
pointing at its replacement.

Generation wraps at `HANDLE_GEN_MAX - 1`, not at the maximum: a generation equal
to the maximum would make one slot's handle collide with the next slot's.

| Call | Answers |
|---|---|
| `sup_lookup(name)` | handle + code; `E_NOTFOUND` for an unknown name, which is different from a stale handle |
| `sup_handle(slot)` | handle, or 0 for no such slot |
| `sup_resolve(handle)` | slot, or -1 if stale |
| `sup_name_of(handle)` | the name, or `""` for a stale handle — never a guess |
| `sup_release(slot)` | frees a STOPPED slot; refused with `E_STATE` on anything else |

`sup_name_of` returns a slice into the static table, not into a local copy:
a slice of a fixed-size local would dangle the moment the function returned.

