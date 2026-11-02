# `crates/stack` — behaviours the Rust port does not carry (B197)

The "Python original" of this crate is not Python: the source is
`run-stack.sh` (bash). The `os/` tree contains the services the stack
starts, not the composition, so no `os/` file is the original. Each gap
below names the script line that carries the behaviour.

These are tasks, not work done here. B197 says: list them, do not port
them.

| # | Behaviour not carried | Source | Why it matters |
|---|---|---|---|
| G1 | Third transport state: no key and no opt-in means **NOT CONFIGURED / offline** — the stack still starts, generation is unavailable | `run-stack.sh:45-49` | The crate reports `DevHelper` for this case (`src/lib.rs:117-121`), which is a false statement about the live stack |
| G2 | Explicit DEV opt-in `TRIO_SPARK_VIA_HELPER=1` | `run-stack.sh:41-44` | Cannot distinguish an operator's opt-in from a missing key |
| G3 | Key present unsets `TRIO_SPARK_VIA_HELPER` | `run-stack.sh:38-40` | Ambient helper flag is not cleared in the plan's env |
| G4 | `PIDS` array, `cleanup()`, `trap cleanup EXIT INT TERM` | `run-stack.sh:52-58` | A runner must kill every started PID; the crate has no representation of it |
| G5 | `wait_http`: 50 attempts, `sleep 0.2`, `curl -sf -m 2`, return 1 after exhaustion | `run-stack.sh:60-72` | Constants exist (`lib.rs:38-45`) but no runner enforces the exit-on-failure semantics |
| G6 | Agent readiness: `sleep 1`, `kill -0`, `FAILED: resident agent exited`, exit 1 | `run-stack.sh:86-88` | Modelled as `Readiness::ProcessAlive` only; the failure line/exit code is not produced |
| G7 | Start banners before each service | `run-stack.sh:73`, `78`, `83`, `90` | Output parity gap only; no decision depends on it |
| G8 | Final `wait` keeps the script alive until a child exits | `run-stack.sh:104` | A runner must block; the crate returns immediately |
| G9 | `set -euo pipefail` and `cd "$(dirname "$0")"` | `run-stack.sh:28-29` | Failure propagation and working-root resolution are the script's, not the plan's |
| G10 | Ambient environment passes through to every service | `run-stack.sh:74`, `79`, `84`, `91` | `Service.env` lists only what the script sets; a runner must merge the ambient env |

## Not a gap

- `TRIO_UPSTASH_HOST` is absent from the crate **and** from the script
  (`batches/B06.md:23` is the only place that lists it). Omitting it is
  correct; the batch doc carries the error.
- Ports are not validated in either place. The crate keeps the script's
  oddity on purpose (`src/lib.rs:13-17`); do not "fix" it without a
  script change.
