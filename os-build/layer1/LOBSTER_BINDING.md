# The Lobster host binding (BF4-10) — NOT BUILT

Task: "services callable from the Lobster agent host, one real round trip (agent
calls a service, service answers), log committed."

**Status: NOT BUILT. There is no round trip, and no log of one, because there is
nothing in the repository that a Lobster program could call.** This document is
the evidence and the plan, in that order. It is not a claim of progress.

## What exists, measured 2026-11-02

| thing | state | command that shows it |
|---|---|---|
| `lobster` binary | **present**, `/opt/homebrew/bin/lobster` | `ls /opt/homebrew/bin/lobster` |
| Lobster source in this repo | **zero files** | `find . -name '*.lobster' \| wc -l` → `0` |
| Lobster build step for services | **none** | `grep -rl lobster os-build/ --include=*.sh --include=*.py` → only `mcp/mcp_client.py` (the MCP client, not a build step) |
| Goose callable surface | **one symbol per service**: `export "svc_entry" fn service_main() -> i32`, no arguments, returns a code | `grep -n 'export' services/*/entry.goose` |
| Anything a host could call with arguments | **nothing** | `grep -rn '^export fn' services/` → no matches |

So the gap is not wiring. The services expose a single entry point that takes
nothing and returns an exit code. A host that "calls a service" needs a function
that takes arguments, returns a value, and has a name the host can resolve. That
function does not exist in this layer at any level.

## Why it is not a one-line shim

Three separate things are missing, and each one is honest work:

1. **A callable surface.** Each service would export typed functions
   (`log_info(tag, msg) -> i32`, `fs_create_path(ino, name, kind) -> i64, i64`)
   instead of only `svc_entry`. Goose's `export "name" fn` supports this
   (spec#41), so the shape is available — it has simply never been used for an
   arguments-and-return call, only for the entry symbol.
2. **A dispatcher.** One C function per exported service function, or one
   generated table: `int64_t svc_log_log_info(const char *tag, int64_t tag_len,
   const char *msg, int64_t msg_len)`. This is mechanical, and `goose -o x.c`
   output is what it links against.
3. **A way for Lobster to reach it.** The installed `lobster` binary loads a fixed
   set of native modules; it has no documented mechanism in this repo for calling
   into an arbitrary C library at run time. The route that works is building the
   Lobster host from source with the dispatcher registered as a builtin — which
   means a C++ toolchain build of Lobster itself, outside this repository, before
   a single line of the round trip exists.

Item 3 is why this is NOT BUILT rather than half built: the cheapest honest
version still needs a build of the host, and a fake round trip (a Lobster program
that prints a canned service reply) is exactly the thing the boss's NO MOCKS rule
forbids.

## What the round trip will look like when it is built

```lobster
// os-build/layer1/sdk/host_roundtrip.lobster   (NOT WRITTEN)
let code = svc_call("logd.log_info", "smoke", "round trip")
print("service answered: " + code)
```

with `svc_call` a builtin that resolves the name to a dispatcher entry, calls it,
and maps the returned code to a Lobster value. The log to commit is the
program's own output plus the service's `sys_write_serial` line, so the two sides
of the round trip are visible in one transcript.

## The four steps, in order of cost

1. Export two functions from one service (smallest: `logfmt.format` or
   `logd.log_info`) and prove the C symbol exists:
   `nm <objects> | grep log_info`. **Cheap, no Lobster involved.**
2. Write the dispatcher and a C driver that calls it from a plain `main`, run it
   under `run_native.sh`'s shim. This is a round trip *through the C ABI* and is
   worth committing on its own — it is the half that does not need Lobster.
3. Build Lobster from source with the dispatcher registered as a builtin. This is
   the expensive step and it is a toolchain task, not a services task.
4. Write `host_roundtrip.lobster`, run it, commit the transcript next to this
   file. Only then does BF4-10 move from NOT BUILT to RUNS.

## What I did not do, and why

I did not build Lobster from source tonight: it is a C++ build of a compiler that
this lane has never touched, it is outside the repository, and starting it without
a ruled ABI (Pax's 2026-11-02 decision) risks building the wrong calling
convention into a host binary. Steps 1 and 2 are the ones that can be done
before that ruling, and neither of them was on this round's list.

The report says BF4-10 NOT BUILT. Nothing in this document should be read as
"wired".
