# Round 13 — Section C restart and state-survival index

The requested proof is a before/after state hash plus a restart log. One unit has
a real file-backed daemon and was drilled. The other twenty-four have no process,
no state file, or only volatile memory, so their records state that and file the
gap instead of inventing a hash.

| task | service | state | gaps | record |
|---|---|---|---|---|
| R13-051 | `dashboard` | GAP | 1 gap | `os-build/round13/restarts/R13-051.md` |
| R13-052 | `devices` | GAP | 1 gap | `os-build/round13/restarts/R13-052.md` |
| R13-053 | `devmgr` | GAP | 1 gap | `os-build/round13/restarts/R13-053.md` |
| R13-054 | `dhcp` | GAP | 1 gap | `os-build/round13/restarts/R13-054.md` |
| R13-055 | `display` | GAP | 1 gap | `os-build/round13/restarts/R13-055.md` |
| R13-056 | `dns` | GAP | 1 gap | `os-build/round13/restarts/R13-056.md` |
| R13-057 | `dock` | GAP | 1 gap | `os-build/round13/restarts/R13-057.md` |
| R13-058 | `echo` | GAP | 1 gap | `os-build/round13/restarts/R13-058.md` |
| R13-059 | `fs` | GAP | 1 gap | `os-build/round13/restarts/R13-059.md` |
| R13-060 | `heartbeat` | OBSERVED | 0 gaps | `os-build/round13/restarts/R13-060.md` |
| R13-061 | `input` | GAP | 1 gap | `os-build/round13/restarts/R13-061.md` |
| R13-062 | `logd` | GAP | 1 gap | `os-build/round13/restarts/R13-062.md` |
| R13-063 | `logfmt` | GAP | 1 gap | `os-build/round13/restarts/R13-063.md` |
| R13-064 | `mcp-host` | GAP | 1 gap | `os-build/round13/restarts/R13-064.md` |
| R13-065 | `net` | GAP | 1 gap | `os-build/round13/restarts/R13-065.md` |
| R13-066 | `netcfg` | GAP | 1 gap | `os-build/round13/restarts/R13-066.md` |
| R13-067 | `notify` | GAP | 1 gap | `os-build/round13/restarts/R13-067.md` |
| R13-068 | `registry` | GAP | 1 gap | `os-build/round13/restarts/R13-068.md` |
| R13-069 | `session` | GAP | 1 gap | `os-build/round13/restarts/R13-069.md` |
| R13-070 | `settings` | GAP | 1 gap | `os-build/round13/restarts/R13-070.md` |
| R13-071 | `shell` | GAP | 1 gap | `os-build/round13/restarts/R13-071.md` |
| R13-072 | `socket` | GAP | 1 gap | `os-build/round13/restarts/R13-072.md` |
| R13-073 | `sockets` | GAP | 1 gap | `os-build/round13/restarts/R13-073.md` |
| R13-074 | `storage` | GAP | 1 gap | `os-build/round13/restarts/R13-074.md` |
| R13-075 | `supervisor` | GAP | 1 gap | `os-build/round13/restarts/R13-075.md` |

## Counts

- audited: 25 / 25
- observed with hashes: 1 (`heartbeat`)
- gaps filed: 24
- restart log: `os-build/round13/restarts/R13-060.log`
