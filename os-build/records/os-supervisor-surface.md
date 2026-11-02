# `crates/os-supervisor` — public surface inventory (B022)

Criterion used for the last column, stated so it can be checked:
**chain** = called by another module in this crate; **drill** = called
by `src/drills/*`; **test-only** = referenced only inside its own
`#[cfg(test)]` module; **none** = no caller found in this tree.
Because every item is `pub`, `dead_code` never warns — this inventory is
the only usage reading. `cargo doc -p os-supervisor` is the exhaustive
signature list.

## `thresholds` (`thresholds.rs`)

Constants `STALL_MINUTES_DEFAULT:25`, `PROGRESS_STALL_MINUTES_DEFAULT:29`,
`LEASE_RISK_WINDOW_MINUTES_DEFAULT:32`,
`LEASE_RISK_QUIET_MINUTES_DEFAULT:35`,
`ALERT_DEDUPE_COOLDOWN_MINUTES_DEFAULT:39`,
`SILENT_ROOM_MINUTES_DEFAULT:42`, `WATCHDOG_BEAT_TTL_SECONDS_DEFAULT:45`,
`TICK_PAGE_SIZE_DEFAULT:48`, `TICK_MAX_MESSAGES_DEFAULT:51`,
`WATCHMAN_STALE_MINUTES_DEFAULT:55`,
`TIMER_SWEEP_INTERVAL_SECONDS_DEFAULT:58`, `LEASE_DEFAULT_SECONDS:61` —
all **chain** (read by drills at `drills/watchman_bridge.rs:54`,
`drills/watchman_boot.rs:71`, `drills/watchman_cycle.rs:72`, and by the
service).
`parse_env_int:70` **chain**; `env_int:87` **chain** (`from_env` calls
it); `Thresholds:94` with `defaults:120` and `from_env:137` **chain**.

## `watchdog` (`watchdog.rs`)

- `LEASE_DEFAULT_SECONDS:67`, `SEVERITY_BY_KIND:1588` — **chain**.
- `Thresholds:75` (`from_env:157`, `from_env_with:166`, `Default:108`),
  `env_int:120`, `env_int_range:136` — **chain** (drills build
  thresholds; `e2e` uses its own fixture).
- `DETECTORS:1570` (pub static, the ten registered detectors) — **chain**.
- Values/records: `Value:220`, `Job:317`, `Message:360`,
  `BudgetEntry:369`, `TickWindow:380`, `Snapshot:396`, `Alert:610`,
  `JournalEntry:1948` — **chain** (constructed by detectors, drills,
  e2e, load check).
- Detectors: `detect_presence_stall:840`, `progress_stall:894`,
  `lease_risk:1007`, `dead_dep:1062`, `missing_dep:1121`,
  `file_collision:1161`, `attempt_exhaustion:1258`, `silent_room:1326`,
  `rejected_dispatch:1390`, `budget_warning:1521` — **chain** (registered
  in `DETECTORS`).
- Tracking: `detect_walk_on_workers:970` + `WalkOnRecord:945` — **none**
  outside its own tests; deliberately not a detector.
- Explanations: `render_explanation:722`, `PolishClient:796`,
  `polish_explanation:807` — **chain** (detectors).
- `DetectorFn:833` — **chain**.
- Announcements: `format_announcement:1621`, `announcements_for:1657` —
  **chain** (drills and the CLI).
- Pagination/window: `paginate:1666`, `cap_tick_snapshot:1689` —
  **chain** (tick).
- Clock: `parse_server_time:1734`, `wall_clock_now:1765`,
  `resolve_tick_now:1778`, `resolve_tick_now_with_clock:1784` —
  **chain** (tick).
- Tick: `tick_full:1813`, `tick:1866`, `tick_with_thresholds:1883` —
  **chain**.
- Restart note: `restart_event_note:1912` — **test-only**.
- Journal: `JOURNAL_RELAY_UNIT_PREFIX:1941`,
  `JOURNAL_FAILURE_MAX_PRIORITY:1944`,
  `journal_entry_fields:1996`, `journal_entry_fields_from_text:2001`,
  `journal_entry_is_failure:2014`, `journal_entry_is_failure_value:2032`,
  `parse_journal_entries:2042`, `detect_journal_failures:2063`,
  `journal_watch_tick_text:2114`, `journal_watch_tick_entries:2125` —
  **chain** (CLI journal path) / **test-only** for the value helpers.
- `parse_json:2372`, `run_cli:2408` — **chain** (CLI, tests).

## `watchdog_load_check` (`watchdog_load_check.rs`)

`MESSAGE_COUNT:37`, `JOB_COUNT:39`, `SILENT_COUNT:41`, `STUCK_COUNT:43`,
`CLAIMED_COUNT:45`, `SILENT_WORKER:47`, `STUCK_WORKER:49`,
`ADVANCE_SECONDS:53`, `REBEAT_GAP_SECONDS:55`, `TICK_BUDGET_SECONDS:58`,
`TOTAL_BUDGET_SECONDS:60`, `STAGE_NAMES:63` — **test-only** in this
tree (no orchestrator calls the check yet).
`IntegrationSurface:69`, `IntIntegration:87` — **none** outside tests.
`AlertSummary:103`, `StoredRecord:125`, `TickRecord:136`,
`StageResult:149`, `RunResult:160`, `Tick1Outcome:181`,
`Tick2Outcome:192`, `Tick3Outcome:209` — **none** outside tests.
`validate_tick1:245`, `validate_tick2:321`, `validate_tick3:380`,
`validate_budgets:401`, `evaluate:429`, `render_transcript:508`,
`render_watchdog_load_md:547` — **none** outside tests; the live caller
is a gap (G6).

## `e2e_watchdog_surfaces` (`e2e_watchdog_surfaces.rs`)

`NOW:46`, `E2E_ROOM:48`, `EXPECTED_ALERT_ID:50` — **test-only**.
`SnapshotJob:55`, `Snapshot:75`, `Alert:86`, `AlertRecord:113`,
`WatchItem:146`, `DashboardRow:155`, `DashboardOutcome:166` — **none**
outside tests. `E2eSurfaces:179`, `LocalSurfaces:363` — **none**
outside tests. `stall_snapshot:189`, `quiet_snapshot:204`,
`detect_presence_stall:222`, `clean_room:271`,
`build_alert_record:286`, `extract_watch_items:326`,
`watch_items_lines:347`, `StageResult:397`, `LoopResult:408`,
`run_loop:427` — **none** outside tests. The live surfaces are a gap.

## `reconcile` (`reconcile.rs`)

`JobHash:26` **chain**, `ReconcileBackend:31` **none** (no impl in
tree), `done_unverified_from:50` **chain**, `blocked_from:64` **chain**,
`ReconcileReport:77` + `is_clean:97` **chain**, `reconcile:109`
**none** (no startup caller), `render_summary:133` **test-only**,
`exit_code:158` **test-only**.

## `overseer` (`overseer.rs`)

`LEASE_DEFAULT:37` **test-only**, `CheckResult:42` **chain**,
`CapabilityRecord:53` **chain**, `OverseerBackend:62` **none** (no
impl), `parse_job_id:120` **chain**, `parse_requeued_lines:134`
**chain**, `format_report:148` **chain**, `truncate_tail:167` **chain**,
`normalize_requirements:178` **chain**, `DmResult:187` **chain**,
`dispatch:199` **none**, `set_verified:236` **none**,
`verify_done:269` **none**, `done_unverified:346` **none**,
`TickReport:361` **none**, `tick:377` **none**. The overseer is a
library with no production caller yet (gap G2).

## `relay_watchman` (`relay_watchman.rs`)

`DEFAULT_INTERVAL_SECONDS:66`, `DEFAULT_HEARTBEAT_STALE_SECONDS:70`,
`WAKE:73`, `NUDGE:76`, `EXIT_OK:79`, `EXIT_BAD_INPUT:82` — **test-only**.
`EventKind:86`, `Event:110`, `Job:134`, `AgentInput:156`, `Agent:172`,
`AgentsInput:188` — **chain** in module. `text:201`, `addressed_to:217`,
`normalize_agents:228`, `is_sleeping:279`, `wake_key:287`,
`nudge_key:301`, `tick:319`, `InputLoad:407`, `StateLoad:424` (+
`ledger:431`), `OnceSuccess:459`, `OnceError:471`, `merge_ledger:476`,
`run_once:490`, `once_exit_code:527`, `loop_cycle:540`,
`validate_args:556` — **test-only** outside the module; no parent CLI
in this tree (gap G7).

## `watchman_watch` (`watchman_watch.rs`)

`ALIVE:47`, `DEAD:49`, `UNKNOWN:51`, `WATCHMAN_STALE_MINUTES:53` —
**chain**. `WatchmanRecord:60` (+`new:73`), `WatchmanSnapshot:85`
(+`new:93`), `StateRecord:99`, `BlockedPush:114`,
`BlockedPushBuilder:131`, `DefaultPushBuilder:147`,
`JournalEntry:206` (+`new:236`) — **chain**. `stale_minutes_default:249`,
`machine_state:264`, `current_states:293`,
`watchman_watch_tick:397`, `watchman_watch_tick_with_push:407`,
`watchman_brief_lines:481`, `board_lines:517` — **chain**.

## `watchman_bridge` (`watchman_bridge.rs`)

`WAKE_KIND:46`, `WatchEvent:54` (+`new:69`), `fold_tick:84`,
`machines_snapshot:115`, `snapshot_from_records:130`,
`watchman_tick:159` — all **chain**.

## `watchman_loop` (`watchman_loop.rs`)

`LoopRun:67`, `Diagnostics:76`, `parse_event_lines:90`, `loop_cycle:383`
— **chain**.

## `watchman_cycle` (`watchman_cycle.rs`)

`MachinesArg:64`, `RunnerResult:87`, `CycleDiagnostics:101`,
`run_cycle:180` — **chain**.

## `watchman_runner` (`watchman_runner.rs`)

`DEFAULT_SNAPSHOT_DIR:80`, `DEFAULT_TIMEOUT_SECONDS:82`,
`default_program:86`, `machine_argv:124`, `run_once:169`,
`make_subprocess_runner:244`, `run_cycle_with_subprocess:283` —
**chain**.

## `watchman_service` (`watchman_service.rs`)

`DEFAULT_INTERVAL_SECONDS:97`, `UNIT_DIRECTIVES:102`,
`UNIT_MACHINE_LIST_GAP:117`, `unit_directive:124`, `CycleFnOutput:134`,
`ServeOptions:149`, `ServiceResult:204`, `default_cycle_fn:219`,
`serve_cycles:265`, `CliArgs:445`, `parse_service_args:464`,
`service_main:553` — **chain** (service) / **none** as a binary entry
(no `main.rs` in this crate).

## `watchman_boot` (`watchman_boot.rs`)

`ARRIVED_DURING_DOWNTIME:57`, `LEASE_EXPIRED_DURING_DOWNTIME:59`,
`BootJob:67` (+`new:80`), `Ring:95`, `SweepMismatch:111`,
`BootNote:120`, `post_boot_rings:159`, `sweep_mismatch:217`,
`verify_boot_cycle:254`, `boot_brief_lines:312` — **chain** (the boot
drill) / **none** as a production caller yet.

## `drills` (`src/drills/*`)

Every `phase_*`, `run_drill`, and fixture helper is **test-only**: the
drills are the tests. `drills/mod.rs` declares nine modules.
