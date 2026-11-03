# Round 13 — Section C restart and state-survival index

The requested proof is a before/after state hash plus a restart log. One unit has a real file-backed
daemon and was drilled; the other nine have no process, no state file, or only volatile memory, so
their records state that and file the gap instead of inventing a hash.

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

## Counts

- audited: 10 / 10
- observed with hashes: 1 (`heartbeat`)
- gaps filed: 9
- restart log: `os-build/round13/restarts/R13-060.log`
