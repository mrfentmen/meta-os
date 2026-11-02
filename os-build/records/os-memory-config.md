# `crates/os-memory` — config surface (B044)

Every environment variable, flag, and file the crate reads, with the
default and the refusal when it is wrong.

## Environment variables

None. The crate reads no environment variable. A repo-wide scan of
`lib.rs` finds no `std::env` use; the only process input is
`argv` passed to `run_cli` (`lib.rs:1008`).

## Constants (documentation only)

| Name | Value | Read by the crate? | Meaning | Source |
|---|---|---|---|---|
| `STORE_ROOT_DEFAULT` | `/var/lib/metaos/memory` | No — the caller must pass a root | the image default named in `memory.py` | `lib.rs:42` |
| `AGENTS_DIR` | `agents` | Yes, to build paths | per-agent namespace base | `lib.rs:44` |
| `SHARED_DIR` | `shared` | Yes, to build paths | crew namespace | `lib.rs:46` |
| `JOURNAL_NAME` | `journal.jsonl` | Yes, to build paths | journal file in every namespace | `lib.rs:48` |

Consequence: there is no way to configure the store through the
environment. `run_cli` always takes `ROOT` as its second word
(`lib.rs:1023`, `lib.rs:1046`, `lib.rs:1062`, `lib.rs:1076`,
`lib.rs:1102`, `lib.rs:1118`, `lib.rs:1140`).

## CLI flags

`run_cli` accepts only two flags, and both are looked up in the raw
argument words:

| Flag | Commands | Value | Default | Refusal when wrong | Source |
|---|---|---|---|---|---|
| `--author A` | `write`, `write-shared` | any string, including empty | empty → stored as `"unknown"` | none; a missing value falls back to empty (see gap 5) | `lib.rs:1010-1021`, `lib.rs:1048-1050` |
| `--version N` | `read`, `read-shared` | base-10 integer | none → latest version | non-integer → `MEMORY_ERROR: invalid literal for int() with base 10: '<text>'`, exit 2; below 1 → `version must be a positive integer`; past end → `key '<k>' has N versions, no vM` | `lib.rs:1076-1090`, `lib.rs:1102-1116`, `lib.rs:848-861` |

No other flag is recognised; it is treated as an ordinary argument
word. An unknown command, wrong word count, or absent command prints
the usage line to stderr and exits 2 (`lib.rs:988-1006`,
`lib.rs:1156-1160`).

## Files read and written

| Path | Operation | When missing | Refusal | Source |
|---|---|---|---|---|
| `<root>/agents/<nick>/journal.jsonl` | read | treated as an empty namespace | unreadable → `journal unreadable: <io error>`; bad line → `journal line N does not parse: …`; wrong shape → `journal line N has an unexpected shape` | `lib.rs:676-702`, `lib.rs:659-674` |
| `<root>/shared/journal.jsonl` | read | same | same | `lib.rs:676-702` |
| `<root>/agents/<nick>/journal.jsonl` | append | created, with parent directories | any `io::Error` becomes `MemoryError` via `From<io::Error>` | `lib.rs:739-751`, `lib.rs:511-513` |
| `<root>/shared/journal.jsonl` | append | created | same | `lib.rs:739-751` |
| `<root>/agents`, `<root>/shared` | create | created | `create_dir_all` error becomes `MemoryError` | `lib.rs:957-966` |

No config file, no lock file, no cache file, and no network endpoint is
read. The store is exactly the two journal paths above.

## Cross-check with the Python original

`os/mos/memory.py:66-70` defines the same four constants. Its CLI also
takes `ROOT` explicitly, so the "no environment variable" rule is the
original behaviour, not a Rust omission.
