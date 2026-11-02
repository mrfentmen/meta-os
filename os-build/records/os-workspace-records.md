# Worked records — `os-workspace`

Every shape below is taken from the code that writes it (`lib.rs` ranges named
per record). Values are one worked example, not a captured run: the SHA-256 of
`hello` is the real digest; the timestamp is an ordinary Unix-seconds value.
`<40-hex>` marks the places git supplies a commit hash.

## 1. `jobs/<job_id>/manifest.json` — the store's own record

Written by `write_manifest` (`lib.rs:925-943`) with sorted keys, two-space
indent, and a trailing newline. Shape from `record_to_value` (`983-1000`) and
`deposit` (`1051-1066`):

```json
{
  "artifacts": {
    "report.md": {
      "author": "alice",
      "deposited_at": 1730592000,
      "name": "report.md",
      "path": "jobs/job-1/report.md",
      "reference": "artifact:job-1/report.md@v1",
      "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
      "size": 5,
      "version": 1
    }
  },
  "job_id": "job-1"
}
```

| Field | Meaning | Source |
|---|---|---|
| `artifacts` | map keyed by artifact name; one entry per name, latest version only | `1129-1143`, `1085-1099` |
| `job_id` | the validated job id | `1085-1087` |
| `author` | depositing nick, or `"unknown"` when blank | `1058-1062` |
| `deposited_at` | Unix seconds, from `SystemTime::now` | `1002-1007` |
| `name` | artifact name, relative POSIX path | `1052` |
| `path` | dashboard-linkable `jobs/<job_id>/<name>` | `1053`, `953-955` |
| `reference` | `artifact:<job_id>/<name>@v<version>` | `1054` |
| `sha256` | lowercase hex digest of the deposited bytes | `1056`, `569-633` |
| `size` | byte length | `1057` |
| `version` | counts from 1 per artifact name | `1050`, `1055` |

A byte-identical redeposit changes nothing here and returns the existing record
with no commit (`1030-1038`).

## 2. `DepositOutcome` — the Rust return value

`lib.rs:742-747`. Not written to disk:

```
DepositOutcome {
    record: ArtifactRecord { name, path, reference, version, sha256, size, author, deposited_at },
    new_commit: true,
}
```

`new_commit` is `false` only for a byte-identical redeposit
(`1035-1038`). The manifest never carries it; the CLI adds it to the printed
object (`run_cli`, `1310-1330`).

## 3. CLI `deposit` — one compact JSON line on stdout

Producer: `run_cli` (`lib.rs:1310-1335`), serialized by `json_dump_compact`
(`506-553`). Keys are sorted, `", "` between items:

```json
{"author": "alice", "deposited_at": 1730592000, "name": "report.md", "new_commit": true, "path": "jobs/job-1/report.md", "reference": "artifact:job-1/report.md@v1", "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", "size": 5, "version": 1}
```

Same fields as record 1, plus `new_commit`; no wrapper object.

## 4. CLI `list` — one line per artifact

Producer: `run_cli` (`lib.rs:1337-1351`). Same object as record 3 **without**
`new_commit`:

```json
{"author": "alice", "deposited_at": 1730592000, "name": "report.md", "path": "jobs/job-1/report.md", "reference": "artifact:job-1/report.md@v1", "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", "size": 5, "version": 1}
```

Sorted by name because the manifest is a `BTreeMap` (`1129-1143`).

## 5. CLI `read` — raw bytes, no envelope

Producer: `run_cli` (`lib.rs:1353-1387`). The artifact bytes are written
verbatim (`1356-1360`); a five-byte deposit prints exactly `hello` and nothing
else. Errors go to stderr, never into stdout (`1289-1292`).

## 6. CLI `show` — version history lines

Producer: `history` (`lib.rs:1218-1241`) printed at `lib.rs:1389-1396`:

```
v1 <40-hex-commit>
v2 <40-hex-commit>
```

Oldest first; version numbers are positional, not stored
(`1218-1241`).

## 7. Store git commit — one commit per deposit

Producer: `deposit` (`lib.rs:1101-1113`). Fixed identity is passed per commit,
never written to global config:

```
job job-1: deposit report.md v1 by alice
```

## 8. Merge commit — the gitops record

Producer: `approve_merge` (`lib.rs:1566-1580`):

```
Merge feature (MOS approved)
```

`--no-ff` always creates the merge commit; the returned hash is
`rev-parse HEAD` (`1581`).

## 9. Rejection summary — returned, not written

Producer: `reject_branch` (`lib.rs:1583-1589`):

```
REJECTED feature: needs tests
```

Leading/trailing whitespace in the reason is trimmed; a blank reason is an
error (`1585`). Nothing is deleted or written to disk.

## 10. `attach` — a job record with artifact entries

Producer: `attach` (`lib.rs:1243-1277`). The input is copied; existing
`artifacts` entries are kept and the store's entries appended
(`1255-1276`):

```json
{
  "artifacts": [
    {
      "path": "jobs/job-1/report.md",
      "reference": "artifact:job-1/report.md@v1",
      "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
      "version": 1
    }
  ],
  "title": "Live job"
}
```

| Entry field | Meaning | Source |
|---|---|---|
| `path` | dashboard link target | `1264` |
| `reference` | versioned artifact reference | `1265` |
| `sha256` | digest of that version | `1267` |
| `version` | version number | `1266` |

Top-level fields other than `artifacts` are carried through unchanged
(`1248-1252`).
