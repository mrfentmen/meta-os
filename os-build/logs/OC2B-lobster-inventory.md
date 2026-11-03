# OC2B-176/177 — Lobster inventory + runtime

Runtime: `/opt/homebrew/bin/lobster` (present on build host, runs
all scripts below exit 0 unless noted).

Scripts in `lobster/` and what each does (read from headers + runs):

- `hello.lobster` — prints `HELLO FROM LOBSTER`. Baseline smoke.
- `agent-call.lobster` — defers to host tools (`echo` via host
  `list`/`echo` tools): `{"ok":true,"tools":["echo"]}` then
  `{"ok":true,"result":"hello from lobster"}`. Host-call path live.
- `memory.lobster` — home-scoped files (`homes/lobster-agent/note.txt`):
  note reads back across runs (persistence works).
- `identity.lobster` — home gate (own home read-only; cross-home
  reads REFUSED per README).
- `bus-send.lobster` / `bus-recv.lobster` — channel-dir pattern
  (`bus/general/`, send appends, recv drains). See bus verdict file.
- `service-roundtrip.lobster` — launches a real OS service
  (`../services/echo/echo.goose` via the goose toolchain binary) as a
  child process, stdin→stdout. No canned reply.
- `budget.lobster` — `spend()` gate: 3 calls recorded, 4th REFUSED
  (budget exhausted), refusal recorded.
- `scheduled.lobster` — busy-wait `seconds_elapsed` workaround (no
  sleep builtin).
- `shim.lobster`, `roundtrip.log`, `host.log`, `req-echo.json`,
  `req-list.json` — harness artifacts.
- `failures/identity-hash-comments.lobster` (+ `.err`) — OS-177
  museum: `#` comments illegal, fails EXACTLY as the `.err` records
  (expected-fail, not a defect).
