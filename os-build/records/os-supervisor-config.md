# `crates/os-supervisor` — config surface (B020)

Every environment variable, flag, and file the crate reads. Defaults
and refusal behaviour are the code's, not a plan's.

## Environment variables

Read once by `thresholds::Thresholds::from_env` (`thresholds.rs:137-200`)
and by `watchdog::Thresholds::from_env` (`watchdog.rs:157-212`). Both
use the same fallback rule: unset, blank, unparseable, or below-minimum
falls back to the default **silently** (`thresholds.rs:70-92`;
`watchdog.rs:120-134`). A typo never crashes the watchdog.

| Variable | Field | Default | Minimum | Read by |
|---|---|---:|---:|---|
| `WATCHDOG_STALL_MINUTES` | `stall_minutes` | 10 | 0 | thresholds, watchdog |
| `WATCHDOG_PROGRESS_STALL_MINUTES` | `progress_stall_minutes` | 10 | 0 | thresholds, watchdog |
| `WATCHDOG_LEASE_RISK_WINDOW_MINUTES` | `lease_risk_window_minutes` | 5 | 0 | thresholds, watchdog |
| `WATCHDOG_LEASE_RISK_QUIET_MINUTES` | `lease_risk_quiet_minutes` | 2 | 0 | thresholds, watchdog |
| `WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES` | `alert_dedupe_cooldown_minutes` | 30 | 0 | thresholds, watchdog |
| `WATCHDOG_SILENT_ROOM_MINUTES` | `silent_room_minutes` | 60 | 0 | thresholds, watchdog |
| `WATCHDOG_BEAT_TTL_SECONDS` | `watchdog_beat_ttl_seconds` | 300 | 1 | thresholds, watchdog |
| `WATCHDOG_TICK_PAGE_SIZE` | `tick_page_size` | 1000 | 1 | thresholds, watchdog |
| `WATCHDOG_TICK_MAX_MESSAGES` | `tick_max_messages` | 1000 | 1 | thresholds, watchdog |
| `WATCHDOG_WATCHMAN_STALE_MINUTES` | `watchman_stale_minutes` | 5 | 0 | thresholds; also `stale_minutes_default` (`watchman_watch.rs:249-261`, accepts f64) |
| `WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS` | `timer_sweep_interval_seconds` | 300 | 1 | thresholds |
| `WATCHDOG_BUDGET_WARN_PERCENT` | `budget_warn_percent` | 80 | 1, max 100 | watchdog only (`env_int_range`, `watchdog.rs:136-153`) |

`LEASE_DEFAULT_SECONDS = 1800` is deliberately **not** env-overridable
(`thresholds.rs:63-68`): the lease belongs to jobs, and two modules
overriding the same number would disagree silently.

## Command lines

### `watchdog` — `run_cli` (`watchdog.rs:2408-…`)

| Flag | Meaning | Bad value |
|---|---|---|
| `--once` | run one tick | — |
| `--loop` | tick repeatedly | — |
| `--announce` | print each critical WDG-015 line (stdout only, never a bus post) | — |
| `--beat` | accepted; the callback is a no-op sink here | — |
| `--snapshot <path>` | read the snapshot JSON | missing value → exit 2, `watchdog: --snapshot needs a value`; unreadable/unparseable → exit 1, `watchdog: cannot load snapshot: …` |
| `--journal <path>` | read journal JSON from a file (no journalctl exec) | same missing-value rule |
| `--interval <secs>` | loop pause, default 60 | `watchdog: bad --interval: <v>` → exit 2 |
| `--max-ticks <n>` | bound a loop run | `watchdog: bad --max-ticks: <v>` → exit 2 |
| `--room <name>` | recorded, not read yet (waits on FND-014) | missing value → exit 2 |
| anything else | — | `watchdog: unknown argument: <arg>` → exit 2 |

Neither `--once` nor `--loop` given: `watchdog needs --once or --loop`,
exit 2 (`watchdog.rs:2497-2500`).

### `relay-watchman-watch.service` — `parse_service_args` (`watchman_service.rs:464-551`)

| Flag | Meaning | Bad value |
|---|---|---|
| `--machines a,b` | comma-separated names, trimmed; a bare flag reads as an empty list | — |
| `--cycles <n>` | bounded loop | missing → `missing --cycles value`; non-int → `invalid --cycles value` |
| `--interval <secs>` | default 60 | missing → `missing --interval value`; non-number → `invalid --interval value` |
| `--snapshot-dir <dir>` | snapshot directory | missing → `missing --snapshot-dir value` |
| anything else | — | `unknown argument: <arg>` |

`service_main` returns 2 on a malformed command line
(`watchman_service.rs:553-…`).

### `relay_watchman` — `validate_args` (`relay_watchman.rs:556-566`)

`--interval` default 10 s, `--heartbeat-stale-seconds` default 300 s
(`relay_watchman.rs:66-70`). Invalid: `watchman: --interval must be
positive and --heartbeat-stale-seconds non-negative` → exit 2
(`EXIT_BAD_INPUT`, `relay_watchman.rs:82`). The file/loop shell is
modelled, not read: see `os-supervisor-gaps.md` G7.

## Files

| File | Who reads it | Default / note |
|---|---|---|
| Snapshot JSON | `watchdog --snapshot` | none: no flag → `Snapshot::default()` (empty) |
| Journal JSON | `watchdog --journal` | none: no flag → no journal input |
| Snapshot directory | `watchman_runner` | `DEFAULT_SNAPSHOT_DIR = "/run/metaos"` (`watchman_runner.rs:80`) |
| Jobs JSON / agents JSON / state JSON | relay watchman | modelled as `InputLoad`/`StateLoad` (`relay_watchman.rs:400-455`); the CLI shell does the reads |
| Unit directives | `watchman_service::UNIT_DIRECTIVES` | text only (`watchman_service.rs:102-116`); this crate installs nothing |

## Refusal summary

No config value ever aborts a threshold read: the fallback is silent by
design (`thresholds.rs:12-18`). Command-line errors are the loud ones:
exit 2 for usage, exit 1 for an unreadable snapshot/journal, and a typed
`Err` string for the library parsers.
