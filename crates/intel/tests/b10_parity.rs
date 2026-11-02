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
    sections::SnapMessage { nick: nick.into(), text: text.into(), ts: None }
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
        source_window: None,
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
        source_window: None,
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
        source_window: None,
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
        source_window: None,
    };
    let s = sections::derive_sections(&snap);
    assert_eq!(s.watch_items, ["ALERT-X: first line".to_string()]);
}

// ---- B10 T190 continued: brief window line + message parts (BRF-013) ----
// Mirrors os/intel/brief.py `_window_line` / `_message_parts` directly;
// no Python unit test pins these two helpers, so the cases below pin
// the Python behavior itself (dict window, string window, start point,
// unstated; dict message, bus string, plain string).

use intel::b10_brief::window::{message_parts, window_line, RawMessage, SourceWindow, WindowHours, WindowInput};

#[test] fn test_intel_brief_window_line_dict_window() {
    let input = WindowInput {
        source_window: Some(SourceWindow::Dict {
            max_messages: Some(500),
            max_hours: Some(WindowHours::Float(24.0)),
            messages_kept: Some(120),
            messages_dropped: Some(380),
        }),
        window_start: None,
    };
    assert_eq!(
        window_line(&input),
        "Window: last 500 messages or last 24 hours, 120 kept, 380 dropped"
    );
}

#[test] fn test_intel_brief_window_line_string_start_unstated() {
    let stated = WindowInput {
        source_window: Some(SourceWindow::Text("yesterday".into())),
        window_start: None,
    };
    assert_eq!(window_line(&stated), "Window: yesterday");
    let truncated = WindowInput {
        source_window: None,
        window_start: Some("2026-10-26 08:00".into()),
    };
    assert!(window_line(&truncated).contains("Earlier history is not in this window"));
    assert_eq!(
        window_line(&WindowInput::default()),
        "Window: not stated in this snapshot"
    );
}

// ---- B10 T190 continued: brief constants, canned failure lines,
// trim-to-budget (BRF-007/026/028) ----
// Mirrors os/intel/brief.py BRIEF_SECTIONS / BRIEF_KINDS /
// BRIEF_BUDGETS / BRIEF_REGENERATION_WINDOW_SECONDS /
// BRIEF_FAILURE_COPY / _trim_to_budget directly.

#[test] fn test_intel_brief_failure_copy_kinds() {
    assert_eq!(
        brief::failure_copy_for_kind("unavailable").unwrap(),
        "No brief is available right now. Try again in a few minutes."
    );
    assert_eq!(
        brief::failure_copy_for_kind("spark_down").unwrap(),
        "The brief writer is down, so no fresh brief could be written. Try again later."
    );
    assert_eq!(
        brief::failure_copy_for_kind("no_data").unwrap(),
        "No brief yet, this room has no activity to brief on."
    );
    assert!(brief::failure_copy_for_kind("invented").is_err());
}

#[test] fn test_intel_brief_constants_and_budgets() {
    assert_eq!(
        brief::BRIEF_SECTIONS,
        ["Decisions", "In flight", "Owners", "Blocked and why", "Watch items"]
    );
    assert_eq!(brief::BRIEF_KINDS, ["morning", "onjoin", "ondemand"]);
    assert_eq!(brief::BRIEF_REGENERATION_WINDOW_SECONDS, 300);
    assert_eq!(brief::brief_budget("morning"), Some(220));
    assert_eq!(brief::brief_budget("onjoin"), Some(150));
    assert_eq!(brief::brief_budget("ondemand"), Some(300));
    assert_eq!(brief::brief_budget("bogus"), None);
}

#[test] fn test_intel_brief_trim_to_budget() {
    let t = "Window: x\n## Watch items\n- one two\n- three four\n- five six";
    assert_eq!(brief::trim_to_budget(t, 5), "Window: x\n## Watch items");
    assert_eq!(brief::trim_to_budget("a b c d e f", 3), "a b (trimmed)");
    assert_eq!(brief::trim_to_budget("one two three", 3), "one two three");
}

#[test] fn test_intel_brief_message_parts_forms() {
    assert_eq!(
        message_parts(&RawMessage::Dict { nick: "pax".into(), text: "hi".into() }),
        ("pax".to_string(), "hi".to_string())
    );
    assert_eq!(
        message_parts(&RawMessage::Text("milo: DONE: x".into())),
        ("milo".to_string(), "DONE: x".to_string())
    );
    assert_eq!(
        message_parts(&RawMessage::Text("plain hello".into())),
        (String::new(), "plain hello".to_string())
    );
}

// ---- B10 T190 continued: brief prompt path + load (BRF-007/019) ----
// Mirrors os/intel/brief.py brief_prompt_path / load_brief_prompt
// against the carried fixtures in crates/intel/fixtures/b10/prompts
// (test_intel_brief_prompt_wiring.py + test_intel_brief_prompt_version.py).
// The generate_brief halves that feed the prompt to a Spark client
// stay with the B11 client trait; only path/load are ported here.

#[test]
fn test_intel_brief_prompt_each_kind_loads_its_v1_file() {
    let dir = "fixtures/b10/prompts";
    for (kind, heading, file) in [
        ("morning", "Morning brief prompt", "brief_morning.md"),
        ("onjoin", "On-join brief prompt", "brief_onjoin.md"),
        ("ondemand", "On-demand brief prompt", "brief_ondemand.md"),
    ] {
        let text = brief::load_brief_prompt(kind, Some(dir), "v1");
        assert!(text.contains(heading), "{kind} must load its v1 file");
        let path = brief::brief_prompt_path(kind, Some(dir), "v1").unwrap();
        assert!(path.ends_with(file), "{kind} path must end in {file}");
        assert_eq!(path.rsplit('/').next().unwrap(), file);
    }
}

#[test]
fn test_intel_brief_prompt_v1_default_and_v2_files() {
    // Default dir (None) is the carried fixtures dir, like Python's
    // default prompts dir next to brief.py.
    let v1 = brief::load_brief_prompt("morning", None, "v1");
    assert!(v1.contains("Morning brief prompt"));
    assert!(v1.contains("v1 (BRF-001)"));
    let v2 = brief::load_brief_prompt("morning", None, "v2");
    assert!(v2.contains("Morning brief prompt"));
    assert!(v2.contains("v2 (BRF-019)"));
    let onjoin_v2 = brief::load_brief_prompt("onjoin", None, "v2");
    assert!(onjoin_v2.contains("On-join brief prompt"));
    assert!(onjoin_v2.contains("v2 (BRF-019)"));
    assert_eq!(
        brief::brief_prompt_path("morning", None, "v2")
            .unwrap()
            .rsplit('/')
            .next()
            .unwrap(),
        "brief_morning_v2.md"
    );
    assert_eq!(
        brief::brief_prompt_path("onjoin", None, "v2")
            .unwrap()
            .rsplit('/')
            .next()
            .unwrap(),
        "brief_onjoin_v2.md"
    );
}

#[test]
fn test_intel_brief_prompt_v2_ondemand_loads_nothing_no_fallback() {
    // Ondemand has no v2 file: the caller gets "", not a silent
    // v1 text under a v2 label.
    assert_eq!(brief::load_brief_prompt("ondemand", None, "v2"), "");
    assert_eq!(brief::brief_prompt_path("ondemand", None, "v2"), None);
}

#[test]
fn test_intel_brief_prompt_unknown_kind_version_and_missing_dir() {
    assert_eq!(brief::load_brief_prompt("morning", None, "v3"), "");
    assert_eq!(brief::brief_prompt_path("morning", None, "v3"), None);
    assert_eq!(brief::load_brief_prompt("nope", None, "v2"), "");
    assert_eq!(brief::brief_prompt_path("nope", None, "v2"), None);
    assert_eq!(brief::load_brief_prompt("nope", None, "v1"), "");
    assert_eq!(brief::brief_prompt_path("nope", None, "v1"), None);
    // A missing directory loads nothing and never raises.
    assert_eq!(
        brief::load_brief_prompt("morning", Some("/nonexistent-prompts-dir"), "v1"),
        ""
    );
}

// ---- B10 T190 partial: generate_brief orchestration (BRF-024/028/009) ----
// Template path only: the morning composer is compose_template_brief
// trimmed to budget; the Spark composer arrives with B11. The read
// fake and the write fake are separate structs because generate
// takes the store and the writer as separate borrows.

struct FakeReadStore {
    list: Vec<brief::BriefIndexEntry>,
    records: Vec<(brief::BriefTs, brief::StoredBriefRecord)>,
}

impl brief::BriefStore for FakeReadStore {
    fn list_briefs(&self, _room: &str) -> Result<Vec<brief::BriefIndexEntry>, String> {
        Ok(self.list.clone())
    }
    fn get_brief(
        &self,
        _room: &str,
        ts: brief::BriefTs,
    ) -> Result<Option<brief::StoredBriefRecord>, String> {
        let want = match ts {
            brief::BriefTs::Int(v) => v as f64,
            brief::BriefTs::Float(v) => v,
        };
        Ok(self
            .records
            .iter()
            .find(|(t, _)| {
                let got = match t {
                    brief::BriefTs::Int(v) => *v as f64,
                    brief::BriefTs::Float(v) => *v,
                };
                got == want
            })
            .map(|(_, r)| r.clone()))
    }
}

struct FakeWriter {
    puts: Vec<brief::GeneratedBriefRecord>,
    indexes: Vec<Vec<brief::BriefIndexEntry>>,
}

impl brief::BriefWriter for FakeWriter {
    fn put_brief(
        &mut self,
        _room: &str,
        _ts: i64,
        record: &brief::GeneratedBriefRecord,
    ) -> Result<String, String> {
        self.puts.push(record.clone());
        Ok(format!("BRIEF:main:{}", record.generated_at))
    }
    fn set_brief_index(
        &mut self,
        _room: &str,
        index: &[brief::BriefIndexEntry],
    ) -> Result<(), String> {
        self.indexes.push(index.to_vec());
        Ok(())
    }
}

fn gen_snapshot() -> brief::TemplateSnapshot {
    brief::TemplateSnapshot {
        base: sections::Snapshot {
            messages: vec![
                sections::SnapMessage { nick: "pax".into(), text: "DONE: ship it".into(), ts: None },
                sections::SnapMessage { nick: "milo".into(), text: "hello".into(), ts: None },
            ],
            jobs: vec![
                sections::SnapJob { id: "1".into(), title: "open job".into(), status: "open".into(), claim: String::new(), note: String::new(), last_progress_at: None, claimed_at: None },
                sections::SnapJob { id: "2".into(), title: "claimed job".into(), status: "claimed".into(), claim: "pax".into(), note: String::new(), last_progress_at: None, claimed_at: None },
                sections::SnapJob { id: "3".into(), title: "blocked job".into(), status: "blocked".into(), claim: String::new(), note: "waiting on gate".into(), last_progress_at: None, claimed_at: None },
            ],
            alerts: vec![],
            source_window: None,
        },
        ..Default::default()
    }
}

fn gen_window(kept: i64) -> intel::b10_brief::window::SourceWindow {
    intel::b10_brief::window::SourceWindow::Dict {
        max_messages: Some(500),
        max_hours: Some(intel::b10_brief::window::WindowHours::Int(24)),
        messages_kept: Some(kept),
        messages_dropped: Some(0),
    }
}

#[test]
fn test_intel_brief_generate_morning_fresh_builds_record_and_stores() {
    let store = FakeReadStore { list: vec![], records: vec![] };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let out = brief::generate_morning_brief(&gen_snapshot(), "main", Some(1200), false, &store, &mut writer).unwrap();
    match out {
        brief::GenerateBriefOutcome::Fresh { text, record, stored } => {
            assert!(stored);
            assert!(text.starts_with("TEMPLATE"));
            assert_eq!(record.room, "main");
            assert_eq!(record.generated_at, 1200);
            assert_eq!(record.kind, "morning");
            assert_eq!(record.model, "template");
            assert_eq!(record.spend_id, None);
            assert_eq!(record.sections.decisions, vec!["done: ship it".to_string()]);
            assert_eq!(record.sections.in_flight, vec!["1 open job".to_string(), "2 claimed job".to_string()]);
            assert_eq!(record.sections.owners, vec!["pax: claimed job".to_string()]);
            assert_eq!(record.sections.blocked, vec!["3 blocked job: waiting on gate".to_string()]);
            assert!(record.sections.watch_items.is_empty());
            assert_eq!(record.source_window, Some(gen_window(2)));
            assert!(!record.boot);
        }
        _ => panic!("expected a fresh build, got a guard hit"),
    }
    assert_eq!(writer.puts.len(), 1);
    assert_eq!(writer.puts[0].generated_at, 1200);
    assert_eq!(writer.indexes.len(), 1);
    assert_eq!(writer.indexes[0].len(), 1);
    assert_eq!(writer.indexes[0][0].ts, Some(brief::BriefTs::Int(1200)));
    assert_eq!(writer.indexes[0][0].kind.as_deref(), Some("morning"));
}

#[test]
fn test_intel_brief_generate_morning_guard_hit_returns_stored_no_store() {
    let store = FakeReadStore {
        list: vec![brief::BriefIndexEntry {
            ts: Some(brief::BriefTs::Int(1000)),
            generated_at: None,
            kind: Some("morning".into()),
        }],
        records: vec![(
            brief::BriefTs::Int(1000),
            brief::StoredBriefRecord {
                kind: "morning".into(),
                stored: brief::StoredBriefText {
                    text: Some("stored brief text".into()),
                    source_window: Some(gen_window(2)),
                    sections: std::collections::HashMap::new(),
                },
            },
        )],
    };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let out = brief::generate_morning_brief(&gen_snapshot(), "main", Some(1200), false, &store, &mut writer).unwrap();
    match out {
        brief::GenerateBriefOutcome::GuardHit { text, record } => {
            assert_eq!(text, "stored brief text");
            assert_eq!(record.kind, "morning");
        }
        _ => panic!("expected a guard hit, got a fresh build"),
    }
    assert!(writer.puts.is_empty());
    assert!(writer.indexes.is_empty());
}

#[test]
fn test_intel_brief_generate_morning_dry_run_builds_without_storing() {
    let store = FakeReadStore { list: vec![], records: vec![] };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let out = brief::generate_morning_brief(&gen_snapshot(), "main", Some(1200), true, &store, &mut writer).unwrap();
    match out {
        brief::GenerateBriefOutcome::Fresh { stored, record, .. } => {
            assert!(!stored);
            assert_eq!(record.generated_at, 1200);
        }
        _ => panic!("expected a fresh build, got a guard hit"),
    }
    assert!(writer.puts.is_empty());
    assert!(writer.indexes.is_empty());
}

#[test]
fn test_intel_brief_generate_boot_skips_guard() {
    let store = FakeReadStore {
        list: vec![brief::BriefIndexEntry {
            ts: Some(brief::BriefTs::Int(1000)),
            generated_at: None,
            kind: Some("morning".into()),
        }],
        records: vec![(
            brief::BriefTs::Int(1000),
            brief::StoredBriefRecord {
                kind: "morning".into(),
                stored: brief::StoredBriefText {
                    text: Some("stored brief text".into()),
                    source_window: Some(gen_window(2)),
                    sections: std::collections::HashMap::new(),
                },
            },
        )],
    };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let compose = |snap: &brief::TemplateSnapshot, boot: bool, kind: &str| -> String {
        brief::trim_to_budget(&brief::compose_template_brief(snap, boot, kind), 220)
    };
    let out = brief::generate_brief(
        &gen_snapshot(), "main", "morning", None, Some(1200), false, true, &store, &mut writer, &compose,
    )
    .unwrap();
    match out {
        brief::GenerateBriefOutcome::Fresh { record, stored, .. } => {
            assert!(stored);
            assert!(record.boot);
        }
        _ => panic!("a boot brief must skip the guard, got a guard hit"),
    }
    assert_eq!(writer.puts.len(), 1);
}

#[test]
fn test_intel_brief_generate_invalid_kind_errors_and_stores_nothing() {
    let store = FakeReadStore { list: vec![], records: vec![] };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let compose = |snap: &brief::TemplateSnapshot, boot: bool, kind: &str| -> String {
        brief::trim_to_budget(&brief::compose_template_brief(snap, boot, kind), 220)
    };
    let err = brief::generate_brief(
        &gen_snapshot(), "main", "nope", None, Some(1200), false, false, &store, &mut writer, &compose,
    )
    .unwrap_err();
    assert!(err.contains("invalid brief record"), "{err}");
    assert!(writer.puts.is_empty());
    assert!(writer.indexes.is_empty());
}

fn gen_record(ts: i64) -> brief::GeneratedBriefRecord {
    brief::GeneratedBriefRecord {
        room: "main".into(),
        generated_at: ts,
        kind: "morning".into(),
        sections: Default::default(),
        source_window: Some(gen_window(2)),
        model: "template".into(),
        spend_id: None,
        text: "TEMPLATE x".into(),
        screenshot_refs: vec![],
        boot: false,
    }
}

#[test]
fn test_intel_brief_store_brief_appends_and_sorts_index() {
    let store = FakeReadStore {
        list: vec![brief::BriefIndexEntry {
            ts: Some(brief::BriefTs::Int(9)),
            generated_at: None,
            kind: Some("morning".into()),
        }],
        records: vec![],
    };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    let key = brief::store_brief(&store, &mut writer, "main", &gen_record(5)).unwrap();
    assert!(!key.is_empty());
    assert_eq!(writer.puts.len(), 1);
    assert_eq!(writer.indexes.len(), 1);
    let ts: Vec<i64> = writer.indexes[0]
        .iter()
        .map(|e| match e.ts {
            Some(brief::BriefTs::Int(v)) => v,
            _ => panic!("index entry must carry an int ts"),
        })
        .collect();
    assert_eq!(ts, vec![5, 9]);
}

#[test]
fn test_intel_brief_store_brief_same_ts_does_not_duplicate_index() {
    let store = FakeReadStore {
        list: vec![brief::BriefIndexEntry {
            ts: Some(brief::BriefTs::Int(9)),
            generated_at: None,
            kind: Some("morning".into()),
        }],
        records: vec![],
    };
    let mut writer = FakeWriter { puts: vec![], indexes: vec![] };
    brief::store_brief(&store, &mut writer, "main", &gen_record(9)).unwrap();
    assert_eq!(writer.puts.len(), 1);
    assert!(writer.indexes.is_empty());
}
