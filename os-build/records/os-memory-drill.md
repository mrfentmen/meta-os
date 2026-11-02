# `crates/os-memory` — failure drill (B045)

What breaks first when its inputs stop arriving, written from the code.
The crate has three inputs: the journal file, the root directory it sits
in, and the clock. The drill below is runnable by another agent; it
creates a throwaway integration test, runs it, and removes it.

## The failure order, from the code

1. **Journal missing.** `read_journal` returns an empty vector
   (`lib.rs:677-680`). Reads return `[]`/`no memory entry`; no IO error.
   The first symptom is silence — an agent sees amnesia, not a fault.
   A write recreates the directory and file (`lib.rs:739-748`), so the
   condition self-heals on the next write.
2. **Journal corrupt.** Every read refuses at the first bad line
   (`lib.rs:686-696`). Every write refuses too, because `write_inner`
   reads the journal before appending (`lib.rs:778`). The store becomes
   read-only-broken until the line is removed; there is no repair path
   in the crate. First symptom: `MEMORY_ERROR: journal line N does not
   parse: …`.
3. **Namespace directory unwritable.** `append_entry` fails at
   `create_dir_all` or `OpenOptions` (`lib.rs:739-748`); the IO error
   is wrapped by `From<io::Error>` (`lib.rs:511-513`). Reads may still
   work if the file exists and is readable. First symptom: a CLI write
   exits 2 with the OS error text in `MEMORY_ERROR`.
4. **Root path is a file, not a directory.** `ensure_root`
   (`lib.rs:957-966`) and `append_entry` both fail `create_dir_all`;
   reads of a nonexistent journal still return empty, so `read` reports
   "no memory entry" rather than "root is bad". First symptom: `ensure`
   exits 2, while `read` misleadingly says the key is absent.
5. **Clock stops or jumps.** `now_unix` (`lib.rs:757-762`) still
   returns a number (or a negative number before the epoch); timestamps
   are wrong but nothing refuses. First symptom: fresh entries carry a
   stale or future `ts`; ordering inside the journal is unaffected
   because it is append order, not timestamp order.

Nothing here retries, buffers, or drops silently; the crate has no
background task and no queue.

## Runnable drill

Run from the repo root. It writes one temporary test file, runs it with
the crate, and removes it. Each step prints a named check.

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

cat > crates/os-memory/tests/drill_inputs.rs <<'RS'
use os_memory::{ensure_root, read, run_cli, write};
use std::fs;
use std::path::{Path, PathBuf};

fn tmp(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-memory-drill-{}-{}", std::process::id(), name
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();
    dir
}

fn cli(args: &[&str]) -> os_memory::CliOutcome {
    run_cli(&args.iter().map(|s| s.to_string()).collect::<Vec<_>>())
}

#[test]
fn drill_1_missing_journal_is_silent_then_recreated() {
    let root = tmp("missing");
    assert!(read(&root, "pax", "k.md", None).is_err());
    assert!(cli(&["list", root.to_str().unwrap(), "pax"]).stdout.is_empty());
    write(&root, "pax", "k.md", "x", "", Some(1)).unwrap();
    assert!(root.join("agents/pax/journal.jsonl").is_file());
}

#[test]
fn drill_2_corrupt_journal_refuses_reads_and_writes() {
    let root = tmp("corrupt");
    let dir = root.join("agents/pax");
    fs::create_dir_all(&dir).unwrap();
    fs::write(dir.join("journal.jsonl"), "not json\n").unwrap();
    let read_err = read(&root, "pax", "k.md", None).unwrap_err().0;
    assert!(read_err.contains("journal line 1 does not parse"), "{read_err}");
    let write_err = write(&root, "pax", "k.md", "x", "", Some(1)).unwrap_err().0;
    assert!(write_err.contains("journal line 1 does not parse"), "{write_err}");
}

#[test]
fn drill_3_root_as_file_refuses_ensure() {
    let base = tmp("rootfile");
    let root = base.join("store");
    fs::write(&root, "not a directory").unwrap();
    assert!(ensure_root(&root).is_err());
}

#[test]
fn drill_4_unwritable_namespace_refuses_write() {
    let root = tmp("unwritable");
    let agent_dir = root.join("agents/pax");
    fs::create_dir_all(&agent_dir).unwrap();
    // journal.jsonl as a directory makes appending fail without needing chmod.
    fs::create_dir_all(agent_dir.join("journal.jsonl")).unwrap();
    let err = write(&root, "pax", "k.md", "x", "", Some(1)).unwrap_err().0;
    assert!(!err.is_empty());
}
RS

cargo test -p os-memory --test drill_inputs -- --nocapture
rm -f crates/os-memory/tests/drill_inputs.rs
```

Expected: four passing tests. If step 1 fails with an error instead of
an empty list, the "missing journal is empty" contract changed. If step
2 succeeds in writing, the read-before-append rule changed. If step 3
succeeds, `create_dir_all` started accepting a file. If step 4
succeeds, the append path stopped surfacing the IO error.

Cleanup: remove the temp directories under `/tmp/os-memory-drill-*`.
