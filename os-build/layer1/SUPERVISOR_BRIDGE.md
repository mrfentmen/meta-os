# Supervisor → runtime bridge (B1, one page)

Status: **design**, with B2 implementing exactly this and nothing more. The supervisor decides;
the runtime acts; the bridge is the only thing that turns a decision into a process. No kernel is
involved and no kernel claim is made.

## What exists on each side

| side | what it really is | what it cannot do |
|---|---|---|
| `services/supervisor` (Goose) | a 32-slot table, legal transitions, restart policy (`sup_decide`), a dependency gate (`sup_can_start`), and the 22-row boot order (`bo_sequence`) | start anything. `sys_spawn`/`sys_kill` are proposals (P3); it is a decision engine with no actor |
| `agents/runtime.mjs` (Node) | real `spawn`, two-step `killAgent`, wall-clock budget, STOP polling, a JSONL ledger per run, a baton per run | order, dependency, restart policy, or a service table. It runs one agent when told |

Neither side is wrong. The supervisor's job is to know *whether* a service may run; the runtime's
job is to run one. The bridge is the missing verb between them, and it is deliberately thin: it
holds no policy of its own, it asks the supervisor's table what the order is and reports back what
happened.

## The mapping (one row per concept, no invented states)

| supervisor | bridge | runtime |
|---|---|---|
| `sup_register(name, needs, enabled)` | boot entry `{agent, needs}` (v1 reads `agents/boot.json`) | registry entry with `command` |
| `ST_STARTING` | written when `spawnAgent` returns | `spawn` ledger line |
| `ST_RUNNING` | state after a successful spawn | child alive |
| `ST_STOPPING` → `ST_STOPPED` | `stop()`: STOP file, then `killAgent` (grace, then hard) | `stop-request`, `exit` |
| `ST_FAILED` | nonzero exit without a stop request | `exit` with `code != 0` |
| `RP_NEVER` | v1 restarts nothing; stated, not implied | — |
| `bo_sequence()` order | `bootAll()` walks the boot file in order | — |
| `sup_can_start` | `start()` refuses unless every `needs` agent is `running` | — |

The bridge never invents a state the supervisor does not have. "Blocked on a dependency" is a
refusal, not a new state, and it lands in `bridge.jsonl` as `refused` with the missing names.

## The STOP window — the 00d895d class, stated as three windows

The bug that commit fixed was a check-then-act gap: STOP was consulted at one point, so a STOP
filed *after* the check but *before* the act still let the act happen. A STOP check is only worth
what its narrowest window is, so the bridge names all three and closes each:

1. **Before the claim.** `stop/<agent>.STOP` is checked before anything is spawned. If it is
   present the start is refused, nothing is spawned, and the ledger says `stop-pre-spawn`.
   This is the window a pre-start `STOP` needs; the run directory does not exist yet, so a STOP
   inside it is impossible by construction.
2. **After the claim, before the child is useful.** The runtime's STOP poll starts with the child
   and looks in the run directory every 100 ms. A STOP written there immediately after `spawn`
   kills the run and records `stop-file` — never a silent start followed by nothing.
3. **After the act.** A STOP filed for a finished run is a no-op: the poll is cleared on `done`,
   so it cannot manufacture a stop record (A1.4 asserts exactly this).

The residual gap is honest and stated: between `spawnAgent` returning and the first 100 ms poll,
the child runs. That is a polling window, not a check-then-act window, and closing it fully needs
a checkpoint API inside the child (A1's open item 3).

## Ordering

`bootAll()` walks `agents/boot.json` in order. `start(name)` refuses when any `needs` entry is not
`running`, and records the refusal with the names it was waiting for. The boot file's order and
its `needs` must agree; `bridge_check` (B2's test) asserts the same invariant `bo_order_ok` does
for services — every dependency appears earlier — so a hand edit fails a test rather than a boot.

## Records

- `bridge.jsonl` (one per root): `start-request`, `started`, `refused`, `stop-request`,
  `stop-pre-spawn`, `exited`.
- each run's own `ledger.jsonl`: the runtime's record, unchanged.
- The bridge writes no line it cannot support from one of those two.

## Non-goals (v1, stated so nobody reads them in)

- No restart policy beyond "record the failure". `RP_ON_FAIL` needs a stable exit reason per
  service and a backoff clock the bridge does not have.
- No kernel. The in-kernel version of this bridge is Rowan's lane when spawn/kill exist; the
  contracts above are written to move down unchanged.
- No service table of its own: `needs` comes from the boot file, which mirrors `BOOT_ORDER.md`'s
  shape for agents. When the supervisor can export its table, the bridge reads it instead — the
  mapping table above is the contract for that swap.
