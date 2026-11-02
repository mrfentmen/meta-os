# `crates/stack` — failure drill (B201)

What breaks first when the inputs stop arriving.

The crate takes one snapshot of the environment and returns. "Inputs
not arriving" has two meanings, and they fail in different places:

1. **The environment is wrong/absent** — nothing in the crate fails.
   The wrong value is carried into the plan and only fails later, when a
   runner tries to reach the URL.
2. **A service never comes up** — the crate cannot see it. The failure
   belongs to the runner the crate does not have (G4/G5/G6/G8) and to
   `run-stack.sh` today.

## Drill A — run the crate (safe, no processes)

```
cargo test -p stack -j1
```

Expected: all unit tests plus `error_paths`, `edge_cases` and
`gap_close` green. If a test fails, the first failing test names the
first broken assumption; do not restart services before reading it.

## Drill B — prove the plan against the script (no services)

```
grep -nE 'RELAY_PORT=|QUEUE_PORT=|PORT=|SPARK_API_KEY|TRIO_SPARK_VIA_HELPER|TRIO_JOB_NS' run-stack.sh
grep -nE 'resolve_port|resolve_transport|TRIO_JOB_NS' crates/stack/src/lib.rs
```

Expected: ports and their defaults agree; the transport lines do
**not** agree (the script has three states, the crate two). That is the
first documented divergence, and it is visible before anything starts.

## Drill C — the live stack (do this on a machine allowed to run it)

Run `bash run-stack.sh` with no `SPARK_API_KEY` and no
`TRIO_SPARK_VIA_HELPER`, then stop each dependency in turn. Expected
first failure, in order:

| Step | What you remove | First observable failure | Time to fail |
|---|---|---|---|
| 1 | relay (`relay/relay.mjs` missing or dies) | `FAILED to come up: Meta Nuntius relay (http://127.0.0.1:8787/health)`; `set -e` exits; cleanup kills started PIDs | 50 × 0.2 s ≈ 10 s |
| 2 | queue service file | same line for the queue service, after the relay is up | ≈ 10 s |
| 3 | resident agent file | `FAILED: resident agent exited` and exit 1 — no HTTP retry | 1 s + one `kill -0` |
| 4 | app server file | same HTTP line for `:8080/api/health` | ≈ 10 s |

Source for every line: `run-stack.sh:60-72` (HTTP wait), `86-88`
(agent), `52-58` (cleanup), `28` (`set -e`).

## Drill D — input change after the plan is built

Build a `StackConfig`, change the environment, then call `plan()` with
the old config. Expected: the plan does not change — the snapshot is
the input. Only a new `from_env()` sees the change. This is why the
crate cannot model a service that disappears mid-run; that is the
runner's job (G8).

## First break, summarised

- Wrong/missing env: no break inside the crate; the first break is the
  unreachable URL in a runner.
- Absent service: relay readiness first (start order), then queue, then
  the agent's 1-second alive check, then the app server.
