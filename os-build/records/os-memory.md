# `crates/os-memory` — behaviour record (B037, 2026-11-02)

Read from the crate as it stands on `main`. Every claim carries a
`file:line` reference. Status words: **CARRIED** (present and tested),
**REFUSED** (a documented refusal branch), **GAP** (the Python source
does something this port does not; listed in `os-memory-gaps.md`).

Source of truth: `crates/os-memory/src/lib.rs` (2,296 lines).

## What the crate is

A std-only port of `os/mos/memory.py` plus the
`with_memory_depth` / `memory_depth_lines` slice of
`os/intel/brief.py`. No external crates, no network, no clock beyond
`SystemTime::now()` (`lib.rs:757-762`). It is one library; there is no
binary target (`Cargo.toml:1-5`).

Crate constants (`lib.rs:42-48`):

- `STORE_ROOT_DEFAULT = "/var/lib/metaos/memory"` — documentation of the
  image default; the crate never reads it.
- `AGENTS_DIR = "agents"`, `SHARED_DIR = "shared"`,
  `JOURNAL_NAME = "journal.jsonl"`.

## 1. JSON value, parser, serializer

- `Value` (`lib.rs:62-83`) has `Null`, `Bool`, `Int(i64)`, `Float(f64)`,
  `Str`, `List`, `Map(Vec<(String, Value)>)`. Object members keep
  insertion order; `get` returns the first duplicate key
  (`lib.rs:85-94`).
- `parse_json` (`lib.rs:387-389`) parses exactly one document and
  refuses trailing characters (`lib.rs:146-154`).
- The parser accepts the full JSON value grammar:
  object/array/string/number/`true`/`false`/`null`
  (`lib.rs:156-169`). Integer literals that do not fit `i64` become
  `Float` (`lib.rs:226-235`).
- Strings decode the short escapes and `\uXXXX`, including surrogate
  pairs; lone surrogates and control characters are errors
  (`lib.rs:251-328`).
- `write_json` (`lib.rs:427-464`) emits Python-`json.dumps`-shaped
  output: `", "` and `": "` separators, non-ASCII escaped as `\uXXXX`
  with surrogate pairs (`lib.rs:394-425`). A float with no fraction is
  written with one decimal (`lib.rs:433-439`), matching `json.dumps`.
- `to_json_sorted` (`lib.rs:469-489`) recursively sorts object keys,
  matching `sort_keys=True`.

This is the journal codec, not a general JSON library: it exists so the
crate can read and write the Python journal format without `serde`
(`lib.rs:32-40`).

## 2. Store types

- `MemoryError(String)` (`lib.rs:500-514`) is the single error type; it
  implements `Display` and `std::error::Error`, and converts `io::Error`.
- `Entry` (`lib.rs:520-562`): `key`, `version`, `author`, `ts`, `text`,
  plus `extra` for fields the Python reader would preserve. `to_value`
  and `to_journal_line` write the five known fields then the extras
  (`lib.rs:543-561`).
- `WriteOutcome` (`lib.rs:565-574`): the stored entry and
  `new_version: bool`.
- `ReadAll` (`lib.rs:577-585`): `own` and `shared` as separate
  `BTreeMap`s, never merged.
- `MountPaths` (`lib.rs:588-595`) and `EnsureRoot` (`lib.rs:597-602`)
  carry the two directories the launcher/image paths name.

## 3. Validation — what is refused

`validate_agent` (`lib.rs:605-635`) refuses, in this order:

1. empty nick → `agent nick must be a non-empty string`
   (`lib.rs:606-610`);
2. `/`, `\`, NUL, `.` or `..` → `agent nick must be a single path
   segment` (`lib.rs:611-622`);
3. anything outside Unicode alphanumeric plus `._-` → `agent nick holds
   characters outside [A-Za-z0-9._-]` (`lib.rs:625-633`).

The slash check runs before the charset check, so `a/b` reports "single
path segment", not the charset message — the Python oddity is kept
(`lib.rs:614-616`).

`validate_key` (`lib.rs:637-657`) refuses:

1. empty → `memory key must be a non-empty string`;
2. leading `/`, backslash, or NUL → `memory key must be a relative
   POSIX path`;
3. any `""`, `.`, or `..` path segment → `memory key must not contain
   empty, . or .. segments`.

`namespace_dir`/`journal_path` (`lib.rs:659-674`) map `None` to
`<root>/shared` and `Some(nick)` to `<root>/agents/<nick>` after
validation.

## 4. Journal reading and writing

- `read_journal` (`lib.rs:676-702`): a missing file is an empty
  namespace; a blank line is skipped; a line that does not parse
  refuses with `journal line N does not parse: …`; a line that does not
  carry the entry shape refuses with `journal line N has an unexpected
  shape`.
- `entry_from_value` (`lib.rs:704-737`) requires string `key`, `text`,
  `author`; `version` and `ts` accept `Int` or a JSON boolean, because
  Python's `isinstance(True, int)` is true. That quirk is deliberate
  (`lib.rs:697-703`).
- `append_entry` (`lib.rs:739-751`) creates the namespace directory,
  opens append-only, and writes one sorted JSON line plus `\n`.
- `latest` (`lib.rs:753-755`) takes the last journal line for a key.

## 5. Writes

`write_inner` (`lib.rs:764-810`) is the one write path; `write`
(`lib.rs:812-822`) and `write_shared` (`lib.rs:824-832`) call it with
the agent namespace or the shared one. Behaviour:

- validates agent (when present), then key (`lib.rs:771-777`);
- reads the journal before deciding (`lib.rs:778`);
- if the latest text is identical, returns the current entry with
  `new_version: false` and appends nothing (`lib.rs:779-788`);
- otherwise version = latest version + 1 (`lib.rs:789-791`);
- an empty author is stored as `"unknown"` (`lib.rs:794-798`);
- a missing timestamp is the current Unix time (`lib.rs:799`,
  `lib.rs:757-762`);
- the entry is appended and returned with `new_version: true`
  (`lib.rs:800-809`).

There is no update-in-place and no delete: the journal is append-only.

## 6. Reads

- `read_version` (`lib.rs:834-866`): no entry for the key refuses with
  `no memory entry for key '<key>'`; `None` returns the latest; a
  version below 1 refuses `version must be a positive integer`; a
  version past the end refuses `key '<key>' has N versions, no vM`.
- `read` (`lib.rs:868-882`) and `read_shared` (`lib.rs:884-893`) validate
  the key (and agent) first, then read.
- `history` (`lib.rs:895-904`) and `history_shared` (`lib.rs:906-912`)
  return journal order, oldest first; a missing key is an empty list,
  not an error.
- `list_keys`/`list_shared_keys` (`lib.rs:923-935`) reduce to the latest
  entry per key into a `BTreeMap`, so output is sorted by key.
- `read_all` (`lib.rs:937-945`) calls both and keeps them separate.

## 7. Mount and root creation

- `mount_paths` (`lib.rs:947-955`) returns the agent directory and the
  shared directory; it creates nothing.
- `ensure_root` (`lib.rs:957-966`) creates `<root>/agents` and
  `<root>/shared` with `create_dir_all`; it is idempotent and also
  returns those two paths.

## 8. CLI as a library function

`run_cli` (`lib.rs:1008-1161`) ports `memory.py main()` without writing
to process streams: it returns `CliOutcome { code, stdout, stderr }`
(`lib.rs:976-986`). Exit codes are 0 on success and 2 on every usage or
memory error (`lib.rs:988-1006`).

Commands and their real argument rules:

| command | arity | success output |
|---|---|---|
| `ensure ROOT` | exactly 2 words | `{"agents": "...", "shared": "..."}` |
| `write ROOT AGENT KEY TEXT [--author A]` | at least 5 | one journal line |
| `write-shared ROOT KEY TEXT [--author A]` | at least 4 | one journal line |
| `read ROOT AGENT KEY [--version N]` | at least 4 | one journal line |
| `read-shared ROOT KEY [--version N]` | at least 3 | one journal line |
| `list ROOT AGENT` | exactly 3 | one journal line per key |
| `history ROOT AGENT KEY` | exactly 4 | one line per version |

Anything else prints the exact usage line (`lib.rs:988`) and exits 2.
Error output is `MEMORY_ERROR: <message>` (`lib.rs:990-996`). A
non-integer `--version` value refuses with Python's
`invalid literal for int() with base 10: '<value>'`
(`lib.rs:1080-1090`, `lib.rs:1106-1116`).

**GAP:** success output for `write` and `write-shared` does not include
`new_version`, while the Python CLI prints the whole returned dict. See
`os-memory-gaps.md` item 1.

## 9. Brief memory-depth record

- `format_brief_time` (`lib.rs:1204-1233`) converts a stored timestamp
  to `YYYY-MM-DD HH:MM ET`, using the post-2007 US DST rule; `Int` and
  finite `Float` are accepted, everything else is `None`.
- `environment_age_label` (`lib.rs:1235-1240`) returns
  `" (as of …)"` or `" (snapshot time not reported)"`.
- `with_memory_depth` (`lib.rs:1261-1346`): a snapshot that already has
  `memory_depth` is returned unchanged; `memory_down: true` adds only
  that flag; otherwise usable `aged_decisions`, `due_commitments`, and
  `fresh_context` are copied, and a snapshot with nothing usable gets
  no record. The input is cloned, never mutated (`lib.rs:1276-1280`).
- `memory_depth_lines` (`lib.rs:1348-1440`) renders the record: a down
  service produces one sentence and no items; missing dates read
  "not reported"; entries without their text are skipped; an empty
  category reads "none reported"; every line carries the age label.

## 10. Tests in-crate

`#[cfg(test)] mod tests` starts at `lib.rs:1435-1436` and runs to the
end (`lib.rs:2296`). It covers store round-trips, versioning, no-op
rewrites, namespace separation, validation, corrupt journals, the
CLI, image-bake files, the depth caller, and DST boundaries.

## Refusal summary (the complete set)

| Refusal | Where | Message |
|---|---|---|
| empty agent | `lib.rs:606-610` | `agent nick must be a non-empty string` |
| bad agent segment | `lib.rs:611-622` | `agent nick must be a single path segment` |
| bad agent charset | `lib.rs:625-633` | `agent nick holds characters outside [A-Za-z0-9._-]` |
| empty key | `lib.rs:638-643` | `memory key must be a non-empty string` |
| absolute/backslash/NUL key | `lib.rs:644-649` | `memory key must be a relative POSIX path` |
| empty/dot/dotdot segment | `lib.rs:650-656` | `memory key must not contain empty, . or .. segments` |
| unreadable journal | `lib.rs:681-683` | `journal unreadable: <io error>` |
| unparseable line | `lib.rs:689-691` | `journal line N does not parse: <detail>` |
| wrong-shaped line | `lib.rs:692-696` | `journal line N has an unexpected shape` |
| missing key | `lib.rs:838-842` | `no memory entry for key '<key>'` |
| version < 1 | `lib.rs:848-851` | `version must be a positive integer` |
| version past end | `lib.rs:852-861` | `key '<key>' has N versions, no vM` |
| usage | `lib.rs:998-1004` | the usage line |
| any CLI memory error | `lib.rs:990-996` | `MEMORY_ERROR: <message>` |

No refusal silently returns a neighbouring entry or a fabricated value.

## Findings (B040: docs versus code, reported not fixed)

1. **Stale header.** `lib.rs:8-9` said "Skeleton only: no logic yet"
   after 2,296 lines of ported behaviour had landed. Corrected in this
   pass to describe the B17 scope; documentation only.
2. **`--version N` is positional, not the stored version number.**
   `read_version` returns `matches[(v - 1)]` (`lib.rs:848-862`), i.e.
   the Nth journal line for that key. In a well-formed journal the two
   agree. In a hand-edited or out-of-order journal they do not: the
   entry stored with `version: 3` can be returned by `--version 2` if
   it is the second line. Python does the same
   (`memory.py:227-233`), so this is a shared contract wording problem,
   not a port drift. Pinned by `tests/edge_cases.rs`
   (`b039_out_of_order_input_reads_journal_order_not_version_order`).
3. **CLI write output omits `new_version`.** The library carries it,
   the CLI print path does not (`lib.rs:1050-1070` versus the Python
   `main` print at `memory.py:340` and `memory.py:348`). Listed as
   gap 1 in `os-memory-gaps.md`.
4. **The JSON parser is looser than `json.loads` on leading zeros.**
   `parse_json("01")` is `Int(1)` here (`lib.rs:180-236`); Python
   refuses it. Listed as gap 9 in `os-memory-gaps.md`.
5. **No runtime check for non-string `text`.** Python raises the
   documented `MemoryError`; Rust enforces it at the type boundary
   (`lib.rs:812-832`). Not fixable without changing the API; recorded
   so a parity reader knows why the branch is absent.
