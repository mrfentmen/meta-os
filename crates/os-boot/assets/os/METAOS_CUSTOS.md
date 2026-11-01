# metaos-custos: the Custos patrol as a Meta OS service

Meta Custos is the night watch for machines (pack:
`os/worlds/custos/`). Stage 1 built the patrol loop
(`os/worlds/custos/runtime/patrol.py`): one patrol reads the CISA
known-exploited-vulnerabilities feed, checks watched hosts'
certificate expiry, service liveness, and undeclared sensitive-port
exposure, classifies every observation, and appends records. Stage 2
(the files here) runs that patrol as a standing Meta OS service.

## Pieces

- `bin/metaos-custos` — the driver (POSIX sh). One patrol per
  invocation; owns the kill switch, the lock, and the state layout.
- `services/metaos-custos.service` — oneshot unit, runs as the
  `relay` user from `/opt/relay`, optional environment from
  `/etc/metaos/custos.env`.
- `services/metaos-custos.timer` — fires the service 10 minutes
  after boot and then hourly.
- Build wiring: `build-image.sh` and `build-live.sh` install the
  driver to `/usr/local/bin`, enable the timer under
  `relay.target`, and create `/var/lib/metaos/custos` owned by
  `relay`.

## Configuration

The installation configures what it watches in
`/etc/metaos/custos.json` (shape: the pack's
`os/worlds/custos/hosts.example.json`). With no config file the
driver logs `not configured` and exits 0 — it never invents a host
list, and the example config is never used as a default.

Driver environment (all optional):

| Variable | Default | Meaning |
|---|---|---|
| `METAOS_CUSTOS_REPO` | `/opt/relay` | Repo checkout the patrol runs from |
| `METAOS_CUSTOS_STATE` | `/var/lib/metaos/custos` | State dir: records, seen-state, log, lock |
| `METAOS_CUSTOS_STOP` | `$STATE/STOP` | Kill-switch file path |
| `METAOS_CUSTOS_CONFIG` | `/etc/metaos/custos.json` | Watched-hosts config |
| `METAOS_CUSTOS_PATROL` | `python3 $REPO/os/worlds/custos/runtime/patrol.py` | Patrol command prefix |

## State layout (`/var/lib/metaos/custos`)

- `records.jsonl` — the patrol record: one JSON line per
  observation, per escalation, per patrol summary. Appended, never
  rewritten.
- `seen.json` — CVE ids already recorded, so a feed entry alerts
  once, not every patrol.
- `custos.log` — one line per driver run.
- `STOP` — create this file to halt the service (the boss's kill
  switch). The driver checks it before anything else and exits 0.

## Honest status

The driver is pinned by tests (`tests/custos/test_driver.py`:
kill switch, live/stale lock, not-configured no-op, patrol
invocation with the right paths). It has **not** yet run on a booted
Meta OS image; the patrol's host probes have never run live from a
machine with a direct network path to watched hosts. The pack
manifest (`os/worlds/custos/pack.json`) carries the same statement.
