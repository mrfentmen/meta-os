# OC2 agent layer — what runs at login

Patrol + crew + queue + livecams, as systemd user units (Debian/Xubuntu target).
`loginctl enable-linger` keeps them alive without an open session.

## Order
1. `oc2-queue.service` — local job API on 127.0.0.1:8935 (loopback only). Must be up first.
2. `oc2-patrol.service` — one bounded patrol cycle (`--max-checks 20`) at login, after the queue.
3. `oc2-patrol.timer` — repeats the cycle hourly (`OnBootSec=30min`, `OnUnitActiveSec=60min`).

`crew.py` is patrol's library; `livecams.py` is patrol's camera source + CLI. Neither runs alone.

## Key
`SPARK_API_KEY` is NEVER in these files. The login shell imports it into the user
manager (`systemctl --user import-environment`, wired by `install.sh` into the profile).
Without a key the guardrail refuses and patrol pauses LOUD (existing behavior) — check
`journalctl --user -u oc2-patrol` for the pause line rather than silence.

## Check health
`systemctl --user status oc2-queue oc2-patrol`
`journalctl --user -u oc2-patrol -n 50` (cycle counts)
`systemctl --user list-timers oc2-patrol.timer`

## Stop
`systemctl --user stop oc2-queue oc2-patrol.timer`

## Logs that prove a boot
`journalctl --user -b -u oc2-queue -u oc2-patrol` — queue start line + patrol cycle counts,
no hand-typed commands between login and the first completed cycle.

## In the ISO image

`stage.sh <root>` writes this layer into a root filesystem without a daemon:

    sh agent-layer/stage.sh <root>
    sh agent-layer/stage.sh <root> --check

It copies the queue runtime to `/usr/share/metaos/agent` (keeping
`server/queue` and `js/` in the shape `trio_repo.py` expects), the four units
to `/usr/lib/systemd/user`, and creates the `.wants` symlinks by hand so the
image needs no systemd running at build time. The env template goes to
`/etc/skel/.config/oc2-agent/env` with `OC2_CHECKOUT` pointed at the payload,
and `meta-agent-login.sh` goes to `/etc/xdg/autostart` to seed older accounts
and start the units at login.

Lingering is not enabled: `loginctl enable-linger` needs root after install.
The layer runs for the session, which is what the desktop needs.

## Scheduled health check

`oc2-health.timer` runs `meta-agent-health.py` two minutes after login and
every five minutes after that. One run checks six things: the six units exist,
the five enable links are whole, the queue answers on its loopback port, and
how old the watchman heartbeat is. It writes
`~/.local/state/oc2-agent/health.json` plus one line in `health.jsonl`, and
exits 1 on a failed row so `systemctl --user status oc2-health` shows it.

An absent watchman heartbeat is recorded as `absent`, not a failure — the ISO
does not ship the relay watchman, and a clean install must not alarm.

No restart is wired in. Set `META_AGENT_RESTART` to a command and it runs once
after a failed queue row, with its exit code written as a `restart` row. Until
a lane owner supplies the watchman's start command, nothing guesses one.

Tests: `python3 tests/test_agent_health.py` — real staged roots, a real
listening socket, real child processes.

## Notifications

`agents/notify.mjs` is the layer's one voice. A job refused, failed or finished
writes a notice; the watchman calls it, and nothing else decides on its own
what is worth saying.

Three sinks, in order of reach:

| Sink | When | Where it lands |
|---|---|---|
| `journal` | always | `~/.local/state/oc2-agent/notices.jsonl`, one line per notice |
| `desktop` | a session has `DISPLAY` or `WAYLAND_DISPLAY` | `notify-send`, `critical` for an alarm |
| `webhook` | only when `METAOS_NOTIFY_WEBHOOK` is set | one JSON POST, 3 s timeout |

An alarm with the same key is suppressed for 15 minutes after it rings. It is
still written to the journal, marked `suppressed: true` — quiet, not silent.
Notes are never suppressed.

A dead webhook does not throw and is not recorded as delivered; the notice
says which sinks answered.

Not wired: the health probe's failure goes to the journal through systemd, not
through this module, because it is Python and a second notifier is a second
set of rules. `METAOS_NOTIFY_WEBHOOK` is not in `.env.example` yet — it belongs
to whoever owns that file.

## Submitting work

A person types one of these:

    meta-ask --list                                   # who can take work
    meta-ask "sweep the tree for stray licenses" --agent watch
    meta-ask "..." --agent aegis --dry-run            # validate, write nothing

A script uses the node tool underneath:

    node agents/submit.mjs --root ~/.local/state/oc2-agent \
      --agent aegis --orders "sweep the tree" [--id my-job]

Both refuse an unknown agent, a draft agent, empty orders, an unsafe id and an
id already on the board. The write is a rename, so the watchman never sees half
a job. `--max-continues N` sets the continuation bound for that job.

## Watching it

    meta-agent-status          # heartbeat, board, notices
    meta-agent-status --json   # the same, for a program

Both read `$METAOS_AGENT_STATE`, else `$XDG_STATE_HOME/oc2-agent` — the same
directory the units pass to the watchman.

## After a failure

A job that exits non-zero is retried **once**, on the next poll, with its baton
carried over — the same agent, the same work, the notes it had when it died.
The second failure is final: the job writes `retry: "exhausted"` and raises an
alarm notice, so a loop that never works cannot look busy forever. A job that
asked to continue is continued, not retried; the two paths never overlap.

A stale watchman heartbeat is a failed health row. `oc2-health.service` ships
`META_AGENT_WATCHMAN_RESTART=systemctl --user restart oc2-watchman.service`, so
a hung relay is restarted once and the attempt is recorded as
`restart-watchman`.

