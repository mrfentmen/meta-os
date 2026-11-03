# Contract note — R13-017, heartbeat manifest entry

Status: **AUDITED — 2 gaps filed**.
Facet: the service-manifest entry for `heartbeat`, including its id, entry symbol and supervision
state.

## Evidence

Commands:

```sh
nl -ba services/heartbeat/heartbeat.goose
grep -nEi 'heartbeat' services/MANIFEST.md services/callmatrix/*.goose os-build/layer1/callmatrix_audit.py
```

Relevant output:

```text
8   fn main() {
9       var n = 0;
10      while n < 3600 {
11          if file_exists("STOP") { break; }
14          append_file("heartbeat.log", "beat");
16          sleep(1.0);
18      print("daemon stopping cleanly");
```

```text
os-build/layer1/callmatrix_audit.py:18  four demo programs (hello, heartbeat, echo, mcp-host) do neither
os-build/layer1/callmatrix_audit.py:52  NOT_SERVICES = {"example", "callmatrix", "hello", "heartbeat", "echo", "mcp-host"}
```

`services/MANIFEST.md` has no `heartbeat` row.

## Corrected contract

`heartbeat` is an entry-only Goose program: `fn main()`, `import os`, no `svc_entry`, no
`service_main`, no `SVC_*` id. It appends the bare token `beat` to `heartbeat.log` once per second
for at most 3,600 iterations, checks for a `STOP` file before every beat, and prints
`daemon stopping cleanly` on exit.

It has no manifest entry and is deliberately in `NOT_SERVICES` in `callmatrix_audit.py`. It is not
supervised and has no restart drill.

## Mismatches

- **R13-017-G1** — there is no manifest entry, so no id, owner or supervision state is recorded
  in the manifest.
- **R13-017-G2** — the source header says “one timestamped line per second”; the code appends
  `beat` with no timestamp and no newline. See `services/heartbeat/GAPS_R13.md`.
