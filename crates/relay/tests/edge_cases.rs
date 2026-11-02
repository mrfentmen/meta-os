//! Edge cases named the way the task asks: empty, maximum, duplicate,
//! out-of-order. One test per case, plus the sub-case that belongs to it.

use relay::http::Relay;
use relay::validation::MAX_BODY_BYTES;
use std::path::PathBuf;

fn new_relay() -> Relay {
    Relay::with_viewer(None, Some(PathBuf::from("/nonexistent-viewer.html")))
}

fn status_and_body(relay: &mut Relay, method: &str, target: &str, body: &[u8]) -> (u16, String) {
    let (status, content_type, body) = relay.handle(method, target, body);
    assert_eq!(content_type, "application/json", "{method} {target}");
    (status, body)
}

fn id_of(body: &str) -> String {
    let start = body.find("\"id\":\"").expect("response carries an id") + 6;
    body[start..].split('"').next().unwrap().to_string()
}

#[test]
fn empty_inputs_are_answered_not_crashed() {
    let mut relay = new_relay();

    // Empty POST body: a 400 with the JSON refusal.
    let (status, raw) = status_and_body(&mut relay, "POST", "/rooms/main/messages", b"");
    assert_eq!(status, 400);
    assert!(raw.contains("not valid JSON"), "{raw}");

    // No lines yet: total 0, empty array.
    let (status, raw) = status_and_body(&mut relay, "GET", "/rooms/main/messages", b"");
    assert_eq!(status, 200);
    assert!(raw.contains(r#""total":0"#), "{raw}");
    assert!(raw.contains(r#""messages":[]"#), "{raw}");

    // An empty room segment is not a room route: parts are [rooms, messages].
    let (status, raw) = status_and_body(&mut relay, "GET", "/rooms//messages", b"");
    assert_eq!(status, 404);
    assert!(raw.contains("not found"), "{raw}");

    // `/health` on a brand-new relay.
    let (status, raw) = status_and_body(&mut relay, "GET", "/health", b"");
    assert_eq!(status, 200);
    assert!(raw.contains(r#""rooms":0"#), "{raw}");
}

#[test]
fn maximum_lengths_are_accepted_at_the_cap() {
    let mut relay = new_relay();
    let room = "a".repeat(32);
    let nick = "n".repeat(40);
    let text = "t".repeat(2000);
    let body = format!(r#"{{"nick":"{nick}","text":"{text}"}}"#);
    let (status, raw) = status_and_body(
        &mut relay,
        "POST",
        &format!("/rooms/{room}/messages"),
        body.as_bytes(),
    );
    assert_eq!(status, 201, "32/40/2000 should be inside the caps: {raw}");
    assert!(raw.contains(r#""index":0"#), "{raw}");

    let topic = "p".repeat(64);
    let notify = format!(r#"{{"severity":"info","topic":"{topic}","text":"{text}"}}"#);
    let (status, raw) =
        status_and_body(&mut relay, "POST", &format!("/rooms/{room}/notify"), notify.as_bytes());
    assert_eq!(status, 201, "64/2000 should be inside the notify caps: {raw}");
    assert!(raw.contains(r#""index":1"#), "{raw}");
}

#[test]
fn an_exactly_maximum_body_is_not_an_oversized_body() {
    let mut relay = new_relay();
    let empty = r#"{"nick":"n","text":"t","pad":""}"#;
    let pad_len = MAX_BODY_BYTES - empty.len();
    let body = format!(
        r#"{{"nick":"n","text":"t","pad":"{}"}}"#,
        "p".repeat(pad_len)
    );
    assert_eq!(body.len(), MAX_BODY_BYTES);
    let (status, raw) = status_and_body(&mut relay, "POST", "/rooms/main/messages", body.as_bytes());
    assert_eq!(status, 201, "the cap is inclusive: {raw}");

    let mut over = body.clone();
    over.push(' ');
    let (status, raw) = status_and_body(&mut relay, "POST", "/rooms/main/messages", over.as_bytes());
    assert_eq!(status, 400, "one byte over must refuse: {raw}");
}

#[test]
fn duplicate_notify_payloads_keep_one_id_and_two_indices() {
    let mut relay = new_relay();
    let payload =
        br#"{"severity":"info","topic":"trio-result","text":"same payload"}"#;

    let (status, first) = status_and_body(&mut relay, "POST", "/rooms/main/notify", payload);
    assert_eq!(status, 201);
    let (status, second) = status_and_body(&mut relay, "POST", "/rooms/main/notify", payload);
    assert_eq!(status, 201);

    assert!(first.contains(r#""index":0"#), "{first}");
    assert!(second.contains(r#""index":1"#), "{second}");
    assert_eq!(id_of(&first), id_of(&second), "same basis must hash the same");

    let (_, lines) = status_and_body(&mut relay, "GET", "/rooms/main/messages", b"");
    assert!(lines.contains(r#""total":2"#), "{lines}");
}

#[test]
fn duplicate_json_keys_follow_last_one_wins() {
    let mut relay = new_relay();
    let body = r#"{"nick":"first","nick":"second","text":"x"}"#;
    let (status, raw) = status_and_body(&mut relay, "POST", "/rooms/main/messages", body.as_bytes());
    assert_eq!(status, 201, "{raw}");
    let (_, lines) = status_and_body(&mut relay, "GET", "/rooms/main/messages", b"");
    assert!(lines.contains("second: x [ts:"), "{lines}");
    assert!(!lines.contains("first: x"), "{lines}");
}

#[test]
fn out_of_order_watermarks_are_clamped_and_first_since_wins() {
    let mut relay = new_relay();
    status_and_body(
        &mut relay,
        "POST",
        "/rooms/main/messages",
        br#"{"nick":"pax","text":"only line"}"#,
    );

    // Ahead of the room: caught up, but total still reports the room.
    let (status, ahead) =
        status_and_body(&mut relay, "GET", "/rooms/main/messages?since=999", b"");
    assert_eq!(status, 200);
    assert!(ahead.contains(r#""total":1"#), "{ahead}");
    assert!(ahead.contains(r#""messages":[]"#), "{ahead}");

    // Below the floor: the whole room.
    let (_, below) =
        status_and_body(&mut relay, "GET", "/rooms/main/messages?since=-99", b"");
    assert!(below.contains("only line"), "{below}");

    // At the last index: empty.
    let (_, at) = status_and_body(&mut relay, "GET", "/rooms/main/messages?since=0", b"");
    assert!(at.contains(r#""messages":[]"#), "{at}");

    // Duplicate query params: the first one is read, like URLSearchParams.get.
    let (_, dup) =
        status_and_body(&mut relay, "GET", "/rooms/main/messages?since=0&since=5", b"");
    assert!(dup.contains(r#""messages":[]"#), "{dup}");

    // parseInt's leading-digit prefix, and NaN's whole-room fallback.
    let (_, prefix) =
        status_and_body(&mut relay, "GET", "/rooms/main/messages?since=3abc", b"");
    assert!(prefix.contains(r#""messages":[]"#), "{prefix}");
    let (_, nan) = status_and_body(&mut relay, "GET", "/rooms/main/messages?since=abc", b"");
    assert!(nan.contains("only line"), "{nan}");
}

#[test]
fn a_get_before_any_post_is_an_honest_empty_room() {
    let mut relay = new_relay();
    let (status, raw) =
        status_and_body(&mut relay, "GET", "/rooms/never-used/messages?since=-1", b"");
    assert_eq!(status, 200);
    assert!(raw.contains(r#""room":"never-used""#), "{raw}");
    assert!(raw.contains(r#""total":0"#), "{raw}");
    assert!(raw.contains(r#""messages":[]"#), "{raw}");
}
