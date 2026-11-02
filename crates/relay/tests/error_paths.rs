//! Every refusal and failure branch the crate documents, proved through the
//! public API. Refusal strings are the exact ones in `src/http.rs`.
//!
//! These are integration tests: no mocks, no network, no external crates.

use relay::http::Relay;
use relay::store::RoomStore;
use relay::validation::MAX_BODY_BYTES;
use std::path::PathBuf;

fn relay() -> Relay {
    Relay::with_viewer(None, Some(PathBuf::from("/nonexistent-viewer.html")))
}

fn json_call(relay: &mut Relay, method: &str, target: &str, body: &[u8]) -> (u16, String) {
    let (status, content_type, body) = relay.handle(method, target, body);
    assert_eq!(
        content_type, "application/json",
        "route {method} {target} answered {content_type}"
    );
    (status, body)
}

#[test]
fn invalid_room_names_are_refused_with_the_documented_message() {
    let mut relay = relay();
    let body = br#"{"nick":"pax","text":"x"}"#;
    let rooms = vec![
        "UPPER".to_string(),
        "with.dot".to_string(),
        "under_score".to_string(),
        "a".repeat(33),
        "bad%20room".to_string(), // decodes to "bad room"
    ];
    for room in rooms {
        let (status, raw) = json_call(
            &mut relay,
            "POST",
            &format!("/rooms/{room}/messages"),
            body,
        );
        assert_eq!(status, 400, "room {room} was accepted");
        assert!(
            raw.contains("room name must match [a-z0-9-]{1,32}"),
            "room {room} answered {raw}"
        );
    }
}

#[test]
fn a_malformed_percent_escape_is_a_500_not_a_400() {
    let mut relay = relay();
    let (status, raw) = json_call(&mut relay, "GET", "/rooms/%zz/messages", b"");
    assert_eq!(status, 500);
    assert!(
        raw.contains("invalid percent-encoding in room name"),
        "{raw}"
    );
}

#[test]
fn an_oversized_body_is_refused_before_parsing() {
    let mut relay = relay();
    let body = vec![b'x'; MAX_BODY_BYTES + 1];
    let (status, raw) = json_call(&mut relay, "POST", "/rooms/main/messages", &body);
    assert_eq!(status, 400);
    assert!(raw.contains("request body too large or unreadable"), "{raw}");
}

#[test]
fn a_body_that_is_not_a_json_object_is_refused() {
    let mut relay = relay();
    for body in [&b"not json"[..], &b""[..], &b"null"[..], &b"[]"[..]] {
        let (status, raw) = json_call(&mut relay, "POST", "/rooms/main/messages", body);
        assert_eq!(status, 400, "body {:?} was accepted", String::from_utf8_lossy(body));
        assert!(raw.contains("request body is not valid JSON"), "{raw}");
    }
}

#[test]
fn nick_refusals_name_the_nick_field() {
    let mut relay = relay();
    let too_long = "n".repeat(41);
    let bodies = vec![
        r#"{"text":"x"}"#.to_string(),                       // missing
        r#"{"nick":3,"text":"x"}"#.to_string(),              // non-string
        r#"{"nick":"","text":"x"}"#.to_string(),             // empty
        format!(r#"{{"nick":"{too_long}","text":"x"}}"#),    // 41 units
        r#"{"nick":"a\nb","text":"x"}"#.to_string(),         // newline
        r#"{"nick":"a\tb","text":"x"}"#.to_string(),         // tab
        r#"{"nick":"a\u007fb","text":"x"}"#.to_string(),     // DEL
    ];
    for body in bodies {
        let (status, raw) = json_call(&mut relay, "POST", "/rooms/main/messages", body.as_bytes());
        assert_eq!(status, 400, "accepted {body}");
        assert!(raw.contains("nick must be a single line"), "{body} -> {raw}");
    }
}

#[test]
fn text_refusals_name_the_text_field() {
    let mut relay = relay();
    let too_long = "t".repeat(2001);
    let bodies = vec![
        r#"{"nick":"pax"}"#.to_string(),
        r#"{"nick":"pax","text":7}"#.to_string(),
        r#"{"nick":"pax","text":""}"#.to_string(),
        format!(r#"{{"nick":"pax","text":"{too_long}"}}"#),
        r#"{"nick":"pax","text":"two\nlines"}"#.to_string(),
    ];
    for body in bodies {
        let (status, raw) = json_call(&mut relay, "POST", "/rooms/main/messages", body.as_bytes());
        assert_eq!(status, 400, "accepted {body}");
        assert!(raw.contains("text must be a single line"), "{body} -> {raw}");
    }
}

#[test]
fn notify_refuses_severity_topic_and_text_in_that_order() {
    let mut relay = relay();
    let cases = vec![
        (
            r#"{"severity":"loud","topic":"t","text":"x"}"#.to_string(),
            "severity must be one of",
        ),
        (
            r#"{"severity":"INFO","topic":"t","text":"x"}"#.to_string(),
            "severity must be one of",
        ),
        (
            r#"{"topic":"t","text":"x"}"#.to_string(),
            "severity must be one of",
        ),
        (
            r#"{"severity":"info","text":"x"}"#.to_string(),
            "topic must be a single line",
        ),
        (
            r#"{"severity":"info","topic":"","text":"x"}"#.to_string(),
            "topic must be a single line",
        ),
        (
            format!(
                r#"{{"severity":"info","topic":"{}","text":"x"}}"#,
                "p".repeat(65)
            ),
            "topic must be a single line",
        ),
        (
            r#"{"severity":"info","topic":"a\nb","text":"x"}"#.to_string(),
            "topic must be a single line",
        ),
        (
            r#"{"severity":"info","topic":"t"}"#.to_string(),
            "text must be a single line",
        ),
        (
            r#"{"severity":"info","topic":"t","text":""}"#.to_string(),
            "text must be a single line",
        ),
    ];
    for (body, want) in cases {
        let (status, raw) = json_call(&mut relay, "POST", "/rooms/main/notify", body.as_bytes());
        assert_eq!(status, 400, "accepted {body}");
        assert!(raw.contains(want), "{body} -> {raw}");
    }
}

#[test]
fn unknown_routes_and_wrong_methods_are_404_json() {
    let mut relay = relay();
    for (method, target) in [
        ("GET", "/nope"),
        ("PUT", "/rooms/main/messages"),
        ("POST", "/health"),
        ("DELETE", "/rooms/main/notify"),
    ] {
        let (status, raw) = json_call(&mut relay, method, target, b"");
        assert_eq!(status, 404, "{method} {target} was not a 404");
        assert!(raw.contains("not found"), "{method} {target} -> {raw}");
    }
}

#[test]
fn a_missing_viewer_is_500_plain_text_with_the_upstream_wording() {
    let mut relay = relay();
    let (status, content_type, body) = relay.handle("GET", "/", &[]);
    assert_eq!(status, 500);
    assert_eq!(content_type, "text/plain");
    assert_eq!(body, "viewer.html is missing beside relay.mjs");
}

#[test]
#[should_panic(expected = "failed to read store file")]
fn an_unreadable_store_file_panics_at_boot() {
    let dir = std::env::temp_dir();
    // A directory exists but cannot be read as a UTF-8 file: `with_file`
    // returns Err, and `Relay` turns that into the documented boot panic.
    let _ = Relay::with_viewer(Some(dir), Some(PathBuf::from("/nonexistent-viewer.html")));
}

#[test]
fn room_store_reports_the_unreadable_file_as_an_error() {
    let dir = std::env::temp_dir();
    assert!(RoomStore::with_file(dir).is_err());
}

#[test]
fn health_on_an_empty_relay_names_zero_rooms_and_the_memory_store() {
    let mut relay = relay();
    let (status, raw) = json_call(&mut relay, "GET", "/health", b"");
    assert_eq!(status, 200);
    assert!(raw.contains(r#""ok":true"#), "{raw}");
    assert!(raw.contains(r#""rooms":0"#), "{raw}");
    assert!(raw.contains(r#""store":"memory""#), "{raw}");
}
