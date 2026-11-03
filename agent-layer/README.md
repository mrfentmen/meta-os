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
