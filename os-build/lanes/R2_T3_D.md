# R2-T3 Section D — patrol, watchman, eval, demo: findings

Worktree `/tmp/agent-r2-t3`, branch `agent-r2-t3` (base `047c1f16`).
No branch switches, no commits, no merges/pushes, no QEMU, no paid calls,
no secrets printed. Data dir: no `os-build/lanes/R2_T3_A.md` exists in this
worktree, so runtime state defaults **outside the git tree**
(`$R2T3_DATA_DIR`, else `~/.local/state/oc2-agent-r2t3-d/`); only eval
records (`agents/eval-results/*.json`) are kept in-tree so the gate has a
committable history. `board/`, `bus.html`, app pages, `os-build/face/*`,
`os-build/identity/*`, `provision.sh`, image units, `server/queue` core logic:
read-only, reused via import/subprocess, never edited.

## Files created (all inside allowed dirs)

- `agents/heartbeat.mjs` — daily scheduler-proof record (task 67)
- `agents/unit_alert.mjs` — unit-failure alarm naming unit + reason over the
  notify dedupe window (tasks 65-66)
- `agents/cleanup.mjs` — stale-run abandonment marking (task 79)
- `agents/eval.mjs` — offline stub-provider harness, 12 tasks, artifact-scored,
  timestamp+commit result JSONs, `--gate`, `--last10`, non-zero exits (68-75)
- `agents/eval_tasks.json` — the 12 tasks, each with a pass/fail definition
- `agents/eval-results/eval-2026-11-04T11-56-59-841Z{,.json}`
  `agents/eval-results/eval-2026-11-04T11-57-00-179Z{,.json}` — records (71)
- `agents/demo.mjs` — 3-job receipt demo, twice-safe (76-78)
- `agents/r2t3_d.test.mjs` — 9 tests beside the code, all passing
- `agents/RUNBOOK.md` — operator runbook (80)
- `agent-layer/units/oc2-eval.service` + `agent-layer/units/oc2-eval.timer` —
  daily eval gate (picked up by `stage.sh`'s `*.service/*.timer` glob)

Nothing edited outside `agents/` + `agent-layer/units/` + this report.

## Task 63 — inventory: every scheduled agent + unit timer

Agent-layer units (`agent-layer/units/`):

| unit | type | schedule / mode |
|---|---|---|
| `oc2-queue.service` | simple, always-on | local job API `127.0.0.1:8935`, `Restart=on-failure` |
| `oc2-trio.service` | simple, always-on | drains the queue, `Requires=oc2-queue.service` |
| `oc2-patrol.service` | oneshot | bounded run `--max-checks`, `Requires=queue+trio` |
| `oc2-patrol.timer` | timer | `OnBootSec=30min`, `OnUnitActiveSec=60min`, `Persistent=true` |
| `oc2-health.service` | oneshot | probe; exit 1 on a failed row |
| `oc2-health.timer` | timer | `OnBootSec=2min`, `OnUnitActiveSec=5min` |
| `oc2-watchman.service` | simple, always-on | relay bell, `Restart=on-failure` |
| `oc2-eval.service` **(new)** | oneshot | `node ${OC2_CHECKOUT}/agents/eval.mjs --gate` |
| `oc2-eval.timer` **(new)** | timer | `OnBootSec=45min`, `OnUnitActiveSec=24h`, `Persistent=true` |

Scheduled/scheduled-ish agents (`agents/registry.json`): exactly one entry
carries a cadence — `watch` (`agents/watchman.mjs --once`,
`watchCadenceMs: 900000`, `agents/registry.json:96-99`; consumed at
`agents/runtime.mjs:445`). All other hosted loops run on demand from board
jobs, not timers. `imperium-patrol` is `draft:true` with no command
(`agents/registry.json:15-21`) — the real patrol runs via the timer above.

Noted, out of lane scope (read-only): `crates/os-boot/.../metaos-custos.timer`
(60 min), `relay-overseer.timer` (5 min), `metaos-loop.timer` (30 min),
`os-build/face/metaos-update.timer` (15 min).

## Tasks 64-67, 79 — patrol / watchman / scheduler proofs

All claims below were produced by `node agents/eval.mjs` (each check writes an
artifact file, then scores by reading it back — task 70) and pinned by
`node --test agents/r2t3_d.test.mjs`.

- **64 patrol empty record.** Real `server/queue/patrol.py:Patrol.run_cycle`
  with `cameras=[]` (heavy crew modules stubbed in `sys.modules`, shipped
  budget/priority/status code untouched) returns `outcome: no-cameras` and a
  status record `state: idle`. Artifact `patrol_empty.json`.
- **65 watchman names unit + reason.** A `fail-fast` agent (`process.exit(1)`)
  leaves an alarm in `notices.jsonl`: title `Agent job failed: fail-fast`,
  body `exit 1` (key `job:eval-fail-1:failed`). Unit-level helper
  `agents/unit_alert.mjs` files `Unit failed: <unit>` / `unit <u> failed:
  <reason>` under key `unit:<unit>:failed`.
- **66 dedupe.** 10 identical alarm notifies, same key → 1 unrung bell, 9
  journaled-as-suppressed (`agents/notify.mjs` `WINDOW_MS` = 15 min).
- **67 heartbeat.** `beatDaily` twice one UTC day → 1 line; next day → 2nd
  line carrying `commit` + `scheduler: oc2-eval.timer`.
- **79 cleanup.** Fixture `runs/run-old` (2 days, no exit) gains
  `abandoned.json` `{reason: stale-run}` + a `run-abandoned` ledger line;
  `runs/run-fresh` and an exited old run are untouched.

## Tasks 68-75 — eval harness

12 tasks (see `agents/eval_tasks.json` for each pass/fail definition),
including one eval task each for **bus** (`bus-post-read`,
`bus-room-validation`, `bus-notify-id`), **queue retry** (`queue-retry`,
`queue-retry-refuses-clean`) and **receipt tamper** (`receipt-valid`,
`receipt-tamper`, via `server/queue/receipt_validate.py` as a subprocess —
reuse, no core-logic edit). Provider is `stub` (in-process stubs, loopback
board, local python3 stdlib). Result JSONs carry `ts`, `iso`, `commit`
(`047c1f16…`), `provider`, `score`, per-task `ok`/`artifact`/`detail`.

Score table (`node agents/eval.mjs --last10`):

```text
iso                       score   passed  commit    runId
2026-11-04T11:57:00.431Z  100.0%  12/12   047c1f16  eval-2026-11-04T11-57-00-179Z
2026-11-04T11:56:59.841Z  100.0%  12/12   047c1f16  eval-2026-11-04T11-56-59-841Z
```

Command+output (full run, task 75: exit 0 only when every task passes):

```sh
$ node agents/eval.mjs
PASS  bus-post-read  index 0, line round-trips
PASS  bus-room-validation  both refused 400 with JSON errors
PASS  bus-notify-id  ntf-5db4ec7fada7fdff deterministic
PASS  queue-retry  r2 continues run-abc, repeat idempotent
PASS  queue-retry-refuses-clean  refused: job q-9 finished cleanly; nothing to retry
PASS  receipt-valid  2 receipt line(s), 0 error(s)
PASS  receipt-tamper  exit 1, lines 2+3 named
PASS  patrol-empty-record  outcome no-cameras, status idle recorded
PASS  watchman-alert  alarm names fail-fast + exit 1
PASS  dedupe-window  10 sends, 1 bell, 9 suppressed
PASS  heartbeat-daily  1 line day one, 2nd line next day
PASS  cleanup-stale  run-old abandoned, run-fresh live
12/12 passed (score 100.0%) -> eval-2026-11-04T11-57-00-179Z.json
$ echo exit=$?
exit=0
```

Exit-code proofs: unknown task → exit 1 (`0/1 passed`, record still written);
replayed lowered score (13-task file with one bogus id against a prior 1.0
record in a scratch dir) → `gate: REGRESSION: score 0.923… < last recorded 1`
→ **exit 2**. Precedence: gate trip (2) outranks task failure (1); both are
non-zero, so task 75 holds either way.

Tests (`node --test agents/r2t3_d.test.mjs`): **9 pass, 0 fail** (covers 64,
65, 66, 67, 72, 74-shape via `gateVerdict`, 75, 76-78 double-run).

## Tasks 76-78 — demo

```sh
$ R2T3_DATA_DIR=/tmp/r2t3-d-demo node agents/demo.mjs
receipt demo-r2t3-1 code=0 fresh=true
  job    /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-1.job.json
  result /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-1.result.json
  ledger /tmp/r2t3-d-demo/demo/runs/demo-echo-mw229mm5/ledger.jsonl
receipt demo-r2t3-2 code=0 fresh=true
  job    /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-2.job.json
  result /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-2.result.json
  ledger /tmp/r2t3-d-demo/demo/runs/demo-echo-mw229mm9/ledger.jsonl
receipt demo-r2t3-3 code=0 fresh=true
  job    /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-3.job.json
  result /tmp/r2t3-d-demo/demo/jobs/demo-r2t3-3.result.json
  ledger /tmp/r2t3-d-demo/demo/runs/demo-echo-mw229mma/ledger.jsonl
board: {"queued":0,"running":0,"done":3,"failed":0,"refused":0,"unreadable":0} (reused 0)
verify: OK: 3 jobs, 3 code-0 receipts
```

Second run (same command): `reused 3`, `verify: OK`, board still 3 done, the
jobs dir holds exactly the same 6 files, and all three `.result.json` files
are byte-identical to run 1 (md5-checked) — no duplicate ids, no respawns
(`finishedSince` skips finished jobs).

## Task 80 — runbook

`agents/RUNBOOK.md`: start/stop (units + one-shot commands + per-agent STOP
files), inspect (board, `--last10`, notices, heartbeat, health probe),
retry (`--retry` continues the dead run; refusals are resubmitted, never
retried), cancel (no delete path — board is the audit trail; hold via stop
file or pre-claim removal), verify (demo), stale runs, daily records, alert
path with dedupe semantics.

## Skips + why

- No new systemd unit for heartbeat/cleanup standalone: heartbeat is a library
  called by the eval gate path and demo/test fixtures; cleanup runs as eval
  task `cleanup-stale` plus its own CLI. One new timer (`oc2-eval.timer`)
  covers the daily cadence; extra always-on units would widen the image for no
  scheduled work.
- No `server/queue` edits at all: patrol/receipt/queue behaviors were proven
  by driving the shipped code (subprocess `receipt_validate.py`, real
  `Patrol` class, real `retryJob`), so no diffs were needed.

## Cross-lane requests ( exact file:line )

1. **Image/Section-B lane — `agent-layer/stage.sh:86-89`**: `--check` asserts a
   hardcoded 7-unit list (`oc2-queue/trio/patrol×2/health×2/watchman`).
   `oc2-eval.service`/`oc2-eval.timer` are *staged and enabled* by the existing
   globs (`stage.sh:270`, `:274-284` — all `*.service` get want-links except
   `oc2-health.service`), but `--check` will never verify them. Request: add
   `oc2-eval.service` + `oc2-eval.timer` to the check list and the
   `timers.target.wants` assertion (`stage.sh:100-103` pattern).
2. **Section A (data dir)**: no `os-build/lanes/R2_T3_A.md` present, so this
   lane defaulted runtime state to `$R2T3_DATA_DIR` /
   `~/.local/state/oc2-agent-r2t3-d/` (outside git tree) with eval records in
   `agents/eval-results/`. If Section A standardizes a different state root,
   `defaultDataDir()` (`agents/heartbeat.mjs`, imported by `demo.mjs`) is the
   single choke point to repoint.
3. **Notify/window tuning (Section C?)**: `agents/notify.mjs:18`
   `WINDOW_MS = 15min` governs task-66 dedupe; if the lane wants per-unit
   windows, the key scheme `unit:<unit>:failed` (`agents/unit_alert.mjs`)
   already isolates units — only the constant would change.
