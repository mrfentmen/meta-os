# R2-T3 patrol/watchman/eval operator runbook

State lives **outside the git tree**: `$R2T3_DATA_DIR`, else
`~/.local/state/oc2-agent-r2t3-d/` (demo state under `demo/`).
Eval records are the exception: `agents/eval-results/*.json` are committed
so the regression gate has a history to compare against.

## Start

```sh
# scheduled layer (user units; patrol + health + eval ride timers)
systemctl --user start oc2-queue.service oc2-trio.service oc2-watchman.service
systemctl --user start oc2-patrol.timer oc2-health.timer oc2-eval.timer

# one-off: drain the board once, run patrol once, run the eval now
node agents/watchman.mjs --root ~/.local/state/oc2-agent --once
python3 server/queue/patrol.py --once
node agents/eval.mjs --gate
```

## Stop

```sh
systemctl --user stop oc2-patrol.timer oc2-health.timer oc2-eval.timer
systemctl --user stop oc2-watchman.service oc2-trio.service oc2-queue.service
# halt ONE agent without stopping the relay: drop agents stop file
touch ~/.local/state/oc2-agent/stop/<agent-name>.STOP   # watchman holds its jobs
rm ~/.local/state/oc2-agent/stop/<agent-name>.STOP      # jobs resume next poll
```

## Inspect

```sh
node agents/jobs.mjs --root <STATE>            # board: queued/running/done/failed/refused
node agents/jobs.mjs --root <STATE> --json
node agents/eval.mjs --last10                  # last 10 eval runs as a table
cat <STATE>/notices.jsonl                      # alarms + notes (dedupe state: notices-state.json)
cat <STATE>/watchman.heartbeat.json            # last watchman beat
node agents/watchdog.mjs check <STATE>/watchman.heartbeat.json
python3 agent-layer/meta-agent-health.py --json
```

## Retry a failed job

```sh
node agents/jobs.mjs --root <STATE> --retry <id>     # creates <id>-r<N> continuing the dead run
# refused jobs (draft/budget) are NOT retried: fix the registry entry, resubmit:
node agents/submit.mjs --root <STATE> --agent <name> --orders "..." --id <new-id>
```

## Cancel a job

There is no delete path on purpose (the board is the audit trail). To stop
a job from running: remove its `.job.json` BEFORE the watchman claims it, or
file a stop for its agent (above) to hold it on the board. A claimed job that
must not run again: leave its result file in place — `finishedSince` skips it.

## Verify receipts (demo)

```sh
R2T3_DATA_DIR=~/.local/state/oc2-agent-r2t3-d node agents/demo.mjs
# prints job path, result path, run-ledger path per job + board counts + verify line.
# Safe to re-run: fixed ids, duplicates reused, receipts byte-identical.
```

## Stale runs

```sh
node agents/cleanup.mjs --root <STATE> --json        # marks >24h runs w/o exit as abandoned
node agents/cleanup.mjs --root <STATE> --max-age-hours 48
# Record per run: runs/<id>/abandoned.json + a run-abandoned ledger line.
```

## Daily records

- Scheduler proof: `agents/heartbeat.mjs --dir <DIR>` appends one JSONL line
  per UTC day (`heartbeat.jsonl`: date, iso, commit, scheduler `oc2-eval.timer`).
- Eval history: `agents/eval-results/eval-<ts>.json` (ts, iso, git commit,
  provider `stub`, score, per-task ok/artifact/detail). The `--gate` run fails
  (exit 2) when the score drops below the last recorded score.

## Alert path

Failing jobs/units alarm through `agents/notify.mjs` into
`<STATE>/notices.jsonl`, key `job:<id>:failed` / `unit:<unit>:failed`, title
naming the agent or unit, body carrying the exit code/signal. Alarms dedupe
15 min per key (`WINDOW_MS`); repeats are journaled as suppressed, never rung.
