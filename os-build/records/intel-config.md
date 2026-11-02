# `crates/intel` — config surface (B176)

Everything the crate reads from outside itself: environment variables,
files, and the injected inputs that stand in for configuration. There
is **no binary and no command-line flag** in this crate; the only
CLI-shaped code is `b09_core::cli`, which is a set of pure predicates
(`needs_confirm_large`, `format_dispatch_announcement`,
`approval_granted`) and reads nothing.

## Environment variables

| Name | Read at | Default | Accepted | Wrong value |
|---|---|---:|---|---|
| `MUSE_RELAY_KEY_PREFIX` | `b09_core/store.rs:14-16` (called per key build) | `muse-bus` | any string | never refused; an empty value produces keys beginning `:intel:...` |
| `CARGO_MANIFEST_DIR` | `b10_brief/brief.rs:173` (compile time) | the crate dir | build-time path | compile-time only; no runtime refusal |
| `WATCHDOG_STALL_MINUTES` | `b12a_drills/deps.rs:140-176` | `10` | integer ≥ 0 | empty, non-integer, or below 0 → silently `10` |
| `WATCHDOG_PROGRESS_STALL_MINUTES` | same | `10` | integer ≥ 0 | silently `10` |
| `WATCHDOG_LEASE_RISK_WINDOW_MINUTES` | same | `5` | integer ≥ 0 | silently `5` |
| `WATCHDOG_LEASE_RISK_QUIET_MINUTES` | same | `2` | integer ≥ 0 | silently `2` |
| `WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES` | same | `30` | integer ≥ 0 | silently `30` |
| `WATCHDOG_SILENT_ROOM_MINUTES` | same | `60` | integer ≥ 0 | silently `60` |
| `WATCHDOG_BEAT_TTL_SECONDS` | same | `300` | integer ≥ 1 | silently `300` |
| `WATCHDOG_TICK_PAGE_SIZE` | same | `1000` | integer ≥ 1 | silently `1000` |
| `WATCHDOG_TICK_MAX_MESSAGES` | same | `1000` | integer ≥ 1 | silently `1000` |
| `WATCHDOG_WATCHMAN_STALE_MINUTES` | same | `5` | integer ≥ 0 | silently `5` |
| `WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS` | same | `300` | integer ≥ 1 | silently `300` |

`parse_env_int` (`deps.rs:40-55`) trims, returns the default for an
empty string, parses `i64`, and returns the default when the value is
below the minimum or does not parse. **There is no refusal path**: a
bad threshold is not an error, it is the default. That is deliberate
(the Python `_env_int` rule), and it means a typo cannot stop a drill.

`lease_default_seconds` is fixed at `1800` (`deps.rs:106`, `:175`) and
has no environment override.

Not read by this crate but named by its docs/originals:

- `SPARK_TRANSPORT` — the Python source reads it (`os/intel/spark_client.py:101`).
  In Rust, `TransportKind::from_env(transport: &str)`
  (`b11_spark/spark_client.rs:53-61`) takes the string and refuses
  anything except `agent` / `http` with
  `SparkError::NotConfigured("unknown SPARK_TRANSPORT: ...")`. The
  caller does the env read.
- `METAOS_LAUNCH_DIR` — written into the child environment by
  `b14_trust/launch_run.rs:85-89`; not read by this crate.

## Files

| Path | Reader | Missing/unreadable behaviour |
|---|---|---|
| `fixtures/b10/prompts/*.md` | `b10_brief/brief.rs:160-194` (`brief_prompt_path`, `load_brief_prompt`) | `brief_prompt_path` returns `None` for an unknown kind/version; `load_brief_prompt` returns `""` for any failure, never raises. A missing prompt therefore sends no system text, it does not fail the brief. |
| `fixtures/b09/capabilities/*.json` | `b09_core/capability_files.rs:96-260` (`load_grant`, `load_grant_for`, `load_crew_grants`) | `load_grant` returns `Err(String)` on bad JSON/fields; `load_grant_for` returns `Ok(None)` when no grant file exists. Test evidence includes the carried file at `capability_files.rs:273`. |
| `fixtures/b13/` pack | `b13_devpack/mod.rs:18-23` (`PACK_FILES`) and the B13 test | The pack is data, not read by the shapers; a stale pack must be regenerated, never hand-edited (`mod.rs:11-16`). |
| `fixtures/b14/metaos-demo.env` | fixture for the B14 demo-profile test (`b14_trust/mod.rs:7`) | Never loaded by production; a missing fixture fails the test that reads it. |
| temp dirs | `b12a_drills/spoof_dispatch_drill.rs:73`, `redis_down_drill.rs:168`, `tests/b12a_parity.rs:108` | Created per run with `std::env::temp_dir()`; failure to create is an I/O error from the standard library, not a crate-specific refusal. |

The store is **in memory** (`b09_core/store.rs:75-90`): no Redis
connection, no file, no credentials. A Redis boundary adapter is not
in this crate.

## Flags and injected config

There are no flags. The equivalent surfaces are constructor/argument
values:

| Surface | Where | Default / refusal |
|---|---|---|
| `Thresholds::locked()` | `deps.rs:66-86` | the twelve locked defaults above |
| `Thresholds::from_env_map(&[(String, String)])` | `deps.rs:88-138` | same names/minimums; explicit map, no process env |
| `Thresholds::from_env()` | `deps.rs:140-176` | process env; silent fallback |
| `TransportKind` | `spark_client.rs:32-61` | `agent` or `http`; anything else is `NotConfigured` |
| `complete(..., spend_so_far_usd, cap_usd)` | `spark_client.rs:129-145` | HTTP only: `spend_so_far_usd >= cap_usd` → `SparkError::Budget`; agent calls are not capped here (they carry no API cost) |
| `check_preconditions(...)` | `b14_trust/launch_run.rs:40-57` | empty argv, missing dir, missing `launch.json` → `LaunchRunError` |
| `run_from_launch(...)` | `launch_run.rs:59-83` | verifier `ok: false` → `LaunchRunError("launch refused, verification failed: ...")` |

## Findings

1. `key_prefix()` re-reads `MUSE_RELAY_KEY_PREFIX` on every key build
   (`store.rs:14`). Changing the variable mid-process changes the keys
   an existing `Store` uses, so records written before and after the
   change land under different prefixes. The Python original resolves
   the prefix once at import (`os/intel/store.py:4`, `os/admin.py:53`).
2. There is no configuration refusal anywhere for the watchdog
   variables: a negative or malformed value is silently replaced by
   the default. That matches the Python, but it means a drill cannot
   prove a bad config was rejected — it can only prove the default.
3. The crate reads no secrets and no network settings; every network
   edge (Redis, Spark HTTP) is outside it by design.
