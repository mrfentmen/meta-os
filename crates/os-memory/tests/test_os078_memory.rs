//! Parity tests for `os/tests/test_os078_memory.py` (store half).
//!
//! Journaled, versioned store with per-agent and shared namespaces,
//! no-op identical rewrites, escaping validation, corrupt-journal
//! loudness, sorted listings, mount paths, idempotent ensure, and
//! the CLI shapes (read/ensure + MEMORY_ERROR refusal). Bake pins
//! live in [`os_memory::bake`]; CLI-subprocess equivalence is
//! covered by calling the same [`os_memory::memory::cli`] entry the
//! binary would.

use os_memory::memory::*;
use std::path::PathBuf;

fn tmp_root(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-memory-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir.join("memory")
}

fn text(entry: &Entry, key: &str) -> String {
    entry
        .get(key)
        .and_then(|v| {
            v.as_str()
                .map(|s| s.to_string())
                .or_else(|| v.as_i64().map(|n| n.to_string()))
        })
        .unwrap_or_default()
}

#[test]
fn write_and_read_round_trip() {
    let root = tmp_root("roundtrip");
    let record = write(&root, "pax", "decisions/router.md", "Router is the queue, not the chat.", "pax", Some(1000)).unwrap();
    assert_eq!(text(&record, "version"), "1");
    assert_eq!(record["new_version"], serde_json::json!(true));
    assert_eq!(text(&record, "author"), "pax");
    assert_eq!(text(&record, "ts"), "1000");
    let back = read(&root, "pax", "decisions/router.md", None).unwrap();
    assert_eq!(text(&back, "text"), "Router is the queue, not the chat.");
    assert_eq!(text(&back, "version"), "1");
}

#[test]
fn versions_increment_and_versioned_read() {
    let root = tmp_root("versions");
    write(&root, "pax", "note.txt", "one", "", Some(1)).unwrap();
    write(&root, "pax", "note.txt", "two", "", Some(2)).unwrap();
    let record = write(&root, "pax", "note.txt", "three", "", Some(3)).unwrap();
    assert_eq!(text(&record, "version"), "3");
    assert_eq!(text(&read(&root, "pax", "note.txt", Some(1)).unwrap(), "text"), "one");
    assert_eq!(text(&read(&root, "pax", "note.txt", Some(2)).unwrap(), "text"), "two");
    assert_eq!(text(&read(&root, "pax", "note.txt", None).unwrap(), "text"), "three");
    let hist = history(&root, "pax", "note.txt").unwrap();
    assert_eq!(
        hist.iter().map(|e| text(e, "version")).collect::<Vec<_>>(),
        vec!["1", "2", "3"]
    );
    assert_eq!(
        hist.iter().map(|e| text(e, "text")).collect::<Vec<_>>(),
        vec!["one", "two", "three"]
    );
}

#[test]
fn identical_rewrite_is_a_noop() {
    let root = tmp_root("noop");
    write(&root, "milo", "k.md", "same", "", Some(1)).unwrap();
    let journal = root.join("agents/milo/journal.jsonl");
    let before = std::fs::read_to_string(&journal).unwrap();
    let record = write(&root, "milo", "k.md", "same", "", Some(2)).unwrap();
    assert_eq!(text(&record, "version"), "1");
    assert_eq!(record["new_version"], serde_json::json!(false));
    assert_eq!(std::fs::read_to_string(&journal).unwrap(), before);
}

#[test]
fn shared_namespace_versions_independently() {
    let root = tmp_root("shared");
    write(&root, "pax", "settled.md", "agent view", "", Some(1)).unwrap();
    write_shared(&root, "settled.md", "crew view", "", Some(2)).unwrap();
    write_shared(&root, "settled.md", "crew view v2", "", Some(3)).unwrap();
    assert_eq!(text(&read(&root, "pax", "settled.md", None).unwrap(), "text"), "agent view");
    assert_eq!(text(&read_shared(&root, "settled.md", None).unwrap(), "text"), "crew view v2");
    assert_eq!(text(&read_shared(&root, "settled.md", Some(1)).unwrap(), "text"), "crew view");
    let (own, shared) = read_all(&root, "pax").unwrap();
    assert_eq!(text(&own["settled.md"], "text"), "agent view");
    assert_eq!(text(&shared["settled.md"], "text"), "crew view v2");
}

#[test]
fn shared_identical_rewrite_is_a_noop() {
    let root = tmp_root("shared-noop");
    write_shared(&root, "s.md", "once", "", Some(1)).unwrap();
    let record = write_shared(&root, "s.md", "once", "", Some(2)).unwrap();
    assert_eq!(text(&record, "version"), "1");
    assert_eq!(record["new_version"], serde_json::json!(false));
    assert_eq!(history_shared(&root, "s.md").unwrap().len(), 1);
}

#[test]
fn key_validation_refuses_escape() {
    let root = tmp_root("keyval");
    let mut bad_keys: Vec<String> = ["../escape", "/absolute", "a//b", "a/./b", "a/../b",
                         "a\\b", ""]
        .iter()
        .map(|s| s.to_string())
        .collect();
    bad_keys.push(format!("a{}b", char::from(0)));
    for bad in &bad_keys {
        assert!(write(&root, "pax", bad, "x", "", None).is_err(), "{bad:?}");
        assert!(write_shared(&root, bad, "x", "", None).is_err(), "{bad:?}");
    }
}

#[test]
fn agent_validation_refuses_slash() {
    let root = tmp_root("agentval");
    for bad in ["a/b", ".", "..", "", "a\\b"] {
        assert!(write(&root, bad, "k.md", "x", "", None).is_err(), "{bad:?}");
    }
}

#[test]
fn missing_key_and_bad_version_raise_never_guess() {
    let root = tmp_root("missing");
    assert!(read(&root, "pax", "nope.md", None).is_err());
    assert!(read_shared(&root, "nope.md", None).is_err());
    write(&root, "pax", "k.md", "v1", "", Some(1)).unwrap();
    assert!(read(&root, "pax", "k.md", Some(2)).is_err());
    assert!(read(&root, "pax", "k.md", Some(0)).is_err());
}

#[test]
fn corrupt_journal_line_raises() {
    let root = tmp_root("corrupt");
    write(&root, "pax", "k.md", "good", "", Some(1)).unwrap();
    let journal = root.join("agents/pax/journal.jsonl");
    {
        use std::io::Write;
        let mut f = std::fs::OpenOptions::new().append(true).open(&journal).unwrap();
        f.write_all(b"this is not json\n").unwrap();
    }
    let err = read(&root, "pax", "k.md", None).unwrap_err();
    assert!(err.to_string().contains("does not parse"), "{err}");
    // A journal whose only bad line is a shape mismatch raises the
    // shape error instead.
    std::fs::write(&journal, "{\"key\": \"k.md\"}\n").unwrap();
    let err = read(&root, "pax", "k.md", None).unwrap_err();
    assert!(err.to_string().contains("unexpected shape"), "{err}");
}

#[test]
fn list_keys_sorted_and_shared_separate() {
    let root = tmp_root("list");
    write(&root, "hana", "b.md", "b", "", Some(1)).unwrap();
    write(&root, "hana", "a.md", "a", "", Some(2)).unwrap();
    write_shared(&root, "z.md", "z", "", Some(3)).unwrap();
    let own = list_keys(&root, "hana").unwrap();
    assert_eq!(own.keys().cloned().collect::<Vec<_>>(), vec!["a.md", "b.md"]);
    let shared = list_shared_keys(&root).unwrap();
    assert_eq!(shared.keys().cloned().collect::<Vec<_>>(), vec!["z.md"]);
    assert!(!own.contains_key("z.md"));
}

#[test]
fn mount_paths_name_own_and_shared() {
    let root = tmp_root("mount");
    let (own, shared) = mount_paths(&root, "rowan").unwrap();
    assert_eq!(own, root.join("agents/rowan"));
    assert_eq!(shared, root.join("shared"));
}

#[test]
fn ensure_root_creates_namespaces_idempotently() {
    let root = tmp_root("ensure");
    let (agents, shared) = ensure_root(&root).unwrap();
    assert!(agents.is_dir());
    assert!(shared.is_dir());
    assert_eq!(ensure_root(&root).unwrap(), (agents, shared));
}

#[test]
fn cli_read_and_ensure_and_refusal() {
    let root = tmp_root("cli");
    let root_s = root.to_string_lossy().into_owned();
    write(&root, "pax", "decisions/x.md", "kept", "", Some(42)).unwrap();
    // CLI read round trip (the subprocess half runs the same entry).
    let (code, out, err) = cli(&[
        "read".to_string(),
        root_s.clone(),
        "pax".to_string(),
        "decisions/x.md".to_string(),
    ]);
    assert_eq!(code, 0, "{err}");
    let value: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(value["text"], serde_json::json!("kept"));
    // CLI ensure.
    let (code, _, err) = cli(&["ensure".to_string(), root_s.clone()]);
    assert_eq!(code, 0, "{err}");
    // CLI read refusal carries MEMORY_ERROR and exit 2.
    let (code, _, err) = cli(&[
        "read".to_string(),
        root_s,
        "pax".to_string(),
        "../escape.md".to_string(),
    ]);
    assert_eq!(code, 2);
    assert!(err.contains("MEMORY_ERROR"), "{err}");
}

#[test]
fn et_reference_vector() {
    // Shared converter check: the pinned age-label timestamp.
    assert_eq!(
        os_memory::brief_depth::render_et(1_793_093_400),
        "2026-10-27 05:30 ET"
    );
}
