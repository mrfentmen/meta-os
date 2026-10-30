//! B15 parity — backend-contract checks (one per portable case).
//!
//! Exclusion-blocked (need the fold-excluded viewer `bus.html` /
//! `crew-board.html` / `index.html`, live Node drivers, real
//! browsers, or the missing submission-assets — marked here, never
//! faked green):
//! test_crewboard_alert_ribbon, test_crewboard_attempts,
//! test_crewboard_files_deps, test_crewboard_os084_artifacts,
//! test_crewboard_signing (also needs B26 `admin.py`),
//! test_dashboard_alert_lifecycle,
//! test_dashboard_bus_index_identity,
//! test_dashboard_palette, test_dashboard_screenshots,
//! test_intel_brief_dashboard_consistency.
//! Split — spec-note halves ported in tests/b15_spec_notes.rs, the
//! viewer/Node halves below stay exclusion-blocked:
//! test_dashboard_brief_sections (viewer half),
//! test_dashboard_cross_browser — FULLY ported (all 3 cases are
//! log cases, carried as fixtures/DSH-035-CROSS-BROWSER-CHECK.md),
//! test_dashboard_deep_links, test_dashboard_demo_mode,
//! test_dashboard_dsh038 — FULLY ported on the spec side (all 5
//! spec cases; the 5 viewer cases stay blocked),
//! test_dashboard_dsp039, test_dashboard_error_states,
//! test_dashboard_help, test_dashboard_intel_focus,
//! test_dashboard_os043, test_dashboard_os084,
//! test_dashboard_performance, test_dashboard_readonly_token,
//! test_dashboard_str005, test_dashboard_today_counters.
//! Split (T238): test_dashboard_accessibility — 2 cases ported below
//! against the carried spec fixture + the DSH-018 palette values
//! (contrast math, spec contrast notes); the other 4 cases
//! (bus/index identity, intel button labels, severity icon pairing,
//! crew-state text) read the fold-excluded bus.html and stay
//! exclusion-blocked.
//! Split (T242): test_dashboard_smoke_checklist — 5 cases ported below
//! against the carried checklist/spec fixtures (structure, pass
//! criteria, deploy gates, run procedure, spec mention); the other 5
//! viewer cases (bus/index identity, panel ids, demo/deep-link
//! markers, mobile CSS, intel-module timers) stay exclusion-blocked:
//! they read the fold-excluded bus.html / index.html.
//! Directly ported (docs/backend-only):
//! test_dashboard_rollback_int031, test_dashboard_deploy_runbook
//! (runbook carried byte-identical under fixtures/).

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

// DOC-018 deploy runbook, ported from
// os/tests/test_dashboard_deploy_runbook.py (fixture carried
// byte-identical; sha256 3f339c3b…96a17 at carry time).
#[test] fn test_dashboard_deploy_runbook_sections_and_gates() {
    let text = include_str!("../fixtures/DEPLOY_RUNBOOK.md");
    assert!(!text.is_empty());
    for section in ["Build marker", "Deploy", "Verify", "Rollback"] {
        assert!(text.contains(section), "missing section: {section}");
    }
    assert!(text.contains("https://muse-relay-live.pages.dev"));
    assert!(text.contains("muse-relay-live"));
    assert!(text.contains("DASHBOARD_SMOKE_CHECKLIST.md"));
    assert!(text.contains("cmp bus.html index.html"));
    assert!(text.contains("DSH-039")); // Pax review gate
    assert!(text.contains("rendered-visible"));
}

#[test] fn test_dashboard_deploy_runbook_honest_limits() {
    let text = include_str!("../fixtures/DEPLOY_RUNBOOK.md");
    // No deploy command is pinned — the runbook says so plainly.
    assert!(text.contains("does\n**not** pin a command"));
    // Rollback is documented but unconfirmed until INT-031.
    assert!(text.contains("INT-031"));
    assert!(text.contains("unconfirmed"));
    // No credential is recorded in the runbook.
    for forbidden in ["api_token", "CF_API_TOKEN", "Bearer "] {
        assert!(!text.contains(forbidden), "credential leak: {forbidden}");
    }
}

// T242 partial — test_dashboard_smoke_checklist.py, portable half.
// The 5 cases below assert only against the carried fixtures
// (DASHBOARD_SMOKE_CHECKLIST.md, DASHBOARD_SPEC.md — both
// byte-identical to os/docs/). The other 5 cases read the
// fold-excluded bus.html / index.html and stay exclusion-blocked.

fn smoke_checklist() -> &'static str {
    include_str!("../fixtures/DASHBOARD_SMOKE_CHECKLIST.md")
}

fn smoke_check_numbers() -> Vec<u32> {
    smoke_checklist()
        .lines()
        .filter_map(|line| {
            let rest = line.strip_prefix("## Check ")?;
            let digits: String =
                rest.chars().take_while(|c| c.is_ascii_digit()).collect();
            digits.parse().ok()
        })
        .collect()
}

fn smoke_check_sections() -> Vec<String> {
    let mut sections: Vec<String> = Vec::new();
    let mut current: Option<String> = None;
    for line in smoke_checklist().lines() {
        if line.starts_with("## Check ") {
            if let Some(done) = current.take() {
                sections.push(done);
            }
            current = Some(String::new());
        } else if let Some(sec) = current.as_mut() {
            sec.push_str(line);
            sec.push('\n');
        }
    }
    if let Some(done) = current.take() {
        sections.push(done);
    }
    sections
}

#[test] fn test_dashboard_smoke_checklist_exactly_ten_checks() {
    assert_eq!(
        smoke_check_numbers(),
        vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    );
}

#[test] fn test_dashboard_smoke_checklist_every_check_names_pass_criteria() {
    let sections = smoke_check_sections();
    assert_eq!(sections.len(), 10);
    for (i, sec) in sections.iter().enumerate() {
        assert!(sec.contains("- Pass:"), "check {} has no pass criteria", i + 1);
    }
}

#[test] fn test_dashboard_smoke_checklist_covers_deploy_gates() {
    let text = smoke_checklist();
    for needle in ["intel-crew", "intel-brief", "intel-dispatch",
        "intel-alerts", "?demo=1", "#intel/brief/",
        "#intel/alert/", "390px", "read-only", "setInterval"] {
        assert!(text.contains(needle), "checklist never mentions {needle}");
    }
}

#[test] fn test_dashboard_smoke_checklist_run_procedure_and_log() {
    let text = smoke_checklist();
    assert!(text.contains("Run procedure"));
    assert!(text.contains("Run log"));
    assert!(text.contains("Any fail: stop"));
}

#[test] fn test_dashboard_smoke_checklist_spec_documents_it() {
    let spec = include_str!("../fixtures/DASHBOARD_SPEC.md");
    assert!(spec.contains("DSH-029"));
    assert!(spec.contains("DASHBOARD_SMOKE_CHECKLIST.md"));
}

// T238 partial — test_dashboard_accessibility.py, portable half.
// The 2 cases below need no viewer file: the contrast math runs on
// the hardcoded DSH-018 palette, and the notes check runs against
// the carried DASHBOARD_SPEC.md fixture (byte-identical to os/docs/).
// The other 4 cases read fold-excluded bus.html and stay
// exclusion-blocked (see the file header).

#[test]
fn test_dashboard_accessibility_palette_contrast_meets_aa() {
    for (name, fg) in PALETTE_FOREGROUNDS {
        for bg in PALETTE_BACKGROUNDS {
            let ratio = wcag_contrast_ratio(fg, bg);
            assert!(
                ratio >= 4.5,
                "{name} {fg} on {bg} fails WCAG AA: {ratio:.2}"
            );
        }
    }
    // Pin the audit math itself, not just the pass bar.
    let critical_page = wcag_contrast_ratio("#f85149", "#0d1117");
    let critical_panel = wcag_contrast_ratio("#f85149", "#161b22");
    assert!((critical_page - 5.65).abs() < 0.01, "critical/page: {critical_page}");
    assert!((critical_panel - 5.16).abs() < 0.01, "critical/panel: {critical_panel}");
}

#[test]
fn test_dashboard_accessibility_spec_carries_contrast_notes() {
    let spec = include_str!("../fixtures/DASHBOARD_SPEC.md");
    assert!(spec.contains("Accessibility (DSH-019)"));
    for hex in ["#f85149", "#d29922", "#58a6ff", "#8b949e"] {
        assert!(spec.contains(hex), "spec contrast notes missing {hex}");
    }
    assert!(spec.contains("4.5"), "spec contrast notes must state the AA bar");
}
