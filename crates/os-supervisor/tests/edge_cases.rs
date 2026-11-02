//! Edge-case tests for `os-supervisor` (B015).
//!
//! Empty, maximum, duplicate, and out-of-order inputs, one named test
//! per case, against the public API only.

use os_supervisor::relay_watchman::validate_args;
use os_supervisor::watchdog::paginate;
use os_supervisor::watchman_boot::{sweep_mismatch, Ring, LEASE_EXPIRED_DURING_DOWNTIME};
use os_supervisor::watchman_bridge::{fold_tick, WatchEvent};
use os_supervisor::watchman_loop::parse_event_lines;
use os_supervisor::watchman_watch::{
    current_states, machine_state, WatchmanRecord, WatchmanSnapshot, ALIVE, DEAD, UNKNOWN,
};

fn wake(at: f64) -> WatchEvent {
    WatchEvent::new("wake", Some(at))
}

fn record(alive: Option<bool>, bell: Option<f64>) -> WatchmanRecord {
    WatchmanRecord {
        watchman_alive: alive,
        last_bell: bell,
        ..WatchmanRecord::default()
    }
}

// --- empty input -----------------------------------------------------------

#[test]
fn empty_input_paginates_to_no_pages() {
    let pages = paginate::<i32>(&[], 10).expect("positive page size");
    assert!(pages.is_empty());
}

#[test]
fn empty_text_parses_to_zero_events_and_zero_malformed() {
    assert_eq!(parse_event_lines(Some("")), (Vec::new(), 0));
    assert_eq!(parse_event_lines(Some("\n\n  \n")), (Vec::new(), 0));
}

#[test]
fn a_missing_events_string_counts_as_one_malformed_line() {
    let (events, malformed) = parse_event_lines(None);
    assert!(events.is_empty());
    assert_eq!(malformed, 1);
}

// --- maximum input ---------------------------------------------------------

#[test]
fn maximum_input_paginates_into_full_pages_then_the_remainder() {
    let items: Vec<i32> = (0..2500).collect();
    let pages = paginate(&items, 1000).expect("positive page size");
    assert_eq!(pages.len(), 3);
    assert_eq!(pages[0].len(), 1000);
    assert_eq!(pages[1].len(), 1000);
    assert_eq!(pages[2].len(), 500);
    assert_eq!(pages[2][499], 2499);
}

#[test]
fn maximum_page_size_larger_than_input_is_one_page() {
    let pages = paginate(&[1, 2, 3], 1000).expect("positive page size");
    assert_eq!(pages, vec![vec![1, 2, 3]]);
}

// --- duplicate input -------------------------------------------------------

#[test]
fn duplicate_sweep_ids_collapse_and_do_not_create_extra_mismatches() {
    let rings = vec![Ring {
        job_id: "7".to_string(),
        reason: LEASE_EXPIRED_DURING_DOWNTIME.to_string(),
        posted_at: None,
        lease_expires_at: Some(100.0),
    }];
    let sweep = vec!["7".to_string(), "7".to_string(), "7".to_string()];
    let mismatch = sweep_mismatch(&rings, &sweep);
    assert!(mismatch.missing.is_empty());
    assert!(mismatch.extra.is_empty());
}

#[test]
fn duplicate_wake_events_at_the_same_time_keep_the_same_bell() {
    let records = fold_tick(&[wake(500.0), wake(500.0)], 600.0, None);
    assert_eq!(records.last_bell, Some(500.0));
}

// --- out-of-order input ----------------------------------------------------

#[test]
fn out_of_order_wakes_keep_the_latest_bell() {
    let descending = fold_tick(&[wake(900.0), wake(100.0)], 1000.0, None);
    assert_eq!(descending.last_bell, Some(900.0));
    let ascending = fold_tick(&[wake(100.0), wake(900.0)], 1000.0, None);
    assert_eq!(ascending.last_bell, Some(900.0));
}

#[test]
fn an_older_wake_never_moves_the_prior_bell_backwards() {
    let prior = record(Some(true), Some(800.0));
    let folded = fold_tick(&[wake(100.0)], 1000.0, Some(&prior));
    assert_eq!(folded.last_bell, Some(800.0));
}

#[test]
fn board_states_come_out_in_machine_name_order() {
    let mut snapshot = WatchmanSnapshot::new();
    snapshot
        .machines
        .insert("zulu".to_string(), Some(record(Some(true), Some(100.0))));
    snapshot
        .machines
        .insert("alpha".to_string(), Some(record(Some(true), Some(100.0))));
    snapshot
        .machines
        .insert("mike".to_string(), Some(record(Some(true), Some(100.0))));
    let names: Vec<String> = current_states(&snapshot, 120.0)
        .into_iter()
        .map(|s| s.machine)
        .collect();
    assert_eq!(names, vec!["alpha", "mike", "zulu"]);
}

// --- state judgement edges -------------------------------------------------

#[test]
fn a_missing_record_is_unknown() {
    assert_eq!(machine_state(None, 1000.0, Some(5.0)), UNKNOWN);
}

#[test]
fn an_explicit_dead_flag_wins_over_a_fresh_bell() {
    let dead = record(Some(false), Some(999.0));
    assert_eq!(machine_state(Some(&dead), 1000.0, Some(5.0)), DEAD);
}

#[test]
fn alive_without_a_bell_is_unknown() {
    let no_bell = record(Some(true), None);
    assert_eq!(machine_state(Some(&no_bell), 1000.0, Some(5.0)), UNKNOWN);
}

#[test]
fn a_stale_bell_is_dead_and_a_fresh_one_is_alive() {
    let fresh = record(Some(true), Some(1000.0));
    assert_eq!(machine_state(Some(&fresh), 1000.0, Some(5.0)), ALIVE);
    assert_eq!(machine_state(Some(&fresh), 1301.0, Some(5.0)), DEAD);
    // Exactly at the window edge is still alive: the check is `>`.
    assert_eq!(machine_state(Some(&fresh), 1300.0, Some(5.0)), ALIVE);
}

#[test]
fn malformed_event_lines_are_counted_without_losing_the_good_ones() {
    let text = "{\"kind\":\"wake\",\"ts\":1}\nnot json\n{\"kind\":\"wake\",\"ts\":2}\n";
    let (events, malformed) = parse_event_lines(Some(text));
    assert_eq!(events.len(), 2);
    assert_eq!(malformed, 1);
    assert_eq!(events[1].ts, Some(2.0));
}

// --- boundaries ------------------------------------------------------------

#[test]
fn relay_timing_boundaries_are_inclusive() {
    assert!(validate_args(1, 0.0).is_ok());
    assert!(validate_args(1, 0.0001).is_ok());
}
