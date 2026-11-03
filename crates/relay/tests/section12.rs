use relay::http::Relay;
use relay::notify::{message_line, parse_message_line};
use relay::store::RoomStore;
use std::path::PathBuf;

fn relay() -> Relay {
    Relay::with_viewer(None, Some(PathBuf::from("/nonexistent-viewer.html")))
}

#[test]
fn message_empty_body() {
    let mut r = relay();
    let (status, _, body) = r.handle("POST", "/rooms/main/messages", b"");
    assert_eq!(status, 400);
    assert!(body.contains("not valid JSON"));
}

#[test]
fn nick_first_colon_split() {
    let line = message_line("pa:x", "hello: world", 9);
    assert_eq!(parse_message_line(&line), Some(("pa".to_string(), "x: hello: world".to_string(), 9)));
}

#[test]
fn read_append_order() {
    let mut s = RoomStore::memory();
    for i in 0..10 {
        s.append("main", &message_line("pax", &format!("m{i}"), i));
    }
    let texts: Vec<String> = s.messages("main").iter().map(|l| parse_message_line(l).unwrap().1).collect();
    assert_eq!(texts, (0..10).map(|i| format!("m{i}")).collect::<Vec<_>>());
}

#[test]
fn cursor_beyond_end() {
    let mut s = RoomStore::memory();
    s.append("main", &message_line("pax", "only", 1));
    assert!(s.messages_since("main", 99).is_empty());
}

#[test]
fn room_isolation() {
    let mut s = RoomStore::memory();
    s.append("a", &message_line("pax", "a-only", 1));
    assert_eq!(s.messages("b").len(), 0);
}

#[test]
fn trim_oldest_first() {
    let mut s = RoomStore::with_max_lines(3);
    for i in 0..5 {
        s.append("main", &message_line("pax", &format!("m{i}"), i));
    }
    let texts: Vec<String> = s.messages("main").iter().map(|l| parse_message_line(l).unwrap().1).collect();
    assert_eq!(texts, vec!["m2", "m3", "m4"]);
}

#[test]
fn timestamps_monotonic() {
    let mut s = RoomStore::memory();
    for i in 0..5 {
        s.append("main", &message_line("pax", "x", 10 + i));
    }
    let stamps: Vec<u64> = s.messages("main").iter().map(|l| parse_message_line(l).unwrap().2).collect();
    assert!(stamps.windows(2).all(|w| w[0] <= w[1]));
}
