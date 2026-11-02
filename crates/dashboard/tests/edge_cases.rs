//! B147 — edge cases: empty, maximum, duplicate, out-of-order.
//!
//! Each test is named for the case it covers. Values are real inputs
//! to the contract functions; nothing is mocked.

use dashboard::contract::*;

// ---- empty ----

#[test]
fn empty_inputs_return_empty_results_not_errors() {
    assert!(alerts_feed(Vec::new()).is_empty());
    assert!(addressable_cards(&[]).is_empty());
    assert_eq!(unresolved_critical_count(&[]), 0);
    assert_eq!(resolved_count(&[]), 0);
    let counts = count_today_records(&[], &[], None, &[], 1_700_000_000);
    assert_eq!(
        (
            counts.jobs_done,
            counts.briefs,
            counts.alerts_fired,
            counts.alerts_resolved
        ),
        (0, 0, 0, 0)
    );
    assert_eq!(files_line(Some("")), None);
    assert_eq!(deps_line(Some(" , ")), None);
    assert_eq!(parse_deep_link(""), None);
}

// ---- maximum ----

#[test]
fn maximum_length_room_still_validates_against_its_own_id() {
    let room = "r".repeat(10_000);
    let p = BriefPayload {
        id: format!("brief:{room}:100"),
        room: room.clone(),
        kind: "ondemand".into(),
        generated_at: 100,
        age_seconds: 0,
        template: false,
    };
    assert_eq!(validate_brief_payload(&p), Ok(()));
}

#[test]
fn maximum_feed_sorts_ten_thousand_cards_newest_first() {
    let cards: Vec<AlertCard> = (0..10_000)
        .map(|i| AlertCard {
            id: format!("alert-{i}"),
            created_at: i as i64,
            resolved: false,
        })
        .collect();
    let feed = alerts_feed(cards);
    assert_eq!(feed.len(), 10_000);
    assert_eq!(feed.first().unwrap().id, "alert-9999");
    assert_eq!(feed.last().unwrap().id, "alert-0");
}

#[test]
fn maximum_brief_history_dedupes_to_distinct_timestamps() {
    let history: Vec<i64> = (0..10_000).map(|_| 1_700_000_000).collect();
    let counts = count_today_records(&[], &history, Some(1_700_000_000), &[], 1_700_000_001);
    assert_eq!(counts.briefs, 1);
}

#[test]
fn maximum_files_line_keeps_every_name() {
    let files = (0..10_000)
        .map(|i| format!("dir/file-{i}.txt"))
        .collect::<Vec<_>>()
        .join(", ");
    let line = files_line(Some(files.as_str())).unwrap();
    assert!(line.starts_with("files: dir/file-0.txt"));
    assert!(line.ends_with("dir/file-9999.txt"));
}

// ---- duplicate ----

#[test]
fn duplicate_alert_ids_keep_input_order_on_a_tie() {
    let cards = vec![
        AlertCard { id: "same".into(), created_at: 5, resolved: false },
        AlertCard { id: "same".into(), created_at: 5, resolved: true },
    ];
    let feed = alerts_feed(cards);
    assert_eq!(feed.len(), 2);
    // sort_by is stable: equal keys keep the caller's order.
    assert!(!feed[0].resolved);
    assert!(feed[1].resolved);
}

#[test]
fn duplicate_lifecycle_id_acks_only_the_first_record() {
    let mut alerts = vec![
        LifecycleAlert {
            id: "a".into(),
            severity: "critical".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: None,
        },
        LifecycleAlert {
            id: "a".into(),
            severity: "warning".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: None,
        },
    ];
    let result = acknowledge_alert(&mut alerts, "a", 10, "bond");
    assert!(matches!(result, LifecycleResult::Acknowledged(_)));
    assert_eq!(alerts[0].status.as_deref(), Some("acknowledged"));
    assert_eq!(alerts[1].status, None);
}

#[test]
fn duplicate_deps_tokens_are_rendered_as_given() {
    assert_eq!(deps_line(Some("3, 3, 7")).as_deref(), Some("deps: #3, #3, #7"));
}

// ---- out-of-order ----

#[test]
fn out_of_order_feed_is_sorted_by_time_then_id_descending() {
    let feed = alerts_feed(vec![
        AlertCard { id: "a".into(), created_at: 1, resolved: false },
        AlertCard { id: "c".into(), created_at: 3, resolved: false },
        AlertCard { id: "b".into(), created_at: 2, resolved: false },
    ]);
    let ids: Vec<&str> = feed.iter().map(|c| c.id.as_str()).collect();
    assert_eq!(ids, vec!["c", "b", "a"]);
}

#[test]
fn out_of_order_history_counts_the_same_day_once() {
    let now = 1_700_000_000;
    let counts = count_today_records(
        &[],
        &[now - 10, now - 90_000, now - 20],
        None,
        &[],
        now,
    );
    // -90_000 falls on the previous UTC day; the other two are today.
    assert_eq!(counts.briefs, 2);
}

#[test]
fn out_of_order_jobs_and_alerts_are_counted_independently() {
    let now = 1_700_000_000;
    let jobs = vec![
        TodayJob { status: "done".into(), done_at: Some(now) },
        TodayJob { status: "open".into(), done_at: Some(now) },
        TodayJob { status: "done".into(), done_at: None },
    ];
    let alerts = vec![
        TodayAlert { created_at: Some(now), resolved_at: None },
        TodayAlert { created_at: None, resolved_at: Some(now) },
        TodayAlert { created_at: Some(now), resolved_at: Some(now) },
    ];
    let c = count_today_records(&jobs, &[], None, &alerts, now);
    assert_eq!(
        (c.jobs_done, c.alerts_fired, c.alerts_resolved),
        (1, 2, 2)
    );
}

// ---- boundaries ----

#[test]
fn stale_boundary_is_exactly_two_hours() {
    assert!(!is_stale(7_199));
    assert!(is_stale(7_200));
    assert!(stale_label(7_199).is_none());
    assert!(stale_label(7_200).is_some());
}

#[test]
fn same_day_boundary_is_utc_midnight() {
    assert!(same_day(0, 86_399));
    assert!(same_day(86_400, 172_799));
    assert!(!same_day(86_399, 86_400));
    assert!(!same_day(-1, 0));
}

#[test]
fn zero_max_attempts_is_already_danger() {
    let badge = attempts_badge(Some("0"), Some("0")).unwrap();
    assert_eq!(badge.text, "attempts 0/0");
    assert_eq!(badge.class, "pill attempts danger");
}

// ---- escaping ----

#[test]
fn escape_is_applied_in_the_documented_order() {
    assert_eq!(html_escape("&amp;"), "&amp;amp;");
    assert_eq!(html_escape("<b>&</b>"), "&lt;b&gt;&amp;&lt;/b&gt;");
    assert_eq!(html_escape("naïve"), "naïve");
}

#[test]
fn route_encoding_covers_every_non_unreserved_byte() {
    assert_eq!(route_encode_id("alert:1"), "alert%3A1");
    assert_eq!(route_encode_id("a b"), "a%20b");
    assert_eq!(route_encode_id("a-b_c.d~e"), "a-b_c.d~e");
    assert_eq!(route_encode_id("é"), "%C3%A9");
}
