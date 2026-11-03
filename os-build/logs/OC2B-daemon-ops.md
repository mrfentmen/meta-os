# OC2B-091 — Daemon operator doc (install/start/stop/logs per daemon)

Daemons = oc2-queue (simple), oc2-trio (simple), oc2-patrol (oneshot+timer).

- install: `sh agent-layer/install.sh` (copies units, reload, enable,
  linger, key hook). Idempotent; verify with
  `systemctl --user list-unit-files | grep oc2-`.
- start: `systemctl --user start oc2-queue oc2-trio oc2-patrol.timer`
  (patrol fires via timer; queue/trio run immediately).
- stop: `systemctl --user stop oc2-queue oc2-trio oc2-patrol oc2-patrol.timer`
  (OC2B-stop.md). Data kept.
- logs: `journalctl --user -u oc2-queue|oc2-trio|oc2-patrol` (OC2B-service-logs.md).
- restart policy: on-failure + caps (OC2B-daemon-watch.md); watchdog
  `agent-layer/watchdog.sh` supervises anywhere without systemd.
- alerts: `.blocked` state file + `BLOCKED cause=` journal line; owner OC2.
