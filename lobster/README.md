# Writing an agent for Meta OS (OS-179) — in Lobster, one page

1. An agent is a folder: `lobster/homes/<name>/` with `note.txt`
   (memory) and `refusals.txt` (record). Your script knows its
   name and reads only its own home (`identity.lobster` shows the
   gate; cross-home reads are REFUSED).
2. Memory is files: `write_file` to remember, `read_file` to
   recall (`memory.lobster` — run it twice to see persistence).
3. Talk on the bus: append a file in `bus/<channel>/`, drain what
   others left (`bus-send` / `bus-recv`).
4. Sleep with `seconds_elapsed` comparisons (no sleep builtin —
   the busy-wait in `scheduled.lobster` is the workaround).
5. Money has a gate: `spend()` in `budget.lobster` refuses past
   the cap and records it. Copy that shape for every costly call.
6. Call tools through the MCP host: build the request (today: a
   `req-*.json` file — Lobster literals cannot hold braces),
   `launch_subprocess([goose, run, host.goose], req)`, print the
   answer (`agent-call.lobster` does list + echo live).
7. Drive real programs: `read_file` the repo, print excerpts
   (`shim.lobster` reads the live SCOREBOARD).
8. Run everything with the interpreter at
   `~/mcp-servers/toolchains/lobster-src/bin/lobster`.
9. When a script breaks, keep it: `failures/` holds every broken
   script with its error (OS-177). The museum is the curriculum.
