# supervisor — the service table and lifecycle state machine

Status: **WRITTEN** (every symbol checked against `goose__lookup_symbol` /
`goose__search_docs`; no Goose toolchain on this Mac, so nothing is COMPILED —
see `services/BUILD.md`). Re-checked 2026-11-01 after the pull: `struct` with
fixed-size fields and `Entry { field: value }` literals are `reference#32` and
`tutorial#9`; `class` is **not** a Goose keyword (`goose__list_keywords`), which
is why this file uses `struct`.

Layer 4. The supervisor is the first service, not the last: nothing is running
before it, and every other service's life is a row in its table.

## What this file is, and is not

This is the **table + state machine** (B-L1-20) with the restart *fields* in
place. The restart *policy* — how many times, how fast, when to give up — is
B-L1-21 and lands against these fields. The state machine is complete now so
the policy has a place to attach rather than a design to contradict.

It does **not** start processes. `enter_state` records what the supervisor
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
}

var table: ServiceEntry[..32];
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

The complete legal set, as `transition_legal` implements it — eleven pairs, no
more:

| From | To |
|---|---|
| STOPPED | STARTING |
| STARTING | RUNNING, FAILED |
| RUNNING | STOPPING, FAILED |
| STOPPING | STOPPED, FAILED |
| FAILED | RESTARTING, STOPPED |
| RESTARTING | STARTING, STOPPED |

Two exclusions carry the design:

- **`RUNNING → RUNNING` is not a transition.** It is a heartbeat, and
  `sup_beat` handles it. A state machine that re-enters the same state cannot
  tell a healthy service from a thrashing one.
- **`STOPPED → RUNNING` does not exist.** Every start goes through `STARTING`, so
  "did it actually come up" always has an answer instead of being assumed from a
  optimistic write.

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
- Not compiled, not run. No toolchain on this Mac.
