# Whole-corpus numbers and the status table (A3)

> Counts in this file are as of the round it records. Live numbers: `COUNTS.md`.

Measured 2026-11-02 on `buffy/layer1-goose-services`, once, with `services/root.goose`
in place. Regenerate this file with `python3 os-build/layer1/gen_finish_status.py`.

## The two headline numbers

| Measurement | Value | Command that produces it |
|---|---|---|
| `goose check`, full corpus incl. `services/root.goose` | **54 ok, 0 failed** | `./os-build/layer1/check_services.sh` |
| Native drivers that build and run to exit 0 | **48 of 48, 2172 assertions, 0 failed** | `./os-build/layer1/run_native.sh` |
| Entry programs that build but are not run | 5 (no supervisor to call `svc_entry`) | same run |

The typecheck command exited 0.

## Every service, one row

| Service | Entry point | Driver | Status word | Checks | ABI class |
|---|---|---|---|---|---|
| `agenthost` | no entry | `tests/t59_agenthost` | **RUNS** | 48 | library (no kernel calls) |
| `audit` | no entry | `tests/t60_audit` | **RUNS** | 33 | library (no kernel calls) |
| `board` | no entry | `tests/t91_board` | **RUNS** | 58 | library (no kernel calls) |
| `bootlog` | BUILDS (not run) | `tests/t49_bootlog` | **RUNS** | 23 | needs a proposal |
| `callmatrix` | no entry | `tests/t69_callmatrix` | **RUNS** | 31 | library (no kernel calls) |
| `console` | BUILDS (not run) | `tests/t80_limit_drivers2` | **RUNS** | 30 | needs a proposal |
| `dashboard` | no entry | `tests/t89_dashboard` | **RUNS** | 50 | library (no kernel calls) |
| `devices` | no entry | `tests/t77_gaps` | **RUNS** | 73 | library (no kernel calls) |
| `dhcp` | no entry | `tests/t57_dhcp_dns` | **RUNS** | 45 | library (no kernel calls) |
| `display` | no entry | `tests/t56_input_display` | **RUNS** | 49 | needs a proposal |
| `dns` | no entry | `tests/t57_dhcp_dns` | **RUNS** | 45 | library (no kernel calls) |
| `dock` | no entry | `tests/t88_dock` | **RUNS** | 61 | library (no kernel calls) |
| `fs` | no entry | `tests/t65_fs` | **RUNS** | 75 | library (no kernel calls) |
| `input` | no entry | `tests/t56_input_display` | **RUNS** | 49 | library (no kernel calls) |
| `logd` | BUILDS (not run) | `tests/t81_logd_deep` | **RUNS** | 24 | needs a proposal |
| `logfmt` | no entry | `tests/t50_logd` | **RUNS** | 19 | library (no kernel calls) |
| `net` | no entry | `tests/t85_net_deep` | **RUNS** | 154 | needs a proposal |
| `netcfg` | no entry | `tests/t85_net_deep` | **RUNS** | 154 | library (no kernel calls) |
| `session` | no entry | `tests/t84_session_deep` | **RUNS** | 106 | library (no kernel calls) |
| `settings` | no entry | `tests/t86_settings` | **RUNS** | 67 | library (no kernel calls) |
| `shell` | no entry | `tests/t66_shell` | **RUNS** | 57 | needs a proposal |
| `socket` | no entry | `tests/t77_gaps` | **RUNS** | 73 | library (no kernel calls) |
| `storage` | no entry | `tests/t54_storage` | **RUNS** | 26 | library (no kernel calls) |
| `supervisor` | no entry | `tests/t52_supervisor` | **RUNS** | 53 | library (no kernel calls) |
| `time` | BUILDS (not run) | `tests/t51_time` | **RUNS** | 24 | needs a proposal |
| `timesync` | no entry | `tests/t77_gaps` | **RUNS** | 73 | library (no kernel calls) |
| `updater` | no entry | `tests/t90_updater_client` | **RUNS** | 62 | library (no kernel calls) |
| `updater_client` | no entry | `tests/t90_updater_client` | **RUNS** | 62 | library (no kernel calls) |
| `wallpaper` | no entry | `tests/t87_wallpaper` | **RUNS** | 56 | library (no kernel calls) |
| `watchdog` | no entry | `tests/t53_watchdog` | **RUNS** | 28 | library (no kernel calls) |
| `example` | TYPECHECKS (not run) | — | TYPECHECKS | — | needs a proposal |

## Counted, not summarised

| Status word | Services | What it covers |
|---|---|---|
| **RUNS** | 30 | a driver builds, executes and exits 0 |
| TYPECHECKS | 1 | an entry point builds (or typechecks) but no driver runs it |
| NEITHER | 0 | no driver and no entry point |

A service that `RUNS` is also `TYPECHECKS` (the driver is typechecked too); the rows
above give each service its strongest true word, so the three counts add to 31.

## What this table cannot tell you

- `RUNS` means a host process ran the service's own code against the host shim's ten
  `sys_*` calls. No kernel, no scheduler, no address space. Five shim calls refuse on
  purpose: `sys_spawn`, `sys_kill`, `sys_net_send`, `sys_net_recv`, `sys_read_key`.
- `TYPECHECKS` is a compiler accepting the source. It is not execution, and it is not a
  claim that the service would start if something called `svc_entry`.
- `NEITHER` is the honest word for code that exists and has never been given a caller.
