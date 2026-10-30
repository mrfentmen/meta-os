//! B10 parity — one test per assigned Python test root (26 files).

use intel::b10_brief::{alerts, baton, brief, dispatch, forecast, notify, push, sections, wake};
use intel::b10_brief::baton::BatonSpec;
use intel::b10_brief::brief::BriefRecord;
use intel::b10_brief::dispatch::{Plan, PlanJob};

fn dj(status: &str) -> push::JobView {
    push::JobView { id: "j".into(), title: "T".into(), status: status.into(), verified: true, note: "q?".into() }
}

#[test] fn test_intel_brief_validates_record() {
    let r = BriefRecord { room: "main".into(), ts: 1, text: "x".into(), kind: "morning".into() };
    assert!(brief::validate_brief_record(&r).is_ok());
}
#[test] fn test_intel_brief_announce_frozen() {
    assert_eq!(brief::format_brief_announcement("main", 3), "BRIEF:main:3");
}
#[test] fn test_intel_brief_blocked_contacts_caller_compose() {
    let mut s = std::collections::HashMap::new();
    s.insert("held".into(), "a".into());
    assert!(brief::compose_brief("main", &s).text.contains("Morning brief"));
}
#[test] fn test_intel_brief_boot_environment_redacts() {
    assert_eq!(brief::redact_secrets(&["ROOM_KEY=x".into()]), vec!["ROOM_KEY=<redacted>".to_string()]);
}
#[test] fn test_intel_brief_cold_start_since_all() {
    assert_eq!(brief::parse_since("all", 9).unwrap(), None);
}
#[test] fn test_intel_brief_daily_caller_budget() {
    assert!(brief::brief_exceeds_budget(&"x".repeat(10), 5));
}
#[test] fn test_intel_brief_demo_morning_failure_line() {
    assert!(brief::brief_failure_line("main", "e").contains("failed"));
}
#[test] fn test_intel_brief_e2e_score_age() {
    assert_eq!(brief::brief_age_seconds(10, 4), 6);
}
#[test] fn test_intel_brief_environment_bus_cap() {
    assert!(brief::cap_snapshot_window("abcdef", 3).contains("trimmed"));
}
#[test] fn test_intel_brief_environment_record_index() {
    assert!(brief::brief_index_key("main").contains("main"));
}
#[test] fn test_intel_brief_environment_repo_plan_ok() {
    let p = Plan { goal: "g".into(), jobs: vec![PlanJob { key: "a".into(), title: "A".into(), files: vec![], deps: vec![], max_attempts: 3 }] };
    assert!(dispatch::check_dep_graph(&p).is_ok());
}
#[test] fn test_intel_brief_federation_caller_cycle() {
    let p = Plan { goal: "g".into(), jobs: vec![
        PlanJob { key: "a".into(), title: "A".into(), files: vec![], deps: vec!["b".into()], max_attempts: 3 },
        PlanJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3 }] };
    assert!(dispatch::check_dep_graph(&p).is_err());
}
#[test] fn test_intel_brief_held_decisions_caller_baton() {
    let spec = BatonSpec { job_id: "j".into(), goal: "g".into(), progress: String::new(), files: vec![], steps: vec![], acceptance: vec![] };
    assert!(baton::compose_baton(&spec, "a", "b").contains("BATON j"));
}
#[test] fn test_intel_brief_held_sources_remaining() {
    let spec = BatonSpec { job_id: "j".into(), goal: "g".into(), progress: "p".into(), files: vec!["a".into()], steps: vec![], acceptance: vec![] };
    assert_eq!(baton::remaining_files(&spec, &["a".into()]), Vec::<String>::new());
}
#[test] fn test_intel_brief_onjoin_template_push_done() {
    let v = push::Verification { ok: true, checks: vec![push::Check { check: "c".into(), ok: true }], artifacts: vec![] };
    assert!(push::build_done_push(&dj("done"), Some(&v)).is_some());
}
#[test] fn test_intel_brief_previous_brief_caller_blocked() {
    assert_eq!(push::build_blocked_push(&dj("blocked"), None).unwrap().text, "q?");
}
#[test] fn test_intel_brief_previous_session_caller_ledger() {
    let mut l = push::PushLedger::default();
    let p = push::build_blocked_push(&dj("blocked"), Some("q")).unwrap();
    assert!(l.decide_push(p.clone()).is_some() && l.decide_push(p).is_none());
}
#[test] fn test_intel_brief_priority_caller_forecast() {
    assert_eq!(forecast::project_end_of_day(1.0, 1.0, 1.0), Some(2.0));
}
#[test] fn test_intel_brief_priority_contacts_preempt() {
    assert!(forecast::preempt_decision(80.0, 75.0));
}
#[test] fn test_intel_brief_prompt_v2_no_secrets() {
    assert!(dispatch::check_no_secrets("plain plan").is_ok());
    assert!(dispatch::check_no_secrets("sk-live-abc").is_err());
}
#[test] fn test_intel_brief_prompt_version_clamp() {
    let mut p = Plan { goal: "g".into(), jobs: vec![PlanJob { key: "a".into(), title: "A".into(), files: vec![], deps: vec![], max_attempts: 0 }] };
    dispatch::clamp_attempt_budgets(&mut p);
    assert_eq!(p.jobs[0].max_attempts, 3);
}
#[test] fn test_intel_brief_prompt_wiring_notify_line() {
    let n = notify::Notification { id: "i".into(), severity: "low".into(), topic: "t".into(), text: "x".into() };
    assert_eq!(notify::render_line(&n), "[low] t: x");
}
#[test] fn test_intel_brief_recovery_caller_wake() {
    assert!(wake::is_sleeping_muse(false, 30));
    assert_eq!(wake::dedupe_key("m", "j"), "wake:m:j");
}
#[test] fn test_intel_brief_screenshots_alert_lifecycle() {
    let mut s = alerts::Store::default();
    s.write_alert(intel::b09_core::store::AlertRecord { id: "a".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None }).unwrap();
    assert!(alerts::acknowledge_alert(&mut s, "a", 2));
}
#[test] fn test_intel_brief_since_last_parse() {
    assert_eq!(brief::parse_since("1h", 3600).unwrap(), Some(0));
}
#[test] fn test_intel_brief_system_state_caller_confidence() {
    assert_eq!(forecast::confidence_for(2), "low");
}

// ---- B10 T190 partial: brief section derivation (INT-025 fixtures) ----
// Fixture values from test_intel_brief_dashboard_consistency.py: the
// busy/stall/quiet snapshots. The panel half of that file stays
// exclusion-blocked (Node driver over the fold-excluded bus.html);
// these tests pin the record half only.

fn msg(nick: &str, text: &str) -> sections::SnapMessage {
    sections::SnapMessage { nick: nick.into(), text: text.into() }
}

fn job(id: &str, title: &str, status: &str, claim: &str, note: &str) -> sections::SnapJob {
    sections::SnapJob {
        id: id.into(), title: title.into(), status: status.into(),
        claim: claim.into(), note: note.into(),
        last_progress_at: None, claimed_at: None,
    }
}

#[test] fn test_intel_brief_sections_busy_fixture_values() {
    let snap = sections::Snapshot {
        messages: vec![
            msg("pax", "DECISION: freeze the wire format today"),
            msg("milo", "DONE: watchdog loop runs on the stall fixture"),
            msg("rowan", "BLOCKED: brief panel needs the frozen payload contract"),
        ],
        jobs: vec![
            job("3", "brief panel", "claimed", "pax", "working"),
            job("5", "dispatch poster", "open", "", ""),
            job("7", "spark client", "blocked", "", "waiting on the real Spark endpoint, not a fake one"),
            job("9", "watchdog loop", "done", "", "finished"),
        ],
        alerts: vec![],
    };
    let s = sections::derive_sections(&snap);
    assert_eq!(s.decisions, [
        "decision: freeze the wire format today".to_string(),
        "done: watchdog loop runs on the stall fixture".to_string(),
        "blocked: brief panel needs the frozen payload contract".to_string(),
    ]);
    assert_eq!(s.in_flight, ["3 brief panel".to_string(), "5 dispatch poster".to_string()]);
    assert_eq!(s.owners, ["pax: brief panel".to_string()]);
    assert_eq!(s.blocked, ["7 spark client: waiting on the real Spark endpoint, not a fake one".to_string()]);
    assert_eq!(s.watch_items, Vec::<String>::new());
}

#[test] fn test_intel_brief_sections_stall_fixture_values() {
    let snap = sections::Snapshot {
        messages: vec![msg("milo", "DECISION: restart the watchdog loop")],
        jobs: vec![job("11", "watchdog loop", "blocked", "", "no beat in 20 minutes")],
        alerts: vec![sections::SnapAlert {
            id: "ALERT-STALL-1".into(),
            summary: "watchdog loop silent for 20 minutes".into(),
            explanation: "".into(),
        }],
    };
    let s = sections::derive_sections(&snap);
    assert_eq!(s.decisions, ["decision: restart the watchdog loop".to_string()]);
    assert_eq!(s.in_flight, Vec::<String>::new());
    assert_eq!(s.owners, Vec::<String>::new());
    assert_eq!(s.blocked, ["11 watchdog loop: no beat in 20 minutes".to_string()]);
    assert_eq!(s.watch_items, ["ALERT-STALL-1: watchdog loop silent for 20 minutes".to_string()]);
}

#[test] fn test_intel_brief_sections_quiet_snapshot_is_empty() {
    let snap = sections::Snapshot {
        messages: vec![msg("pax", "morning, checking in")],
        jobs: vec![],
        alerts: vec![],
    };
    let s = sections::derive_sections(&snap);
    assert!(s.decisions.is_empty());
    assert!(s.in_flight.is_empty());
    assert!(s.owners.is_empty());
    assert!(s.blocked.is_empty());
    assert!(s.watch_items.is_empty());
}

#[test] fn test_intel_brief_sections_watch_item_falls_back_to_explanation() {
    let snap = sections::Snapshot {
        messages: vec![],
        jobs: vec![],
        alerts: vec![sections::SnapAlert {
            id: "ALERT-X".into(),
            summary: "".into(),
            explanation: "first line\nsecond line".into(),
        }],
    };
    let s = sections::derive_sections(&snap);
    assert_eq!(s.watch_items, ["ALERT-X: first line".to_string()]);
}
