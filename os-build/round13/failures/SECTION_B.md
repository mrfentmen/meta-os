# Round 13 — Section B failure-path index

Each record states whether the requested failure input exists. A condition with no input surface
is filed as a gap; it is not simulated with a call that looks like the condition but is not.

| task | service | condition | state | gaps | record |
|---|---|---|---|---|---|
| R13-026 | `bootlog` | missing config | **GAP** | 1 gap | `os-build/round13/failures/R13-026.md` |
| R13-027 | `build` | malformed config | **GAP** | 1 gap | `os-build/round13/failures/R13-027.md` |
| R13-028 | `callmatrix` | dependency down | **GAP** | 1 gap | `os-build/round13/failures/R13-028.md` |
| R13-029 | `console` | state file corrupt | **GAP** | 1 gap | `os-build/round13/failures/R13-029.md` |
| R13-030 | `dashboard` | state file missing | **GAP** | 1 gap | `os-build/round13/failures/R13-030.md` |
| R13-031 | `devices` | port already in use | **GAP** | 1 gap | `os-build/round13/failures/R13-031.md` |
| R13-032 | `devmgr` | permission denied on write | **GAP** | 1 gap | `os-build/round13/failures/R13-032.md` |
| R13-033 | `dhcp` | input past the size cap | **GAP** | 1 gap | `os-build/round13/failures/R13-033.md` |
| R13-034 | `display` | empty input | **OBSERVED** | 0 gaps | `os-build/round13/failures/R13-034.md` |
| R13-035 | `dns` | unknown command | **GAP** | 1 gap | `os-build/round13/failures/R13-035.md` |
| R13-036 | `dock` | dependency returns an error envelope | **GAP** | 1 gap | `os-build/round13/failures/R13-036.md` |
| R13-037 | `echo` | disk full on write | **GAP** | 1 gap | `os-build/round13/failures/R13-037.md` |
| R13-038 | `fs` | killed mid-write | **GAP** | 1 gap | `os-build/round13/failures/R13-038.md` |
| R13-039 | `heartbeat` | clock moved backwards | **GAP** | 1 gap | `os-build/round13/failures/R13-039.md` |
| R13-040 | `input` | duplicate start | **OBSERVED** | 0 gaps | `os-build/round13/failures/R13-040.md` |
| R13-041 | `logd` | start while stopping | **GAP** | 1 gap | `os-build/round13/failures/R13-041.md` |
| R13-042 | `logfmt` | bad env var value | **GAP** | 1 gap | `os-build/round13/failures/R13-042.md` |
| R13-043 | `mcp-host` | env var missing | **GAP** | 1 gap | `os-build/round13/failures/R13-043.md` |
| R13-044 | `net` | log target unwritable | **GAP** | 1 gap | `os-build/round13/failures/R13-044.md` |
| R13-045 | `netcfg` | fixture missing | **GAP** | 1 gap | `os-build/round13/failures/R13-045.md` |
| R13-046 | `notify` | manifest entry stale | **GAP** | 1 gap | `os-build/round13/failures/R13-046.md` |
| R13-047 | `registry` | socket peer gone | **GAP** | 1 gap | `os-build/round13/failures/R13-047.md` |
| R13-048 | `session` | peer sends garbage | **GAP** | 1 gap | `os-build/round13/failures/R13-048.md` |
| R13-049 | `settings` | timeout below the work size | **GAP** | 1 gap | `os-build/round13/failures/R13-049.md` |
| R13-050 | `shell` | restart loop (3 fast deaths) | **GAP** | 1 gap | `os-build/round13/failures/R13-050.md` |

## Counts

- audited: 25 / 25
- gaps filed: 23
- observed without a gap: 2 (`display` empty input, `input` duplicate start)
- test: `services/tests/t140_r13_failpaths_b.goose` — exit 0, pass=9 fail=0
