//! B15 parity — backend-contract checks (one per portable case).
//!
//! Exclusion-blocked (need the fold-excluded viewer `bus.html` /
//! `crew-board.html` / `index.html`, live Node drivers, real
//! browsers, or the missing submission-assets — marked here, never
//! faked green):
//! Split (T237, tests/b15_crewboard.rs): test_crewboard_alert_ribbon,
//! test_crewboard_attempts, test_crewboard_files_deps,
//! test_crewboard_os084_artifacts, test_crewboard_signing — the §7
//! rule halves and the signing-builder halves are ported there; the
//! card/detail HTML rendering halves (Node driver over the
//! fold-excluded crew-board.html), the OS-084 JSON-string-field
//! parse, the live attach() cross-check, and the signing
//! `admin.py` verify cross-check stay exclusion-blocked.
//! test_dashboard_bus_index_identity,
//! test_dashboard_palette, test_dashboard_screenshots,
//! test_intel_brief_dashboard_consistency.
//! Split (DSH-014, tests/b15_parity.rs below):
//! test_dashboard_alert_lifecycle — the WDG-014 transition rules
//! (status derivation, ack/resolve outcomes, unresolved-critical
//! count, resolved-collapse count, write gate) are ported against
//! the file's fixture values; the Node-driver halves, the bus/index
//! identical check, and the HTML rendering halves (resolved
//! collapse rendering, disabled-button HTML, source-text checks
//! over bus.html) stay exclusion-blocked: they read the
//! fold-excluded viewer.
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

// DSH-014 partial — test_dashboard_alert_lifecycle.py, rule half.
// Fixture values from the file's Node driver: alert:1 open
// critical, alert:2 acknowledged warning (acked by pax),
// alert:3 resolved info. The driver/HTML halves stay blocked
// (see the file header).

fn lifecycle_fixtures() -> Vec<LifecycleAlert> {
    vec![
        LifecycleAlert {
            id: "alert:1".into(),
            severity: "critical".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: None,
        },
        LifecycleAlert {
            id: "alert:2".into(),
            severity: "warning".into(),
            status: Some("acknowledged".into()),
            acknowledged_at: Some(1699999500),
            acknowledged_by: Some("pax".into()),
            resolved_at: None,
        },
        LifecycleAlert {
            id: "alert:3".into(),
            severity: "info".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: Some(1699998500),
        },
    ]
}

#[test]
fn test_dashboard_alert_lifecycle_feed_rows_carry_wdg014_status() {
    let alerts = lifecycle_fixtures();
    let rows: Vec<&str> =
        alerts.iter().map(alert_lifecycle_status).collect();
    assert_eq!(rows, vec!["open", "acknowledged", "resolved"]);
}

#[test]
fn test_dashboard_alert_lifecycle_ack_persists_and_idempotent() {
    let mut alerts = lifecycle_fixtures();
    let ack = acknowledge_alert(&mut alerts, "alert:1", 1700003700, "rowan");
    let row = match ack {
        LifecycleResult::Acknowledged(row) => row,
        other => panic!("ack must apply, got {other:?}"),
    };
    assert_eq!(row.status.as_deref(), Some("acknowledged"));
    assert_eq!(row.acknowledged_at, Some(1700003700));
    assert_eq!(row.acknowledged_by.as_deref(), Some("rowan"));
    // Re-ack is idempotent, not re-stamped.
    assert_eq!(
        acknowledge_alert(&mut alerts, "alert:1", 1700003701, "rowan"),
        LifecycleResult::AlreadyAcknowledged
    );
    assert_eq!(alerts[0].acknowledged_at, Some(1700003700));
}

#[test]
fn test_dashboard_alert_lifecycle_resolved_refuses_ack() {
    let mut alerts = lifecycle_fixtures();
    assert_eq!(
        acknowledge_alert(&mut alerts, "alert:3", 1700003700, "rowan"),
        LifecycleResult::RefusedResolved
    );
    assert_eq!(
        resolve_alert(&mut alerts, "alert:3", 1700003700),
        LifecycleResult::AlreadyResolved
    );
    assert_eq!(
        resolve_alert(&mut alerts, "nope", 1700003700),
        LifecycleResult::NotFound
    );
    assert_eq!(
        acknowledge_alert(&mut alerts, "nope", 1700003700, "rowan"),
        LifecycleResult::NotFound
    );
}

#[test]
fn test_dashboard_alert_lifecycle_resolve_unblocks_header() {
    let mut alerts = lifecycle_fixtures();
    assert_eq!(unresolved_critical_count(&alerts), 1);
    assert_eq!(
        resolve_alert(&mut alerts, "alert:1", 1700003800),
        LifecycleResult::Resolved(LifecycleAlert {
            id: "alert:1".into(),
            severity: "critical".into(),
            status: Some("resolved".into()),
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: Some(1700003800),
        })
    );
    // The resolved critical leaves the header count; the
    // acknowledged warning was never in it.
    assert_eq!(unresolved_critical_count(&alerts), 0);
    // The resolved record keeps no ack stamp (it was never acked).
    assert_eq!(alerts[0].acknowledged_at, None);
    // End-state rows mirror the driver's rowsAfter exactly:
    // resolved, acknowledged, resolved. (The "2 resolved" collapse
    // count itself is HTML rendering and stays exclusion-blocked.)
    let rows: Vec<&str> =
        alerts.iter().map(alert_lifecycle_status).collect();
    assert_eq!(rows, vec!["resolved", "acknowledged", "resolved"]);
}

#[test]
fn test_dashboard_alert_lifecycle_legacy_record_derives_status() {
    let legacy = LifecycleAlert {
        id: "alert:0".into(),
        severity: "critical".into(),
        status: None,
        acknowledged_at: Some(1700001000),
        acknowledged_by: None,
        resolved_at: None,
    };
    assert_eq!(alert_lifecycle_status(&legacy), "acknowledged");
}

#[test]
fn test_dashboard_alert_lifecycle_live_write_gate_off() {
    assert_eq!(
        alert_write_enabled(),
        (false, "posting is off for this build")
    );
}

#[test]
fn test_dashboard_alert_lifecycle_resolved_collapse_count() {
    // Driver's htmlBefore carries "1 resolved" (alert:3 only);
    // after alert:1 resolves it carries "2 resolved". The HTML
    // rendering stays blocked; this pins the count behind it.
    let mut alerts = lifecycle_fixtures();
    assert_eq!(resolved_count(&alerts), 1);
    assert_eq!(
        resolve_alert(&mut alerts, "alert:1", 1700003800),
        LifecycleResult::Resolved(LifecycleAlert {
            id: "alert:1".into(),
            severity: "critical".into(),
            status: Some("resolved".into()),
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: Some(1700003800),
        })
    );
    assert_eq!(resolved_count(&alerts), 2);
}

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
