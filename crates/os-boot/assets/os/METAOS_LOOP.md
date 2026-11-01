# METAOS_LOOP.md — the self-development loop

`metaos-loop` is the agent inside Meta OS working on Meta OS: a small
POSIX sh driver (`bin/metaos-loop`) run by a systemd timer that, each
cycle, takes one task off a queue file, hands it to OpenCode headless,
runs the full test suites as a gate, and either commits the result as the
loop identity or resets the tree back to a checkpoint. It is deliberately
dumb: the intelligence lives in the agent and the queue, the driver only
enforces safety.

## Pieces

| Piece | Path |
|---|---|
| Driver | `bin/metaos-loop` (installed to `/usr/local/bin/metaos-loop`) |
| Service | `services/metaos-loop.service` (oneshot, runs as `relay`, cwd `/opt/relay`) |
| Timer | `services/metaos-loop.timer` (5 min after boot, then every 30 min) |
| Task queue | `LOOP_TASKS.md` at the checkout root (format documented in that file) |
| State dir | `/var/lib/metaos/loop` — lock, daily cycle counts, checkpoints record, per-cycle agent logs, gate log |
| Loop log | `/var/lib/metaos/loop/loop.log` — one line per outcome |
| Caps config | `/etc/metaos/loop.env` (optional, read by the service) |
| Kill switch | the STOP file, below |

## STOP file — the boss's kill switch

To halt the loop immediately, create the STOP file:

```
touch /var/lib/metaos/loop/STOP
```

The loop checks it before claiming the lock and again before committing;
a cycle never starts, and a cycle in flight rolls back instead of
committing, while it exists. Delete the file to resume. The path is
configurable with `METAOS_LOOP_STOP`.

## One cycle

1. STOP check. Lock claim (mkdir lock; a lock whose holder is dead is
   stolen, a live holder means the invocation exits quietly).
2. Daily cap check (default max 8 cycles/day, see config).
3. Require `$METAOS_LOOP_REPO` (default `/opt/relay`) to be a git
   checkout with a **clean tree**. Dirty tree: log `dirty-tree`, exit 1.
   The loop never works on top of someone else's changes.
4. Checkpoint: `git tag metaos-loop/cp-<timestamp>` + HEAD recorded in
   the state dir.
5. Next task: first `- [ ] ` line of `LOOP_TASKS.md`. None: log
   `no-tasks`, exit 0.
6. Agent run: `opencode run --auto "<task>"` with stdin closed
   (`</dev/null`), wrapped in `timeout` at the per-cycle cap
   (default 60 minutes).
7. Guards, in order: STOP re-check; **excluded paths** check; test gate.
   Any failure: `git reset --hard` to the checkpoint, tag deleted,
   outcome logged, exit 1.
8. Green + changed tree: the queue line is flipped to `- [x]` and
   everything is committed as identity `metaos-loop
   <metaos-loop@localhost>` with message `metaos-loop: <task>`. Green +
   unchanged tree: log `no-change`, nothing committed.
9. Push: only if `METAOS_LOOP_PUSH=1`. Plain `git push` (the checkout's
   configured credentials do the auth — firstboot collects a push token,
   the loop never sees or stores it). **The driver contains no `--force`
   anywhere; it can never force-push.**
10. Report: one line appended to the loop log; if `METAOS_LOOP_BUS_URL`
    and `METAOS_LOOP_BUS_TOKEN` are set, the same line is RPUSHed to the
    bus list (`METAOS_LOOP_BUS_KEY`, default `muse-bus:room:1`).

## Excluded paths — hard rule

The loop never commits changes to:

- `bus-tools/*`
- `tests/test_bus_admin_e2e.py`

If the agent touches either, the whole cycle is rolled back and logged
as `excluded-touch`. This is enforced by the driver after the agent run,
not by asking the agent nicely.

## Configuration

Environment (defaults in the driver; override via `/etc/metaos/loop.env`):

| Variable | Default | Meaning |
|---|---|---|
| `METAOS_LOOP_REPO` | `/opt/relay` | git checkout to work in |
| `METAOS_LOOP_STATE` | `/var/lib/metaos/loop` | lock, counts, logs |
| `METAOS_LOOP_STOP` | `$STATE/STOP` | kill-switch file |
| `METAOS_LOOP_QUEUE` | `$REPO/LOOP_TASKS.md` | task queue |
| `METAOS_LOOP_OPENCODE` | `opencode` | agent binary (PATH lookup) |
| `METAOS_LOOP_MAX_MINUTES` | `60` | per-cycle agent cap |
| `METAOS_LOOP_MAX_PER_DAY` | `8` | daily cycle cap |
| `METAOS_LOOP_TEST_CMD` | auto | gate command; auto = `cargo test --workspace` if `Cargo.toml` exists AND `npm test` if `package.json` exists, all must pass |
| `METAOS_LOOP_PUSH` | `0` | `1` = push after a green commit |
| `METAOS_LOOP_BUS_URL` / `METAOS_LOOP_BUS_TOKEN` | unset | bus report post; both required or no post |
| `METAOS_LOOP_BUS_KEY` | `muse-bus:room:1` | bus list key |

## Install (image build)

`build-image.sh` installs the driver to `/usr/local/bin`, installs and
enables the units (`metaos-loop.timer` in `relay.target.wants`, plus the
service itself), and creates `/var/lib/metaos/loop` owned by `relay`.
The live-build hook enables the same timer. Installed copies pick up new
versions through the passive updater (`metaos-update`) like everything
else; the loop ships in the repo, not baked into the image by hand.

## Tests

`os/os/loop-tests/metaos-loop.test.sh` runs the driver against throwaway git
repos with a stub agent (no real OpenCode, no network): green cycle
commits and closes the task, red gate rolls back, excluded-path touch
rolls back, STOP halts before and during a cycle, a live lock blocks a
second cycle, the daily cap holds, a dirty tree is refused.
