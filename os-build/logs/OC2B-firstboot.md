# OC2B-041 — First-boot behaviour

No setup wizard blocks the desktop. install.sh enables everything at
install (copies units verbatim → daemon-reload → enable → linger →
login-shell SPARK_API_KEY hook). Units `WantedBy=default.target`
(+ `timers.target`) start them with zero clicks.

At boot/login: queue binds 127.0.0.1:8935; trio drains open jobs in its
poll loop; patrol runs one bounded cycle (`--max-checks`, default 20) at
login plus hourly via timer (`OnBootSec=30min`, `OnUnitActiveSec=60min`,
`Persistent=true`).

No key = loud pause, never silence (named RuntimeError, guardrail
refuse, patrol `paused-budget` in crew-status.json + event feed). Base
`metaos1-firstboot.sh` is mimeapps-only, exits 0, never touches OC2.
Full config: OC2B-runtime-config.md. Order: OC2B-service-order.md.
