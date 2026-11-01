# supervisor — the service table and lifecycle state machine

Status: **WRITTEN** (every symbol checked against `goose__lookup_symbol` /
`goose__search_docs`; no Goose toolchain on this Mac, so nothing is COMPILED —
see `services/BUILD.md`).

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
`Service`. `MAX_NAME` = 16 matches the name registry (B-L1-22) and the `exec`
path limit; the two must not drift.

```goose
class Service {
    name: u8[..MAX_NAME]
    name_len: i32
    state: i32              // ST_*
    restarts: i32
    max_restarts: i32
    last_exit: i32
}
```

`name_len` is explicit rather than a zero terminator, so a name containing a
NUL (possible from a corrupted config file) cannot silently shorten itself. The
registration path still refuses empty names and over-long names, and requires
NUL padding — belt and braces, because both consumers exist.

## The state machine

```
ST_DOWN ──enter(RUNNING)──▶ ST_RUNNING ◀──enter(STARTING)── ST_STARTING
   ▲                          │                                │
   │                          └──enter(STOPPING)──▶ ST_STOPPING ┘
   │                                                │
   └────────────────────────────────────────────────┘
                                                    ▼ (terminal)
                                              ST_FAILED / ST_STOPPING → ST_DOWN
```

Legal transitions, enforced in code — `enter_state` refuses anything else with
`CODE_STATE` and leaves the table untouched:

| From | To |
|---|---|
| DOWN | STARTING, FAILED (a service can fail before it starts) |
| STARTING | RUNNING, FAILED |
| RUNNING | STOPPING, FAILED |
| STOPPING | DOWN, FAILED |
| FAILED | STARTING, DOWN |

`DOWN → FAILED` is allowed on purpose: a config that fails to parse at boot is a
failure with no running process to show for it, and hiding that as `DOWN` would
make the boot log lie.

`FAILED` is not terminal. A service that crashed should be restartable without
being re-registered — otherwise every crash would need the whole table rebuilt.

## Why transition is a separate call from the action

`enter_state` does not do anything. The caller performs the action (spawn, kill)
and records the outcome. This keeps one code path that can refuse an illegal
transition, and it keeps the supervisor testable on a machine with no process
spawning at all — which is every machine until K6.

The discipline this needs from callers: **record after acting, never before.**
If `spawn` fails, the next call is `enter_state(ST_FAILED)`, not
`enter_state(ST_RUNNING)`. A state written before the fact is the bug that makes
supervisors untrustworthy in exactly the situation they exist for.

## What this needs from below

- **A spawn call.** `services/common/sys/sys.goose` currently declares exit,
  write_serial, write_console, read_key, ticks, yield. There is no
  fork/exec/spawn. The supervisor cannot make a state true without it. This is
  a requirement on the K6 shape — flagged in `os-build/layer1/BOUNDARIES.md`,
  not invented here.
- **A clock.** `ticks` is enough for backoff timing, so B-L1-21 needs nothing
  new.

## What this offers above

- `find` — by name, the only lookup other services need.
- `enter_state` — the single gate every lifecycle change passes through, so the
  boot log and the audit record (B-L1-41) can be driven off one function.
- `count_in(state)` — the number a health line reports.

## Verification

- Every symbol (`class`, fixed-array fields, `u8[..N]`, `-> i32, bool`, `match`
  avoided in favour of `if` chains, trailing-bool returns) checked against the
  Goose MCP before being written; the specific sections are the ones cited in
  `services/common/fmt/README.md`.
- Bounds-check behaviour (abort, not exception — `reference#82`) is why every
  array write here is preceded by an explicit capacity check.
- Not compiled, not run. No toolchain on this Mac.
