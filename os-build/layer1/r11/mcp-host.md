# mcp-host — Round 11 record

Source: `services/mcp-host/host.goose` · Test: none (entry-only) · Status: WRITTEN, entry-only

## 1. Limits — NOT APPLICABLE

`NOT IMPORTABLE`. `host.goose` declares `fn main()` and imports `os` (`read_line`,
`write_stdout`, `flush_stdout`, `append_file`) plus `json`. A host driver cannot import it: a
second `main` in one program is a duplicate definition, and the service has no library surface
to call. There are also no numeric caps in the file — no buffer constant, no tool limit, no
line cap of its own (the stdin line builder is growable). Nothing to cross, nothing to drive.

## 2. Refusals — NAMED GAP

The service does not refuse with codes; it answers one JSON error object per failure and keeps
the loop alive:

| condition | reply | reachable by a driver? |
|---|---|---|
| unparseable request line | `{"ok":false,"error":"parse"}` | no — entry-only |
| no `tool` string | `{"ok":false,"error":"no tool"}` | no — entry-only |
| `echo` with no `args.text` | `{"ok":false,"error":"no text"}` | no — entry-only |
| unknown tool name | `{"ok":false,"error":"unknown tool"}` | no — entry-only |

These are real paths in the code and none of them is asserted. The honest status is NAMED GAP,
not "tested through the stdio harness": no such harness exists in this repo.

## 3. Restart — NAMED GAP

There is no `entry.goose` and no `SVC_*` id, so the supervisor neither starts nor restarts this
program. It is a host process driven by Lobster's subprocess call (`OS-170`). On restart it
loses nothing in memory — it has no table — and `host.log` survives on disk because every
request line is appended before parsing. The loss is the in-flight line at the moment of the
kill, which is not written and not counted. No restart was run.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | none | stdio only (`os`), JSON via the in-tree `json` module | **FINDING: no `SVC_*` id and no matrix row** |
| in | Lobster host | one JSON line on stdin, one on stdout | not a service call; no matrix concept for a subprocess pipe |

The matrix's ids run to 31 and stop at `SVC_NOTIFY`; `mcp-host` is not among them and is not in
`services/MANIFEST.md`'s service table. That is the room-1 finding for this record: a shipped
program with no identity in the permission table cannot be audited by it.

## 5. Load — NOT APPLICABLE

There is no test to run a load loop through. The program is line-at-a-time and synchronous; a
load shape would have to be measured by a Lobster driver feeding stdin, which does not exist
yet. Writing an unmeasured number here would be the exact failure this round removes.

## 6. README truth pass — PROVEN

- There was **no README at all** (`services/mcp-host/README.md` did not exist). Created: what it
  is (smallest real MCP host), the two tools (`list`, `echo`), the JSON-line protocol, the
  `host.log` audit trail, and the two absences above (no matrix id, no supervisor entry).
- No stale sentences to rewrite because there was nothing to rewrite; that is recorded rather
  than presented as a pass over prose.
