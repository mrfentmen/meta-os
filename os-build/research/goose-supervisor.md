# Supervisor contract (OS-157): who starts services, who restarts
# them, where their records live.

- Who starts: `supervisor.sh <name> <goose-file> [dir]` — one
  supervisor per service, launched at dev boot (and, later, by the
  init that owns Layer 4). No service starts itself.
- Who restarts: the same supervisor. On child exit it appends a
  crash line (exit code, timestamp), waits 2 s (backoff), and
  restarts. A clean stop (sentinel file) still logs, then the
  supervisor exits too — no restart after an ordered stop.
- Where records live: `<dir>/records.log`, append-only, one line
  per start/stop/crash (OS-160). The supervisor never rotates;
  rotation is the log service's job (not built yet — stated).
- Honest scope: the supervisor is a shell loop on the dev carrier
  because Goose has no process control (no spawn, no signals, no
  exit code inspection). The contract above is what a kernel-side
  Goose supervisor will implement against the K6 syscall channel;
  the dev-carrier loop proves the RECORD semantics, not the
  mechanism.
