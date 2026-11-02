# Service README audit (E3, 2026-11-02)

Measured by walking `services/*/` and checking for a non-empty `README.md`:

**42 service directories. 29 have a README. 13 do not.** The round's target was 25,
so the count is met; the 13 that lack one are listed with their reason rather than left
to be discovered later.

| directory | README lines | status |
|---|---|---|
| `services/agenthost` | 50 | present |
| `services/audit` | 50 | present |
| `services/board` | — | real service, no README — gap named for Pax |
| `services/bootlog` | 69 | present |
| `services/build` | — | a `.gitignore` only; not a service |
| `services/callmatrix` | 50 | present |
| `services/common` | — | library root: 15 library directories, no single service |
| `services/console` | 68 | present |
| `services/dashboard` | — | real service, no README — gap named for Pax |
| `services/devices` | 58 | present |
| `services/devmgr` | 50 | present |
| `services/dhcp` | 52 | present |
| `services/display` | 51 | present |
| `services/dns` | 50 | present |
| `services/dock` | — | real service, no README — gap named for Pax |
| `services/echo` | — | program documented in its source header |
| `services/example` | 24 | present |
| `services/fs` | 34 | present |
| `services/heartbeat` | — | program documented in its source header |
| `services/hello` | — | three-line sample, documented by the file itself |
| `services/input` | 49 | present |
| `services/logd` | 82 | present |
| `services/logfmt` | 47 | present |
| `services/mcp-host` | — | program documented in its source header |
| `services/net` | 41 | present |
| `services/netcfg` | 45 | present |
| `services/notify` | — | real service, no README — gap named for Pax |
| `services/registry` | 50 | present |
| `services/session` | 50 | present |
| `services/settings` | — | real service, no README — gap named for Pax |
| `services/shell` | 31 | present |
| `services/socket` | 53 | present |
| `services/sockets` | 50 | present |
| `services/storage` | 50 | present |
| `services/supervisor` | 228 | present |
| `services/tests` | 37 | present |
| `services/time` | 97 | present |
| `services/timesync` | 50 | present |
| `services/updater` | 47 | present |
| `services/updater_client` | — | real service, no README — gap named for Pax |
| `services/wallpaper` | — | real service, no README — gap named for Pax |
| `services/watchdog` | 90 | present |

## What this does not claim

A README's presence is not a review of its contents. The 29 that exist were checked for
size and read where this lane needed them; they were not edited in this pass. The seven
real services without one (board, dashboard, dock, notify, settings, updater_client,
wallpaper) are documentation debt, named here so the next lane can pay it.
