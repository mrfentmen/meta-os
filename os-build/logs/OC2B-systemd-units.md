# OC2B-030 — systemd user units (XDG alternative)

Shipped set (everything in `agent-layer/units/`, installed with no
hardcoded list):

- `oc2-queue.service` — `Type=simple`,
  `ExecStart=/usr/bin/python3 ${OC2_CHECKOUT}/server/queue/queue_service.py
  --port ${OC2_QUEUE_PORT}`, `Restart=on-failure`, `RestartSec=10`,
  `StartLimitIntervalSec=300` + `StartLimitBurst=3` (restart-loop cap here).
- `oc2-trio.service` — `Type=simple`,
  `ExecStart=…/trio_agent.py --nick oc2-trio`, `Restart=on-failure`,
  `RestartSec=10` (no StartLimit stanza — systemd defaults apply; gap vs
  queue's explicit cap noted, not hidden).
- `oc2-patrol.service` — `Type=oneshot`,
  `ExecStart=…/patrol.py --max-checks ${OC2_PATROL_MAX_CHECKS}
  --reserve-usd ${OC2_PATROL_RESERVE_USD}` (no `Restart=` — timer-driven).
- `oc2-patrol.timer` — `OnBootSec=30min`, `OnUnitActiveSec=60min`,
  `Persistent=true`, `WantedBy=timers.target`.

DELTA (honest): the task asks for units "disabled by default". SHIPPED
STATE = enabled (install.sh enables the whole shipped set). ISO PROPOSAL =
disabled by default (install-but-not-enable, session or user starts them).
One-line change, awaiting ISO-lane accept — NOT claimed as done.
