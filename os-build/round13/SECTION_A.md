# Round 13 — Section A audit index

Every row names the service-folder note and the gap record. `DONE` means the facet was read
against source and README; it does not mean the service implements the facet.

| task | service | facet | state | gaps | evidence |
|---|---|---|---|---|---|
| R13-001 | `agenthost` | startup contract | **DONE** | 2 gaps | `services/agenthost/CONTRACT_R13.md`, `services/agenthost/GAPS_R13.md` |
| R13-002 | `audit` | shutdown contract | **DONE** | 2 gaps | `services/audit/CONTRACT_R13.md`, `services/audit/GAPS_R13.md` |
| R13-003 | `board` | config defaults | **DONE** | 1 gap | `services/board/CONTRACT_R13.md`, `services/board/GAPS_R13.md` |
| R13-004 | `bootlog` | error envelope | **DONE** | 1 gap | `services/bootlog/CONTRACT_R13.md`, `services/bootlog/GAPS_R13.md` |
| R13-005 | `build` | log line format | **DONE** | 1 gap | `services/build/CONTRACT_R13.md`, `services/build/GAPS_R13.md` |
| R13-006 | `callmatrix` | state file shape | **DONE** | 1 gap | `services/callmatrix/CONTRACT_R13.md`, `services/callmatrix/GAPS_R13.md` |
| R13-007 | `console` | restart idempotence | **DONE** | 1 gap | `services/console/CONTRACT_R13.md`, `services/console/GAPS_R13.md` |
| R13-008 | `dashboard` | permission boundary | **DONE** | 1 gap | `services/dashboard/CONTRACT_R13.md`, `services/dashboard/GAPS_R13.md` |
| R13-009 | `devices` | timeout behaviour | **DONE** | 1 gap | `services/devices/CONTRACT_R13.md`, `services/devices/GAPS_R13.md` |
| R13-010 | `devmgr` | retry policy | **DONE** | 1 gap | `services/devmgr/CONTRACT_R13.md`, `services/devmgr/GAPS_R13.md` |
| R13-011 | `dhcp` | input validation | **DONE** | 2 gaps | `services/dhcp/CONTRACT_R13.md`, `services/dhcp/GAPS_R13.md` |
| R13-012 | `display` | output schema | **DONE** | 2 gaps | `services/display/CONTRACT_R13.md`, `services/display/GAPS_R13.md` |
| R13-013 | `dns` | dependency list | **DONE** | 2 gaps | `services/dns/CONTRACT_R13.md`, `services/dns/GAPS_R13.md` |
| R13-014 | `dock` | failure code table | **DONE** | 2 gaps | `services/dock/CONTRACT_R13.md`, `services/dock/GAPS_R13.md` |
| R13-015 | `echo` | metrics line | **DONE** | 2 gaps | `services/echo/CONTRACT_R13.md`, `services/echo/GAPS_R13.md` |
| R13-016 | `fs` | heartbeat line | **DONE** | 2 gaps | `services/fs/CONTRACT_R13.md`, `services/fs/GAPS_R13.md` |
| R13-017 | `heartbeat` | manifest entry | **DONE** | 2 gaps | `services/heartbeat/CONTRACT_R13.md`, `services/heartbeat/GAPS_R13.md` |
| R13-018 | `input` | socket use | **DONE** | 2 gaps | `services/input/CONTRACT_R13.md`, `services/input/GAPS_R13.md` |
| R13-019 | `logd` | file writes list | **DONE** | 2 gaps | `services/logd/CONTRACT_R13.md`, `services/logd/GAPS_R13.md` |
| R13-020 | `logfmt` | env var list | **DONE** | 1 gap | `services/logfmt/CONTRACT_R13.md`, `services/logfmt/GAPS_R13.md` |
| R13-021 | `mcp-host` | exit code table | **DONE** | 2 gaps | `services/mcp-host/CONTRACT_R13.md`, `services/mcp-host/GAPS_R13.md` |
| R13-022 | `net` | fixture coverage | **DONE** | 2 gaps | `services/net/CONTRACT_R13.md`, `services/net/GAPS_R13.md` |
| R13-023 | `netcfg` | README accuracy | **DONE** | 2 gaps | `services/netcfg/CONTRACT_R13.md`, `services/netcfg/GAPS_R13.md` |
| R13-024 | `notify` | deprecation markers | **DONE** | 0 gaps | `services/notify/CONTRACT_R13.md`, `services/notify/GAPS_R13.md` |
| R13-025 | `registry` | upgrade note | **DONE** | 2 gaps | `services/registry/CONTRACT_R13.md`, `services/registry/GAPS_R13.md` |

## Counts

- audited: 25 / 25
- gaps filed: 39
- no-source tasks filed as gaps: 1 (`build`)
- section state: **COMPLETE**
