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
