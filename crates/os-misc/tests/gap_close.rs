//! B215 — test-gap close.
//!
//! The module with the fewest tests was `b24::transport` (zero direct
//! tests). `b27::par_clock` is the crate's best-covered module at 7
//! tests, so this file brings transport to the same depth: the
//! constants, both key mappers, and all three default trait methods.

use os_misc::b24::transport::{bus_key, room_for_key, BusTransport, MAX_TEXT};

struct Bare;
impl BusTransport for Bare {
    fn bus_get(&self, _seen: i64, _key: &str) -> Result<Vec<String>, String> {
        Ok(vec![])
    }
}

#[test]
fn max_text_is_the_relay_common_value() {
    assert_eq!(MAX_TEXT, 2000);
}

#[test]
fn room_for_key_extracts_a_room_name() {
    assert_eq!(room_for_key("muse-bus:room:news"), "news");
    assert_eq!(room_for_key("muse-bus:room:build-x"), "build-x");
}

#[test]
fn room_for_key_treats_the_default_list_as_no_room() {
    assert_eq!(room_for_key("muse-bus"), "");
    assert_eq!(room_for_key("some-other-key"), "");
}

#[test]
fn bus_key_round_trips_the_default_and_a_room() {
    assert_eq!(bus_key(""), "muse-bus");
    assert_eq!(bus_key("news"), "muse-bus:room:news");
    assert_eq!(room_for_key(&bus_key("news")), "news");
}

#[test]
fn own_prefixes_defaults_to_the_canonical_nick_only() {
    assert_eq!(Bare.own_prefixes("milo"), vec!["milo".to_string()]);
}

#[test]
fn presence_beat_default_succeeds() {
    assert!(Bare.presence_beat("muse-bus").is_ok());
}

#[test]
fn mark_seen_default_succeeds() {
    assert!(Bare.mark_seen("muse-bus", "milo", 7).is_ok());
}
