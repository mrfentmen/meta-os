# Lobster Runtime Contract (Lane C, R5 C8)

Scope: what a layer-6 shell can call TODAY on the host interpreter.
Every interface below is **WRITTEN (host-only)**: implemented as a
`.lobster` module whose self-test passes on the host interpreter
(`lobster/run-tests.sh`, 9/9 green). None is kernel-enforced, none is
COMPILED, none is VERIFIED in QEMU — the kernel mediation Lane A asks
for (`os-build/LAYERS_TRUTH.md:23`, A11.4) does not exist yet.

Interpreter (C1): `~/mcp-servers/toolchains/lobster-src/bin/lobster`
(symlinked as `/opt/homebrew/bin/lobster`), aardappel/lobster source
at git `6c1389c`, Mach-O arm64. No `--version` flag; version is the git
hash. All script paths below are relative to `lobster/` AND resolve
relative to the **script file's directory, not CWD** (proven by the
`wr_probe` series: a script in `/tmp` reads/writes `/tmp`, never CWD).
`write_file` does NOT create parent dirs and fails silently without
them — callers (or `run-tests.sh`) must `mkdir -p` first.
`launch_subprocess` needs an **absolute** `argv[0]` (bare `echo`
returns -1; `/bin/echo` returns 0).

## 1. Identity — WRITTEN

```lobster
home_read(caller: string, name: string, rel: string) -> string
```
Serves the file `homes/<caller>/note.txt` only when `name == caller`
and `rel == "note.txt"`; returns `"MISSING"` for an absent own note and
`"REFUSED"` for cross-home reads, path escapes (`../`), and any other
filename. Enforcement is script convention + review, NOT the kernel.
Impl: `lobster/runtime/rt_identity.lobster:7-17`, self-test `:19-40`
prints `IDENTITY SELFTEST OK`, RC 0.

## 2. Lifecycle — WRITTEN

```lobster
transition(from: string, to: string) -> string   // or "REFUSED"
read_state() -> string                          // "NONE"|"BORN"|"RUNNING"|"STOPPED"
```
Legal edges only: `NONE->BORN->RUNNING->STOPPED`; `STOPPED` is
terminal. State persists in `rt_state/lifecycle_agent.state` (script-
dir-relative) so a restarted process re-reads it.
Impl: `lobster/runtime/rt_lifecycle.lobster:11-25`, self-test `:27-52`
prints `LIFECYCLE SELFTEST OK`, RC 0.

## 3. Capabilities — WRITTEN

```lobster
call(caps: [string], cap: string) -> string     // "OK:<cap>" or "REFUSED"
```
No ambient authority: a call runs only if `cap` is in the token's
granted list; match is exact (case-sensitive). There is no
grant/revoke syscall — tokens are caller-held values.
Impl: `lobster/runtime/rt_capabilities.lobster:9-18`, self-test
`:20-37` prints `CAPABILITIES SELFTEST OK`, RC 0.

## 4. Audit record — WRITTEN

```lobster
// lobster runtime/rt_audit.lobster -- write <nonce>    -> appends, prints "AUDIT WROTE event-<nonce>"
// lobster runtime/rt_audit.lobster -- verify <nonce>   -> prints "AUDIT DURABLE OK event-<nonce>", RC 0/1
```
Record shape: `AUDIT <date_time_string> lane-c event-<nonce>\n`,
appended to `rt_state/audit.log`. Write and verify run as TWO
SEPARATE interpreter processes (C15): the file is the memory, and a
wrong nonce fails with `AUDIT FAIL`, RC 1 (negative path verified).
Impl: `lobster/runtime/rt_audit.lobster:11-37`.

## 5. Budget — WRITTEN

```lobster
spend(what: string) -> bool   // true = debited; false = refused AND recorded
```
`budget_left` starts at the cap; at zero `spend` returns false and
appends `refused: <what>` to `rt_state/budget_refusals.txt`. Same
shape as the demo `lobster/budget.lobster:8-16`, but self-testing with
RC propagation.
Impl: `lobster/runtime/rt_budget.lobster:9-22`, self-test `:24-45`
prints `BUDGET SELFTEST OK`, RC 0.

## 6. Transport / bus — WRITTEN (appendix: brief C8 said five; C7 needs this one)

```lobster
send(channel: string, name: string, body: string) -> string
drain(channel: string) -> string                // "name=body;..." then deletes
```
File-channel pattern under `bus/<channel>/` (drain reads back in name
order and deletes, so a second drain is empty). PLUS a proven native
socket path: Lobster HAS `tcp.connect/send/receive/connected`
(builtin list; semantics per `tests/tcp/tcp.lobster` in the toolchain
source). `lobster/board-roundtrip.lobster` speaks HTTP/1.0 over raw TCP
to the live board on `127.0.0.1:18935` with no curl: JSON braces are
built via `unicode_to_string([123/125/34])` because `{}` in a literal
means interpolation (compile error proven). Impl + proofs:
`lobster/runtime/rt_bus.lobster:11-28` (`BUS SELFTEST OK`),
`lobster/board-roundtrip.lobster:9-57` (`BOARD ROUNDTRIP OK`, RC 0).

## What is NOT BUILT

Kernel mediation of any of the above: no gate runs in
`kernel/src/user.rs` syscall table 0-6, no serial-log proof line, no
Goose-service load (same gaps as `os-build/LAYERS_TRUTH.md:20,47`).
A layer-6 shell built on these contracts runs on the host interpreter
only and must be re-proven the day a syscall backs it.
