//! B047 — test-gap close: the JSON value/parser/serializer section.
//!
//! Measured before writing: the crate's `#[cfg(test)]` module covers the
//! store, CLI, bake files, and memory-depth code, but has no direct test
//! for `parse_json`, `write_json`, or `to_json_sorted`; those were only
//! exercised indirectly. This file gives the JSON section the same kind
//! of coverage the store section already has.

use os_memory::{parse_json, to_json_sorted, write_json, Value};

fn value(text: &str) -> Value {
    parse_json(text).unwrap_or_else(|err| panic!("parse {text:?}: {err}"))
}

fn render(v: &Value) -> String {
    let mut out = String::new();
    write_json(v, &mut out);
    out
}

#[test]
fn gap_json_parses_every_scalar_shape() {
    assert_eq!(value("null"), Value::Null);
    assert_eq!(value("true"), Value::Bool(true));
    assert_eq!(value("false"), Value::Bool(false));
    assert_eq!(value("0"), Value::Int(0));
    assert_eq!(value("-42"), Value::Int(-42));
    assert_eq!(value("1.5"), Value::Float(1.5));
    assert_eq!(value("1e3"), Value::Float(1000.0));
    assert_eq!(value("\"\""), Value::Str(String::new()));
    assert_eq!(value("\"x\""), Value::Str("x".to_string()));
}

#[test]
fn gap_json_big_integer_falls_back_to_float_like_the_port_says() {
    // lib.rs:226-235: an integer too large for i64 parses as Float.
    match value("9223372036854775808") {
        Value::Float(_) => {}
        other => panic!("expected Float for an i64 overflow, got {other:?}"),
    }
    assert_eq!(
        value("9223372036854775807"),
        Value::Int(9223372036854775807)
    );
}

#[test]
fn gap_json_strings_decode_short_escapes_and_surrogate_pairs() {
    assert_eq!(
        value(r#""a\nb\tc\"d\\e""#),
        Value::Str("a\nb\tc\"d\\e".to_string())
    );
    assert_eq!(value(r#""\u00e9""#), Value::Str("é".to_string()));
    assert_eq!(
        value(r#""\ud83d\ude00""#),
        Value::Str("😀".to_string()),
        "a valid surrogate pair decodes to one scalar"
    );
    assert!(parse_json(r#""\ud83d""#).is_err(), "lone high surrogate");
    assert!(parse_json(r#""\ude00""#).is_err(), "lone low surrogate");
    assert!(parse_json("\"\u{0001}\"").is_err(), "raw control character");
}

#[test]
fn gap_json_objects_keep_order_and_get_returns_the_first_duplicate() {
    let v = value(r#"{"b": 1, "a": 2, "b": 3}"#);
    match &v {
        Value::Map(members) => {
            let keys: Vec<&str> = members.iter().map(|(k, _)| k.as_str()).collect();
            assert_eq!(keys, vec!["b", "a", "b"]);
        }
        other => panic!("expected a map, got {other:?}"),
    }
    assert_eq!(v.get("b"), Some(&Value::Int(1)));
    assert_eq!(v.get("missing"), None);
}

#[test]
fn gap_json_parser_refuses_empty_trailing_and_unterminated_input() {
    for bad in ["", " ", "{} x", "[1,", "{\"a\":}", "\"unterminated"] {
        assert!(parse_json(bad).is_err(), "accepted {bad:?}");
    }
}

#[test]
fn gap_json_writer_preserves_insertion_order_while_sorted_sorts() {
    let v = Value::Map(vec![
        ("b".to_string(), Value::Int(1)),
        ("a".to_string(), Value::Int(2)),
    ]);
    assert_eq!(render(&v), r#"{"b": 1, "a": 2}"#);
    assert_eq!(to_json_sorted(&v), r#"{"a": 2, "b": 1}"#);

    let nested = Value::Map(vec![(
        "z".to_string(),
        Value::Map(vec![
            ("d".to_string(), Value::Int(4)),
            ("c".to_string(), Value::Int(3)),
        ]),
    )]);
    assert_eq!(to_json_sorted(&nested), r#"{"z": {"c": 3, "d": 4}}"#);
}

#[test]
fn gap_json_writer_escapes_non_ascii_and_control_characters() {
    assert_eq!(render(&Value::Str("é".to_string())), r#""\u00e9""#);
    assert_eq!(
        render(&Value::Str("😀".to_string())),
        r#""\ud83d\ude00""#
    );
    assert_eq!(
        render(&Value::Str("\u{0001}".to_string())),
        r#""\u0001""#
    );
    assert_eq!(render(&Value::Str("\n\t\r".to_string())), r#""\n\t\r""#);
}

#[test]
fn gap_json_writer_formats_floats_like_json_dumps() {
    assert_eq!(render(&Value::Float(1.0)), "1.0");
    assert_eq!(render(&Value::Float(1.5)), "1.5");
    assert_eq!(render(&Value::Float(-0.25)), "-0.25");
}

#[test]
fn gap_json_lists_and_empty_containers_round_trip() {
    for text in ["[]", "{}", "[1, [2, 3], {\"a\": null}]"] {
        let parsed = value(text);
        let rendered = render(&parsed);
        let reparsed = parse_json(&rendered).expect("rendered output parses");
        assert_eq!(reparsed, parsed, "round trip for {text}");
    }
}

#[test]
fn gap_json_leading_zero_is_accepted_by_this_parser() {
    // Real behaviour, recorded rather than desired: parse_number consumes
    // the digit run and Rust's i64 parser accepts a leading zero, while
    // Python's json.loads refuses "01". Listed in os-memory-gaps.md.
    assert_eq!(value("01"), Value::Int(1));
}

#[test]
fn gap_json_render_then_parse_keeps_unicode_text() {
    let original = Value::Str("café 😀 — plain".to_string());
    let rendered = render(&original);
    assert_eq!(parse_json(&rendered).unwrap(), original);
}
