//! CB2-314/315 — os-misc public helpers at their documented edge inputs.
//!
//! The B24 helpers are the oddity-for-oddity port of `os/send.py`,
//! `os/watch.py` and `store.room_for_key`. Every assertion below is the
//! behaviour written in those functions: an empty basename becomes `blob`,
//! a duration with no unit is refused by name, and room keys round-trip.
use os_misc::b24::send::{
    parse_duration, parse_pomodoro_duration, parse_ttl, parse_when, sanitize_basename,
};
use os_misc::b24::transport::{bus_key, room_for_key};
use os_misc::b24::watch::validate_interval;

/* ---------- CB2-314: string helpers ---------- */

#[test]
fn misc_string_edges_basename() {
    // Empty input is not a blank name: the pointer still needs one.
    assert_eq!(sanitize_basename(""), "blob");
    assert_eq!(sanitize_basename("   "), "blob", "whitespace trims to empty");

    // Only the last path segment survives, and unsafe characters fold to `_`.
    assert_eq!(sanitize_basename("/tmp/a b.txt"), "a_b.txt");
    assert_eq!(sanitize_basename("dir/sub/file.bin"), "file.bin");
    assert_eq!(sanitize_basename("h\u{e9}llo"), "h_llo", "non-ascii is replaced, not dropped");

    // The cap is 60 characters, never an error.
    let long = sanitize_basename(&"a".repeat(120));
    assert_eq!(long.chars().count(), 60);
    assert!(long.chars().all(|c| c == 'a'));
}

#[test]
fn misc_string_edges_duration() {
    assert_eq!(parse_duration("30s").unwrap(), 30);
    assert_eq!(parse_duration("+10m").unwrap(), 600);
    assert_eq!(parse_duration("1d").unwrap(), 86_400);
    assert_eq!(parse_duration(" 2h ").unwrap(), 7_200, "surrounding space is trimmed");

    // No unit, unknown unit, and the empty string are all the same refusal,
    // and the message names the accepted shapes.
    for bad in ["", " ", "10", "10x", "s", "+"] {
        let err = parse_duration(bad).expect_err(bad);
        assert!(
            err.contains("not a duration (try 30s, 10m, 2h, 1d)"),
            "refusal names the shapes for {bad:?}: {err}",
        );
    }
}

#[test]
fn misc_string_edges_ttl() {
    // A TTL is a duration and nothing else: an ISO date is refused here even
    // though `--at` accepts one.
    assert_eq!(parse_ttl("10m").unwrap(), 600);
    let err = parse_ttl("2026-09-21").expect_err("a date is not a ttl");
    assert!(err.contains("--ttl needs a duration (30s, 10m, 2h, 1d)"), "{err}");
    assert!(err.contains("2026-09-21"), "the refused value is quoted: {err}");
}

#[test]
fn misc_string_edges_pomodoro() {
    assert_eq!(parse_pomodoro_duration("25m").unwrap(), 1_500);
    assert_eq!(parse_pomodoro_duration("1h30m").unwrap(), 5_400);
    assert_eq!(parse_pomodoro_duration("2h 15m").unwrap(), 8_100, "space between parts is allowed");
    assert_eq!(parse_pomodoro_duration("90s").unwrap(), 90);

    // Empty, unitless, zero and a bare unit are refused with the same message.
    for bad in ["", "  ", "25", "25x", "0m", "m"] {
        let err = parse_pomodoro_duration(bad).expect_err(bad);
        assert!(
            err.contains("not a pomodoro duration (try 25m, 1h30m, 90s)"),
            "refusal names the shapes for {bad:?}: {err}",
        );
    }
}

#[test]
fn misc_string_edges_room_keys() {
    // A room key round-trips; anything that is not a room key is no room,
    // never a guessed one.
    assert_eq!(bus_key(""), "muse-bus", "the empty room is the default list");
    assert_eq!(bus_key("main"), "muse-bus:room:main");
    assert_eq!(room_for_key("muse-bus:room:main"), "main");
    assert_eq!(room_for_key("muse-bus"), "");
    assert_eq!(room_for_key(""), "");
    assert_eq!(room_for_key("muse-bus:room:"), "", "an empty room name is empty");

    for room in ["main", "ops", "room:with:colons"] {
        assert_eq!(room_for_key(&bus_key(room)), room, "round-trip for {room}");
    }
}

/* ---------- CB2-315: numeric helpers at the boundaries ---------- */

#[test]
fn misc_numeric_bounds_zero() {
    // Zero is a valid duration and a valid absolute time; it is never
    // silently turned into "now".
    assert_eq!(parse_duration("0s").unwrap(), 0);
    assert_eq!(parse_duration("0d").unwrap(), 0);
    assert_eq!(parse_when("0", 1_700_000_000).unwrap(), 0);
    assert_eq!(
        parse_when("10s", 0).unwrap(),
        10,
        "a zero clock still advances by the duration",
    );
}

#[test]
fn misc_numeric_bounds_timestamps() {
    // The unix-timestamp branch is an i64 parse: its maximum is accepted and
    // one past it is refused, not wrapped.
    assert_eq!(parse_when("9223372036854775807", 0).unwrap(), i64::MAX);
    assert!(
        parse_when("9223372036854775808", 0).is_err(),
        "one past i64 is refused, never saturated",
    );

    // The ISO branch adds whole seconds only: the time of day is exactly the
    // offset from midnight, with no drift.
    let midnight = parse_when("2026-09-21", 0).unwrap();
    let afternoon = parse_when("2026-09-21T14:30", 0).unwrap();
    assert_eq!(afternoon - midnight, 14 * 3_600 + 30 * 60);
    let with_seconds = parse_when("2026-09-21T14:30:59", 0).unwrap();
    assert_eq!(with_seconds - afternoon, 59);

    // Out-of-range fields are refusals, not normalised dates.
    for bad in ["2026-13-01", "2026-09-32", "2026-09-21T24:00", "2026-09-21T14:60"] {
        assert!(parse_when(bad, 0).is_err(), "{bad} is refused");
    }
    assert!(parse_when("garbage!!", 0).is_err());
}

#[test]
fn misc_numeric_bounds_interval() {
    // The interval boundary is strict: zero and negative are the same refusal.
    assert!(validate_interval(0.5).is_ok());
    assert!(validate_interval(86_400.0).is_ok());
    assert!(validate_interval(f64::MIN_POSITIVE).is_ok(), "the smallest positive is accepted");
    assert_eq!(validate_interval(0.0).unwrap_err(), "interval must be positive");
    assert_eq!(validate_interval(-1.0).unwrap_err(), "interval must be positive");
    assert_eq!(
        validate_interval(-0.0).unwrap_err(),
        "interval must be positive",
        "negative zero is not positive either, and gives the same refusal",
    );
}
