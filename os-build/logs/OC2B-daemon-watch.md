# OC2B-084 — Daemon restart policy (watchdog + units)

Units: queue + trio `Restart=on-failure`, `RestartSec=10`; queue adds
`StartLimitIntervalSec=300`/`StartLimitBurst=3`; trio has no StartLimit
stanza (systemd defaults apply — gap named, not hidden). Patrol is
oneshot, timer-driven, no Restart.

Watchdog (`agent-layer/watchdog.sh`): supervises any service —
dead (kill -0 fail, non-zero exit) or hung (HEALTH_SH fails) →
kill + restart, every restart logged with timestamp + cause.
`MAX_RESTARTS` cap: the next failure writes `NAME.blocked` and exits 2
— never restart-loops (proven: `tests/agent-layer/test_watchdog.py`,
4 tests green, kill -9 → restart with `cause=dead-exit-137`;
`false` health → restart with `cause=hung-health-fail`;
cap=1 + 2 kills → exit 2 + `.blocked` exists; clean `exit 0`
propagates with no restart).

State dir: `$LOGDIR/NAME.{log,restarts,blocked}`. Alert path: the
`.blocked` file + `BLOCKED cause=…` log line are the alert (no pager in
tree — sample: `2026-…Z svc BLOCKED cause=hung-health-fail restarts=2
(cap 1)`). Owner on alert: OC2 lane; escalation: lane status BLOCKED row.
