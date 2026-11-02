//! B179 — close the thinnest-tested module's gap.
//!
//! `b09_core::ingest` carried one test; `b10_brief::brief` carries ten,
//! the crate's best-covered module. These nine cases bring `ingest` to
//! the same depth without editing `src/`.
//!
//! The assertions encode the code as written: empty ids and duplicate
//! ids are skipped, a missing cursor starts at page 0, a cursor on the
//! last entry returns nothing, and a page stops at `PAGE`.

use intel::b09_core::ingest::{
    messages_from_cursor, snapshot, store_messages, Message, SnapshotView, PAGE,
};

fn msg(id: &str) -> Message {
    Message {
        id: id.to_string(),
        room: "main".to_string(),
        ts: 0,
        body: "b".to_string(),
    }
}

fn ids(view: &SnapshotView) -> Vec<String> {
    view.messages.iter().map(|m| m.id.clone()).collect()
}

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|s| s.to_string()).collect()
}

#[test]
fn empty_store_is_an_empty_snapshot() {
    let view = messages_from_cursor(&[], None);
    assert!(view.messages.is_empty());
    assert_eq!(view.cursor, None);
    assert_eq!(snapshot(&[]), "snapshot: 0 messages");
}

#[test]
fn cursor_not_found_starts_at_the_first_message() {
    let store = vec![msg("m0"), msg("m1"), msg("m2")];
    let view = messages_from_cursor(&store, Some("gone"));
    assert_eq!(ids(&view), strings(&["m0", "m1", "m2"]));
    assert_eq!(view.cursor.as_deref(), Some("m2"));
}

#[test]
fn cursor_on_last_message_returns_nothing() {
    let store = vec![msg("m0"), msg("m1")];
    let view = messages_from_cursor(&store, Some("m1"));
    assert!(view.messages.is_empty());
    assert_eq!(view.cursor, None);
}

#[test]
fn page_caps_at_page_size() {
    let store: Vec<Message> = (0..=PAGE).map(|i| msg(&format!("m{i}"))).collect();
    let view = messages_from_cursor(&store, None);
    assert_eq!(view.messages.len(), PAGE);
    assert_eq!(view.cursor, Some(format!("m{}", PAGE - 1)));
    assert_eq!(snapshot(&store), format!("snapshot: {} messages", PAGE + 1));
}

#[test]
fn duplicate_ids_are_not_stored() {
    let mut store = Vec::new();
    assert_eq!(store_messages(&mut store, vec![msg("a"), msg("b")]), 2);
    assert_eq!(store_messages(&mut store, vec![msg("a"), msg("b")]), 0);
    assert_eq!(store.len(), 2);
}

#[test]
fn empty_ids_are_skipped() {
    let mut store = Vec::new();
    assert_eq!(store_messages(&mut store, vec![msg(""), msg("a")]), 1);
    assert_eq!(ids(&messages_from_cursor(&store, None)), strings(&["a"]));
}

#[test]
fn store_reports_only_newly_added_messages() {
    let mut store = Vec::new();
    assert_eq!(store_messages(&mut store, vec![msg("a")]), 1);
    assert_eq!(
        store_messages(&mut store, vec![msg("a"), msg("b"), msg("c")]),
        2
    );
    assert_eq!(
        ids(&messages_from_cursor(&store, None)),
        strings(&["a", "b", "c"])
    );
}

#[test]
fn order_is_append_order_and_cursor_is_the_last_id() {
    let mut store = Vec::new();
    store_messages(&mut store, vec![msg("z"), msg("a"), msg("m")]);
    let view = messages_from_cursor(&store, None);
    assert_eq!(ids(&view), strings(&["z", "a", "m"]));
    assert_eq!(view.cursor.as_deref(), Some("m"));
}

#[test]
fn paging_continues_from_the_returned_cursor() {
    let store: Vec<Message> = (0..=PAGE).map(|i| msg(&format!("m{i}"))).collect();
    let first = messages_from_cursor(&store, None);
    let second = messages_from_cursor(&store, first.cursor.as_deref());
    assert_eq!(second.messages.len(), 1);
    assert_eq!(ids(&second), vec![format!("m{}", PAGE)]);
    assert_eq!(second.cursor, Some(format!("m{}", PAGE)));
}
