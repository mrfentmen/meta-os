# Round 12, Section D — services, second ring

Method: for every service directory under `services/` (excluding `tests/`, `common/`, `build/`
and `hello/`, leaving the 38 service directories), this record lists the README, the native
driver(s) that import it, their measured result, the failure-specific driver if one exists, and
the restart result. Native numbers: `os-build/layer1/run_native.sh` on this branch tip,
**86 programs, 86 RUNS, 0 FAILS, 5 built-not-run, 3,804 assertions passed**.

**Restart is tested only where a host can start the service.** Three of the 38 directories have a
runnable `main` (echo, heartbeat, mcp-host). Echo, heartbeat and mcp-host were killed and restarted with
state behaviour recorded (`RESTART_PROOF.json`). The other 35 cannot be started by
`services/supervisor.sh` at all and are filed in `RESTART_GAP.md`.

**The audit is mechanical plus a file read.** It checks README presence, the manifest's own status
word, and whether a driver imports the service; the service's header/status comment was read for
the NOT BUILT rows. It is not a line-by-line contract-vs-code read; that remainder is named as
owed, not claimed.

## Cluster 1 — services 1–5

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `agenthost` | yes | WRITTEN | `tests/t104_agenthost_r11`, `tests/t59_agenthost`, `tests/t79_limit_drivers`, `tests/t97_agent_surface` (193p/0f) | `tests/t79_limit_drivers` | NOT TESTED (no host supervisor) | contract read still owed |
| `audit` | yes | WRITTEN | `tests/t105_audit_r11`, `tests/t60_audit`, `tests/t74_failure`, `tests/t76_demo_session` (109p/0f) | `tests/t74_failure` | NOT TESTED (no host supervisor) | contract read still owed |
| `board` | yes | WRITTEN | `tests/t106_board_r11`, `tests/t91_board`, `tests/t93_face_walkthrough`, `tests/t94_face_failures` (248p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `bootlog` | yes | WRITTEN | `tests/t107_bootlog_r11`, `tests/t49_bootlog` (39p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |
| `callmatrix` | yes | WRITTEN | `tests/t109_callmatrix_r11`, `tests/t69_callmatrix` (60p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |

## Cluster 2 — services 6–10

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `console` | yes | WRITTEN | `tests/t103_limits_rest`, `tests/t110_console_r11`, `tests/t49_bootlog`, `tests/t80_limit_drivers2` (88p/0f) | `tests/t103_limits_rest` | NOT TESTED (no host supervisor) | contract read still owed |
| `dashboard` | yes | WRITTEN | `tests/t111_dashboard_r11`, `tests/t89_dashboard`, `tests/t93_face_walkthrough`, `tests/t94_face_failures` (236p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `devices` | yes | WRITTEN | `tests/t112_devices_r11`, `tests/t77_gaps` (117p/0f) | `tests/t77_gaps` | NOT TESTED (no host supervisor) | contract read still owed |
| `devmgr` | yes | NOT BUILT | none | untested | NOT TESTED (no host supervisor) | manifest: NOT BUILT; no native driver; no failure-specific driver |
| `dhcp` | yes | WRITTEN | `tests/t114_dhcp_r11`, `tests/t57_dhcp_dns` (86p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |

## Cluster 3 — services 11–15

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `display` | yes | WRITTEN | `tests/t103_limits_rest`, `tests/t56_input_display`, `tests/t79_limit_drivers` (102p/0f) | `tests/t103_limits_rest` | NOT TESTED (no host supervisor) | contract read still owed |
| `dns` | yes | WRITTEN | `tests/t116_dns_r11`, `tests/t57_dhcp_dns`, `tests/t79_limit_drivers` (137p/0f) | `tests/t79_limit_drivers` | NOT TESTED (no host supervisor) | contract read still owed |
| `dock` | yes | WRITTEN | `tests/t117_dock_r11`, `tests/t88_dock`, `tests/t93_face_walkthrough`, `tests/t94_face_failures` (279p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `echo` | yes | WRITTEN | none | untested | PASS — killed/restarted (`RESTART_PROOF.json`) | no native driver; no failure-specific driver |
| `example` | yes | WRITTEN | none | untested | NOT TESTED (no host supervisor) | no native driver; no failure-specific driver |

## Cluster 4 — services 16–20

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `fs` | yes | WRITTEN | `tests/t119_fs_r11`, `tests/t131_shell_r11`, `tests/t65_fs`, `tests/t66_shell`, `tests/t74_failure`, `tests/t76_demo_session`, `tests/t80_limit_drivers2`, `tests/t82_fs_deep` (317p/0f) | `tests/t74_failure` | NOT TESTED (no host supervisor) | contract read still owed |
| `heartbeat` | yes | WRITTEN | none | untested | PASS — killed/restarted (`RESTART_PROOF.json`) | no native driver; no failure-specific driver |
| `input` | yes | WRITTEN | `tests/t102_keycompose`, `tests/t121_input_r11`, `tests/t56_input_display` (120p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |
| `logd` | yes | WRITTEN | `tests/t122_logd_r11`, `tests/t50_logd`, `tests/t71_rotate`, `tests/t74_failure`, `tests/t76_demo_session`, `tests/t81_logd_deep` (165p/0f) | `tests/t74_failure` | NOT TESTED (no host supervisor) | contract read still owed |
| `logfmt` | yes | WRITTEN | `tests/t123_logfmt_r11`, `tests/t50_logd`, `tests/t96_logfmt` (94p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |

## Cluster 5 — services 21–25

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `mcp-host` | yes | WRITTEN | none | untested | PASS — killed/restarted (`RESTART_PROOF.json`) | no native driver; no failure-specific driver |
| `net` | yes | WRITTEN | `tests/t101_netaddr`, `tests/t125_net_r11`, `tests/t67_net`, `tests/t68_proto`, `tests/t85_net_deep` (373p/0f) | `tests/t85_net_deep` | NOT TESTED (no host supervisor) | contract read still owed |
| `netcfg` | yes | WRITTEN | `tests/t101_netaddr`, `tests/t114_dhcp_r11`, `tests/t116_dns_r11`, `tests/t125_net_r11`, `tests/t126_netcfg_r11`, `tests/t57_dhcp_dns`, `tests/t67_net`, `tests/t68_proto`, `tests/t77_gaps`, `tests/t79_limit_drivers`, `tests/t80_limit_drivers2`, `tests/t85_net_deep` (715p/0f) | `tests/t77_gaps` | NOT TESTED (no host supervisor) | contract read still owed |
| `notify` | yes | WRITTEN | `tests/t127_notify_r11`, `tests/t95_notify` (125p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |
| `registry` | yes | NOT BUILT | none | untested | NOT TESTED (no host supervisor) | manifest: NOT BUILT; no native driver; no failure-specific driver |

## Cluster 6 — services 26–30

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `session` | yes | WRITTEN | `tests/t129_session_r11`, `tests/t77_gaps`, `tests/t79_limit_drivers`, `tests/t84_session_deep` (269p/0f) | `tests/t77_gaps` | NOT TESTED (no host supervisor) | contract read still owed |
| `settings` | yes | WRITTEN | `tests/t130_settings_r11`, `tests/t86_settings`, `tests/t93_face_walkthrough`, `tests/t94_face_failures` (251p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `shell` | yes | WRITTEN | `tests/t131_shell_r11`, `tests/t66_shell`, `tests/t76_demo_session`, `tests/t80_limit_drivers2` (135p/0f) | `tests/t80_limit_drivers2` | NOT TESTED (no host supervisor) | contract read still owed |
| `socket` | yes | WRITTEN | `tests/t103_limits_rest`, `tests/t77_gaps`, `tests/t79_limit_drivers` (126p/0f) | `tests/t103_limits_rest` | NOT TESTED (no host supervisor) | contract read still owed |
| `sockets` | yes | NOT BUILT | none | untested | NOT TESTED (no host supervisor) | manifest: NOT BUILT; no native driver; no failure-specific driver |

## Cluster 7 — services 31–35

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `storage` | yes | WRITTEN | `tests/t134_storage_r11`, `tests/t54_storage`, `tests/t74_failure`, `tests/t82_fs_deep` (125p/0f) | `tests/t74_failure` | NOT TESTED (no host supervisor) | contract read still owed |
| `supervisor` | yes | WRITTEN | `tests/t135_supervisor_r11`, `tests/t52_supervisor`, `tests/t61_bootorder`, `tests/t66_shell`, `tests/t75_supervisor_load`, `tests/t76_demo_session`, `tests/t83_sup_deep`, `tests/t92_sup_load` (415p/0f) | `tests/t75_supervisor_load` | NOT TESTED (no host supervisor) | contract read still owed |
| `time` | yes | WRITTEN | `tests/t136_time_r11`, `tests/t51_time`, `tests/t99_calendar` (101p/0f) | driver only | NOT TESTED (no host supervisor) | no failure-specific driver |
| `timesync` | yes | WRITTEN | `tests/t137_timesync_r11`, `tests/t77_gaps`, `tests/t80_limit_drivers2` (129p/0f) | `tests/t77_gaps` | NOT TESTED (no host supervisor) | contract read still owed |
| `updater` | yes | WRITTEN | `tests/t103_limits_rest`, `tests/t138_updater_r11`, `tests/t58_updater`, `tests/t79_limit_drivers`, `tests/t80_limit_drivers2`, `tests/t98_delta` (194p/0f) | `tests/t103_limits_rest` | NOT TESTED (no host supervisor) | contract read still owed |

## Cluster 8 — services 36–38

| service | README | manifest | drivers (measured) | failure path | restart | gaps |
|---|---|---|---|---|---|---|
| `updater_client` | yes | WRITTEN | `tests/t139_updater_client_r11`, `tests/t90_updater_client`, `tests/t94_face_failures` (201p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `wallpaper` | yes | WRITTEN | `tests/t87_wallpaper`, `tests/t93_face_walkthrough`, `tests/t94_face_failures` (207p/0f) | `tests/t94_face_failures` | NOT TESTED (no host supervisor) | contract read still owed |
| `watchdog` | yes | WRITTEN | `tests/t53_watchdog`, `tests/t78_lib_limits`, `tests/t79_limit_drivers` (97p/0f) | `tests/t78_lib_limits` | NOT TESTED (no host supervisor) | contract read still owed |

## Summary (R12-035)

- services inventoried: **38**
- with a README: **38**; without: **0**
- with at least one measured native driver: **31**; without: **7**
- manifest NOT BUILT: **3** (`devmgr`, `registry`, `sockets`)
- assertions attributed through those drivers: **5853 passed, 0 failed**
- failure-path tested by a dedicated driver: **24**; driver-only: **7**; untested: **7**
- restart tested: **3 of 38** (echo, heartbeat, mcp-host). **35 have no runnable `main`**
  (`RESTART_GAP.md`).

**Named untested:** every restart cell above; every service row whose driver column says none;
the failure path of every row that says "driver only"; and the contract-vs-code read for every
row (the mechanical check is not that read).
