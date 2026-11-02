# devices — Round 11 record

Source: `services/devices/devices.goose`, `services/devices/hotplug.goose` ·
Test: `services/tests/t112_devices_r11.goose` · Status: RUNS (reached by `tests/t77_gaps`,
73 checks)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `DEV_MAX` | `16` | `devices.goose` | driven by `t112` | one device per kind fills the table to 16; the seventeenth kind returns `-1, E_NOROOM` |
| `HP_QUEUE` | `8` | `hotplug.goose` | driven by `t112` | nine raised events leave eight pending and `dropped=1`; the oldest (`seq 1`) is the one gone, the newest (`seq 9`) survives |
| `HP_SUBS` | `8` | `hotplug.goose` | driven by `t112` | eight subscriptions succeed, the ninth returns `-1`; an empty mask is refused the same way |

`LIMITS.md` lists `DEV_MAX` against `t77_gaps` (which names the constant). `HP_QUEUE` and
`HP_SUBS` are **not** in `LIMITS.md` at all — the generator's heuristic missed the two
`hotplug.goose` constants. They are exercised by `t112`, so the gap is in the generated
inventory, not in the tests. **FINDING for room 1: `gen_limits.py` misses `HP_QUEUE` and
`HP_SUBS`.**

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| empty name, a 16-byte name, kind 0 | `E_INVAL` | three separate `dev_add` assertions, each expecting `-1, E_INVAL` |
| a second device of the same kind | `E_STATE` | "a second device of the same kind is refused" |
| `READY → DETECTED` | `E_STATE` | "READY -> DETECTED is refused" |
| details of a non-ready device | `E_STATE` | "details of a non-ready device are refused" |
| an out-of-range slot in `dev_mark` | `E_INVAL` | "an out-of-range slot is refused" |
| the table at `DEV_MAX` | `E_NOROOM` | "the seventeenth device is refused with E_NOROOM" |
| a device not in the table | `E_NOTFOUND` | `dev_detail` returns it when `dev_find` is -1 (structural path; the host driver covers the `E_STATE` branch above) |
| an unknown hot-plug kind, an empty mask, a ninth subscriber | `E_INVAL` / `-1` | "an unknown event kind is refused", "an empty mask is refused", "the ninth subscriber is refused" |
| unsubscribing twice | `E_NOTFOUND` | "unsubscribing twice is not found" |

**FINDING for room 1: `hp_subscribe` takes a bit mask, but nothing says so and nothing
checks it.** The kinds are `HP_ADD=1 … HP_READY=4`; the mask is `1 << kind`. A caller that
passes the kind constant itself (the obvious reading of `hp_subscribe(h, HP_ADD)`) subscribes
to bit 1, receives nothing forever, and `hp_raise` still returns `delivered=0` with
`CODE_OK` — a silent no-subscription. This driver's first draft did exactly that: the
subscriber tests failed with `delivered 0`, which is how the mismatch was found. The test now
passes `1 << HP_ADD`. The service refuses only mask 0; it does not refuse a mask with no
defined bit, so the mistake is uncatchable at subscribe time. Either the API should take a
kind (not a mask), or `hp_subscribe` should return `-1` for a mask with no bit in
`1<<HP_ADD .. 1<<HP_READY`.

## 3. Restart — NAMED GAP

The table is static memory rebuilt by `dev_probe_boot(BootInfo)` at start-up. A restart
therefore loses every post-boot state change — a device marked `FAULT`, one marked
`ABSENT`, a recovered `READY` — and returns to what `BootInfo` said at boot. No supervisor
restart was run here; the loss is named, not proven continuous. **What survives: nothing in
this process. What rebuilds it: the boot block, which is why the absence of a keyboard in
`BootInfo` is a persistent fact rather than a transient one.**

## 4. Contract — PROVEN

Imports: `common.boot.boot`, `common.err.err`. No service is imported; the table is built
from the boot block and queried by callers.

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | log | none in code | declared: `cm_set(SVC_DEVICES, ... SVC_LOG ...)` — DORMANT |
| out | bootlog | none in code | declared: `cm_set(SVC_DEVICES, ... SVC_BOOTLOG)` — DORMANT |
| in | bootlog | none in code | bootlog's row includes `SVC_DEVICES` — DORMANT |
| in | storage | none in code | storage's row includes `SVC_DEVICES` — DORMANT |
| in | time | none in code | time's row includes `SVC_DEVICES` — DORMANT |
| in | net | none in code | net's row includes `SVC_DEVICES` — DORMANT |

All six edges are declared in `callmatrix.goose` and none is exercised by an import. That is
honest for a table every service is *allowed* to query, but `FINDING: the matrix records six
device edges and no importer exists` — the first caller will be the first proof.

## 5. Load — NAMED GAP

The load loop runs 700 `dev_find`/`dev_ready` queries (ten times a 70-query sweep) against a
full sixteen-entry table. It approaches `DEV_MAX` for lookup, not insertion: the table is
read far more often than it is built.

RUNS pass=44 fail=0 · `LOAD devices ops=700 ok=700 refused=0`

## 6. README truth pass — PROVEN

`services/devices/README.md` rewritten; four stale statements:

- **"Status: WRITTEN (not COMPILED)"** — the unit is RUNS: `tests/t77_gaps` reaches it with
  73 checks, and the corpus typechecks the module. Now says RUNS.
- **"Deliberately absent: ... no hot-plug (B-L1-113, needs IPC)"** — `hotplug.goose` exists
  and does not need IPC: `hp_raise` queues an event after the table has changed, and
  subscribers drain it. The README now documents the queue, the subscriber mask, and the
  drop-oldest rule.
- **"Not compiled, not run."** — removed.
- **Limits** — added `DEV_MAX` (16), `HP_QUEUE` (8), `HP_SUBS` (8), each with the test that
  reaches it, and the note that `HP_QUEUE`/`HP_SUBS` are missing from the generated
  `LIMITS.md`.
