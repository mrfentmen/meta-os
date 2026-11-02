# Round 8 checkpoint — sections A, B, C closed

Branch: `buffy/round8` (on `origin/main` 84a70c4 + the carried t100-t102 work).
Room-1 post is not available from this lane, so this file is the checkpoint Pax merges against.

## Verification, measured just now

- `node --test tests/agents-*.test.mjs tests/handsfree.test.mjs` → ℹ pass 43 ℹ fail 0 
- Goose corpus, last full run of this tree: `58 of 58 drivers RUNS, 2704 assertions, 0 failed`,
  `64 typechecked, 0 failed` (`SERVICE_RUNS.md`). No Goose source changed in A/B/C.

## A — agent runtime hardening

| item | deliverable | evidence |
|---|---|---|
| A1 | failure-injection pack, 7 cases | `tests/agents-hardening.test.mjs`; `AGENT_HARDENING.md` |
| A2 | restart drill | `tests/agents-restart.test.mjs`, `AGENT_RESTART_DRILL.md` |
| A3 | heartbeat + alarm line | `agents/watchdog.mjs`, `WATCHMAN_WATCHDOG_DRILL.md` |

What the pack found and what changed: a torn ledger line made the whole run unreadable, and the
next append fused onto the torn line so the record after the crash was lost too. `Ledger.add`
now separates before appending and `Ledger.read` skips what it cannot parse. The watchman now
reconciles at start-up: a claim with no bell is released (the lost-job window), and a bell whose
run has no `exit` is marked `run-orphaned` and continued from its baton.

## B — supervisor for real

| item | deliverable | evidence |
|---|---|---|
| B1 | one-page bridge design | `SUPERVISOR_BRIDGE.md` |
| B2 | bridge built | `agents/bridge.mjs`, `agents/boot.json`, `tests/agents-bridge.test.mjs` |
| B3 | three-agent drill | `BRIDGE_DRILL.md` |

The bridge is the actor the supervisor lacks: boot order, dependency refusals, and all three STOP
windows (pre-claim refusal, mid-run kill, no-op after exit). The drill shows one clean finish, one
budget kill, one STOP — with the ledger lines in the document.

## C — Hands-Free

| item | deliverable | evidence |
|---|---|---|
| C1 | inbox → job files | `handsfree/intake.mjs`, `HANDS_FREE.md` |
| C2 | one speakable brief | `handsfree/brief.mjs` |
| C3 | yes/no in the run ledger | `handsfree/approval.mjs` |
| — | all three together | `HANDS_FREE_DRILL.md` |

Unparseable inbox lines stay in the inbox rather than being silently dropped; "stopped" is never
reported as "finished"; a second approval answer is refused and writes nothing.

## D — Aegis services

| item | deliverable | evidence |
|---|---|---|
| D1 | manifest inventory, no network | `aegis/manifests.mjs`, 7 tests |
| D2 | append-only findings record | `aegis/findings.mjs`, 6 tests |
| D3 | watch-target pack, checked against the real poller | `aegis/watch-targets.mjs`, 7 tests |
| — | drill + measured inventory | `os-build/layer1/aegis_drill.mjs`, `os-build/aegis/DRILL.json` |

20/20 Aegis tests pass; the drill found 23 manifests in this tree (22 cargo, 1 npm), skipped
5 cache/VCS dirs, and detected a deliberate page write. `os-build/aegis/README.md` lists what
is not built: no OSV sweep, no registry entry, no face.

## E — Round 7 remainder

- **E1 closed.** `t103_limits_rest` drives the five host-reachable constants that were still
  open; `gen_limits.py` now separates dead declarations and structurally unreachable limits
  from unproven ones. Final count: 95 constants, 78 proven, 9 not limits, 8 unreachable,
  **0 unproven** — `COUNTS.md`, `LIMITS.md`.
- **E2** gives the four shallowest programs (hello, heartbeat, echo, mcp-host) a runnable
  regression test each: `tests/goose-programs.test.mjs`.
- **E3** audit: 29 of 42 service directories have a README (target was 25); the 13 without
  are named with reasons in `README_AUDIT.md`, including seven real documentation gaps.

## F — Lobster host

`lobster/service-roundtrip.lobster` calls the merged `echo` service through the Goose child
process and prints the service's own answer; `lobster/roundtrip.log` is the committed
transcript. `LOBSTER_BINDING.md` now states both truths: the stdio round trip is PROVEN, the
in-process C ABI/FFI path is still NOT BUILT, and the earlier "zero Lobster files" claim is
corrected in the same file.

## Still open (not this lane's)

- Two runtime items deliberately left to Pax: STOP is polled, not checkpointed; the ledger
  has no rotation. Both are named with their consequences in `AGENT_HARDENING.md`.
- Seven services still have no README (`README_AUDIT.md`), and the dead limit constants
  listed in `COUNTS.md` want either a real call site or deletion.

## Commits on this branch

`f0cab0e` carry t100-t102 + script modes · `8aefc2f` A1 ledger hardening · `8ca1353` A2 restart ·
`85d57f9` A3 watchdog · `3983386`/B1-B2 bridge + B3 drill · `c114563` C shapes.

`e4339bc` D Aegis services · `0d42f71` F Lobster round trip · `a3eee7f` E1 limits ledger.
