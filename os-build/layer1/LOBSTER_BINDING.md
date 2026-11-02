# The Lobster host binding (BF4-10) — one round trip proven, FFI still not built

Status measured 2026-11-02: **PROVEN — a Lobster program calls a merged OS service and
prints the service's own answer** (`lobster/roundtrip.log`). **NOT BUILT — the in-process
C ABI / FFI path** (steps 1–3 of the old plan, below). Both statements are true at once and
the rest of this file keeps them apart.

## Correction to the earlier version of this document

The previous text said "Lobster source in this repo: zero files". That was wrong. `lobster/`
holds real programs (hello, shim, agent-call, bus-send/recv, budget, identity, memory,
scheduled, failures/). They landed in `75e1feb`; the earlier measurement was taken from a
stale listing and repeated as fact. The table below is from the tree as it stands.

## What exists, measured

| thing | state | command that shows it |
|---|---|---|
| `lobster` binary | present, `/opt/homebrew/bin/lobster` | `command -v lobster` |
| Lobster programs in repo | **11** `.lobster` files under `lobster/` | `find lobster -name '*.lobster' \| wc -l` |
| merged service `echo` | **runs** under the Goose toolchain | `goose run services/echo/echo.goose` |
| MCP host `services/mcp-host/host.goose` | **runs**, answers JSON lines | `lobster agent-call.lobster` |
| services exporting an argument-taking function | **none** — one `svc_entry` per service | `grep -rn '^export fn' services/` |
| dispatcher / C ABI shim for a host | **none** | `ls os-build/layer1/sdk` → absent |

## Round trip A — Lobster → merged service (PROVEN)

Program: `lobster/service-roundtrip.lobster`. Mechanism: the interpreter's own
`launch_subprocess` builtin starts the Goose toolchain on `services/echo/echo.goose`, feeds
the request on stdin, and captures stdout. The service's reply is printed, not composed.

Transcript, `lobster/roundtrip.log`, produced by
`cd lobster && lobster service-roundtrip.lobster`:

```
service exit: 0
service said: > echo: hello from lobster
> 
```

The `> ` is the echo service's own prompt; `echo: hello from lobster` is its own output.
The exit code is the service process's, not the program's guess. Reproduce the log exactly
with the command above.

Why a subprocess round trip counts: the requirement was one real round trip — call, answer,
log — and stdio JSON-lines is the dev-carrier contract the services already implement
(`os-build/research/goose-ipc.md`). When the kernel channel lands it replaces the transport,
not the contract, and neither side of this proof changes.

## Round trip B — Lobster → MCP host (also proven)

`lobster/agent-call.lobster` sends `{"tool":"list"}` and `{"tool":"echo",...}` to
`services/mcp-host/host.goose`; `lobster/host.log` holds the requests, and the program's
transcript shows the answers (`{"ok":true,"tools":["echo"]}` and
`{"ok":true,"result":"hello from lobster"}`). Same mechanism, different host program.

## What is still NOT built — the in-process FFI path

The four steps from the original plan are unchanged, and none of them is done:

1. **A callable surface.** Each service would export typed functions with arguments and
   returns (`log_info(tag, msg) -> i32`) instead of only `svc_entry`.
2. **A dispatcher.** One C function per exported function, linked against the Goose
   output.
3. **A way for Lobster to reach it in-process.** The installed interpreter has no
   documented mechanism for calling an arbitrary C library at run time; the route that
   works is building Lobster from source with the dispatcher registered as a builtin.
4. **`host_roundtrip.lobster`** calling that builtin, with a transcript.

Until 1–3 exist, a Lobster program can call a service *process* (proven above) and cannot
call a service *function*. That is the exact boundary of this commit.

## Files

- `lobster/service-roundtrip.lobster` — the F1 program (new)
- `lobster/roundtrip.log` — committed transcript of the run above (new)
- `lobster/agent-call.lobster`, `lobster/host.log` — the MCP-host proof (existing)
- `services/echo/echo.goose` — the merged service that answers
