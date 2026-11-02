# Meta OS Rust rebuild — batch map (B00)

Skeleton laid by Pax (B00). The Python/Node sources in this repo are the
spec: port behavior, do not redesign. Wire contracts stay frozen
(`/api/assess` shape, job kind `trio-assessment` v1, result keys).

## Rules

- **Two compile gates.** Gate 1: Milo's VM (fast loop — every batch
  compiles there first). Gate 2: the boss's Mac (final check). Nothing
  counts as compiled from the sandbox; rustc cannot write output there.
- **Parity rule.** A batch is DONE when it compiles at both gates and
  its ported tests pass. Until then the Python original stays the live
  fallback — never delete or stub over a Python source to make a batch
  look finished.
- **Test assignment.** `os/tests/` files are assigned to the batch that
  owns the module they name; cross-cutting and unmatched tests sit in
  B31 (parity harness).
- **Exclusion-blocked tests — honest caveat.** The cleaned tree excludes
  the `relay_common` module and the muse-relay viewer/bus files. The
  fold measured 959 runnable OS tests in the cleaned tree: 769 pass;
  the rest fail or error only because they import or read the excluded
  relay code. Batches touching those areas port behavior from source
  and mark the affected tests **exclusion-blocked** — never silently
  dropped, never faked green.
- **B07** is integration assist across Rowan's crates: no dedicated
  source files and no crate of its own.
- **Parity reference (stays in place):** `tests/queue-python/test_queue.py`
  is the test bar for B01–B04. It is not moved or ported as a file.

## Summary

| Batch | Owner | Crate | Title | Files |
|---|---|---|---|---|
| B01 | Rowan | crates/queue-core | Queue core (queue service) | 3 |
| B02 | Rowan | crates/queue-store | Queue store (Upstash store + repo layer) | 2 |
| B03 | Rowan | crates/guardrail | Guardrail + Spark transport | 2 |
| B04 | Rowan | crates/agent-runtime | Agent runtime (trio agent) | 1 |
| B05 | Rowan | crates/assess-server | Assess server (Node service) | 5 |
| B06 | Rowan | crates/stack | Stack wiring (run-stack) | 1 |
| B07 | Rowan | — | Integration assist (no dedicated sources) | 0 |
| B08 | Hana | crates/relay | Nuntius relay | 3 |
| B09 | Hana | crates/intel | Intel core & capability registry | 70 |
| B10 | Hana | crates/intel | Briefings & dispatch | 43 |
| B11 | Hana | crates/intel | Intel Spark client & mind images | 8 |
| B12 | Hana | crates/intel | Evals & drills | 138 |
| B13 | Hana | crates/intel | Examples & devpack | 23 |
| B14 | Hana | crates/intel | Trust & launch (remaining intel) | 4 |
| B15 | Hana | crates/dashboard | Dashboard backend contract | 31 |
| B16 | Milo | crates/os-jobs | Jobs service | 6 |
| B17 | Milo | crates/os-memory | Memory service | 3 |
| B18 | Milo | crates/os-identity | Identity & capabilities service | 1 |
| B19 | Milo | crates/os-workspace | Workspace & artifact store | 2 |
| B20 | Milo | crates/os-budget | Budget & resource policy | 13 |
| B21 | Milo | crates/os-supervisor | Supervisor & watchdog | 39 |
| B22 | Milo | crates/os-worker | Worker runtime & drivers | 19 |
| B23 | Milo | crates/os-boot | Boot glue & deployment | 46 |
| B24 | Buffy | crates/os-misc | Bus messaging core | 6 |
| B25 | Buffy | crates/os-misc | Bus messaging extras | 10 |
| B26 | Buffy | crates/os-misc | Bus bridges, digest & admin | 9 |
| B27 | Buffy | crates/os-misc | World packs | 19 |
| B28 | Buffy | crates/os-misc | OS docs, roles & root docs | 16 |
| B29 | Buffy | crates/os-misc | Crew dirs & demo/submission assets | 22 |
| B30 | Buffy | crates/os-misc | Lane plans | 12 |
| B31 | Buffy | crates/parity-tests | Parity test harness | 34 |

Total in-scope source files assigned: 591 (every file under `server/`, `relay/`, `os/`, plus `run-stack.sh`, minus the excluded `relay/viewer.html`).

## Batches — exact source files

### B01 — Queue core (queue service) (owner: Rowan, crate: `crates/queue-core`)

- `server/queue/.gitignore`
- `server/queue/README.md`
- `server/queue/queue_service.py`

### B02 — Queue store (Upstash store + repo layer) (owner: Rowan, crate: `crates/queue-store`)

- `server/queue/trio_repo.py`
- `server/queue/trio_store.py`

### B03 — Guardrail + Spark transport (owner: Rowan, crate: `crates/guardrail`)

- `server/queue/spark_gen.py`
- `server/queue/spark_guardrail.py`

### B04 — Agent runtime (trio agent) (owner: Rowan, crate: `crates/agent-runtime`)

- `server/queue/trio_agent.py`

### B05 — Assess server (Node service) (owner: Rowan, crate: `crates/assess-server`)

- `server/README.md`
- `server/assess.mjs`
- `server/model.mjs`
- `server/queue.mjs`
- `server/server.mjs`

### B06 — Stack wiring (run-stack) (owner: Rowan, crate: `crates/stack`)

- `run-stack.sh`

### B07 — Integration assist (no dedicated sources) (owner: Rowan, no crate)

- No dedicated source files. Integration assist across the
  queue, store, guardrail, agent-runtime, assess-server and stack
  crates: wiring, contract checks, and compile-error triage.

### B08 — Nuntius relay (owner: Hana, crate: `crates/relay`)

- `relay/README.md`
- `relay/relay.mjs`
- `relay/relay.test.mjs`

### B09 — Intel core & capability registry (owner: Hana, crate: `crates/intel`)

- `os/intel.py`
- `os/intel/README.md`
- `os/intel/__init__.py`
- `os/intel/capabilities/buffy.json`
- `os/intel/capabilities/hana.json`
- `os/intel/capabilities/milo.json`
- `os/intel/capabilities/pax.json`
- `os/intel/capabilities/rowan.json`
- `os/intel/capability.py`
- `os/intel/capability_files.py`
- `os/intel/explanations.py`
- `os/intel/gate.py`
- `os/intel/ingest.py`
- `os/intel/integration.py`
- `os/intel/join.py`
- `os/intel/ladder.py`
- `os/intel/store.py`
- `os/tests/test_intel_abrun.py`
- `os/tests/test_intel_attempt_gate.py`
- `os/tests/test_intel_baton_pass.py`
- `os/tests/test_intel_capability.py`
- `os/tests/test_intel_capability_files.py`
- `os/tests/test_intel_cli.py`
- `os/tests/test_intel_cursor.py`
- `os/tests/test_intel_dem014_final_mix.py`
- `os/tests/test_intel_dem018_local.py`
- `os/tests/test_intel_demo_ambient.py`
- `os/tests/test_intel_demo_caption.py`
- `os/tests/test_intel_demo_goal.py`
- `os/tests/test_intel_demo_operator_card.py`
- `os/tests/test_intel_devpack.py`
- `os/tests/test_intel_dispatch.py`
- `os/tests/test_intel_dispatch_announce.py`
- `os/tests/test_intel_dispatch_fallback.py`
- `os/tests/test_intel_dispatch_readme.py`
- `os/tests/test_intel_dispatch_req.py`
- `os/tests/test_intel_dispatch_show.py`
- `os/tests/test_intel_dispatch_templates.py`
- `os/tests/test_intel_drill_collision.py`
- `os/tests/test_intel_drill_dead_dep.py`
- `os/tests/test_intel_drill_demo_catch_time.py`
- `os/tests/test_intel_drill_demo_silent_failure.py`
- `os/tests/test_intel_drill_tournament.py`
- `os/tests/test_intel_e2e1.py`
- `os/tests/test_intel_e2e2.py`
- `os/tests/test_intel_e2e3.py`
- `os/tests/test_intel_explanations.py`
- `os/tests/test_intel_fnd029.py`
- `os/tests/test_intel_git_workflow.py`
- `os/tests/test_intel_integration.py`
- `os/tests/test_intel_load.py`
- `os/tests/test_intel_mind_image.py`
- `os/tests/test_intel_mind_loader.py`
- `os/tests/test_intel_notify.py`
- `os/tests/test_intel_os039_boot_audio.py`
- `os/tests/test_intel_push.py`
- `os/tests/test_intel_redis_down.py`
- `os/tests/test_intel_restart_contract.py`
- `os/tests/test_intel_sam_eval.py`
- `os/tests/test_intel_security_pass.py`
- `os/tests/test_intel_self_repair_ladder.py`
- `os/tests/test_intel_snapshot.py`
- `os/tests/test_intel_soak_review.py`
- `os/tests/test_intel_spoof_dispatch.py`
- `os/tests/test_intel_store.py`
- `os/tests/test_intel_timer_sweep.py`
- `os/tests/test_intel_trust.py`
- `os/tests/test_intel_trust_negative.py`
- `os/tests/test_intel_wake.py`
- `os/tests/test_relay_intel_config.py`

### B10 — Briefings & dispatch (owner: Hana, crate: `crates/intel`)

- `os/intel/alerts.py`
- `os/intel/baton.py`
- `os/intel/brief.py`
- `os/intel/dispatch.py`
- `os/intel/forecast.py`
- `os/intel/notify.py`
- `os/intel/prompts/README.md`
- `os/intel/prompts/brief_boot.md`
- `os/intel/prompts/brief_morning.md`
- `os/intel/prompts/brief_morning_v2.md`
- `os/intel/prompts/brief_ondemand.md`
- `os/intel/prompts/brief_onjoin.md`
- `os/intel/prompts/brief_onjoin_v2.md`
- `os/intel/prompts/dispatch.md`
- `os/intel/prompts/dispatch_v2.md`
- `os/intel/push.py`
- `os/intel/wake.py`
- `os/tests/test_intel_brief.py`
- `os/tests/test_intel_brief_announce.py`
- `os/tests/test_intel_brief_blocked_contacts_caller.py`
- `os/tests/test_intel_brief_boot_environment.py`
- `os/tests/test_intel_brief_cold_start.py`
- `os/tests/test_intel_brief_daily_caller.py`
- `os/tests/test_intel_brief_demo_morning.py`
- `os/tests/test_intel_brief_e2e_score.py`
- `os/tests/test_intel_brief_environment_bus.py`
- `os/tests/test_intel_brief_environment_record.py`
- `os/tests/test_intel_brief_environment_repo.py`
- `os/tests/test_intel_brief_federation_caller.py`
- `os/tests/test_intel_brief_held_decisions_caller.py`
- `os/tests/test_intel_brief_held_sources.py`
- `os/tests/test_intel_brief_onjoin_template.py`
- `os/tests/test_intel_brief_previous_brief_caller.py`
- `os/tests/test_intel_brief_previous_session_caller.py`
- `os/tests/test_intel_brief_priority_caller.py`
- `os/tests/test_intel_brief_priority_contacts.py`
- `os/tests/test_intel_brief_prompt_v2.py`
- `os/tests/test_intel_brief_prompt_version.py`
- `os/tests/test_intel_brief_prompt_wiring.py`
- `os/tests/test_intel_brief_recovery_caller.py`
- `os/tests/test_intel_brief_screenshots.py`
- `os/tests/test_intel_brief_since_last.py`
- `os/tests/test_intel_brief_system_state_caller.py`

### B11 — Intel Spark client & mind images (owner: Hana, crate: `crates/intel`)

- `os/intel/mind_image.py`
- `os/intel/mind_loader.py`
- `os/intel/skills_loader.py`
- `os/intel/spark_agent.py`
- `os/intel/spark_client.py`
- `os/tests/test_intel_spark_agent.py`
- `os/tests/test_intel_spark_client.py`
- `os/tests/test_intel_spark_down.py`

### B12 — Evals & drills (owner: Hana, crate: `crates/intel`)

- `os/intel/abrun.py`
- `os/intel/boot_audio_check.py`
- `os/intel/boot_selfcheck.py`
- `os/intel/dem018_local_check.py`
- `os/intel/drills/__init__.py`
- `os/intel/drills/ab_run.py`
- `os/intel/drills/attempt_gate.py`
- `os/intel/drills/baton_pass.py`
- `os/intel/drills/boot_selfcheck.py`
- `os/intel/drills/boot_status.py`
- `os/intel/drills/capability_refusal.py`
- `os/intel/drills/collision.py`
- `os/intel/drills/dead_dep.py`
- `os/intel/drills/demo_catch_time.py`
- `os/intel/drills/demo_silent_failure.py`
- `os/intel/drills/demo_thresholds_dropin.py`
- `os/intel/drills/journal_watch.py`
- `os/intel/drills/power_cut.py`
- `os/intel/drills/restart_contract.py`
- `os/intel/drills/self_repair_ladder.py`
- `os/intel/drills/soak_review.py`
- `os/intel/drills/timer_sweep.py`
- `os/intel/drills/tournament.py`
- `os/intel/drills/trust_enforcement.py`
- `os/intel/drills/trust_negative.py`
- `os/intel/drills/wake.py`
- `os/intel/e2e1.py`
- `os/intel/e2e2.py`
- `os/intel/e2e3.py`
- `os/intel/evals/README.md`
- `os/intel/evals/ab_run.md`
- `os/intel/evals/attempt_gate.log`
- `os/intel/evals/attempt_gate.md`
- `os/intel/evals/baton_pass.log`
- `os/intel/evals/baton_pass.md`
- `os/intel/evals/boot_audio.md`
- `os/intel/evals/boot_selfcheck.log`
- `os/intel/evals/boot_selfcheck.md`
- `os/intel/evals/boot_status.md`
- `os/intel/evals/brief_rubric.md`
- `os/intel/evals/budget_forecast.md`
- `os/intel/evals/budget_gate.log`
- `os/intel/evals/budget_gate.md`
- `os/intel/evals/capability_refusal.log`
- `os/intel/evals/capability_refusal.md`
- `os/intel/evals/cgroup_limits.log`
- `os/intel/evals/cgroup_limits.md`
- `os/intel/evals/cost.log`
- `os/intel/evals/cost.md`
- `os/intel/evals/dem018_local.md`
- `os/intel/evals/demo_catch_time.log`
- `os/intel/evals/demo_catch_time.md`
- `os/intel/evals/demo_operator_card.md`
- `os/intel/evals/demo_silent_failure.log`
- `os/intel/evals/demo_silent_failure.md`
- `os/intel/evals/demo_thresholds_dropin.log`
- `os/intel/evals/demo_thresholds_dropin.md`
- `os/intel/evals/dispatch_adversarial.md`
- `os/intel/evals/dispatch_golden.md`
- `os/intel/evals/drill_tournament.log`
- `os/intel/evals/drill_tournament.md`
- `os/intel/evals/driver_heartbeat_bridge.log`
- `os/intel/evals/driver_heartbeat_bridge.md`
- `os/intel/evals/driver_stall.log`
- `os/intel/evals/driver_stall.md`
- `os/intel/evals/driver_supervision.log`
- `os/intel/evals/driver_supervision.md`
- `os/intel/evals/e2e1.log`
- `os/intel/evals/e2e2.log`
- `os/intel/evals/e2e3.log`
- `os/intel/evals/e2e_watchdog_surfaces.log`
- `os/intel/evals/final_mix.md`
- `os/intel/evals/fnd029.md`
- `os/intel/evals/int012_git_workflow.md`
- `os/intel/evals/journal_watch.log`
- `os/intel/evals/journal_watch.md`
- `os/intel/evals/load.log`
- `os/intel/evals/load.md`
- `os/intel/evals/log.md`
- `os/intel/evals/power_cut.log`
- `os/intel/evals/power_cut.md`
- `os/intel/evals/redis_down.log`
- `os/intel/evals/redis_down.md`
- `os/intel/evals/restart_contract.log`
- `os/intel/evals/restart_contract.md`
- `os/intel/evals/sam/README.md`
- `os/intel/evals/sam/alerts-firing-desktop.png`
- `os/intel/evals/sam/alerts-firing-phone.png`
- `os/intel/evals/sam/alerts-quiet-desktop.png`
- `os/intel/evals/sam/alerts-quiet-phone.png`
- `os/intel/evals/sam/pairs.json`
- `os/intel/evals/sam_pairs.md`
- `os/intel/evals/security_pass.log`
- `os/intel/evals/security_pass.md`
- `os/intel/evals/self_repair_ladder.log`
- `os/intel/evals/self_repair_ladder.md`
- `os/intel/evals/soak_review.log`
- `os/intel/evals/soak_review.md`
- `os/intel/evals/spark_down.log`
- `os/intel/evals/spark_down.md`
- `os/intel/evals/spoof_dispatch.log`
- `os/intel/evals/spoof_dispatch.md`
- `os/intel/evals/timer_sweep.log`
- `os/intel/evals/timer_sweep.md`
- `os/intel/evals/trust_enforcement.log`
- `os/intel/evals/trust_enforcement.md`
- `os/intel/evals/trust_negative.log`
- `os/intel/evals/trust_negative.md`
- `os/intel/evals/wake.log`
- `os/intel/evals/wake.md`
- `os/intel/evals/watchdog_load.log`
- `os/intel/evals/watchdog_load.md`
- `os/intel/evals/watchdog_tuning.md`
- `os/intel/evals/watchdog_tuning.py`
- `os/intel/evals/watchman_boot.log`
- `os/intel/evals/watchman_boot.md`
- `os/intel/evals/watchman_bridge.md`
- `os/intel/evals/watchman_bridge_tick.md`
- `os/intel/evals/watchman_cycle.log`
- `os/intel/evals/watchman_cycle.md`
- `os/intel/evals/watchman_loop.log`
- `os/intel/evals/watchman_loop.md`
- `os/intel/evals/watchman_runner.log`
- `os/intel/evals/watchman_runner.md`
- `os/intel/evals/watchman_service.md`
- `os/intel/evals/watchman_service_cli.md`
- `os/intel/evals/watchman_service_unit.md`
- `os/intel/evals/watchman_watch.log`
- `os/intel/evals/watchman_watch.md`
- `os/intel/final_mix_check.py`
- `os/intel/load_check.py`
- `os/intel/redis_down_drill.py`
- `os/intel/sam_check.py`
- `os/intel/sam_render.py`
- `os/intel/security_pass.py`
- `os/intel/soak_review.py`
- `os/intel/spark_down_drill.py`
- `os/intel/spoof_dispatch_drill.py`

### B13 — Examples & devpack (owner: Hana, crate: `crates/intel`)

- `os/intel/devpack.py`
- `os/intel/devpack/README.md`
- `os/intel/devpack/alerts.json`
- `os/intel/devpack/brief.json`
- `os/intel/devpack/crew_board.json`
- `os/intel/devpack/plan_preview.json`
- `os/intel/examples/mind-images/pax-default/brief.json`
- `os/intel/examples/mind-images/pax-default/changelog.md`
- `os/intel/examples/mind-images/pax-default/constitution.md`
- `os/intel/examples/mind-images/pax-default/gateway-catalog.json`
- `os/intel/examples/mind-images/pax-default/grants.json`
- `os/intel/examples/mind-images/pax-default/manifest.json`
- `os/intel/examples/mind-images/pax-default/memory/own/NOTE.md`
- `os/intel/examples/mind-images/pax-default/memory/shared/NOTE.md`
- `os/intel/examples/mind-images/pax-default/skills/coordinate/SKILL.md`
- `os/intel/examples/mind-images/pax-default/skills/dispatch/SKILL.md`
- `os/intel/examples/skills/fixture-brief/SKILL.md`
- `os/intel/examples/skills/fixture-brief/template.md`
- `os/intel/examples/skills/fixture-ledger/SKILL.md`
- `os/intel/examples/skills/fixture-ledger/notes.md`
- `os/intel/examples/skills/not-a-skill/notes.md`
- `os/intel/notes/hana-source-map.md`
- `os/intel/notes/milo-reuse-audit.md`

### B14 — Trust & launch (remaining intel) (owner: Hana, crate: `crates/intel`)

- `os/intel/launch_run.py`
- `os/intel/metaos-demo.env`
- `os/intel/timer_sweep.py`
- `os/intel/trust.py`

### B15 — Dashboard backend contract (owner: Hana, crate: `crates/dashboard`)

- `os/docs/DASHBOARD_SMOKE_CHECKLIST.md`
- `os/docs/DASHBOARD_SPEC.md`
- `os/tests/test_crewboard_alert_ribbon.py`
- `os/tests/test_crewboard_attempts.py`
- `os/tests/test_crewboard_files_deps.py`
- `os/tests/test_crewboard_os084_artifacts.py`
- `os/tests/test_crewboard_signing.py`
- `os/tests/test_dashboard_accessibility.py`
- `os/tests/test_dashboard_alert_lifecycle.py`
- `os/tests/test_dashboard_brief_sections.py`
- `os/tests/test_dashboard_bus_index_identity.py`
- `os/tests/test_dashboard_cross_browser.py`
- `os/tests/test_dashboard_deep_links.py`
- `os/tests/test_dashboard_demo_mode.py`
- `os/tests/test_dashboard_deploy_runbook.py`
- `os/tests/test_dashboard_dsh038.py`
- `os/tests/test_dashboard_dsp039.py`
- `os/tests/test_dashboard_error_states.py`
- `os/tests/test_dashboard_help.py`
- `os/tests/test_dashboard_intel_focus.py`
- `os/tests/test_dashboard_os043.py`
- `os/tests/test_dashboard_os084.py`
- `os/tests/test_dashboard_palette.py`
- `os/tests/test_dashboard_performance.py`
- `os/tests/test_dashboard_readonly_token.py`
- `os/tests/test_dashboard_rollback_int031.py`
- `os/tests/test_dashboard_screenshots.py`
- `os/tests/test_dashboard_smoke_checklist.py`
- `os/tests/test_dashboard_str005.py`
- `os/tests/test_dashboard_today_counters.py`
- `os/tests/test_intel_brief_dashboard_consistency.py`

### B16 — Jobs service (owner: Milo, crate: `crates/os-jobs`)

- `os/jobs.py`
- `os/tests/test_claims.py`
- `os/tests/test_intel_brief_environment_jobs.py`
- `os/tests/test_jobs.py`
- `os/tests/test_jobs_req.py`
- `os/tests/test_os_jobs_unit.py`

### B17 — Memory service (owner: Milo, crate: `crates/os-memory`)

- `os/mos/memory.py`
- `os/tests/test_intel_brief_memory_depth_caller.py`
- `os/tests/test_os078_memory.py`

### B18 — Identity & capabilities service (owner: Milo, crate: `crates/os-identity`)

- `os/mos/capabilities.py`

### B19 — Workspace & artifact store (owner: Milo, crate: `crates/os-workspace`)

- `os/mos/artifact_store.py`
- `os/mos/gitops.py`

### B20 — Budget & resource policy (owner: Milo, crate: `crates/os-budget`)

- `os/intel/brief_cost_check.py`
- `os/intel/budgets.py`
- `os/intel/cost_check.py`
- `os/intel/drills/budget_forecast.py`
- `os/intel/drills/budget_gate.py`
- `os/intel/drills/cgroup_limits.py`
- `os/mos/disk_audit.py`
- `os/tests/test_intel_brief_cost.py`
- `os/tests/test_intel_brief_environment_budget.py`
- `os/tests/test_intel_brief_memory_budget_caller.py`
- `os/tests/test_intel_budget_forecast.py`
- `os/tests/test_intel_budget_gate.py`
- `os/tests/test_intel_cost.py`

### B21 — Supervisor & watchdog (owner: Milo, crate: `crates/os-supervisor`)

- `os/intel/drills/kill_worker.py`
- `os/intel/drills/watchman_boot.py`
- `os/intel/drills/watchman_bridge.py`
- `os/intel/drills/watchman_bridge_tick.py`
- `os/intel/drills/watchman_cycle.py`
- `os/intel/drills/watchman_loop.py`
- `os/intel/drills/watchman_runner.py`
- `os/intel/drills/watchman_service.py`
- `os/intel/drills/watchman_service_cli.py`
- `os/intel/drills/watchman_watch.py`
- `os/intel/e2e_watchdog_surfaces.py`
- `os/intel/thresholds.py`
- `os/intel/watchdog.py`
- `os/intel/watchdog_load_check.py`
- `os/intel/watchman_boot.py`
- `os/intel/watchman_bridge.py`
- `os/intel/watchman_cycle.py`
- `os/intel/watchman_loop.py`
- `os/intel/watchman_runner.py`
- `os/intel/watchman_service.py`
- `os/intel/watchman_watch.py`
- `os/mos/overseer.py`
- `os/mos/reconcile.py`
- `os/os/watchman/relay_watchman.py`
- `os/tests/test_intel_e2e_watchdog_surfaces.py`
- `os/tests/test_intel_watchdog.py`
- `os/tests/test_intel_watchdog_load.py`
- `os/tests/test_intel_watchdog_service.py`
- `os/tests/test_intel_watchman_boot.py`
- `os/tests/test_intel_watchman_bridge.py`
- `os/tests/test_intel_watchman_bridge_tick.py`
- `os/tests/test_intel_watchman_cycle.py`
- `os/tests/test_intel_watchman_loop.py`
- `os/tests/test_intel_watchman_runner.py`
- `os/tests/test_intel_watchman_service.py`
- `os/tests/test_intel_watchman_service_cli.py`
- `os/tests/test_intel_watchman_service_unit.py`
- `os/tests/test_intel_watchman_watch.py`
- `os/tests/test_os_watchman.py`

### B22 — Worker runtime & drivers (owner: Milo, crate: `crates/os-worker`)

- `os/intel/drills/driver_heartbeat_bridge.py`
- `os/intel/drills/driver_stall.py`
- `os/intel/drills/driver_supervision.py`
- `os/mos/worker.py`
- `os/os/drivers/CONFORMANCE.md`
- `os/os/drivers/CONTRACT.md`
- `os/os/drivers/muse_driver.py`
- `os/os/drivers/run_driver.py`
- `os/os/drivers/stub_driver.py`
- `os/os/uplink/relay_uplink.py`
- `os/tests/test_intel_dispatch_worker.py`
- `os/tests/test_intel_drill_kill_worker.py`
- `os/tests/test_intel_driver_heartbeat_bridge.py`
- `os/tests/test_intel_driver_stall.py`
- `os/tests/test_intel_driver_supervision.py`
- `os/tests/test_os_driver_contract.py`
- `os/tests/test_os_driver_muse.py`
- `os/tests/test_os_worker_units.py`
- `os/tests/test_os_workers_slice.py`

### B23 — Boot glue & deployment (owner: Milo, crate: `crates/os-boot`)

- `os/mos.py`
- `os/mos/__init__.py`
- `os/mos/cli.py`
- `os/os/BASE.md`
- `os/os/README-FIRSTBOOT.md`
- `os/os/README.md`
- `os/os/bin/metaos-boot-checklist`
- `os/os/bin/metaos-secrets-sweep`
- `os/os/bin/metaos-update`
- `os/os/build-all.sh`
- `os/os/build-image.sh`
- `os/os/build-live.sh`
- `os/os/build-packer.sh`
- `os/os/firstboot/metaos-firstboot`
- `os/os/grub-early.cfg`
- `os/os/live-build/auto/config`
- `os/os/live-build/config/hooks/live/0900-metaos-services.hook.chroot`
- `os/os/live-build/config/package-lists/metaos.list.chroot`
- `os/os/packages.txt`
- `os/os/packer/metaos.pkr.hcl`
- `os/os/preseed.cfg`
- `os/os/services/metaos-firstboot.service`
- `os/os/services/relay-brief.service`
- `os/os/services/relay-bus.service`
- `os/os/services/relay-dashboard.service`
- `os/os/services/relay-driver@.service`
- `os/os/services/relay-drivers.slice`
- `os/os/services/relay-jobs.service`
- `os/os/services/relay-mcp-gateway.service`
- `os/os/services/relay-memory.service`
- `os/os/services/relay-overseer.service`
- `os/os/services/relay-overseer.timer`
- `os/os/services/relay-ready.service`
- `os/os/services/relay-uplink.service`
- `os/os/services/relay-watchdog.service`
- `os/os/services/relay-watchdog.service.d/demo-thresholds.conf`
- `os/os/services/relay-watchman-watch.service`
- `os/os/services/relay-watchman.service`
- `os/os/services/relay-worker@.service`
- `os/os/services/relay-workers.slice`
- `os/os/services/relay.target`
- `os/os/test-boot.sh`
- `os/tests/test_mos_acceptance.py`
- `os/tests/test_mos_capabilities.py`
- `os/tests/test_mos_flow.py`
- `os/tests/test_mos_gitops.py`

### B24 — Bus messaging core (owner: Buffy, crate: `crates/os-misc`)

- `os/poll.py`
- `os/presence.py`
- `os/send.py`
- `os/store.py`
- `os/watch.py`
- `os/watch_nick.py`

### B25 — Bus messaging extras (owner: Buffy, crate: `crates/os-misc`)

- `os/announce.py`
- `os/clipboard.py`
- `os/edits.py`
- `os/forward.py`
- `os/paste.py`
- `os/saved.py`
- `os/tests/test_announce.py`
- `os/tests/test_edits.py`
- `os/tests/test_forward.py`
- `os/tests/test_saved.py`

### B26 — Bus bridges, digest & admin (owner: Buffy, crate: `crates/os-misc`)

- `os/admin.py`
- `os/digest.py`
- `os/export.py`
- `os/health.py`
- `os/tests/test_digest.py`
- `os/tests/test_export.py`
- `os/tests/test_webhook.py`
- `os/timecapsule.py`
- `os/webhook.py`

### B27 — World packs (owner: Buffy, crate: `crates/os-misc`)

- `os/worlds/README.md`
- `os/worlds/dep/PACK.md`
- `os/worlds/dep/pack.json`
- `os/worlds/doe/PACK.md`
- `os/worlds/doe/pack.json`
- `os/worlds/dsny/PACK.md`
- `os/worlds/dsny/pack.json`
- `os/worlds/ems/PACK.md`
- `os/worlds/ems/pack.json`
- `os/worlds/fdny/PACK.md`
- `os/worlds/fdny/pack.json`
- `os/worlds/fdny/runtime/par_clock.py`
- `os/worlds/hospital/PACK.md`
- `os/worlds/hospital/pack.json`
- `os/worlds/mta/PACK.md`
- `os/worlds/mta/pack.json`
- `os/worlds/nypd/PACK.md`
- `os/worlds/nypd/pack.json`
- `os/worlds/validate_pack.py`

### B28 — OS docs, roles & root docs (owner: Buffy, crate: `crates/os-misc`)

- `os/.gitignore`
- `os/INSTANCES.md`
- `os/README.md`
- `os/ROADMAP.md`
- `os/_redirects`
- `os/docs/DEPLOY_RUNBOOK.md`
- `os/docs/DSH-035-CROSS-BROWSER-CHECK.md`
- `os/docs/ROWAN_OS_SCOUT_20261026.md`
- `os/docs/briefs-gallery.md`
- `os/docs/mos-operations.md`
- `os/roles/builder.md`
- `os/roles/documenter.md`
- `os/roles/overseer.md`
- `os/roles/planner.md`
- `os/roles/reviewer.md`
- `os/roles/tester.md`

### B29 — Crew dirs & demo/submission assets (owner: Buffy, crate: `crates/os-misc`)

- `os/crew/README.md`
- `os/crew/buffy/README.md`
- `os/crew/hana/README.md`
- `os/crew/milo/README.md`
- `os/crew/pax/README.md`
- `os/crew/rowan/README.md`
- `os/demo-assets/audio/LICENSES.md`
- `os/demo-assets/audio/TAKE_LOG.md`
- `os/demo-assets/audio/TIMING.md`
- `os/demo-assets/audio/dem014-final-mix.mp3`
- `os/demo-assets/audio/dem015-caption-watchdog-moment.mp3`
- `os/demo-assets/audio/dem017-ambient-bed.mp3`
- `os/demo-assets/audio/wdg030-watchdog-segment-take1.mp3`
- `os/demo-assets/audio/wdg030-watchdog-segment-take2.mp3`
- `os/demo-assets/audio/wdg031-opening-framing-take1.mp3`
- `os/demo-assets/audio/wdg031-opening-framing-take2.mp3`
- `os/demo-assets/audio/wdg033-fallback-full-demo.mp3`
- `os/demo-assets/audio/wdg033-fallback-script.txt`
- `os/demo-assets/audio/wdg034-alert-sting.mp3`
- `os/demo-assets/audio/wdg034-success-sting.mp3`
- `os/submission-assets/audio/os039-boot-sting.mp3`
- `os/submission-assets/audio/os039-boot-voice-line.mp3`

### B30 — Lane plans (owner: Buffy, crate: `crates/os-misc`)

- `os/plan/DEMO.md`
- `os/plan/LAYER_PLAN.md`
- `os/plan/MASTER_PLAN.md`
- `os/plan/META_OS.md`
- `os/plan/META_WORLD.md`
- `os/plan/SCHEDULE.md`
- `os/plan/lanes/BUFFY.md`
- `os/plan/lanes/DALE.md`
- `os/plan/lanes/HANA.md`
- `os/plan/lanes/MILO.md`
- `os/plan/lanes/PAX.md`
- `os/plan/lanes/ROWAN.md`

### B31 — Parity test harness (owner: Buffy, crate: `crates/parity-tests`)

- `os/mos/acceptance.py`
- `os/tests/fake_redis.py`
- `os/tests/helpers.py`
- `os/tests/test_boss_trigger.py`
- `os/tests/test_bus_rename.py`
- `os/tests/test_bustools_parity.py`
- `os/tests/test_clip.py`
- `os/tests/test_fdny_par_clock.py`
- `os/tests/test_os021_update.py`
- `os/tests/test_os058_gateway_unit.py`
- `os/tests/test_os059_gateway_bake.py`
- `os/tests/test_os065_skills_loader.py`
- `os/tests/test_os083_artifact_store.py`
- `os/tests/test_os094_job_artifacts.py`
- `os/tests/test_os102_launch_run.py`
- `os/tests/test_os128_disk_audit.py`
- `os/tests/test_os_base.py`
- `os/tests/test_os_boot_harness.py`
- `os/tests/test_os_boot_selfcheck.py`
- `os/tests/test_os_boot_status.py`
- `os/tests/test_os_bus_unit.py`
- `os/tests/test_os_journal_watch.py`
- `os/tests/test_os_livebuild.py`
- `os/tests/test_os_manifest.py`
- `os/tests/test_os_overseer_unit.py`
- `os/tests/test_os_packer.py`
- `os/tests/test_os_power_cut.py`
- `os/tests/test_os_stackbake.py`
- `os/tests/test_os_target_unit.py`
- `os/tests/test_os_tree.py`
- `os/tests/test_os_uplink.py`
- `os/tests/test_pomodoro.py`
- `os/tests/test_status.py`
- `os/tests/test_worlds_pack.py`

## Excluded — not Rust targets (no batch)

- `relay/viewer.html` — Nuntius web viewer (web UI; served as a static
  asset, not ported).
- `native/` — the Swift MetaTrio app (25 files). Not a Rust target.
- Web UI: `index.html`, `logo-studio.html`, `styles.css`, `UI_README.md`, `js/` (34 files), `design/` (1 file).
- `tests/` (229 files) — Trio/server JS test suites stay with
  their surfaces; the one Python file is the B01–B04 parity reference above.
- `eval/` (21 files), `verify/` (4 files), `test-footage/` (18 files) — Trio eval/verification
  assets, not OS Rust targets.
- Root docs and config: `.gitignore`, `BRIEF.md`, `FIRST_RESPONSE.md`, `MASTER_DIRECTIVE_V2.md`, `MEDICUS_PIVOT_SPEC.md`, `README.md`, `RUNBOOK.md`, `package.json`.
- Absent from the tree by design (excluded at fold time, assigned to no
  batch): the `relay_common` module and the muse-relay viewer/bus files
  (`bus.html`, `crew-board.html` and related relay assets). Behavior that
  touched them is ported from the in-tree callers, with affected tests
  marked exclusion-blocked per the caveat above.
