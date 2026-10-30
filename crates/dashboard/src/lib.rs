//! Crate `dashboard` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B15 — Dashboard backend contract. Owner: Hana.
//! Source files this batch ports:
//! - `os/docs/DASHBOARD_SMOKE_CHECKLIST.md`
//! - `os/docs/DASHBOARD_SPEC.md`
//! - `os/tests/test_crewboard_alert_ribbon.py`
//! - `os/tests/test_crewboard_attempts.py`
//! - `os/tests/test_crewboard_files_deps.py`
//! - `os/tests/test_crewboard_os084_artifacts.py`
//! - `os/tests/test_crewboard_signing.py`
//! - `os/tests/test_dashboard_accessibility.py`
//! - `os/tests/test_dashboard_alert_lifecycle.py`
//! - `os/tests/test_dashboard_brief_sections.py`
//! - `os/tests/test_dashboard_bus_index_identity.py`
//! - `os/tests/test_dashboard_cross_browser.py`
//! - `os/tests/test_dashboard_deep_links.py`
//! - `os/tests/test_dashboard_demo_mode.py`
//! - `os/tests/test_dashboard_deploy_runbook.py`
//! - `os/tests/test_dashboard_dsh038.py`
//! - `os/tests/test_dashboard_dsp039.py`
//! - `os/tests/test_dashboard_error_states.py`
//! - `os/tests/test_dashboard_help.py`
//! - `os/tests/test_dashboard_intel_focus.py`
//! - `os/tests/test_dashboard_os043.py`
//! - `os/tests/test_dashboard_os084.py`
//! - `os/tests/test_dashboard_palette.py`
//! - `os/tests/test_dashboard_performance.py`
//! - `os/tests/test_dashboard_readonly_token.py`
//! - `os/tests/test_dashboard_rollback_int031.py`
//! - `os/tests/test_dashboard_screenshots.py`
//! - `os/tests/test_dashboard_smoke_checklist.py`
//! - `os/tests/test_dashboard_str005.py`
//! - `os/tests/test_dashboard_today_counters.py`
//! - `os/tests/test_intel_brief_dashboard_consistency.py`
//!
//! The backend contract lives in [`contract`]: brief payloads (BRF-042),
//! staleness labels (BRF-043), visual-check verdicts (STR-004), the alerts
//! feed (DSH-013), deep links (DSH-022), demo mode (DSH-028), today
//! counters (DSH-032), error/empty states (DSH-021), the readonly-token
//! posture (GOV-002), OS-043 / OS-084 surface, and the INT-031 rollback
//! runbook pins. The spec docs themselves are carried byte-identical under
//! `crates/dashboard/fixtures/` and checked by the parity tests.
//!
//! §7 crew-board rules (DSH-023 files/deps, DSH-024 attempts badge,
//! DSH-025 alert ribbon, OS-084 artifact links) and the keyless
//! signing entry builders live in [`contract`] too; the card/detail
//! HTML rendering of those rules stays exclusion-blocked with the
//! fold-excluded viewer.
//!
//! Deliberately absent: the web viewer. It was fold-excluded from the
//! cleaned tree and is not a Rust target, so viewer/Node/browser-dependent
//! parity cases are recorded exclusion-blocked in
//! `crates/dashboard/tests/b15_parity.rs`, never faked green. See
//! `batches/B15.md` for the compile gates and the parity rule.

/// The dashboard backend contract: brief payloads, staleness, alerts
/// feed and lifecycle, deep links, demo mode, today counters, error
/// states, the readonly-token posture, rollback pins, and the §7
/// crew-board rules. See [`contract`] for the section refs.
pub mod contract;
