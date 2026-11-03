//! B171 — edge cases: empty input, maximum input, duplicate input, and
//! out-of-order input across intel's public surface.
use std::collections::HashMap;

use intel::b09_core::gate::{gate_tick, JobInt, JobRecord, JournalRecord};
use intel::b09_core::ingest::{messages_from_cursor, store_messages, Message};
use intel::b09_core::ladder::{classify, ladder_action, Snapshot, Stall, REASSIGN, RESTART};
use intel::b10_brief::brief::{
    parse_since, previous_session_digest, recovery_line, redact_secrets, system_state_lines,
    trim_to_budget, BatonStep, CorruptedEntry, PreviousSession, RecoveryRecord, RecoveredEntry,
    SystemState,
};
use intel::b10_brief::dispatch::{clamp_attempt_budgets, Plan, PlanJob};
use intel::b10_brief::forecast::{confidence_for, project_end_of_day, usable_number};
use intel::b13_devpack::{
    alerts_feed, brief_entry, plan_preview, serde_json_like::Json, AlertRow, PreviewPlan,
};

fn job_record(id: Option<&str>, status: &str, attempts: i64, max: i64) -> JobRecord {
    JobRecord {
        id: id.map(str::to_string),
        status: status.to_string(),
        attempts: Some(JobInt::Int(attempts)),
        max_attempts: Some(JobInt::Int(max)),
        blocker_kind: None,
        note: String::new(),
    }
}

fn message(id: &str, ts: i64) -> Message {
    Message {
        id: id.to_string(),
        room: "main".to_string(),
        ts,
        body: format!("body {id}"),
    }
}

#[test]
fn since_accepts_all_forms_and_boundaries() {
    assert_eq!(parse_since("all", 1000).unwrap(), None);
    assert_eq!(parse_since("  ALL  ", 1000).unwrap(), None);
    assert_eq!(parse_since("0", 1000).unwrap(), Some(0));
    assert_eq!(parse_since("45m", 10_000).unwrap(), Some(10_000 - 2_700));
    assert_eq!(parse_since(" 2h ", 10_000).unwrap(), Some(10_000 - 7_200));
    assert_eq!(parse_since("3d", 100_000).unwrap(), Some(100_000 - 259_200));
}

#[test]
fn trim_keeps_exact_budget_and_drops_bullets_first() {
    assert_eq!(trim_to_budget("one two three", 3), "one two three");
    let text = "Window: x\n## Watch\n- one two\n- three four";
    assert_eq!(trim_to_budget(text, 5), "Window: x\n## Watch");
    // Documented oddity: a zero budget keeps all but the last word.
    assert_eq!(trim_to_budget("a b c", 0), "a b (trimmed)");
}

#[test]
fn redaction_only_touches_secretish_assignments() {
    let lines = vec![
        "API_TOKEN=abc".to_string(),
        "noequals".to_string(),
        "room=main".to_string(),
        "secret=a=b".to_string(),
    ];
    assert_eq!(
        redact_secrets(&lines),
        vec![
            "API_TOKEN=<redacted>".to_string(),
            "noequals".to_string(),
            "room=main".to_string(),
            "secret=<redacted>".to_string(),
        ]
    );
}

#[test]
fn previous_session_digest_handles_singulars_and_empty_titles() {
    let one = PreviousSession {
        last_brief_at: "2026-11-02 08:00".to_string(),
        jobs_completed: vec!["".to_string(), "A".to_string()],
        open_threads: vec!["B".to_string()],
    };
    assert_eq!(
        previous_session_digest(Some(&one)).unwrap(),
        "Previous session: last brief 2026-11-02 08:00, 1 job completed (A), 1 open thread (B)"
    );
    assert_eq!(previous_session_digest(None), None);
}

#[test]
fn system_state_filters_empty_names_and_reports_a_down_gateway() {
    let state = SystemState {
        drivers: Some(vec!["".to_string()]),
        gateway_healthy: Some(false),
        skill_apps: Some(vec!["".to_string()]),
    };
    assert_eq!(
        system_state_lines(&state),
        vec![
            "Drivers: no drivers reported".to_string(),
            "Tools: MCP gateway down, so agents cannot reach their tools through it".to_string(),
            "Skill apps: no skill apps mounted".to_string(),
        ]
    );
}

#[test]
fn recovery_line_says_incomplete_on_mismatch_unreadable_and_corrupt_records() {
    let unreadable = RecoveryRecord {
        corrupted: None,
        recovered: Some(vec![RecoveredEntry::Unreadable]),
        sweep_count: Some(1),
    };
    assert!(recovery_line(Some(&unreadable)).contains("a recovered job record is unreadable"));

    let corrupt = RecoveryRecord {
        corrupted: Some(vec![CorruptedEntry::Plain("old job".to_string())]),
        recovered: None,
        sweep_count: None,
    };
    assert!(recovery_line(Some(&corrupt)).contains("old job has a corrupted record"));

    let mismatch = RecoveryRecord {
        corrupted: None,
        recovered: Some(vec![RecoveredEntry::Job {
            id: "T1".to_string(),
            title: "Alpha".to_string(),
            baton_step: BatonStep::Missing,
        }]),
        sweep_count: Some(2),
    };
    assert!(recovery_line(Some(&mismatch)).contains("reports 2 recovered but 1 job records"));
}

#[test]
fn gate_skips_empty_ids_done_jobs_and_duplicate_parks() {
    assert!(gate_tick(&[job_record(None, "open", 9, 1)], &[]).is_empty());
    assert!(gate_tick(&[job_record(Some("j"), "done", 9, 1)], &[]).is_empty());
    // A max of zero is unbudgeted, not an exhausted budget.
    assert!(gate_tick(&[job_record(Some("j"), "open", 99, 0)], &[]).is_empty());

    let first = gate_tick(&[job_record(Some("j"), "open", 5, 1)], &[]);
    assert_eq!(first.len(), 2);
    let second = gate_tick(&[job_record(Some("j"), "open", 5, 1)], &first);
    assert!(second.is_empty());
    let journal: Vec<JournalRecord> = first;
    assert_eq!(journal[0].dedupe_key, "park:j");
    assert_eq!(journal[1].dedupe_key, "escalate:j");
}

#[test]
fn ladder_returns_nothing_for_malformed_or_unknown_stalls() {
    let snap = Snapshot {
        registered: vec!["milo".to_string()],
        present: vec![],
        jobs: vec![("j1".to_string(), "t".to_string(), "p".to_string(), vec![])],
    };
    assert_eq!(classify(&snap, &Stall { nick: None, job: Some("j1".to_string()) }), None);
    assert_eq!(
        classify(&snap, &Stall { nick: Some("milo".to_string()), job: Some("ghost".to_string()) }),
        None
    );
    assert_eq!(
        classify(&snap, &Stall { nick: Some("milo".to_string()), job: Some("j1".to_string()) }),
        Some(RESTART)
    );
    let stranger = Stall { nick: Some("walk-on".to_string()), job: Some("j1".to_string()) };
    assert_eq!(classify(&snap, &stranger), Some(REASSIGN));
    assert!(ladder_action(&snap, &stranger).unwrap().baton.is_some());
}

#[test]
fn ingest_dedupes_and_pages_at_one_hundred() {
    let mut store = Vec::new();
    let msgs: Vec<Message> = (0..101).map(|i| message(&format!("m{i}"), i as i64)).collect();
    assert_eq!(store_messages(&mut store, msgs), 101);
    // A duplicate id is not stored twice.
    assert_eq!(store_messages(&mut store, vec![message("m0", 0)]), 0);

    let first = messages_from_cursor(&store, None);
    assert_eq!(first.messages.len(), 100);
    assert_eq!(first.cursor.as_deref(), Some("m99"));

    let second = messages_from_cursor(&store, first.cursor.as_deref());
    assert_eq!(second.messages.len(), 1);
    assert_eq!(second.cursor.as_deref(), Some("m100"));

    let end = messages_from_cursor(&store, Some("m100"));
    assert!(end.messages.is_empty());
    assert_eq!(end.cursor, None);

    // An unknown cursor starts from the beginning, as the code does.
    let unknown = messages_from_cursor(&store, Some("nope"));
    assert_eq!(unknown.messages.len(), 100);
}

#[test]
fn alerts_feed_breaks_ties_on_id_descending() {
    let feed = alerts_feed(vec![
        AlertRow { id: "a".to_string(), created_at: 5 },
        AlertRow { id: "b".to_string(), created_at: 5 },
        AlertRow { id: "c".to_string(), created_at: 9 },
    ]);
    assert_eq!(
        feed.iter().map(|r| r.id.as_str()).collect::<Vec<_>>(),
        vec!["c", "b", "a"]
    );
}

#[test]
fn plan_preview_accepts_an_empty_plan() {
    let plan = PreviewPlan { summary: "s".to_string(), jobs: vec![] };
    let preview = plan_preview(&plan, &[]).unwrap();
    assert_eq!(preview.jobs_count, 0);
    assert_eq!(preview.max_attempts_total, 0);
    assert!(preview.posting_order.is_empty());
}

#[test]
fn attempt_budgets_clamp_at_both_ends() {
    let mut plan = Plan {
        goal: "g".to_string(),
        jobs: vec![
            PlanJob { key: "a".to_string(), title: "A".to_string(), files: vec![], deps: vec![], max_attempts: 0, spec: String::new(), accept: vec![] },
            PlanJob { key: "b".to_string(), title: "B".to_string(), files: vec![], deps: vec![], max_attempts: 11, spec: String::new(), accept: vec![] },
            PlanJob { key: "c".to_string(), title: "C".to_string(), files: vec![], deps: vec![], max_attempts: 1, spec: String::new(), accept: vec![] },
        ],
    };
    clamp_attempt_budgets(&mut plan);
    assert_eq!(
        plan.jobs.iter().map(|j| j.max_attempts).collect::<Vec<_>>(),
        vec![3, 10, 1]
    );
}

#[test]
fn forecast_refuses_non_finite_and_negative_numbers() {
    assert_eq!(usable_number(0.0), Some(0.0));
    assert_eq!(usable_number(f64::NAN), None);
    assert_eq!(usable_number(f64::INFINITY), None);
    assert_eq!(usable_number(-0.1), None);
    assert_eq!(project_end_of_day(1.0, f64::NAN, 1.0), None);
    assert_eq!(confidence_for(0), "high");
    assert_eq!(confidence_for(1), "medium");
    assert_eq!(confidence_for(9), "low");
}

#[test]
fn brief_entry_copies_fields_verbatim_and_allows_a_negative_age() {
    let mut record = HashMap::new();
    record.insert("generated_at".to_string(), Json::Int(100));
    record.insert("text".to_string(), Json::Str("body".to_string()));
    let entry = brief_entry(&record, &Json::Int(90)).unwrap();
    assert_eq!(entry["text"], Json::Str("body".to_string()));
    assert_eq!(entry["as_of"], Json::Int(90));
    assert_eq!(entry["age_seconds"], Json::Int(-10));
}
