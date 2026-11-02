//! Edge cases named by B075: empty input, maximum input, duplicate
//! input, out-of-order input. Each test is named for the case it proves.

use os_worker::{
    announcements_for, build_prompt, head_chars, parse_announcement, parse_section,
    parse_section_multi, sweep_expired_leases, tail_chars, uplink_tick, JobSpec, Order, StallAlert,
    SweepJob, UplinkState,
};

fn spec() -> JobSpec {
    JobSpec::new(
        "7",
        "title",
        "do the work",
        vec!["out.txt".to_string()],
        "file-exists: out.txt",
        Some("SECRET-SIGNATURE"),
    )
}

fn order(id: &str, text: &str) -> Order {
    Order {
        id: id.to_string(),
        text: text.to_string(),
        origin: "phone".to_string(),
        received_at: Some(1000),
    }
}

#[test]
fn empty_input_accept_text_verifies_true_with_one_note() {
    let dir = std::env::temp_dir().join(format!("os-worker-edge-empty-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("dir");
    let (ok, results) = os_worker::verify_accept("", &dir);
    assert!(ok);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].check, "(no acceptance criteria)");
}

#[test]
fn maximum_input_note_is_cut_to_the_limit_on_char_boundaries() {
    let long = "é".repeat(250);
    let cut = head_chars(&long, 200);
    assert_eq!(cut.chars().count(), 200);
    assert!(cut.chars().all(|c| c == 'é'));

    let tail = tail_chars(&long, 200);
    assert_eq!(tail.chars().count(), 200);

    // A string at the limit is returned unchanged, not clipped.
    let exact = "x".repeat(200);
    assert_eq!(head_chars(&exact, 200), exact);
}

#[test]
fn duplicate_uplink_order_is_reported_and_the_state_does_not_grow() {
    let mut state = UplinkState::default();
    state.seen_ids.push("o-1".to_string());
    let (events, next) = uplink_tick(&state, &[order("o-1", "again")], 1000, true, None, false);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].event_type, "duplicate");
    assert_eq!(next.seen_ids, vec!["o-1".to_string()]);
    assert!(next.pending.is_empty());
}

#[test]
fn out_of_order_pending_drains_before_new_orders() {
    let state = UplinkState {
        pending: vec![order("o-2", "queued first")],
        ..UplinkState::default()
    };
    let (events, next) = uplink_tick(
        &state,
        &[order("o-1", "new second")],
        1000,
        true,
        Some("key"),
        false,
    );
    assert_eq!(events.len(), 2);
    assert_eq!(events[0].order_id.as_deref(), Some("o-2"));
    assert_eq!(events[1].order_id.as_deref(), Some("o-1"));
    assert!(next.pending.is_empty());
    assert_eq!(next.seen_ids, vec!["o-2".to_string(), "o-1".to_string()]);
}

#[test]
fn disconnected_orders_queue_and_the_backoff_doubles() {
    let (events, next) = uplink_tick(
        &UplinkState::default(),
        &[order("o-1", "hold")],
        1000,
        false,
        None,
        false,
    );
    assert_eq!(events[0].event_type, "queued");
    assert_eq!(next.failures, 1);
    assert_eq!(next.next_retry_at, Some(1005));
    assert_eq!(next.pending.len(), 1);

    let (events, next2) = uplink_tick(&next, &[order("o-1", "hold")], 2000, false, None, false);
    assert_eq!(events[0].event_type, "duplicate");
    assert_eq!(next2.failures, 2);
    assert_eq!(next2.next_retry_at, Some(2010));
    assert_eq!(next2.pending.len(), 1);
}

#[test]
fn crew_mode_without_a_key_refuses_intake_but_keeps_the_order() {
    let (events, next) = uplink_tick(
        &UplinkState::default(),
        &[order("o-3", "crew work")],
        1000,
        true,
        None,
        true,
    );
    assert_eq!(events[0].event_type, "unsigned-refused");
    assert_eq!(
        events[0].reason.as_deref(),
        Some("crew mode requires a signing key")
    );
    assert!(events[0].record.is_none());
    assert!(next.seen_ids.is_empty());
    assert_eq!(next.pending.len(), 1);
}

#[test]
fn lease_expiry_boundary_requeues_and_open_jobs_are_untouched() {
    let mut jobs = vec![
        SweepJob {
            id: "expired".to_string(),
            status: "claimed".to_string(),
            claim: Some("pax".to_string()),
            claim_host: Some("box".to_string()),
            claimed_at: Some(900),
            lease_until: Some(1000),
        },
        SweepJob {
            id: "open".to_string(),
            status: "open".to_string(),
            ..SweepJob::default()
        },
        SweepJob {
            id: "no-lease".to_string(),
            status: "claimed".to_string(),
            claim: Some("pax".to_string()),
            lease_until: None,
            ..SweepJob::default()
        },
    ];
    let requeued = sweep_expired_leases(&mut jobs, 1000);
    assert_eq!(requeued, vec!["expired".to_string()]);
    assert_eq!(jobs[0].status, "open");
    assert!(jobs[0].claim.is_none() && jobs[0].claim_host.is_none());
    assert!(jobs[0].claimed_at.is_none() && jobs[0].lease_until.is_none());
    assert_eq!(jobs[1].status, "open");
    assert_eq!(jobs[2].status, "claimed");
    assert_eq!(jobs[2].claim.as_deref(), Some("pax"));
}

#[test]
fn duplicate_ini_keys_take_the_last_value_and_multi_keeps_all() {
    let text = "[svc]\nEnvironmentFile=a\nEnvironmentFile=b\nExecStart=x\n[other]\nExecStart=y\n";
    let single = parse_section(text, "svc");
    assert_eq!(single.get("ExecStart").map(String::as_str), Some("x"));
    let multi = parse_section_multi(text, "svc");
    assert_eq!(
        multi.get("EnvironmentFile"),
        Some(&vec!["a".to_string(), "b".to_string()])
    );
    assert_eq!(multi.get("ExecStart"), Some(&vec!["x".to_string()]));
}

#[test]
fn prompt_carries_the_work_but_never_the_signature() {
    let prompt = build_prompt(&spec());
    assert!(prompt.contains("Job: title (id: 7)"));
    assert!(prompt.contains("  - out.txt"));
    assert!(prompt.contains("file-exists: out.txt"));
    assert!(prompt.contains("max_attempts=3"));
    assert!(!prompt.contains("SECRET-SIGNATURE"));
}

#[test]
fn announcement_parser_requires_a_digit_id_and_a_trailing_req_clause() {
    let (jid, title, reqs) = parse_announcement("noise JOB:42 fix the bug req=rust,docs").unwrap();
    assert_eq!(jid, "42");
    assert_eq!(title, "fix the bug");
    assert_eq!(
        reqs.into_iter().collect::<Vec<_>>(),
        vec!["docs".to_string(), "rust".to_string()]
    );

    assert!(parse_announcement("JOB:x not a number").is_none());
    assert!(parse_announcement("JOB:7").is_none());
    assert!(parse_announcement("no job here").is_none());
}

#[test]
fn announcements_only_emit_for_critical_and_flatten_newlines() {
    let critical = StallAlert {
        kind: "presence-stall".to_string(),
        severity: "critical".to_string(),
        nick: "pax".to_string(),
        job: "7".to_string(),
        job_title: "demo".to_string(),
        last_progress_age_seconds: 700,
        last_progress_age_minutes: 11,
        dedupe_key: "presence-stall:pax:7".to_string(),
        created_at: 1000,
        explanation: "line one\nline two".to_string(),
    };
    let mut info = critical.clone();
    info.severity = "info".to_string();

    let lines = announcements_for(&[info, critical]);
    assert_eq!(lines.len(), 1);
    assert!(lines[0].starts_with("ALERT:presence-stall:pax:7 presence-stall: "));
    assert!(!lines[0].contains('\n'));
    assert!(lines[0].contains("line one line two"));
}
