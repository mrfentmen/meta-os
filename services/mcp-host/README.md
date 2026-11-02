# `mcp-host` — the smallest real MCP host

**Status: WRITTEN, entry-only.** A host process driven by Lobster's
`launch_subprocess(cmdline, stdin)`; it is not started by the supervisor and has no
`entry.goose`.

## What it does

Reads one JSON request line from stdin, answers one JSON line on stdout, and appends
every request line to `host.log` before parsing it — so a request that crashes the
parser is still in the log.

Two tools:

| tool | request | reply |
|---|---|---|
| `list` | `{"tool":"list"}` | `{"ok":true,"tools":["echo"]}` |
| `echo` | `{"tool":"echo","args":{"text":"..."}}` | `{"ok":true,"result":"..."}` |

Failures are JSON objects, not exit codes: `parse`, `no tool`, `no text`, `unknown tool`.
The loop stays alive after each one.

## Contract

- **Imports:** `os` (stdin/stdout/append_file) and the in-tree `json` module.
- **Kernel surface:** none directly; stdin/stdout are the host's.
- **Supervisor:** none. There is no `svc_entry`, so nothing can start or restart it.
- **Matrix:** **no `SVC_*` id and no row** — recorded as a Round 11 finding in
  `os-build/layer1/r11/mcp-host.md`. A shipped program with no identity in
  `callmatrix.goose` cannot be audited by it.

## Limits

None of its own: the stdin line builder is growable and there is no tool-count or
message-size constant in the file. The `json` module's limits (`JSON_MAX`, `JSON_KEY_MAX`)
apply to the request and are driven by `tests/t78_lib_limits`.

## Not verified

No host driver exists: the file is entry-only, so `run_native.sh` cannot import it and the
four error replies above are unasserted. The Lobster-side subprocess call is tested on its
own side, not here.
