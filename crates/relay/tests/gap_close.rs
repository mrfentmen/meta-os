//! B191 — the `json` module had the fewest tests (3, tied with `sha256`),
//! while `http` carries 10. These cases take the store's parser/serializer
//! past that depth without touching production code.

use relay::json::{escape, parse_record, record_line};

#[test]
fn escape_uses_the_named_control_sequences() {
    assert_eq!(escape("\u{0}"), "\\u0000");
    assert_eq!(escape("\u{1}"), "\\u0001");
    assert_eq!(escape("\u{8}"), "\\b");
    assert_eq!(escape("\t"), "\\t");
    assert_eq!(escape("\n"), "\\n");
    assert_eq!(escape("\u{c}"), "\\f");
    assert_eq!(escape("\r"), "\\r");
    assert_eq!(escape("\u{1f}"), "\\u001f");
    // All in one string, in order.
    assert_eq!(
        escape("\u{0}\u{1}\u{8}\t\n\u{c}\r\u{1f}"),
        "\\u0000\\u0001\\b\\t\\n\\f\\r\\u001f"
    );
}

#[test]
fn escape_leaves_del_and_everything_above_it_alone() {
    // JSON.stringify escapes only U+0000–U+001F; DEL and U+0080–U+009F pass.
    assert_eq!(escape("\u{7f}"), "\u{7f}");
    assert_eq!(escape("\u{80}\u{9f}"), "\u{80}\u{9f}");
}

#[test]
fn escape_handles_quotes_backslashes_and_unicode() {
    assert_eq!(escape("a\"b\\c"), "a\\\"b\\\\c");
    assert_eq!(escape("héllo 😀"), "héllo 😀");
    assert_eq!(escape("/slash/"), "/slash/");
}

#[test]
fn record_line_round_trips_every_hostile_character() {
    let line = "pax: say \"hi\" \\ back\nnext\ttab 😀 [ts:1]";
    let raw = record_line("main", line);
    assert_eq!(
        parse_record(&raw),
        Some(("main".to_string(), line.to_string())),
        "raw record was {raw}"
    );
}

#[test]
fn parse_ignores_extra_fields_including_nested_ones() {
    let raw = r#"{"room":"r","meta":{"a":[1,2,{"b":true}]},"line":"l","n":null}"#;
    assert_eq!(parse_record(raw), Some(("r".to_string(), "l".to_string())));
}

#[test]
fn parse_rejects_every_shape_that_is_not_a_room_line_object() {
    for raw in [
        r#"["r","l"]"#,
        r#""r""#,
        r#"{"room":"r"}"#,
        r#"{"line":"l"}"#,
        r#"{"room":3,"line":"x"}"#,
        r#"{"room":"r","line":3}"#,
        r#"{"room":"r","line":"l"} trailing"#,
        "",
        "{",
    ] {
        assert_eq!(parse_record(raw), None, "accepted {raw}");
    }
}

#[test]
fn parse_decodes_unicode_escapes_and_surrogate_pairs() {
    let raw = r#"{"room":"r","line":"a\u0041\uD83D\uDE00"}"#;
    assert_eq!(
        parse_record(raw),
        Some(("r".to_string(), "aA😀".to_string()))
    );
}

#[test]
fn parse_rejects_lone_surrogates() {
    assert_eq!(parse_record(r#"{"room":"r","line":"\uD800"}"#), None);
    assert_eq!(parse_record(r#"{"room":"r","line":"\uDC00"}"#), None);
    assert_eq!(
        parse_record(r#"{"room":"r","line":"\uD800\u0041"}"#),
        None
    );
}

#[test]
fn parse_duplicate_keys_last_one_wins() {
    let raw = r#"{"room":"a","room":"b","line":"x"}"#;
    assert_eq!(parse_record(raw), Some(("b".to_string(), "x".to_string())));
}

#[test]
fn parse_tolerates_whitespace_between_tokens() {
    let raw = "  { \"room\" : \"r\" , \"line\" : \"l\" }  ";
    assert_eq!(parse_record(raw), Some(("r".to_string(), "l".to_string())));
}
