# OC2B-031 — Start order + dependencies (quoted from unit files)

Order: **queue → trio → patrol**.

- `oc2-queue.service`: `After=network-online.target`,
  `Wants=network-online.target`. Root — no sibling dependency.
- `oc2-trio.service`: `After=network-online.target oc2-queue.service`,
  `Wants=network-online.target`, `Requires=oc2-queue.service`. Trio never
  runs without the queue.
- `oc2-patrol.service`: `After=network-online.target oc2-queue.service
  oc2-trio.service`, `Wants=network-online.target`,
  `Requires=oc2-queue.service oc2-trio.service`. Requires both up.
- `oc2-patrol.timer`: first fire `OnBootSec=30min`, then every
  `OnUnitActiveSec=60min`, `Persistent=true` (catch-up if a tick missed).

Verify on target: `systemctl --user list-dependencies oc2-patrol.service`.
