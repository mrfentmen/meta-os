# Section D restart — the exact gap

R12-027..R12-034 ask for each cluster's services to be **killed and restarted with state
behaviour recorded**. That is only possible for a service the host can start. This record states
what can be started, what was started, and what cannot — with the command that produced the
counts.

## The check

```
grep -lE '^[[:space:]]*(fn|function)[[:space:]]+main\b' services/*/*.goose
```

Of the 38 service directories (excluding `tests/`, `common/`, `build/`, `hello/`), **three**
contain a runnable `main`:

| service | cluster | restart proof |
|---|---|---|
| `echo` | 3 | **PASS** — killed, restarted, answered again (`RESTART_PROOF.json`) |
| `heartbeat` | 4 | **PASS** — killed, restarted, append-only log grew, STOP exited 0 (`RESTART_PROOF.json`) |
| `mcp-host` | 5 | not drilled; it has a `main`, so the same harness can run it next round |

The other **35** either export `svc_entry` (the kernel/host supervisor calls it) or are libraries
with no process entry. `services/supervisor.sh` requires a `<name>.goose` with a `main`; running
one of these fails at compile time, not at runtime. Starting them needs the supervisor on the
kernel (K5/K6), which does not exist on this host.

## What is claimed

- `heartbeat`: killed mid-run, restarted, the existing log was appended to (not truncated), and
  the STOP sentinel ended it cleanly with exit 0.
- `echo`: killed and restarted; it answered a line before the kill and a new line after.
- No other service restart is claimed. `SECOND_RING.md` says `NOT TESTED` on those rows.

## What is not claimed

- These are host processes under `services/supervisor.sh`, not kernel services under the OS
  supervisor. No address space, no scheduler, no kernel restart.
- `mcp-host` is named but not drilled here.
- A 35-service restart requires a supervisor that can call `svc_entry` — that is the K5/K6 gap,
  not something this lane can fabricate with a shell loop.
