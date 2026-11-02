# `crates/os-memory` — public surface inventory (B046)

Every exported name, one line each, marked used or unused in the repo
today. "Unused" here means no caller outside `crates/os-memory/`; the
crate's own `#[cfg(test)]` module exercises most of them. There is no
other Rust caller (see `os-memory-callers.md`).

## Constants

| Name | One line | Used in repo |
|---|---|---|
| `STORE_ROOT_DEFAULT` | Image default store root, documentation only. | UNUSED |
| `AGENTS_DIR` | Subdirectory name for agent namespaces. | UNUSED outside crate; used by path builders and tests |
| `SHARED_DIR` | Subdirectory name for the shared namespace. | UNUSED outside crate; used by path builders and tests |
| `JOURNAL_NAME` | Journal file name inside every namespace. | UNUSED outside crate; used by path builders and tests |

## Types

| Name | One line | Used in repo |
|---|---|---|
| `Value` | Minimal JSON value (null/bool/int/float/string/list/map). | UNUSED outside crate; used throughout its API and tests |
| `MemoryError` | The single refusal type, with a human-readable message. | UNUSED outside crate |
| `Entry` | One journal entry: key, version, author, ts, text, extras. | UNUSED outside crate |
| `WriteOutcome` | Stored entry plus the `new_version` flag. | UNUSED outside crate |
| `ReadAll` | Own and shared latest maps, never merged. | UNUSED outside crate |
| `MountPaths` | The two directories a launcher would mount. | UNUSED outside crate |
| `EnsureRoot` | The two directories `ensure_root` creates/returns. | UNUSED outside crate |
| `CliOutcome` | Exit code plus captured stdout/stderr. | UNUSED outside crate |

## `Value` methods

| Name | One line | Used in repo |
|---|---|---|
| `Value::get` | Look up an object key, first duplicate wins. | UNUSED outside crate; used by the store and depth code |
| `Value::as_str` | The string value or `None`. | UNUSED outside crate; used by the store and depth code |
| `Value::is_json_true` | True only for JSON `true` (Python `is True`). | UNUSED outside crate |

## `Entry` methods

| Name | One line | Used in repo |
|---|---|---|
| `Entry::to_value` | Entry as a JSON value, known fields plus extras. | UNUSED outside crate |
| `Entry::to_journal_line` | Entry as one sorted journal line. | UNUSED outside crate; used by `append_entry`/CLI |

## Functions

| Name | One line | Used in repo |
|---|---|---|
| `parse_json` | Parse exactly one JSON document. | UNUSED outside crate; used by `read_journal` and tests |
| `write_json` | Serialize a value in `json.dumps` shape. | UNUSED outside crate |
| `to_json_sorted` | Serialize with object keys recursively sorted. | UNUSED outside crate; used by journal lines |
| `write` | Append an agent entry; identical text is a no-op. | UNUSED outside crate |
| `write_shared` | Append a shared entry with the same rules. | UNUSED outside crate |
| `read` | Latest or numbered agent entry; never guesses. | UNUSED outside crate |
| `read_shared` | Latest or numbered shared entry. | UNUSED outside crate |
| `history` | All versions of an agent key, oldest first. | UNUSED outside crate |
| `history_shared` | All versions of a shared key, oldest first. | UNUSED outside crate |
| `list_keys` | Latest agent entries as a key-sorted map. | UNUSED outside crate |
| `list_shared_keys` | Latest shared entries as a key-sorted map. | UNUSED outside crate |
| `read_all` | Own and shared maps under separate fields. | UNUSED outside crate |
| `mount_paths` | Name the two launcher mount directories. | UNUSED outside crate |
| `ensure_root` | Create the two namespace bases, idempotently. | UNUSED outside crate |
| `run_cli` | The `memory.py main()` port as a pure function. | UNUSED outside crate |
| `format_brief_time` | Timestamp to `YYYY-MM-DD HH:MM ET`. | UNUSED outside crate |
| `environment_age_label` | The `" (as of …)"` suffix or its honest absence. | UNUSED outside crate |
| `with_memory_depth` | Fill a snapshot's `memory_depth` record. | UNUSED outside crate |
| `memory_depth_lines` | Render the record as brief lines. | UNUSED outside crate |

## Summary

- 4 constants, 8 types, 5 methods, 19 free functions: 36 exported names.
- 36/36 are unused outside the crate today. 0 are dead inside it:
  the crate's tests and its own call graph reference every one, except
  `STORE_ROOT_DEFAULT` and the three directory-name constants, which are
  documentation/contract values and are read by the tests.
- No `pub(crate)`-only surface is listed here; those are private by
  definition (`lib.rs:605-1006`).
