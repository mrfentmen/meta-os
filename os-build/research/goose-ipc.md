# IPC contract (OS-158): messages, errors, timeouts

Between the Goose layer and the kernel (Section F syscalls).

- Dev carrier (today): stdio JSON-lines. Request: one JSON object
  per line (`{"tool":...,"args":{...}}`). Response: one JSON
  object per line (`{"ok":true,...}` / `{"ok":false,"error":...}`).
  Errors are VALUES, never crashes: unknown tool, bad JSON, and
  unmapped buffers all answer with `ok:false` and a log line.
  Timeouts: the caller decides (2 s default in the runner); the
  service answers or the caller records a timeout and moves on.
- Kernel (when K6 lands): the same shapes over syscalls —
  `write` carries requests out, replies come back through a
  reply buffer (design; the syscall numbers exist, OS-075).
- The echo service proves the dev-carrier end; the MCP host
  proves request/response/error logging; the Lobster agent-call
  proves a second language can speak it.
