# OC2B-009 — runtime config files (read at startup, with defaults)

Source: `agent-layer/env.example`, `agent-layer/units/*`, `agent-layer/install.sh`,
environ reads in `server/queue/*.py`.

## 1. `~/.config/oc2-agent/env` (from `agent-layer/env.example`)

Non-secret defaults, committed template. install.sh creates once (with
`OC2_CHECKOUT=<repo-root>` substituted), otherwise refreshes `OC2_CHECKOUT`
+ backfills missing keys; fails closed on secret-looking values.

| Key | Default | Consumed by | Optional? |
|---|---|---|---|
| `OC2_CHECKOUT` | `/home/relay/bake/meta-os` (OVERWRITTEN at install) | unit `ExecStart` paths | NO — rewritten by installer |
| `OC2_QUEUE_PORT` | `8935` | queue `--port` | yes |
| `OC2_PATROL_MAX_CHECKS` | `20` | patrol `--max-checks` | yes |
| `OC2_PATROL_RESERVE_USD` | `5` | patrol `--reserve-usd` | yes |
| `TRIO_JOB_NS` | `oc2` | `trio_store.NS` (default `trio`) | yes |
| `LIVECAMS_API_URL` | `https://webcams.nyctmc.org/api/cameras` | livecams `--api-url` | yes |

OC2B-010 verdict: exactly ONE absolute dev-home path in the tree —
`env.example:3` (`OC2_CHECKOUT=/home/relay/bake/meta-os`). It is the
template placeholder the installer substitutes per-host (proof:
`OC2B-config-paths.txt`, 1 line). No code path hardcodes a home dir.

## 2. systemd user units (`agent-layer/units/`, copied verbatim, enabled)

All four carry `EnvironmentFile=%h/.config/oc2-agent/env`. No
`Environment=` literals, no secrets in any unit.

- `oc2-queue.service`: `Type=simple`, `After/Wants=network-online.target`,
  `ExecStart=/usr/bin/python3 ${OC2_CHECKOUT}/server/queue/queue_service.py
  --port ${OC2_QUEUE_PORT}`, `Restart=on-failure`, `RestartSec=10`,
  `StartLimitIntervalSec=300`, `StartLimitBurst=3`.
- `oc2-trio.service`: `Type=simple`, `After/Wants=network-online.target`,
  `Requires=oc2-queue.service`, `ExecStart=…/trio_agent.py --nick oc2-trio`,
  `Restart=on-failure`, `RestartSec=10`.
- `oc2-patrol.service`: `Type=oneshot`,
  `After=network-online.target oc2-queue.service oc2-trio.service`,
  `Requires=oc2-queue.service oc2-trio.service`,
  `ExecStart=…/patrol.py --max-checks … --reserve-usd …`.
- `oc2-patrol.timer`: `OnBootSec=30min`, `OnUnitActiveSec=60min`,
  `Persistent=true`.

Order: queue → trio → patrol (oneshot at login + hourly). Full start-order
table: `OC2B-service-order.md`.

## 3. Other environ (all optional; no config file)

REQUIRED at runtime (process environ only, never a file): `SPARK_API_KEY`
(absent → named error, guardrail refuses, patrol pauses LOUD).
Store/data: `TRIO_CREW_DATA_DIR`, `TRIO_LOCAL_DB`, `TRIO_STORE`,
`TRIO_UPSTASH_HOST`, `METAOS_MODEL_RECEIPTS`. Behavior:
`TRIO_CREW_DISPATCH_URL` (default loopback `:8935/dispatch-simulated`),
`TRIO_SPARK_VIA_HELPER` (DEV-only), `TRIO_SAM_SEGMENT`,
`TRIO_REVIEW_WONDER`, `TRIO_JUDGE_MODEL`, supervisor `TRIO_SUPERVISOR_*`.
Key handoff: login-shell hook (`~/.profile`/`~/.zprofile` marker) runs
`systemctl --user import-environment SPARK_API_KEY`.

## 4. First-boot behaviour

Install → `daemon-reload` → enable → linger → hook. At boot/login: queue
binds 127.0.0.1:8935; trio drains; patrol runs one bounded cycle at login
then hourly. No setup wizard blocks the desktop; no-key state is a loud
pause, never silence.
