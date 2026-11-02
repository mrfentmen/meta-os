# `crates/os-supervisor` — behaviour record (B013)

Read from the code at `main` (2026-11-02). Every claim cites a file and
a line range. This crate is the B21 port of the watchman chain, the
watchdog detectors, the load check, and MOS's reconcile/overseer pair.

Status words: **LIVE** (the function runs and its result is used),
**SEAM** (a trait the caller must implement; the crate does not perform
the live effect), **NOT PORTED** (see `os-supervisor-gaps.md`).

## What it is

One library crate, `os-supervisor` (`Cargo.toml:1-5`), fifteen modules
plus nine drill modules (`src/lib.rs:44-62`). It does four jobs:

1. **Watchman chain** — turn relay-watchman events into per-machine
   records, judge alive/dead/unknown, fold the journal, run the cycle,
   and expose the service loop (`watchman_watch.rs`, `watchman_bridge.rs`,
   `watchman_loop.rs`, `watchman_cycle.rs`, `watchman_runner.rs`,
   `watchman_service.rs`, `watchman_boot.rs`).
2. **Watchdog detectors** — evaluate one snapshot into alert records,
   with the locked thresholds and the frozen announcement format
   (`watchdog.rs`, `thresholds.rs`).
3. **Verification and recovery** — reconcile jobs/capabilities after a
   restart (`reconcile.rs`), dispatch/verify/requeue through the
   overseer seam (`overseer.rs`), and check surfaces end to end
   (`e2e_watchdog_surfaces.rs`).
4. **Drills** — runnable reproductions for the watchman and watchdog
   paths (`src/drills/*`, re-exported at `lib.rs:61`).

## The live chain, module by module

| Module | What it does | Load-bearing lines |
|---|---|---|
| `watchman_bridge.rs` | Folds one relay tick's `wake` events into a `WatchmanRecord`; carries the prior bell forward; builds the snapshot the watch module judges. Non-`wake` events and NaN timestamps are ignored. | `fold_tick` 84-113; `machines_snapshot` 115-128; `watchman_tick` 159-196 |
| `watchman_watch.rs` | Judges each machine `alive` / `dead` / `unknown`; opens and closes journal episodes; builds one blocked-push payload when a dead watchman cannot be revived. Never sends the push. | constants 47-53; `machine_state` 264-291; `current_states` 293-322; `episode_open` 326-341; `escalation_for` 379-418; `watchman_watch_tick_with_push` 407-479 |
| `watchman_loop.rs` | Parses one machine's stdout into events and cycles every machine; malformed lines are counted and skipped, never fatal. | `parse_event_lines` 90-115; `loop_cycle` 383-… |
| `watchman_cycle.rs` | Runs one cycle over a machine argument and returns records plus diagnostics; runner failures are reported, not raised. | enums 64-100; `CycleDiagnostics` 101-…; `run_cycle` 180-… |
| `watchman_runner.rs` | Builds the per-machine argv and runs one relay-watchman invocation with a timeout; a non-zero run is discarded. | `DEFAULT_SNAPSHOT_DIR` 80; `machine_argv` 124-167; `run_once` 169-242; `run_cycle_with_subprocess` 283-… |
| `watchman_service.rs` | The `serve_cycles` loop: default cycle function, stop condition, CLI parsing, unit directives as text. | `UNIT_DIRECTIVES` 102-116; `serve_cycles` 265-443; `parse_service_args` 464-551; `service_main` 553-… |
| `watchman_boot.rs` | First post-boot ring set: arrivals and lease expiries during downtime, reconciled against the sweep; no counter is consulted. | `post_boot_rings` 159-215; `sweep_mismatch` 217-252; `verify_boot_cycle` 254-310; `boot_brief_lines` 312-… |
| `relay_watchman.rs` | The resident bell's decision core: `open` jobs addressed to a sleeping local agent wake; `claimed` jobs with a stale heartbeat nudge; every other status is silent. | constants 66-82; `text` 201-211; `addressed_to` 217-226; `normalize_agents` 228-277; `is_sleeping` 279-285; `tick` 319-…; `validate_args` 556-566 |

## Watchdog behaviour

`watchdog.rs` is one file, 5,049 lines. Its contract is stated at
`watchdog.rs:1-63`:

- `tick` evaluates every registered detector over one snapshot and
  returns the alerts found. Detectors are listed in `DETECTORS`
  (`watchdog.rs:1570-1586`); the loop never hardcodes a detector
  (`watchdog.rs:8-10`).
- The detector set is: presence-stall, progress-stall, lease-risk,
  dead-dep, missing-dep, file-collision, attempt-warning/
  attempt-exhaustion, silent-room (info), rejected-dispatch,
  budget-warning (`watchdog.rs:12-17`, `840-1560`).
- Walk-on tracking (`detect_walk_on_workers`, `watchdog.rs:970-1005`)
  and journal failures (`detect_journal_failures`,
  `watchdog.rs:2063-2112`) are deliberately **not** in `DETECTORS`:
  the first is tracking, the second is a separate loop input
  (`watchdog.rs:17-22`).
- Severity is a frozen table, not per-call judgement:
  `SEVERITY_BY_KIND` (`watchdog.rs:1588-1601`).
- Only `critical` announces; the line is
  `ALERT:<id> <kind>: <explanation>` with newlines flattened to spaces
  (`format_announcement`, `watchdog.rs:1621-1655`).
- Pagination refuses a non-positive page size rather than slurping
  everything (`paginate`, `watchdog.rs:1666-1687`).
- A tick's message window is capped, jobs are never dropped: capping
  jobs could hide a stall or a collision (`cap_tick_snapshot`,
  `watchdog.rs:1689-1732`).

Thresholds are locked defaults with silent env fallback:
`thresholds.rs:24-61`, `parse_env_int` `thresholds.rs:70-92`. The
watchdog carries its own `Thresholds` copy and the same fallback rule
(`watchdog.rs:75-116`, `from_env_with` `watchdog.rs:157-212`).

## What it refuses

| Refusal | Where | Behaviour |
|---|---|---|
| Backend unreachable | `reconcile.rs:109-116` | Report returns immediately, all lists empty; `exit_code` is 2 (`reconcile.rs:158-166`); summary prints `redis: UNREACHABLE`. |
| Sweep or prune failure | `reconcile.rs:117-126` | Prints `WARNING: sweep failed (...)` / `WARNING: prune failed (...)` and continues to the job reads. Nothing is invented. |
| Empty dispatch spec | `overseer.rs:199-235` | `dispatch` returns an error; no job is posted. |
| Job id not parseable | `overseer.rs:120-132` | `parse_job_id` returns `Err("could not parse job id from: ...")`. |
| Worker with no DM secret | `overseer.rs:199-235` | Records `(nick, false, "no DM secret registered")`; no DM is sent. |
| Non-positive page size | `watchdog.rs:1666-1672` | `Err("page_size must be a positive int")`. |
| Unknown explanation template | `watchdog.rs:722-…` | Panics, exactly as Python `render` raises; a tick skips a panicking detector (`watchdog.rs:48-52`). |
| Unparseable/blank env value | `thresholds.rs:70-92`; `watchdog.rs:120-134` | Falls back to the default silently; never crashes and never invents a threshold. |
| Blank/missing text | `relay_watchman.rs:201-211` | `None`; a blank value is absent, never guessed. |
| Bad watchman timing args | `relay_watchman.rs:556-566` | `Err("watchman: --interval must be positive and --heartbeat-stale-seconds non-negative")`. |
| Alert record missing kind/severity/dedupe key | `e2e_watchdog_surfaces.rs:286-326` | `Err("detector alert missing kind" / "... severity" / "... dedupe_key")`; nothing is invented. |
| Job with no usable id | `watchman_boot.rs:159-215` | The job never rings. |
| Malformed machine record | `watchman_watch.rs:264-291` | Judges `unknown`; yields no journal record. |

## What it writes down

- `Alert` records (`watchdog.rs:610-720`): kind, severity, subjects,
  the kind's own fields, `explanation`, `suggested_fix`, `dedupe_key`,
  `created_at`, optional explicit `id`.
- `JournalEntry` records (`watchman_watch.rs:206-248`): `kind`
  (`crew-dark`, `watchman-recovered`, `escalation`), machine, reason,
  question, push payload, timestamps, dedupe key.
- `ReconcileReport` (`reconcile.rs:77-107`): `redis`, `requeued`,
  `pruned`, `unverified`, `blocked`.
- `BootNote` / `Ring` / `SweepMismatch` (`watchman_boot.rs:95-140`);
  `boot_brief_lines` renders them (`watchman_boot.rs:312-…`).
- `StateRecord` board rows (`watchman_watch.rs:99-112`) via
  `current_states` (`watchman_watch.rs:293-322`).
- `AlertRecord` / `WatchItem` for the surfaces check
  (`e2e_watchdog_surfaces.rs:113-165`).

Worked, field-by-field examples are in `os-supervisor-records.md`.

## Live-behavior boundary (never faked here)

- No Redis, bus, jobs, capabilities or git call is made. Each is a
  trait seam: `ReconcileBackend` (`reconcile.rs:31-48`),
  `OverseerBackend` (`overseer.rs:62-117`),
  `E2eSurfaces` (`e2e_watchdog_surfaces.rs:179-187`),
  `BlockedPushBuilder` (`watchman_watch.rs:131-145`),
  `PolishClient` (`watchdog.rs:796-805`),
  `IntegrationSurface` (`watchdog_load_check.rs:69-85`).
- The watchdog's `--beat` sink is a no-op in this standalone module;
  the real beat writer belongs to the store module
  (`watchdog.rs:56-63`).
- The watchman only builds a blocked push; it never sends one
  (`watchman_watch.rs:44-46`).
- The relay watchman stops at the decision core; file reads, JSON
  parsing, stdout and sleeping are modelled as inputs/outputs
  (`relay_watchman.rs:30-52`).

## Findings

1. `lib.rs:1` still calls the crate a "skeleton (B00)" while
   `lib.rs:44` says B21 ported the modules. The header is stale; fixed
   to describe the port (B016).
2. `watchdog.rs:75-116` carries a second `Thresholds` and
   `env_int` beside `thresholds.rs:70-92`. The module docs call this a
   deliberate seam (`watchdog.rs:23-27`); it is a duplicate today and a
   future `re-export` candidate, not a behaviour difference — the
   defaults and fallback rule are identical.
3. `lib.rs:1-62` lists 40 source files but the module map is 15 + 9
   drills; `drills/kill_worker.rs` is in `lib.rs`'s source list at
   line 4 but has no counterpart in `drills/mod.rs`? It does
   (`drills/mod.rs` declares it); no drift found.
