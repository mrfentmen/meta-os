# The agent's first minute (OS-214): the structured side

An agent never reads the screen. It reads serial, where every
fact has a parseable twin:

- `META OS KERNEL - alive (K1)` — boot proof line.
- `mem map: N regions, usable X other Y` — memory facts.
- `uptime Ns ticks N` — the heartbeat (one line per second).
- `STATUS tasks=N ticks=N heap_free_kb=N` — the whole machine
  in one line, every `status` command.
- `user exit code N`, `user bad syscall N refused`,
  `INT user page-fault ... task killed` — userspace lifecycle.
- `HELLO FROM USERSPACE`, `sleeper: ...`, `C awake` — program
  output, plain lines.

The agent's minute: wait for alive → read mem map → watch
uptime advance → issue `status` (via the console channel) →
parse STATUS → decide. No screen scraping, no cursor codes,
no color dependence (colors are human-only decoration).
