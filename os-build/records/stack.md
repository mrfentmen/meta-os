# `crates/stack` — behaviour record (B193, 2026-11-02)

Read from `crates/stack/src/lib.rs` (a single module) and the source it
ports, `run-stack.sh`. Line numbers are the files as they stand in this
tree.

## What it is

A pure planner. `plan()` returns the four services in start order with
their argv, cwd, env and readiness gate; `summary_lines()` returns the
four lines the script echoes. It does **not** spawn processes, poll
health, trap signals, or wait (`lib.rs:10-21`). A runner is expected to
execute the plan; no such runner exists in this repo today (B199,
`stack-callers.md`).

## Inputs and outputs

| Input | Where | Output |
|---|---|---|
| env snapshot `(key, value)` pairs | `StackConfig::from_entries` (`lib.rs:127-137`) | `StackConfig` |
| live process env | `StackConfig::from_env` (`lib.rs:139-148`) | `StackConfig` |
| `&StackConfig` | `plan` (`lib.rs:174-226`) | `Vec<Service>` (always 4) |
| `&StackConfig` | `summary_lines` (`lib.rs:232-247`) | `Vec<String>` (always 4) |

## Behaviour

1. **Ports** (`lib.rs:110-115`): a present, non-empty value is copied
   verbatim; missing or empty falls back — relay `8787`, queue `8935`,
   app `8080` (`lib.rs:131-135`; the script's equivalents are
   `run-stack.sh:31-33`). No numeric check: `RELAY_PORT=abc` becomes
   `http://127.0.0.1:abc` (`lib.rs:150-160`).
2. **Transport** (`lib.rs:117-121`): non-empty `SPARK_API_KEY` →
   `ProductionDirect`; missing or empty → `DevHelper`.
3. **Job namespace** (`lib.rs:137`, `176-184`): `TRIO_JOB_NS` is not
   defaulted here. Absent → `None` and no env entry; present (even
   empty) → carried verbatim into the queue service and resident agent.
4. **Service order** (`lib.rs:186-226`): relay → queue service →
   resident agent → app server, matching `run-stack.sh:73-92`.
5. **Readiness** (`lib.rs:163-171`, `68-80`): HTTP health for relay,
   queue and app — 50 attempts, 200 ms apart, 2 s per attempt; the
   resident agent uses `ProcessAlive` (settle 1 s, then alive), matching
   `run-stack.sh:60-72`, `86-88`.
6. **Summary lines** (`lib.rs:232-247`): four lines, byte-for-byte the
   script's `echo` output apart from substituted bases
   (`run-stack.sh:98-101`).

## What it refuses

Nothing. There is no `Result`, no panic branch, and no validation in
this crate. An invalid port is not refused; it is interpolated into a
URL exactly as bash would. This is deliberate and documented
(`lib.rs:13-17`). `error_paths.rs` pins the absence of refusals.

## What it writes down

Nothing. No file I/O, no logging, no environment mutation. The only
"records" are the in-memory structs listed in `stack-records.md`.

## Findings (reported, not fixed)

1. **The transport model is missing a third state.** `run-stack.sh:38-50`
   has three outcomes: production direct (key present), DEV helper
   (`TRIO_SPARK_VIA_HELPER=1`), and **NOT CONFIGURED / offline** (no key,
   no opt-in). The crate has only `ProductionDirect` and `DevHelper`
   (`lib.rs:50-57`) and maps "no key" to `DevHelper`
   (`lib.rs:117-121`), so it claims the DEV helper is in use when the
   script would say generation is not configured. Recorded as G1 in
   `stack-gaps.md`; not ported here by instruction (B197).
2. **`TRIO_SPARK_VIA_HELPER` is never read** (`run-stack.sh:41`), so the
   explicit opt-in cannot be represented (G2).
3. **The crate does not model process supervision.** `PIDS`, the
   `EXIT INT TERM` trap, the 10-second-per-service wait ceiling and the
   final `wait` (`run-stack.sh:52-58`, `60-72`, `104`) are delegated to a
   runner that does not exist in this repo. Stated in the header
   (`lib.rs:10-21`) and in G4/G5/G8.
4. **`batches/B06.md:23` lists `TRIO_UPSTASH_HOST` as part of the env
   contract**, but `run-stack.sh` never sets or mentions it; the crate
   correctly omits it. The batch doc is the side that is wrong; not
   edited here (owned by the batch).
5. **The header calls the port "faithful" (`lib.rs:13`) while finding 1
   is a behaviour difference.** The header should not claim transport
   parity until G1/G2 land. No code change was made; this is the
   finding.
