# `crates/intel` — public surface inventory (B178)

Every exported name in the crate, one row each, with the place it is
used today. "Used" is one of:

- **parity** — imported by a file in `crates/intel/tests/`.
- **unit** — referenced only from its own `#[cfg(test)]` module.
- **drill** — called by another module in `b12a_drills`.
- **drill+parity** — both of the above.
- **none found** — no reference outside its definition in this tree.

No production Rust code uses any of it (`intel-callers.md`). Constants
and types are listed with their functions so the inventory is complete.

## `b09_core`

| Name | Where | Used |
|---|---|---|
| `capability::normalize_path` | `capability.rs:37` | parity |
| `capability::check_action` | `capability.rs:89` | parity |
| `capability::refusal_alert` | `capability.rs:170` | parity |
| `capability::refusal_note` | `capability.rs:185` | parity |
| `capability::capability_tick` | `capability.rs:211` | parity |
| `capability::brief_lines` | `capability.rs:234` | parity |
| `capability::Grant` (type) | `capability.rs` | parity |
| `capability::Decision` (type) | `capability.rs` | parity |
| `capability::RefusalAlert` (type) | `capability.rs` | parity |
| `cli::needs_confirm_large` | `cli.rs:42` | parity |
| `cli::format_dispatch_announcement` | `cli.rs:47` | parity |
| `cli::approval_granted` | `cli.rs:52` | parity |
| `explanations::render` | `explanations.rs:63` | parity |
| `explanations::polish_explanation` | `explanations.rs:77` | parity |
| `gate::as_int` | `gate.rs:30` | parity |
| `gate::attempts_left` | `gate.rs:50` | parity |
| `gate::budget_exhausted` | `gate.rs:59` | parity |
| `gate::is_dale_call` | `gate.rs:63` | parity |
| `gate::question_for` | `gate.rs:69` | parity |
| `gate::gate_tick` | `gate.rs:94` | parity |
| `gate::gate_brief_lines` | `gate.rs:129` | parity |
| `ingest::PAGE` | `ingest.rs:7` | parity |
| `ingest::store_messages` | `ingest.rs:24` | parity |
| `ingest::messages_from_cursor` | `ingest.rs:40` | parity |
| `ingest::snapshot` | `ingest.rs:51` | parity |
| `ingest::Message` (type) | `ingest.rs:9` | parity |
| `ingest::SnapshotView` (type) | `ingest.rs:16` | parity |
| `init::PACKAGE` | `init.rs:6` | unit |
| `init::SUBTREE` | `init.rs:7` | **none found** |
| `integration::env_for` | `integration.rs:9` | parity |
| `integration::export_lines` | `integration.rs:16` | parity |
| `integration::apply_env` | `integration.rs:22` | parity |
| `integration::room_bus_key` | `integration.rs:28` | parity |
| `join::validate_machine` | `join.rs:16` | parity |
| `join::validate_room_address` | `join.rs:26` | parity |
| `join::validate_room_key` | `join.rs:33` | parity |
| `join::validate_trusted_kids` | `join.rs:40` | parity |
| `join::crew_from_grants` | `join.rs:49` | parity |
| `join::announcement_text` | `join.rs:56` | parity |
| `join::build_announcement` | `join.rs:60` | parity |
| `join::JoinError` (type) | `join.rs` | parity |
| `capability_files::validate_grant_fields` | `capability_files.rs:57` | parity |
| `capability_files::load_grant` | `capability_files.rs:96` | parity |
| `capability_files::load_grant_for` | `capability_files.rs:234` | parity |
| `capability_files::load_crew_grants` | `capability_files.rs:244` | parity |
| `capability_files::Grant` (type) | `capability_files.rs` | parity |
| `ladder::classify` | `ladder.rs:44` | parity |
| `ladder::baton_for` | `ladder.rs:58` | parity |
| `ladder::ladder_action` | `ladder.rs:78` | parity |
| `ladder::ladder_tick` | `ladder.rs:88` | parity |
| `ladder::ladder_brief_lines` | `ladder.rs:92` | parity |
| `ladder::Snapshot`, `Stall`, `Baton`, `LadderAction` (types) | `ladder.rs` | parity |
| `store::key_prefix` | `store.rs:14` | parity |
| `store::brief_key` | `store.rs:18` | parity |
| `store::alert_key` | `store.rs:21` | parity |
| `store::alert_index_key` | `store.rs:24` | parity |
| `store::notify_key` | `store.rs:27` | parity |
| `store::notify_index_key` | `store.rs:30` | parity |
| `store::dispatch_key` | `store.rs:33` | parity |
| `store::validate_alert` | `store.rs:53` | parity |
| `store::alert_status` | `store.rs:69` | parity |
| `store::AlertRecord` (type) | `store.rs:36` | parity |
| `store::Store` (type) | `store.rs:75` | parity |
| `Store::put_brief` / `get_brief` | `store.rs:80-86` | parity |
| `Store::write_alert` | `store.rs:88` | parity |
| `Store::get_alert` / `query_alerts` | `store.rs:112-120` | parity |
| `Store::acknowledge_alert` / `resolve_alert` | `store.rs:121-137` | parity |
| `Store::auto_resolve_cleared` | `store.rs:139` | parity |
| `Store::record_spend` / `spend_total` | `store.rs:150-166` | parity |

## `b10_brief`

| Name | Where | Used |
|---|---|---|
| `alerts::acknowledge_alert` | `alerts.rs:10` | parity |
| `alerts::resolve_alert` | `alerts.rs:14` | parity |
| `alerts::auto_resolve_cleared` | `alerts.rs:18` | parity |
| `alerts::Store`, `alert_status` (re-exports) | `alerts.rs:6` | parity |
| `baton::remaining_files` | `baton.rs:17` | parity |
| `baton::remaining_steps` | `baton.rs:21` | parity |
| `baton::acceptance_checks` | `baton.rs:25` | parity |
| `baton::compose_baton` | `baton.rs:29` | parity |
| `baton::baton_brief_lines` | `baton.rs:41` | parity |
| `baton::BatonSpec` (type) | `baton.rs` | parity |
| `brief::brief_index_key` | `brief.rs:19` | parity |
| `brief::parse_since` | `brief.rs:24` | parity |
| `brief::validate_brief_record` | `brief.rs:47` | parity |
| `brief::format_brief_announcement` | `brief.rs:65` | parity |
| `brief::brief_failure_line` | `brief.rs:69` | parity |
| `brief::brief_budget` | `brief.rs:81` | parity |
| `brief::failure_copy_for_kind` | `brief.rs:94` | parity |
| `brief::trim_to_budget` | `brief.rs:111` | parity |
| `brief::brief_prompt_path` | `brief.rs:160` | parity |
| `brief::load_brief_prompt` | `brief.rs:183` | parity |
| `brief::cap_snapshot_window` | `brief.rs:195` | parity |
| `brief::redact_secrets` | `brief.rs:203` | parity |
| `brief::brief_age_seconds` | `brief.rs:218` | parity |
| `brief::brief_exceeds_budget` | `brief.rs:222` | parity |
| `brief::previous_session_digest` | `brief.rs:239` | parity |
| `brief::system_state_lines` | `brief.rs:292` | parity |
| `brief::recovery_line` | `brief.rs:392` | parity |
| `brief::source_pointer_lines` | `brief.rs:493` | parity |
| `brief::compose_brief` | `brief.rs:505` | parity |
| `brief::BriefRecord` (type) | `brief.rs` | parity |
| `dispatch::parse_plan` | `dispatch.rs:39` | parity |
| `dispatch::check_file_overlap` | `dispatch.rs:57` | parity |
| `dispatch::check_dep_graph` | `dispatch.rs:76` | parity |
| `dispatch::clamp_attempt_budgets` | `dispatch.rs:121` | parity |
| `dispatch::check_no_secrets` | `dispatch.rs:132` | parity |
| `dispatch::Plan`, `PlanJob`, `PlanError` (types) | `dispatch.rs` | parity |
| `forecast::usable_number` | `forecast.rs:7` | parity |
| `forecast::project_end_of_day` | `forecast.rs:15` | parity |
| `forecast::confidence_for` | `forecast.rs:19` | parity |
| `forecast::forecast_entry` | `forecast.rs:27` | parity |
| `forecast::preempt_decision` | `forecast.rs:31` | parity |
| `notify::render_line` | `notify.rs:15` | parity |
| `notify::Notification` (type) | `notify.rs` | parity |
| `push::build_done_push` | `push.rs:58` | parity |
| `push::build_blocked_push` | `push.rs:75` | parity |
| `push::build_push` | `push.rs:94` | parity |
| `push::validate_push` | `push.rs:102` | parity |
| `push::Push`, `JobView`, `Verification` (types) | `push.rs` | parity |
| `sections::extract_decisions` | `sections.rs:106` | parity |
| `sections::extract_owners` | `sections.rs:144` | parity |
| `sections::extract_blocked` | `sections.rs:173` | parity |
| `sections::extract_watch_items` | `sections.rs:191` | parity |
| `sections::derive_sections` | `sections.rs:222` | parity |
| `sections::Decision`, `Owner`, `BlockedJob`, `WatchItem`, `Sections`, `Snapshot` | `sections.rs` | parity |
| `wake::is_sleeping_muse` | `wake.rs:7` | parity |
| `wake::should_wake` | `wake.rs:11` | parity |
| `wake::dedupe_key` | `wake.rs:15` | parity |
| `wake::compose_bundle` | `wake.rs:19` | parity |
| `window::message_parts` | `window.rs:26` | parity |
| `window::window_line` | `window.rs:95` | parity |
| `window::RawMessage`, `SourceWindow`, `WindowHours`, `WindowInput` | `window.rs` | parity |

## `b11_spark`

| Name | Where | Used |
|---|---|---|
| `mind_image::parse_bundle` | `mind_image.rs:32` | parity |
| `mind_image::resolve_bundle` | `mind_image.rs:76` | parity |
| `mind_image::validate_bundle` | `mind_image.rs:91` | parity |
| `mind_image::bundle_summary` | `mind_image.rs:103` | parity |
| `mind_image::Bundle`, `BundleError` (types) | `mind_image.rs` | parity |
| `mind_loader::hash_tree` | `mind_loader.rs:23` | parity |
| `mind_loader::assemble_launch` | `mind_loader.rs:36` | parity |
| `mind_loader::verify_launch` | `mind_loader.rs:52` | parity |
| `mind_loader::launch_summary` | `mind_loader.rs:59` | parity |
| `mind_loader::Launch`, `LaunchError` (types) | `mind_loader.rs` | parity |
| `skills_loader::resolve_skill` | `skills_loader.rs:20` | parity |
| `skills_loader::list_skills` | `skills_loader.rs:31` | parity |
| `skills_loader::mount_skill_dirs` | `skills_loader.rs:45` | parity |
| `skills_loader::SkillsLoaderError` (type) | `skills_loader.rs` | parity |
| `spark_agent::unconfigured_generate` | `spark_agent.rs:23` | parity |
| `spark_agent::parse_spark_spec` | `spark_agent.rs:27` | parity |
| `spark_agent::result_key_for` | `spark_agent.rs:57` | parity |
| `spark_agent::result_body_for` | `spark_agent.rs:61` | parity |
| `spark_agent::AgentError` (type) | `spark_agent.rs` | parity |
| `spark_client::result_key_for` | `spark_client.rs:81` | parity |
| `spark_client::result_body_for` | `spark_client.rs:86` | parity |
| `spark_client::complete` | `spark_client.rs:129` | parity |
| `spark_client::SparkError`, `TransportKind`, `CompletionRequest`, `Completion` | `spark_client.rs` | parity |
| `spark_client::Transport` (trait) | `spark_client.rs:72` | parity |
| `spark_client::StubTransport` | `spark_client.rs:147` | parity |

## `b12a_drills`

The 21 drill modules each expose their own `run`-shaped entry and
fixtures. One row per module; names are the module's exported
functions.

| Module | Exports | Used |
|---|---|---|
| `abrun` | `attribute_stall`, `run_comparison`, `measurement_records`, `revision_note` | drill+parity |
| `audiocheck` | `CheckList::check`, `CheckList::print`, `py_bytes_repr`, `read_head3`, `probe_duration`, `volumes`, `max_volume`, `decodes_clean`, `stderr_head` | drill |
| `boot_audio_check` | `execute` | drill |
| `boot_selfcheck` | `expected`, `seeded_fixture`, `run_self_check`, `run_self_check_with` | drill+parity |
| `dem018_local_check` | `execute` | drill |
| `deps` | `Thresholds::locked`, `from_env_map`, `from_env`, `Detector::name`, `default_detectors`; traits `Watchdog`, `TimerSweep`, `JobsSign`, `Trust`, `Wake`, `Ladder`, `SparkClient`, `BriefSurface`, `DispatchSurface`, `AlertRecords`, `BootStatus`, `Capability`, `Gate`, `Push`, `Baton` | drill+parity |
| `drills` | `PACKAGE`, `DrillOutcome` (type) | drill |
| `drills::ab_run` | `bare_image`, `mind_image`, `jobs`, `jobs_value`, `runs`, `images`, `run` | drill |
| `drills::attempt_gate` | `job`, `run` | drill |
| `drills::baton_pass` | `killed_job`, `run` | drill |
| `drills::boot_selfcheck` | `run_drill` | drill |
| `drills::boot_status` | `units`, `workers`, `run_drill` | drill |
| `drills::capability_refusal` | `grants`, `run` | drill |
| `drills::collision` | `CollisionDriver::new/claim/progress`, `run_drill`, `main_lines`, `report` | drill |
| `drills::dead_dep` | `run_drill`, `main_lines`, `report` | drill |
| `drills::demo_catch_time` | `load_profile`, `profile_env`, `check_profile`, `run_rehearsal`, `run_measurement`, `main_lines`, `report` | drill |
| `drills::demo_silent_failure` | `run_drill`, `main_lines`, `report` | drill |
| `drills::demo_thresholds_dropin` | `expected_thresholds`, `parse_env_file`, `watchdog_vars`, `run` | drill+parity |
| `drills::journal_watch` | `fixture`, `run` | drill |
| `drills::power_cut` | `run_drill` | drill |
| `drills::restart_contract` | `snapshot`, `run` | drill |
| `drills::self_repair_ladder` | `base_snapshot`, `job`, `run` | drill |
| `drills::soak_review` | `clean_journal`, `run` | drill+parity |
| `drills::timer_sweep` | `fixture_jobs`, `run` | drill |
| `drills::tournament` | `run_tournament` | drill |
| `drills::trust_enforcement` | `trusted_secret`, `untrusted_secret`, `trust_config`, `keyring`, `base_job`, `sign`, `trusted_job`, `run` | drill |
| `drills::trust_negative` | `trusted_secret`, `outsider_secret`, `trust_config`, `keyring`, `control_job`, `hostile_post`, `spoofed_repost`, `signed_spoof`, `drill_source_is_clean`, `run` | drill |
| `drills::wake` | `WakeDriver::new/start`, `hana_agent`, `rowan_agent`, `job`, `module_imports_banned`, `run` | drill |
| `e2e1` | `brief_budget`, `job_list_json`, `stage`, `transcript`, `plan_json`, `run_loop` | drill+parity |
| `e2e2` | `run_loop` | drill |
| `e2e3` | `section_lines`, `run_loop` | drill |
| `fixtures` | `Agent::new/claim/heartbeat/progress/kill`, `sweep_expired_leases` | drill |
| `final_mix_check` | `execute` | drill |
| `load_check` | `render_load_md`, `run_check` | drill |
| `mod` | `PhaseResult::{pass,fail}`, `DrillReport::{new,ok,pass_line}` | drill+parity |
| `redis_down_drill` | `snapshot_fixture`, `run_drill` | drill |
| `sam_check` | `execute` | drill+parity |
| `sam_render` | `render`, `default_outdir` | drill |
| `security_pass` | `SecretPattern::github_token/github_fine_grained/api_key/aws_access_key_id/bearer_token/private_key/credential_assignment`, `scan_root`, `execute` | drill+parity |
| `sha256` | `sha256_hex`, `sha256` | drill+parity |
| `soak_review` | `review_journal`, `soak_brief_lines` | drill+parity |
| `spark_down_drill` | `snapshot_fixture`, `run_drill` | drill |
| `spoof_dispatch_drill` | `fresh_keyring_line`, `run_drill` | drill |
| `value` | `Value::{obj,s,is_dict,is_list,get,contains_key,set,remove,as_map,as_list,as_text,as_str,is_str,as_number,as_int,is_bool,as_bool,is_null,truthy,py_str,py_repr}`, `py_float_str`, `py_repr_str`, `parse_json`, `to_json`, `to_json_pretty`, `sorted_map` | drill+parity |
| `watchdog_tuning` | `cases`, `execute` | drill+parity |

## `b13_devpack`

| Name | Where | Used |
|---|---|---|
| `PACK_FILES` | `mod.rs:18` | parity (fixture presence) |
| `deep_copy_json` | `mod.rs:26` | **none found** |
| `brief_entry` | `mod.rs:51` | parity |
| `plan_preview` | `mod.rs:94` | parity |
| `alerts_feed` | `mod.rs:118` | parity |
| `crew_board` | `mod.rs:131` | parity |
| `Json` (type) | `mod.rs:33` | parity |
| `DevpackError` | `mod.rs:44` | parity |
| `PreviewJob`, `PreviewPlan`, `PlanPreview` | `mod.rs:60-88` | parity |
| `AlertRow`, `CrewBoard` | `mod.rs:112-128` | parity |

## `b14_trust`

| Name | Where | Used |
|---|---|---|
| `trust::recompute_sig` | `trust.rs:51` | parity |
| `trust::verify_signature` | `trust.rs:69` | parity |
| `trust::claim_decision` | `trust.rs:90` | parity |
| `trust::trust_tick` | `trust.rs:137` | parity |
| `trust::refusal_note` | `trust.rs:173` | parity |
| `trust::trust_brief_lines` | `trust.rs:180` | parity |
| `trust::trust_events` | `trust.rs:192` | parity |
| `trust::Decision`, `JobInput`, `TrustList`, `TrustRecord`, `TrustEvent` | `trust.rs` | parity |
| `timer_sweep::default_interval_seconds` | `timer_sweep.rs:26` | parity |
| `timer_sweep::sweep_cycle` | `timer_sweep.rs:32` | parity |
| `timer_sweep::sweep_brief_lines` | `timer_sweep.rs:82` | parity |
| `timer_sweep::SweepTick` | `timer_sweep.rs` | parity |
| `launch_run::check_preconditions` | `launch_run.rs:40` | parity |
| `launch_run::run_from_launch` | `launch_run.rs:59` | parity |
| `launch_run::child_env` | `launch_run.rs:85` | parity |
| `launch_run::LaunchRunError`, `VerifyReport`, `RunOutput`, `Verifier` | `launch_run.rs` | parity |

## Unused names worth naming

- `b09_core::init::SUBTREE` — declared, never read.
- `b13_devpack::deep_copy_json` — declared, never called; the shapers
  clone directly.
- `b14_trust::launch_run::child_env` is used only by its own test; no
  spawn site calls it in this crate.
- `spark_client::StubTransport` is a test double: correct to keep, but
  it must never be wired as a production transport.

## What "used" does not mean here

`parity` means a test imports the name. It does not mean production
uses it. Nothing outside `crates/intel/tests/` imports the crate, so
every row above is either test-facing or drill-facing today.
