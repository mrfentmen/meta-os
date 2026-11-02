# Round 11, Part 1 — services

38 services. **27 run green**, 2 red (quarantined below), 8 have no importable driver (recorded with the reason). Every service has a six-section record in this directory and a README truth pass where the README was stale.

## Quarantined drivers

- `t115_display_r11.goose.red` — 7 assertions disagree with `display.goose`; not counted as proof.
- `t132_socket_r11.goose.red` — 5 assertions disagree with `socket.goose`; not counted as proof.

## What this round found

- Refusal-order findings: `pkt_add_link` checks capacity before duplicate id; `sup_register` checks capacity before duplicate name.
- `agenthost`: a second bind while CREATED replaces the pid instead of refusing; narrowing caps is legal while CREATED.
- `dhcp`: an ACK binds but installs no lease, so T1/T2 are unreachable through the state machine (filed).
- `display`: argument refusals after a full table are unreachable without a reset; the driver's reset path exposed it.
- `fs`: DESIGN path depth was 15 named components, not 16; corrected in DESIGN and README.
- Retired names now say so: `build`, `devmgr`, `registry`, `sockets` hold no module; their READMEs point at the real owner.
- Entry-only programs have no driver and say why: `echo`, `heartbeat`, `mcp-host`.

Full per-service evidence: `LOAD.md` and the 38 records in this directory.
