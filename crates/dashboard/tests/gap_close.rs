//! B155 — test-gap close.
//!
//! The crate has two modules. `contract` carries every function and
//! seven in-file unit tests; `lib` carries only the module export and
//! no tests. The thinnest covered behaviour is therefore the set of
//! public helpers no existing file exercises directly. These cases
//! bring those up to the same depth as the rest of the contract.
//!
//! Only public API is used; no production code was widened to make
//! any case reachable.

use dashboard::contract::*;

// ---- constants that nothing else asserts ----

#[test]
fn brief_kinds_are_exactly_the_three_spec_kinds() {
    assert_eq!(BRIEF_KINDS, &["morning", "onjoin", "ondemand"][..]);
    assert_eq!(BRIEF_STALE_SECONDS, 7_200);
}

#[test]
fn verdicts_are_the_three_str004_ground_truth_words() {
    assert_eq!(VERDICTS, &["build ok", "build broken", "unclear"][..]);
}

#[test]
fn rollback_steps_are_the_four_int031_names_in_order() {
    assert_eq!(
        ROLLBACK_STEPS,
        &[
            "Deployments",
            "All deployments",
            "Rollback to this deployment",
            "muse-relay-live"
        ][..]
    );
}

// ---- helpers with no direct test ----

#[test]
fn resolve_brief_link_only_accepts_a_timestamp_in_the_window() {
    assert_eq!(resolve_brief_link("100", &[90, 100, 110]), Some(100));
    assert_eq!(resolve_brief_link("100", &[90, 110]), None);
    assert_eq!(resolve_brief_link("not-a-number", &[100]), None);
    assert_eq!(resolve_brief_link("", &[]), None);
}

#[test]
fn default_open_is_closed_for_every_known_section_but_blocked() {
    for section in BRIEF_SECTION_ORDER.iter().copied() {
        assert_eq!(default_open(section), section == "blocked", "{section}");
    }
    assert!(!default_open("unknown"));
}

#[test]
fn stale_label_humanises_hours_and_minutes() {
    // The hours branch has no "ago" of its own; the label supplies "old".
    assert_eq!(
        stale_label(7_200).as_deref(),
        Some("2 h 0 min old — regenerate for current state")
    );
    assert_eq!(
        stale_label(7_260).as_deref(),
        Some("2 h 1 min old — regenerate for current state")
    );
}

#[test]
fn addressable_cards_preserve_order_and_drop_resolved() {
    let cards = vec![
        AlertCard { id: "a".into(), created_at: 1, resolved: false },
        AlertCard { id: "b".into(), created_at: 3, resolved: true },
        AlertCard { id: "c".into(), created_at: 2, resolved: false },
    ];
    let ids: Vec<&str> = addressable_cards(&cards).iter().map(|c| c.id.as_str()).collect();
    assert_eq!(ids, vec!["a", "c"]);
}

#[test]
fn route_encode_id_passes_unreserved_bytes_through() {
    assert_eq!(route_encode_id("AZaz09-_.~"), "AZaz09-_.~");
    assert_eq!(route_encode_id("alert:<x>"), "alert%3A%3Cx%3E");
}

#[test]
fn py_str_json_handles_control_bytes_and_del() {
    assert_eq!(py_str_json("\u{01}"), "\"\\u0001\"");
    assert_eq!(py_str_json("\n\r\t"), "\"\\n\\r\\t\"");
    assert_eq!(py_str_json("del\u{7f}"), "\"del\u{7f}\"");
    assert_eq!(py_str_json("\u{1F600}"), "\"\\ud83d\\ude00\"");
}

#[test]
fn nonce_shape_is_lowercase_hex_and_exactly_sixteen() {
    assert!(is_nonce_hex("0123456789abcdef"));
    assert!(!is_nonce_hex("0123456789abcde"));
    assert!(!is_nonce_hex("0123456789abcdeff"));
    assert!(!is_nonce_hex("0123456789abcdeF"));
}

// ---- lifecycle branches not covered elsewhere ----

#[test]
fn an_unrecognised_status_falls_back_to_the_timestamps() {
    let base = LifecycleAlert {
        id: "a".into(),
        severity: "critical".into(),
        status: Some("closed".into()),
        acknowledged_at: None,
        acknowledged_by: None,
        resolved_at: None,
    };
    assert_eq!(alert_lifecycle_status(&base), "open");
    let acked = LifecycleAlert {
        acknowledged_at: Some(5),
        ..base.clone()
    };
    assert_eq!(alert_lifecycle_status(&acked), "acknowledged");
    let resolved = LifecycleAlert {
        resolved_at: Some(6),
        ..base
    };
    assert_eq!(alert_lifecycle_status(&resolved), "resolved");
}

#[test]
fn resolving_an_acknowledged_record_keeps_the_ack_stamp() {
    let mut alerts = vec![LifecycleAlert {
        id: "a".into(),
        severity: "critical".into(),
        status: Some("acknowledged".into()),
        acknowledged_at: Some(5),
        acknowledged_by: Some("bond".into()),
        resolved_at: None,
    }];
    let out = resolve_alert(&mut alerts, "a", 9);
    match out {
        LifecycleResult::Resolved(row) => {
            assert_eq!(row.status.as_deref(), Some("resolved"));
            assert_eq!(row.acknowledged_at, Some(5));
            assert_eq!(row.acknowledged_by.as_deref(), Some("bond"));
            assert_eq!(row.resolved_at, Some(9));
        }
        other => panic!("expected Resolved, got {other:?}"),
    }
}

#[test]
fn unresolved_critical_count_is_case_insensitive_and_skips_resolved() {
    let alerts = vec![
        LifecycleAlert {
            id: "1".into(),
            severity: "CRITICAL".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: None,
        },
        LifecycleAlert {
            id: "2".into(),
            severity: "critical".into(),
            status: Some("resolved".into()),
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: Some(1),
        },
        LifecycleAlert {
            id: "3".into(),
            severity: "warning".into(),
            status: None,
            acknowledged_at: None,
            acknowledged_by: None,
            resolved_at: None,
        },
    ];
    assert_eq!(unresolved_critical_count(&alerts), 1);
    assert_eq!(resolved_count(&alerts), 1);
}
