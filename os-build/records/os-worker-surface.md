# `crates/os-worker` — public surface inventory (B082)

Every exported name, one line each. "Used" means a caller exists in the
crate or its tests; "unused" means no caller in the repo today (the
crate has no external consumer — see `os-worker-callers.md`).

## Constants

| Name | Used? | Where |
|---|---|---|
| `LOG_NAME` | used | drivers and `compute_artifacts` |
| `DEFAULT_BINARY` | used | `MuseDriver::new` |
| `NOTE_LIMIT` | used | Muse reader |
| `DRIVER_CONTRACT_MD` / `DRIVER_CONFORMANCE_MD` | used | pin tests |
| `DRIVER_CONTRACT_SHA256` / `DRIVER_CONFORMANCE_SHA256` | used | pin tests |
| `BACKOFF_BASE_SECONDS` / `BACKOFF_CAP_SECONDS` | used | `backoff_seconds` |
| `LEASE_DEFAULT_SECONDS` | used | drill |

## Supporting helpers

| Name | Used? | Where |
|---|---|---|
| `sha256` | used | `sha256_hex`, `hmac_sha256_hex` |
| `sha256_hex` | used | snapshot, tests |
| `hmac_sha256_hex` | used | `sign_intake` |
| `now_secs_f64` | used | `progress_record` |
| `tail_chars` / `head_chars` | used | acceptance detail, worker loop, Muse notes |
| `json_escape` | used | `JsonValue::to_json`, `ArtifactsRecord::to_json` |
| `parse_json` | used | `run_driver`, tests |

## JSON

| Name | Used? | Where |
|---|---|---|
| `JsonValue` | used | `parse_json`, `spec_from_json`, `run_driver` |
| `JsonValue::get` / `as_str` / `as_i64` / `as_str_list` / `to_json` | used | `spec_from_json`, tests |

## Acceptance

| Name | Used? | Where |
|---|---|---|
| `parse_accept` | used | `validate_spec`, `verify_accept` |
| `run_accept_checks` | used | `verify_accept` |
| `verify_accept` | used | `compute_artifacts` |
| `AcceptCheck` / `AcceptResult` | used | the three functions and artifacts |

## Driver contract

| Name | Used? | Where |
|---|---|---|
| `DriverError` + `message` / `is_unsigned` / `is_bad_spec` / `is_not_started` | used | every driver path |
| `JobSpec` / `JobSpec::new` | used | drivers, `run_driver`, tests |
| `validate_spec` | used | both drivers, `spec_from_json` |
| `HeartbeatRecord` / `progress_record` | used | drivers and loop |
| `HeartbeatSink` / `vec_sink` | used | driver constructors |
| `ArtifactsRecord` / `to_json` | used | both drivers, tests |
| `snapshot` / `compute_artifacts` | used | drivers |
| `status_code` / `wait_child` / `terminate_child` / `poll_child` | used | drivers |
| `StartRecord` / `StopRecord` | used | drivers |

## Stub and Muse drivers

| Name | Used? | Where |
|---|---|---|
| `StubDriver` + `new` / `heartbeats` / `has_child` / `start` / `heartbeat` / `poll` / `stop` / `wait` / `artifacts` | used | tests and drill |
| `MuseDriver` + `new` / `heartbeats` / `has_child` / `prompt_path` / `tmpdir` / `start` / `heartbeat` / `poll` / `stop` / `wait` / `artifacts` | used | tests and `run_driver` |
| `build_prompt` / `build_argv` / `find_binary` | used | Muse driver |

## Runner

| Name | Used? | Where |
|---|---|---|
| `run_driver` | used (tests) | `lib.rs:3575`, `3594`; no production caller — the Python CLI is the live consumer (gap G3) |
| `spec_from_json` | used | `run_driver`, tests |

## Uplink

| Name | Used? | Where |
|---|---|---|
| `backoff_seconds` | used | `record_failure`, tests |
| `Order` | used | `uplink_tick`, tests |
| `UplinkState` / `empty_state` | used | `empty_state` in the existing uplink tests (`lib.rs:4541-4631`) |
| `IntakeRecord` | used | `take_in` |
| `UplinkEvent` | used | `uplink_tick` |
| `validate_order` | used | `uplink_tick` |
| `sign_intake` | used | `intake_record` |
| `record_failure` / `record_success` | used | `uplink_tick` |
| `uplink_tick` | used | tests; no live caller (caller owns the loop) |

## Worker loop

| Name | Used? | Where |
|---|---|---|
| `parse_announcement` | used | tests |
| `HandlerError` | used | `run_once` signature |
| `RunReport` | used | `run_once` return |
| `Announcement` | used | `WorkerBackend::poll_dms` |
| `WorkerBackend` | used | `run_once` generic bound; no impl in repo (gap G2) |
| `Worker` + `new` / `matches` / `run_once` | used | tests; no live caller |

## Stalls and drills

| Name | Used? | Where |
|---|---|---|
| `StallThresholds` + `defaults` / `from_env` | used | detectors, tests |
| `SnapshotJob` / `Snapshot` | used | detectors, drill |
| `last_activity` | used | both detectors |
| `StallAlert` | used | detectors, `announcements_for`, drill |
| `detect_presence_stall` / `detect_progress_stall` | used | `tick_stalls` |
| `tick_stalls` / `announcements_for` | used | drill |
| `parse_section` / `parse_section_multi` | test only | `test_os_worker_units` parity |
| `slice_expected` | test only | slice parity test |
| `BridgeJob` / `apply_heartbeat` | test only | heartbeat-bridge parity test |
| `SweepJob` / `sweep_expired_leases` | used | drill, tests |
| `KillDrillReport` / `run_kill_worker_drill` | used | drill, tests |

## Count

- 79 exported functions and methods, 26 exported types/traits/enums
  (including the `HeartbeatSink` alias), 10 constants.
- No exported name is dead: every one is used inside the crate or its
  tests. `run_driver` has no production caller; its only callers are the
  crate's own tests.
- Test-only: `parse_section`, `parse_section_multi`, `slice_expected`,
  `BridgeJob`, `apply_heartbeat` (5).
- No external crate imports any of it.
