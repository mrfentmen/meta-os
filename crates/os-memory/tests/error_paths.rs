//! B038 — every refusal and failure branch in `crates/os-memory`.
//!
//! These assert the exact messages the code produces, not paraphrases.
//! Messages are pinned in `lib.rs`; a message change is a behaviour
//! change and should fail here on purpose.

use os_memory::{
    ensure_root, read, read_shared, run_cli, write, write_shared, CliOutcome, MemoryError,
};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn store_root(tag: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!(
        "os-memory-error-{}-{}-{}",
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

fn message<T>(result: Result<T, MemoryError>) -> String {
    match result {
        Ok(_) => panic!("expected a refusal, got Ok"),
        Err(err) => err.0,
    }
}

fn cli(args: &[&str]) -> CliOutcome {
    run_cli(&args.iter().map(|a| a.to_string()).collect::<Vec<_>>())
}

#[test]
fn b038_agent_refusals_keep_the_python_order_and_messages() {
    let dir = store_root("agent");
    let cases = [
        ("", "agent nick must be a non-empty string"),
        ("a/b", "agent nick must be a single path segment"),
        ("a\\b", "agent nick must be a single path segment"),
        ("a\0b", "agent nick must be a single path segment"),
        (".", "agent nick must be a single path segment"),
        ("..", "agent nick must be a single path segment"),
        (
            "bad nick",
            "agent nick holds characters outside [A-Za-z0-9._-]",
        ),
        (
            "bad!nick",
            "agent nick holds characters outside [A-Za-z0-9._-]",
        ),
    ];
    for (bad, expected) in cases {
        let got = message(write(&dir, bad, "k.md", "x", "", Some(1)));
        assert_eq!(got, expected, "agent {bad:?}");
    }
    cleanup(&dir);
}

#[test]
fn b038_key_refusals_keep_the_python_order_and_messages() {
    let dir = store_root("key");
    let cases = [
        ("", "memory key must be a non-empty string"),
        ("/absolute", "memory key must be a relative POSIX path"),
        ("a\\b", "memory key must be a relative POSIX path"),
        ("a\0b", "memory key must be a relative POSIX path"),
        (
            "a//b",
            "memory key must not contain empty, . or .. segments",
        ),
        (
            "a/./b",
            "memory key must not contain empty, . or .. segments",
        ),
        (
            "a/../b",
            "memory key must not contain empty, . or .. segments",
        ),
    ];
    for (bad, expected) in cases {
        let got = message(write(&dir, "pax", bad, "x", "", Some(1)));
        assert_eq!(got, expected, "agent key {bad:?}");
        let got = message(write_shared(&dir, bad, "x", "", Some(1)));
        assert_eq!(got, expected, "shared key {bad:?}");
    }
    cleanup(&dir);
}

#[test]
fn b038_missing_key_and_bad_versions_refuse_with_exact_text() {
    let dir = store_root("versions");
    assert_eq!(
        message(read(&dir, "pax", "nope.md", None)),
        "no memory entry for key 'nope.md'"
    );
    assert_eq!(
        message(read_shared(&dir, "nope.md", None)),
        "no memory entry for key 'nope.md'"
    );

    write(&dir, "pax", "k.md", "v1", "", Some(1)).unwrap();
    write(&dir, "pax", "k.md", "v2", "", Some(2)).unwrap();
    write(&dir, "pax", "k.md", "v3", "", Some(3)).unwrap();

    assert_eq!(
        message(read(&dir, "pax", "k.md", Some(0))),
        "version must be a positive integer"
    );
    assert_eq!(
        message(read(&dir, "pax", "k.md", Some(-4))),
        "version must be a positive integer"
    );
    assert_eq!(
        message(read(&dir, "pax", "k.md", Some(4))),
        "key 'k.md' has 3 versions, no v4"
    );
    cleanup(&dir);
}

#[test]
fn b038_corrupt_journal_refuses_and_names_the_line() {
    use std::io::Write as _;

    let dir = store_root("corrupt");
    write(&dir, "pax", "k.md", "good", "", Some(1)).unwrap();
    let journal = dir.join("agents").join("pax").join("journal.jsonl");
    {
        let mut handle = fs::OpenOptions::new()
            .append(true)
            .open(&journal)
            .unwrap();
        writeln!(handle, "this is not json").unwrap();
    }
    let got = message(read(&dir, "pax", "k.md", None));
    assert!(
        got.starts_with("journal line 2 does not parse: "),
        "{got}"
    );

    // A fresh store: line 1 is a good write, line 2 is well-formed JSON
    // with the wrong shape, so the shape check is what refuses.
    let dir2 = store_root("bad-shape");
    write(&dir2, "pax", "k.md", "good", "", Some(1)).unwrap();
    let journal2 = dir2.join("agents").join("pax").join("journal.jsonl");
    {
        let mut handle = fs::OpenOptions::new()
            .append(true)
            .open(&journal2)
            .unwrap();
        writeln!(handle, "{{\"key\": \"k.md\"}}").unwrap();
    }
    let got = message(read(&dir2, "pax", "k.md", None));
    assert_eq!(got, "journal line 2 has an unexpected shape");
    cleanup(&dir2);
    cleanup(&dir);
}

#[test]
fn b038_unreadable_journal_refuses_with_the_io_reason() {
    let dir = store_root("unreadable");
    let journal = dir.join("agents").join("pax").join("journal.jsonl");
    fs::create_dir_all(&journal).unwrap();
    let got = message(read(&dir, "pax", "k.md", None));
    assert!(got.starts_with("journal unreadable: "), "{got}");
    cleanup(&dir);
}

#[test]
fn b038_write_reads_before_appending_so_a_bad_journal_blocks_writes() {
    let dir = store_root("blocked-write");
    let journal_dir = dir.join("agents").join("pax");
    fs::create_dir_all(&journal_dir).unwrap();
    fs::write(journal_dir.join("journal.jsonl"), "not json\n").unwrap();
    let got = message(write(&dir, "pax", "k.md", "x", "", Some(1)));
    assert!(got.starts_with("journal line 1 does not parse: "), "{got}");
    // Nothing was appended after the refusal.
    let text = fs::read_to_string(journal_dir.join("journal.jsonl")).unwrap();
    assert_eq!(text, "not json\n");
    cleanup(&dir);
}

#[test]
fn b038_shared_key_refusal_leaves_no_shared_directory() {
    let dir = store_root("no-partial");
    assert!(write_shared(&dir, "../escape", "x", "", Some(1)).is_err());
    assert!(
        !dir.join("shared").exists(),
        "a refused write created the shared namespace"
    );
    cleanup(&dir);
}

#[test]
fn b038_ensure_root_refuses_when_the_root_is_a_file() {
    let base = store_root("root-file");
    let root = base.join("store");
    fs::write(&root, "not a directory").unwrap();
    let got = message(ensure_root(&root));
    assert!(!got.is_empty(), "an IO refusal must carry its reason");
    cleanup(&base);
}

#[test]
fn b038_cli_refusals_are_exit_2_with_the_documented_prefix() {
    let dir = store_root("cli");
    let root = dir.to_string_lossy().to_string();

    let out = cli(&[]);
    assert_eq!(out.code, 2);
    assert!(out.stderr.starts_with("usage: memory "), "{}", out.stderr);
    assert!(out.stdout.is_empty());

    let out = cli(&["bogus", &root]);
    assert_eq!(out.code, 2);
    assert!(out.stderr.starts_with("usage: memory "), "{}", out.stderr);

    let out = cli(&["read", &root, "pax", "nope.md"]);
    assert_eq!(out.code, 2);
    assert_eq!(
        out.stderr,
        "MEMORY_ERROR: no memory entry for key 'nope.md'\n"
    );

    write(&dir, "pax", "k.md", "v1", "", Some(1)).unwrap();
    let out = cli(&["read", &root, "pax", "k.md", "--version", "nine"]);
    assert_eq!(out.code, 2);
    assert_eq!(
        out.stderr,
        "MEMORY_ERROR: invalid literal for int() with base 10: 'nine'\n"
    );

    let out = cli(&["list", &root]);
    assert_eq!(out.code, 2);
    assert!(out.stderr.starts_with("usage: memory "), "{}", out.stderr);

    let out = cli(&["ensure", &root, "extra"]);
    assert_eq!(out.code, 2);
    assert!(out.stderr.starts_with("usage: memory "), "{}", out.stderr);

    cleanup(&dir);
}

#[test]
fn b038_a_valid_cli_error_never_writes_to_stdout() {
    let dir = store_root("cli-streams");
    let root = dir.to_string_lossy().to_string();
    // read on a missing key is a refusal.
    let out = cli(&["read", &root, "pax", "missing.md"]);
    assert_eq!(out.code, 2);
    assert!(out.stdout.is_empty(), "error leaked to stdout: {:?}", out.stdout);
    assert!(!out.stderr.is_empty());

    // history on a key with no entries is an honest empty success, not a
    // refusal: the code returns Ok(empty) there (lib.rs history branch).
    let out = cli(&["history", &root, "pax", "missing.md"]);
    assert_eq!(out.code, 0);
    assert!(out.stdout.is_empty());
    assert!(out.stderr.is_empty());
    // list on a store that exists is a success, not an error: it must
    // not be folded into the refusal loop above.
    let listed = cli(&["list", &root, "pax"]);
    assert_eq!(listed.code, 0, "list refused: {}", listed.stderr);
    assert!(listed.stderr.is_empty(), "list wrote stderr: {}", listed.stderr);
    cleanup(&dir);
}
