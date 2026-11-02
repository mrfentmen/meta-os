# Round 11 load and run table

Generated from `os-build/layer1/host/r11_run.log` and the driver transcripts by the coordinator, 2026-11-02. Numbers are what the host run printed; a service with no driver says so.

| service | result | pass | fail | LOAD line |
|---|---|---|---|---|
| `CONVENTIONS` | NO TEST | 0 | 0 | `no LOAD line` |
| `agenthost` | RUNS | 42 | 0 | `LOAD agenthost ops=240 ok=240 refused=0` |
| `audit` | RUNS | 25 | 0 | `LOAD audit ops=80 ok=80 refused=0` |
| `board` | RUNS | 39 | 0 | `LOAD board ops=240 ok=24 refused=216` |
| `bootlog` | RUNS | 16 | 0 | `LOAD bootlog ops=220 ok=220 refused=0` |
| `build` | NO TEST | 0 | 0 | `no LOAD line` |
| `callmatrix` | RUNS | 29 | 0 | `LOAD callmatrix ops=3100 ok=300 refused=2800` |
| `console` | RUNS | 24 | 0 | `LOAD console ops=320 ok=255 refused=65` |
| `dashboard` | RUNS | 35 | 0 | `LOAD dashboard ops=1000 ok=990 refused=10` |
| `devices` | RUNS | 44 | 0 | `LOAD devices ops=700 ok=700 refused=0` |
| `devmgr` | NO TEST | 0 | 0 | `no LOAD line` |
| `dhcp` | RUNS | 41 | 0 | `LOAD dhcp ops=20 ok=20 refused=0` |
| `display` | FAILS | 41 | 7 | `LOAD display ops=800 ok=0 refused=800` |
| `dns` | RUNS | 50 | 0 | `LOAD dns ops=100 ok=90 refused=10` |
| `dock` | RUNS | 67 | 0 | `LOAD dock ops=100 ok=100 refused=0` |
| `echo` | NO TEST | 0 | 0 | `no LOAD line` |
| `fs` | RUNS | 46 | 0 | `LOAD fs ops=200 ok=200 refused=0` |
| `heartbeat` | NO TEST | 0 | 0 | `no LOAD line` |
| `input` | RUNS | 33 | 0 | `LOAD input ops=200 ok=200 refused=0` |
| `logd` | RUNS | 23 | 0 | `LOAD logd ops=240 ok=64 refused=176` |
| `logfmt` | RUNS | 25 | 0 | `LOAD logfmt ops=300 ok=300 refused=0` |
| `mcp-host` | NO TEST | 0 | 0 | `no LOAD line` |
| `net` | RUNS | 55 | 0 | `LOAD net ops=100 ok=100 refused=0` |
| `netcfg` | RUNS | 61 | 0 | `LOAD netcfg ops=100 ok=100 refused=0` |
| `notify` | RUNS | 48 | 0 | `LOAD notify ops=120 ok=12 refused=108` |
| `registry` | NO TEST | 0 | 0 | `no LOAD line` |
| `session` | RUNS | 48 | 0 | `LOAD session ops=120 ok=120 refused=0` |
| `settings` | RUNS | 33 | 0 | `LOAD settings ops=120 ok=107 refused=13` |
| `shell` | RUNS | 23 | 0 | `LOAD shell ops=200 ok=100 refused=100` |
| `socket` | FAILS | 46 | 5 | `LOAD socket ops=320 ok=320 refused=0` |
| `sockets` | NO TEST | 0 | 0 | `no LOAD line` |
| `storage` | RUNS | 38 | 0 | `LOAD storage ops=640 ok=640 refused=0` |
| `supervisor` | RUNS | 79 | 0 | `LOAD supervisor ops=640 ok=500 refused=140` |
| `time` | RUNS | 41 | 0 | `LOAD time ops=1000 ok=1000 refused=0` |
| `timesync` | RUNS | 26 | 0 | `LOAD timesync ops=100 ok=100 refused=0` |
| `updater` | RUNS | 47 | 0 | `LOAD updater ops=100 ok=50 refused=50` |
| `updater_client` | RUNS | 51 | 0 | `LOAD updater_client ops=100 ok=100 refused=0` |
