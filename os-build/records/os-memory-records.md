# `crates/os-memory` — record shapes, worked examples (B042)

One real record of each kind the crate writes or returns, annotated
field by field. Values are produced by the crate's own serializers
(`Entry::to_journal_line`, `lib.rs:557-561`); the sorting and spacing
match `json.dumps(..., sort_keys=True)`.

## 1. Agent journal line — first write

Call: `write(root, "pax", "decisions/router.md", "Router is the queue, not the chat.", "pax", Some(1000))`.

```
{"author": "pax", "key": "decisions/router.md", "text": "Router is the queue, not the chat.", "ts": 1000, "version": 1}
```

| field | value | meaning | source |
|---|---|---|---|
| `author` | `"pax"` | writer; an empty author is stored as `"unknown"` | `lib.rs:794-798` |
| `key` | `"decisions/router.md"` | relative POSIX path inside the namespace | `lib.rs:520-525` |
| `text` | the body | verbatim; compared for the no-op rule | `lib.rs:531-533` |
| `ts` | `1000` | Unix seconds, caller-supplied or `now_unix()` | `lib.rs:536-540`, `lib.rs:757-762` |
| `version` | `1` | 1-based within this key in this namespace | `lib.rs:527-529`, `lib.rs:789-791` |

The line is written with a trailing newline (`lib.rs:750`). Keys are
sorted alphabetically by the serializer, so `author` comes first.

## 2. Agent journal line — a restatement (nothing appended)

Call: the same write again with the same text.

- No journal line is written (`lib.rs:779-788`).
- The returned `WriteOutcome` is
  `WriteOutcome { entry: <the version-1 entry>, new_version: false }`
  (`lib.rs:565-574`).

A caller that only reads `new_version` therefore sees `false`; a caller
that prints the entry sees the old version unchanged.

## 3. Shared journal line — second version

Call: `write_shared(root, "settled.md", "crew view", "", Some(1793093400))`
after one earlier shared version.

```
{"author": "unknown", "key": "settled.md", "text": "crew view", "ts": 1793093400, "version": 2}
```

| field | value | meaning |
|---|---|---|
| `author` | `"unknown"` | empty author default |
| `key` | `"settled.md"` | shared namespace key |
| `text` | `"crew view"` | body |
| `ts` | `1793093400` | 2026-10-27 05:30 ET (`format_brief_time`) |
| `version` | `2` | shared namespace versions independently of any agent |

Path: `<root>/shared/journal.jsonl` (`lib.rs:659-674`).

## 4. `ReadAll` — two namespaces, never merged

```
ReadAll {
    own:    BTreeMap<key, Entry>,   // <root>/agents/<nick>/journal.jsonl
    shared: BTreeMap<key, Entry>,   // <root>/shared/journal.jsonl
}
```

- Each map holds only the latest entry per key (`lib.rs:914-921`).
- `BTreeMap` means the keys are iterated in sorted order
  (`lib.rs:923-935`).
- The same key may appear in both maps with different versions and
  texts; the type has no precedence field and no merge
  (`lib.rs:577-585`, `lib.rs:937-945`).

## 5. `CliOutcome` — a refused read

Call: `run_cli(&["read", root, "pax", "nope.md"])`.

```
CliOutcome {
    code:   2,
    stdout: "",
    stderr: "MEMORY_ERROR: no memory entry for key 'nope.md'\n",
}
```

| field | meaning | source |
|---|---|---|
| `code` | 0 on success, 2 on any usage or memory error | `lib.rs:976-986`, `lib.rs:990-1006` |
| `stdout` | success bytes only; empty on error | `lib.rs:978-982` |
| `stderr` | `MEMORY_ERROR: ` plus the message, or the usage line | `lib.rs:990-1004` |

## 6. `CliOutcome` — a successful `ensure`

Call: `run_cli(&["ensure", "/tmp/store"])`.

```
code:   0
stdout: {"agents": "/tmp/store/agents", "shared": "/tmp/store/shared"}
stderr: ""
```

The JSON object is built directly in the CLI branch
(`lib.rs:1023-1045`), with quoted paths and a space after each colon,
matching `json.dumps` defaults.

## 7. `memory_depth` record — filled by `with_memory_depth`

Input snapshot carries `aged_decisions`, `due_commitments`,
`fresh_context`; `now = 1793093400`.

```
{
  "as_of": 1793093400,
  "aged_decisions": [
    {"decision": "freeze the demo fixture at noon", "original_date": "2026-10-01"}
  ],
  "due_commitments": [
    {"commitment": "ship the demo cut", "due": "2026-11-03"}
  ],
  "fresh_context": [
    "the demo room is build only, never a posting room"
  ]
}
```

| field | meaning | source |
|---|---|---|
| `as_of` | the single stamp shared by every line's age label | `lib.rs:1271-1272` |
| `aged_decisions[]` | `decision` required; `original_date` optional | `lib.rs:1290-1312` |
| `due_commitments[]` | `commitment` required; `due` optional | `lib.rs:1313-1337` |
| `fresh_context[]` | non-empty strings only | `lib.rs:1338-1348` |

A down service produces only `{"as_of": …, "memory_down": true}`
(`lib.rs:1281-1288`). A snapshot with nothing usable gets no
`memory_depth` key at all (`lib.rs:1342-1346`).

Rendered lines (`memory_depth_lines`, `lib.rs:1348-1440`):

```
Aged decision: freeze the demo fixture at noon (from 2026-10-01) (as of 2026-10-27 05:30 ET)
Due commitment: ship the demo cut (due 2026-11-03) (as of 2026-10-27 05:30 ET)
Fresh-agent context: the demo room is build only, never a posting room (as of 2026-10-27 05:30 ET)
```

## 8. `Entry.extra` — unknown journal fields round-trip

A journal line with an extra field:

```
{"author": "pax", "key": "k.md", "note": "kept", "text": "x", "ts": 1, "version": 1}
```

reads as `Entry { key: "k.md", version: 1, author: "pax", ts: 1,
text: "x", extra: [("note", Value::Str("kept"))] }`
(`lib.rs:704-737`). Writing it back emits the known fields plus the
extra (`lib.rs:543-555`), so the field is not lost.
