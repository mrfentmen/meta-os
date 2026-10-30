//! B15 parity — backend-contract checks (one per portable case).
//!
//! Exclusion-blocked (need the fold-excluded viewer `bus.html` /
//! `crew-board.html` / `index.html`, live Node drivers, or real
//! browsers — marked here, never faked green):
//! test_crewboard_alert_ribbon, test_crewboard_attempts,
//! test_crewboard_files_deps, test_crewboard_os084_artifacts,
//! test_crewboard_signing (also needs B26 `admin.py`),
//! test_dashboard_accessibility, test_dashboard_alert_lifecycle,
//! test_dashboard_brief_sections, test_dashboard_bus_index_identity,
//! test_dashboard_cross_browser, test_dashboard_deep_links,
//! test_dashboard_demo_mode, test_dashboard_deploy_runbook,
//! test_dashboard_dsh038, test_dashboard_dsp039,
//! test_dashboard_error_states, test_dashboard_help,
//! test_dashboard_intel_focus, test_dashboard_os043,
//! test_dashboard_os084, test_dashboard_palette,
//! test_dashboard_performance, test_dashboard_readonly_token,
//! test_dashboard_screenshots, test_dashboard_smoke_checklist,
//! test_dashboard_str005, test_dashboard_today_counters,
//! test_intel_brief_dashboard_consistency.
//! Directly ported (docs/backend-only):
//! test_dashboard_rollback_int031.

use dashboard::contract::*;

#[test] fn test_dashboard_rollback_int031_exact_steps() {
    let runbook = "Deployments / All deployments / Rollback to this deployment \
        for muse-relay-live. Only successfully built deployments. \
        Preview deployments are **not** valid rollback targets. \
        See https://developers.cloudflare.com/pages/configuration/rollbacks/ \
        Previous production deployment id: not recorded in any deploy log.";
    assert!(rollback_runbook_ok(runbook).is_ok());
}

#[test] fn test_dashboard_rollback_int031_rejects_invented_id() {
    // A runbook missing the unrecorded-id admission fails, even if steps pass.
    let runbook = "Deployments / All deployments / Rollback to this deployment \
        for muse-relay-live. Only successfully built deployments. \
        Preview deployments are **not** valid. \
        https://developers.cloudflare.com/pages/configuration/rollbacks/";
    assert!(rollback_runbook_ok(runbook).is_err());
}

#[test] fn test_dashboard_brief_payload_contract_brf042() {
    let p = BriefPayload {
        id: "brief:build-relay-intel:1793101200".into(),
        room: "build-relay-intel".into(),
        kind: "morning".into(),
        generated_at: 1793101200,
        age_seconds: 900,
        template: false,
    };
    assert!(validate_brief_payload(&p).is_ok());
    assert!(template_marker(true) == Some("TEMPLATE"));
    assert!(template_marker(false).is_none());
}

#[test] fn test_dashboard_stale_labels_brf043() {
    assert!(!is_stale(900)); // fresh: "15 min ago", no regenerate label
    assert!(stale_label(12600).is_some()); // stale: regenerate label
}

#[test] fn test_dashboard_dsh038_request_only() {
    assert!(dispatch_approve_is_request_only());
    assert!(!dispatch_may_auto_post());
    assert_eq!(brief_me_now_enabled(), (false, "posting is off for this build"));
}

#[test] fn test_dashboard_alert_feed_dsh013() {
    let cards = vec![
        AlertCard { id: "b".into(), created_at: 1, resolved: false },
        AlertCard { id: "a".into(), created_at: 2, resolved: false },
        AlertCard { id: "r".into(), created_at: 3, resolved: true },
    ];
    let feed = alerts_feed(cards);
    assert_eq!(feed[0].id, "r"); // newest first regardless of status
    assert_eq!(addressable_cards(&feed).len(), 2); // resolved not addressable
}

#[test] fn test_dashboard_spec_docs_carried() {
    assert!(include_str!("../fixtures/DASHBOARD_SPEC.md").contains("BRF-042"));
    assert!(include_str!("../fixtures/DASHBOARD_SMOKE_CHECKLIST.md").len() > 0);
}
