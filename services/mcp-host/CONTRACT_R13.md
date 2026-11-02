# Contract note — R13-021, mcp-host exit code table

Status: **AUDITED — 2 gaps filed**.
Facet: the process exit codes `mcp-host` can return, and how a failed request is reported.

## Evidence

Command:

```sh
nl -ba services/mcp-host/host.goose
```

Relevant output:

```text
23  fn main() {
24      loop {
28          guard read_line(line) else { break; }
31          append_file("host.log", line);
33          let root, err = json::parse(line, doc, decoded);
34          if err.len > 0 {
35              write_stdout("{\"ok\":false,\"error\":\"parse\"}\n");
...
41              write_stdout("{\"ok\":false,\"error\":\"no tool\"}\n");
52              write_stdout("{\"ok\":false,\"error\":\"no text\"}\n");
56              write_stdout("{\"ok\":false,\"error\":\"unknown tool\"}\n");
60      }
61  }
```

## Corrected contract

There is no exit-code table. `main` has no explicit `return`, no `exit()` call and no error
return. It leaves the loop only when `read_line` reaches end of input and then falls off the end
of `main` — the conventional zero exit. Every request failure is a JSON object on stdout with
`"ok":false` and one of four `error` strings: `parse`, `no tool`, `no text`, `unknown tool`.
The loop continues after each; a bad request does not kill the host.

The process also appends every raw request line to `host.log` before parsing it.

## Mismatches

- **R13-021-G1** — no exit-code table exists, because no error path sets an exit status.
- **R13-021-G2** — no host driver exists, so none of the four JSON failures or the zero exit is
  asserted. See `services/mcp-host/GAPS_R13.md`.
