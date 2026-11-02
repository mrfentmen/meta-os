//! B039 — the four named edge cases for `crates/os-memory`:
//! empty input, maximum input, duplicate input, out-of-order input.
//! Plus the boundary cases the store makes possible without changing
//! the API (unicode nick, journal-order reads, namespace separation).

use os_memory::{parse_json, read, read_all, write, write_shared, Entry, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn store_root(tag: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!(
        "os-memory-edge-{}-{}-{}",
        std::process::id(),
        tag,
        n
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("create temp root");
    dir
}

fn cleanup(dir: &Path) {
    let _ = fs::remove_dir_all(dir);
}

#[test]
fn b039_empty_input_empty_text_is_a_real_version_and_a_noop_after() {
    let dir = store_root("empty-text");
    let first = write(&dir, "pax", "empty.md", "", "", Some(1)).unwrap();
    assert_eq!(first.entry.version, 1);
    assert!(first.new_version);
    assert_eq!(first.entry.text, "");
    assert_eq!(first.entry.author, "unknown");

    let second = write(&dir, "pax", "empty.md", "", "", Some(2)).unwrap();
    assert_eq!(second.entry.version, 1);
    assert!(!second.new_version);

    let history = os_memory::history(&dir, "pax", "empty.md").unwrap();
    assert_eq!(history.len(), 1, "empty text is a real body, not a delete");

    let line = fs::read_to_string(dir.join("agents/pax/journal.jsonl")).unwrap();
    assert_eq!(line.lines().count(), 1);
    cleanup(&dir);
}

#[test]
fn b039_maximum_input_large_body_and_long_key_round_trip() {
    let dir = store_root("max");
    // 200 KiB body and a 240-byte key segment: large for an entry, small
    // enough that the test itself stays in the hundreds of MB rule.
    let body = "x".repeat(200 * 1024);
    let key = format!("{}md", "k".repeat(237));
    assert_eq!(key.len(), 239);

    let written = write(&dir, "pax", &key, &body, "pax", Some(7)).unwrap();
    assert_eq!(written.entry.text.len(), body.len());
    let back = read(&dir, "pax", &key, None).unwrap();
    assert_eq!(back.text, body);
    assert_eq!(back.key, key);

    // The journal line must reparse as one entry, not as many.
    let text = fs::read_to_string(dir.join("agents/pax/journal.jsonl")).unwrap();
    assert_eq!(text.lines().count(), 1);
    let parsed = parse_json(text.trim()).expect("journal line parses");
    assert_eq!(
        parsed.get("text").and_then(Value::as_str).map(str::len),
        Some(body.len())
    );
    cleanup(&dir);
}

#[test]
fn b039_duplicate_input_identical_write_appends_nothing() {
    let dir = store_root("dupe");
    let journal = dir.join("agents/pax/journal.jsonl");

    write(&dir, "pax", "k.md", "same", "", Some(1)).unwrap();
    let before = fs::read_to_string(&journal).unwrap();
    let outcome = write(&dir, "pax", "k.md", "same", "", Some(2)).unwrap();
    let after = fs::read_to_string(&journal).unwrap();

    assert!(!outcome.new_version);
    assert_eq!(outcome.entry.version, 1);
    assert_eq!(before, after, "a restatement must not touch the journal");
    assert_eq!(after.lines().count(), 1);
    cleanup(&dir);
}

#[test]
fn b039_out_of_order_input_reads_journal_order_not_version_order() {
    let dir = store_root("order");
    let journal_dir = dir.join("agents/pax");
    fs::create_dir_all(&journal_dir).unwrap();
    // Hand-written journal: versions 1, 3, 2 in that order. The store
    // never sorts by version; the latest is the last line.
    let lines = [
        r#"{"author": "pax", "key": "k.md", "text": "one", "ts": 1, "version": 1}"#,
        r#"{"author": "pax", "key": "k.md", "text": "three", "ts": 3, "version": 3}"#,
        r#"{"author": "pax", "key": "k.md", "text": "two", "ts": 2, "version": 2}"#,
    ]
    .join("\n")
        + "\n";
    fs::write(journal_dir.join("journal.jsonl"), lines).unwrap();

    assert_eq!(read(&dir, "pax", "k.md", None).unwrap().text, "two");
    assert_eq!(read(&dir, "pax", "k.md", Some(1)).unwrap().text, "one");
    assert_eq!(read(&dir, "pax", "k.md", Some(2)).unwrap().text, "three");
    assert_eq!(read(&dir, "pax", "k.md", Some(3)).unwrap().text, "two");
    let history = os_memory::history(&dir, "pax", "k.md").unwrap();
    assert_eq!(
        history.iter().map(|e| e.text.as_str()).collect::<Vec<_>>(),
        vec!["one", "three", "two"],
        "history is journal order, not version order"
    );

    // A new write takes the last line's version and adds one.
    let outcome = write(&dir, "pax", "k.md", "next", "", Some(4)).unwrap();
    assert_eq!(outcome.entry.version, 3);
    cleanup(&dir);
}

#[test]
fn b039_duplicate_json_keys_keep_the_first_like_python_dict_order() {
    let value = parse_json(r#"{"a": 1, "a": 2}"#).unwrap();
    assert_eq!(value.get("a"), Some(&Value::Int(1)));
}

#[test]
fn b039_unicode_agent_nick_is_alphanumeric_and_accepted() {
    let dir = store_root("unicode");
    // Python's str.isalnum accepts non-ASCII letters; Rust's
    // char::is_alphanumeric matches. The nick is still one segment.
    let outcome = write(&dir, "pax-é", "k.md", "x", "", Some(1)).unwrap();
    assert_eq!(outcome.entry.version, 1);
    assert_eq!(read(&dir, "pax-é", "k.md", None).unwrap().text, "x");
    cleanup(&dir);
}

#[test]
fn b039_agent_and_shared_namespaces_do_not_leak_into_each_other() {
    let dir = store_root("separate");
    write(&dir, "pax", "same.md", "agent", "", Some(1)).unwrap();
    write_shared(&dir, "same.md", "crew", "", Some(2)).unwrap();

    let all = read_all(&dir, "pax").unwrap();
    assert_eq!(all.own["same.md"].text, "agent");
    assert_eq!(all.shared["same.md"].text, "crew");
    assert_eq!(all.own.len(), 1);
    assert_eq!(all.shared.len(), 1);

    // Another agent does not see pax's key at all.
    let other = read_all(&dir, "milo").unwrap();
    assert!(other.own.is_empty());
    assert_eq!(other.shared["same.md"].text, "crew");
    cleanup(&dir);
}

#[test]
fn b039_extra_journal_fields_round_trip_through_the_typed_entry() {
    let dir = store_root("extra");
    let journal_dir = dir.join("agents/pax");
    fs::create_dir_all(&journal_dir).unwrap();
    fs::write(
        journal_dir.join("journal.jsonl"),
        r#"{"author": "pax", "key": "k.md", "note": "kept", "text": "x", "ts": 1, "version": 1}"#,
    )
    .unwrap();
    let entry: Entry = read(&dir, "pax", "k.md", None).unwrap();
    assert_eq!(entry.extra.len(), 1);
    assert_eq!(entry.extra[0].0, "note");
    assert_eq!(entry.extra[0].1, Value::Str("kept".to_string()));
    let line = entry.to_journal_line();
    assert!(line.contains(r#""note": "kept""#), "{line}");
    cleanup(&dir);
}

#[test]
fn b039_a_blank_journal_line_is_skipped_not_refused() {
    let dir = store_root("blank");
    let journal_dir = dir.join("agents/pax");
    fs::create_dir_all(&journal_dir).unwrap();
    fs::write(
        journal_dir.join("journal.jsonl"),
        "\n{\"author\": \"pax\", \"key\": \"k.md\", \"text\": \"x\", \"ts\": 1, \"version\": 1}\n\n",
    )
    .unwrap();
    assert_eq!(read(&dir, "pax", "k.md", None).unwrap().text, "x");
    cleanup(&dir);
}
