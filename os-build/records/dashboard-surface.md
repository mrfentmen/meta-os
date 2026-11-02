# `dashboard` — public surface inventory (B154)

Every `pub` name in `crates/dashboard/src`, one line each, with its use
in the repo today. "tests-only" means the only caller is a test (the
crate has no production caller); "internal" means another function in
`contract.rs` uses it.

## Module

| Name | Line | Used |
|---|---|---|
| `contract` (module) | `lib.rs:61` | yes — every test imports it |

## Constants

| Name | Line | Used |
|---|---|---|
| `BRIEF_KINDS` | `contract.rs:26` | internal (`validate_brief_payload`) + gap-close test |
| `BRIEF_STALE_SECONDS` | `contract.rs:29` | internal (`is_stale`) + gap-close test |
| `VERDICTS` | `contract.rs:32` | **unused** — `verdict_icon` hardcodes the same words |
| `PALETTE_FOREGROUNDS` | `contract.rs:91` | tests-only (contrast) |
| `PALETTE_BACKGROUNDS` | `contract.rs:101` | tests-only (contrast) |
| `BRIEF_SECTION_ORDER` | `contract.rs:143` | tests-only (order/default-open) |
| `ROLLBACK_STEPS` | `contract.rs:366` | internal (`rollback_runbook_ok`) + error-path test |

## Records and enums

| Name | Line | Used |
|---|---|---|
| `BriefPayload` | `contract.rs:39` | tests + public API shape |
| `AlertCard` | `contract.rs:162` | tests-only |
| `DeepLink` | `contract.rs:181` | tests-only |
| `TodayCounts` | `contract.rs:224` | tests-only |
| `TodayJob` | `contract.rs:261` | tests-only |
| `TodayAlert` | `contract.rs:270` | tests-only |
| `SourceError` | `contract.rs:332` | tests-only (new `error_paths.rs`) |
| `CrewAlert` | `contract.rs:438` | tests-only |
| `Ribbon` | `contract.rs:450` | tests-only |
| `AttemptsBadge` | `contract.rs:499` | tests-only |
| `Artifact` | `contract.rs:567` | tests-only |
| `ArtifactLink` | `contract.rs:577` | tests-only |
| `LifecycleAlert` | `contract.rs:654` | tests-only |
| `LifecycleResult` | `contract.rs:689` | tests-only |
| `RenameLogEntry` | `contract.rs:784` | tests-only |
| `NamesHashEntry` | `contract.rs:806` | tests-only |
| `NamesHistoryEntry` | `contract.rs:827` | tests-only |

## Functions

| Name | Line | Used |
|---|---|---|
| `validate_brief_payload` | `contract.rs:49` | tests-only |
| `template_marker` | `contract.rs:64` | tests-only |
| `is_stale` | `contract.rs:69` | internal (`stale_label`) + tests |
| `stale_label` | `contract.rs:75` | tests-only |
| `wcag_luminance` | `contract.rs:105` | internal (`wcag_contrast_ratio`) + tests |
| `wcag_contrast_ratio` | `contract.rs:118` | tests-only |
| `verdict_icon` | `contract.rs:124` | unit test only |
| `default_open` | `contract.rs:134` | tests-only |
| `brief_section_title` | `contract.rs:148` | tests-only |
| `alerts_feed` | `contract.rs:169` | tests-only |
| `addressable_cards` | `contract.rs:175` | tests-only |
| `parse_deep_link` | `contract.rs:189` | tests-only |
| `resolve_brief_link` | `contract.rs:208` | tests-only (new `gap_close.rs`) |
| `demo_mode_on` | `contract.rs:214` | tests-only |
| `today_counts` | `contract.rs:232` | unit test only |
| `same_day` | `contract.rs:254` | internal (`count_today_records`) + edge test |
| `count_today_records` | `contract.rs:281` | tests-only |
| `today_line` | `contract.rs:321` | tests-only |
| `error_row` | `contract.rs:339` | tests-only (new `error_paths.rs`) |
| `brief_me_now_enabled` | `contract.rs:351` | tests-only |
| `dispatch_approve_is_request_only` | `contract.rs:356` | tests-only |
| `dispatch_may_auto_post` | `contract.rs:361` | tests-only |
| `rollback_runbook_ok` | `contract.rs:377` | tests-only |
| `html_escape` | `contract.rs:407` | internal (ribbon/files/artifact) + edge test |
| `route_encode_id` | `contract.rs:423` | internal (`alert_ribbon`) + tests |
| `alert_ribbon` | `contract.rs:473` | tests-only |
| `attempts_badge` | `contract.rs:508` | tests-only |
| `files_line` | `contract.rs:529` | tests-only |
| `deps_line` | `contract.rs:545` | tests-only |
| `artifact_link` | `contract.rs:585` | tests-only |
| `py_str_json` | `contract.rs:606` | internal (entry builders) + tests |
| `is_nonce_hex` | `contract.rs:637` | tests-only |
| `alert_lifecycle_status` | `contract.rs:667` | internal (ack/resolve) + tests |
| `acknowledge_alert` | `contract.rs:710` | tests-only |
| `resolve_alert` | `contract.rs:735` | tests-only |
| `unresolved_critical_count` | `contract.rs:753` | tests-only |
| `resolved_count` | `contract.rs:767` | tests-only |
| `alert_write_enabled` | `contract.rs:777` | tests-only |

## Methods

| Name | Line | Used |
|---|---|---|
| `RenameLogEntry::to_json` | `contract.rs:790` | tests-only |
| `NamesHashEntry::to_json` | `contract.rs:812` | tests-only |
| `NamesHistoryEntry::to_json` | `contract.rs:834` | tests-only |

## Private (not exported; listed so the count is not confused)

`human_age` (`contract.rs:82`), `subject_names_job`
(`contract.rs:455`), `find_alert_mut` (`contract.rs:698`).

## Summary

65 public items (plus the module): 7 constants, 17 record/enum
types, 38 functions and 3 methods. **One is unused** (`VERDICTS`); the
rest are used internally or by tests. No production crate calls any
of them today — see `dashboard-callers.md`.
